from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.repositories.sql_depositos_y_retiros_diarios_repository import (
    DeadlockDiarioError,
    SqlDepositosYRetirosDiariosRepository,
)
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.schemas import (
    DepositosYRetirosDia,
    DepositosYRetirosDiariosFila,
    DepositosYRetirosDiariosRequest,
    DepositosYRetirosDiariosResponse,
    TransaccionAhorroVistaDia,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)


class DepositosYRetirosDiariosService:
    def __init__(
        self, repository: SqlDepositosYRetirosDiariosRepository,
        catalogo: SqlSituacionCrediticiaAsesoresRepository,
    ) -> None:
        self.repository = repository
        self.catalogo = catalogo

    def obtener(
        self, body: DepositosYRetirosDiariosRequest, auth: AuthContext,
    ) -> DepositosYRetirosDiariosResponse:
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        if body.fecha_fin > fecha_sistema:
            raise HTTPException(400, "fecha_fin no puede superar la fecha del sistema.")
        if body.id_agencia and not self.catalogo.obtener_nombre_agencia(body.id_agencia):
            raise HTTPException(404, "La agencia no existe.")
        try:
            corte = self.repository.obtener_diario(**body.model_dump(), fecha_sistema=fecha_sistema)
        except DeadlockDiarioError as error:
            raise HTTPException(
                503, "No se pudo completar la consulta por un conflicto temporal de bloqueos. Intente nuevamente.",
                headers={"Retry-After": "2"},
            ) from error
        if corte is None:
            raise HTTPException(404, f"No existe un corte de ahorros a la vista disponible para {body.fecha_fin}.")

        dias = [
            body.fecha_inicio + timedelta(days=i)
            for i in range((body.fecha_fin - body.fecha_inicio).days + 1)
        ]
        grupos: dict[tuple[str, int, str], DepositosYRetirosDiariosFila] = {}
        montos: dict[tuple[str, int, str], list[dict[tuple[int, bool], Decimal]]] = {}
        nombres_transacciones: dict[int, str] = {}
        for dato in corte.filas:
            fecha = dato["fecha"]
            if isinstance(fecha, datetime):
                fecha = fecha.date()
            if not body.fecha_inicio <= fecha <= min(body.fecha_fin, corte.fecha):
                continue
            clave = (str(dato["codigo_usuario"]), int(dato["id_agencia"]), str(dato["codigo_producto"]))
            if clave not in grupos:
                grupos[clave] = DepositosYRetirosDiariosFila(
                    codigo_usuario=clave[0], id_agencia=clave[1], codigo_producto=clave[2],
                    nombre_asesor=str(dato["nombre_asesor"]).strip(),
                    agencia=str(dato["agencia"]).strip().upper(),
                    producto_ahorro=str(dato["producto_ahorro"]).strip(), valores=[],
                )
                montos[clave] = [{} for _ in dias]
            valores = montos[clave][(fecha - body.fecha_inicio).days]
            id_transaccion = int(dato["id_transaccion"])
            nombres_transacciones[id_transaccion] = str(dato["tipo_transaccion"]).strip()
            for campo, es_debito in (("depositos", False), ("retiros", True)):
                monto = Decimal(str(dato[campo]))
                if monto > 0:
                    tipo = (id_transaccion, es_debito)
                    valores[tipo] = valores.get(tipo, Decimal(0)) + monto
        for clave, fila in grupos.items():
            fila.valores = [
                DepositosYRetirosDia(
                    depositos=float(sum((m for (_, debito), m in dia.items() if not debito), Decimal(0))),
                    retiros=float(sum((m for (_, debito), m in dia.items() if debito), Decimal(0))),
                    transacciones=[
                        TransaccionAhorroVistaDia(
                            id_transaccion=id_transaccion,
                            tipo_transaccion=nombres_transacciones[id_transaccion],
                            es_debito=es_debito, valor=float(monto.quantize(Decimal("0.01"))),
                        )
                        for (id_transaccion, es_debito), monto in sorted(dia.items())
                    ],
                )
                for dia in montos[clave]
            ]
        return DepositosYRetirosDiariosResponse(
            **body.model_dump(), fecha_corte=corte.fecha, dias=dias,
            filas=sorted(grupos.values(), key=lambda f: (
                f.agencia, f.nombre_asesor, f.codigo_usuario, f.codigo_producto,
            )),
        )
