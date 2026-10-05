from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.schemas import (
    AsesorCarteraComparativo,
    CarteraDiariaAsesor,
    CarteraIndicadores,
    ResumenCarteraComparativo,
    ResumenCarteraSnapshot,
    ResumenDiarioCarteraAsesoresResponse,
)


def _numero(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _codigo_asesor(documento: dict[str, Any]) -> str:
    valor = (
        documento.get("CodigoUsuario")
        or documento.get("CodigoAsesor")
        or documento.get("CODIGOUSUARIO")
    )
    return str(valor or "SIN_CODIGO").strip() or "SIN_CODIGO"


def _numero_prestamo(documento: dict[str, Any]) -> str | None:
    valor = documento.get("NumeroPrestamo")
    if valor is None:
        return None
    numero = str(valor).strip()
    return numero or None


def _indexar_prestamos(
    documentos: list[dict[str, Any]],
    *,
    corte: str,
) -> dict[str, dict[str, Any]]:
    """Indexa cada corte por NumeroPrestamo para alinear préstamos reasignados."""
    prestamos: dict[str, dict[str, Any]] = {}
    for indice, documento in enumerate(documentos):
        numero = _numero_prestamo(documento)
        clave = numero if numero is not None else f"{corte}:SIN_NUMERO:{indice}"
        prestamos.setdefault(clave, documento)
    return prestamos


def _emparejar_prestamos(
    prestamos_hoy: dict[str, dict[str, Any]],
    prestamos_ayer: dict[str, dict[str, Any]],
) -> list[tuple[str, dict[str, Any] | None, dict[str, Any] | None]]:
    """Alinea los dos cortes por NumeroPrestamo, incluso si cambió su asesor."""
    numeros = list(prestamos_hoy)
    numeros.extend(numero for numero in prestamos_ayer if numero not in prestamos_hoy)
    return [
        (numero, prestamos_hoy.get(numero), prestamos_ayer.get(numero))
        for numero in numeros
    ]


class ResumenDiarioCarteraService:
    def __init__(self, sql_repository: Any, mongo_repository: Any) -> None:
        self.sql_repository = sql_repository
        self.mongo_repository = mongo_repository

    def obtener(
        self,
        *,
        id_agencia: int,
        auth_context: AuthContext,
    ) -> ResumenDiarioCarteraAsesoresResponse:
        agencia = self.sql_repository.obtener_nombre_agencia(id_agencia)
        if not agencia:
            raise HTTPException(status_code=404, detail="La agencia no existe.")
        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        fecha_ayer = fecha - timedelta(days=1)
        cortes = self.mongo_repository.obtener_snapshots_por_agencia(
            agencia=agencia,
            fecha_corte_ayer=fecha_ayer.strftime("%Y%m%d"),
        )

        prestamos_hoy = _indexar_prestamos(cortes.get("hoy", []), corte="hoy")
        prestamos_ayer = _indexar_prestamos(cortes.get("ayer", []), corte="ayer")
        emparejados = _emparejar_prestamos(prestamos_hoy, prestamos_ayer)
        documentos_hoy = [
            prestamo_hoy
            for _, prestamo_hoy, _ in emparejados
            if prestamo_hoy is not None
        ]
        documentos_ayer = [
            prestamo_ayer
            for _, _, prestamo_ayer in emparejados
            if prestamo_ayer is not None
        ]
        hoy = self._construir_snapshot(fecha, documentos_hoy)
        ayer = (
            self._construir_snapshot(fecha_ayer, documentos_ayer)
            if documentos_ayer
            else None
        )
        return ResumenDiarioCarteraAsesoresResponse(
            fecha=fecha,
            fecha_ayer=fecha_ayer,
            id_agencia=id_agencia,
            agencia=agencia,
            resumen=ResumenCarteraComparativo(
                hoy=self._indicadores(hoy),
                ayer=self._indicadores(ayer) if ayer else None,
                cambio=self._diferencia(hoy, ayer) if ayer else None,
            ),
            asesores=self._asesores_comparativos(hoy, ayer),
        )

    @staticmethod
    def _construir_snapshot(
        fecha: date,
        documentos: list[dict[str, Any]],
    ) -> ResumenCarteraSnapshot:
        por_asesor: dict[str, dict[str, Any]] = {}
        operaciones = 0
        creditos_en_mora = 0
        creditos_dias_vencidos_1 = 0
        saldo_capital = 0.0
        provision_requerida = 0.0
        capital_no_devenga = 0.0
        capital_vencido = 0.0

        for documento in documentos:
            saldo = _numero(documento.get("SaldoCapital"))
            provision = _numero(documento.get("ProvisionRequerida"))
            no_devenga = _numero(documento.get("CapitalNoDevenga"))
            vencido = _numero(documento.get("CapitalVencido"))
            try:
                dias_vencidos = int(documento.get("DiasVencidos") or 0)
            except (TypeError, ValueError):
                dias_vencidos = 0

            operaciones += 1
            creditos_en_mora += int(dias_vencidos > 0)
            creditos_dias_vencidos_1 += int(1 <= dias_vencidos <= 5)
            saldo_capital += saldo
            provision_requerida += provision
            capital_no_devenga += no_devenga
            capital_vencido += vencido

            codigo = _codigo_asesor(documento)
            asesor = por_asesor.setdefault(
                codigo,
                {
                    "asesor": str(
                        documento.get("NombreAsesor")
                        or documento.get("NombreCompleto")
                        or codigo
                    ),
                    "operaciones": 0,
                    "creditos_en_mora": 0,
                    "creditos_dias_vencidos_1": 0,
                    "saldo_capital": 0.0,
                    "provision_requerida": 0.0,
                    "capital_no_devenga": 0.0,
                    "capital_vencido": 0.0,
                },
            )
            asesor["operaciones"] += 1
            asesor["creditos_en_mora"] += int(dias_vencidos > 0)
            asesor["creditos_dias_vencidos_1"] += int(1 <= dias_vencidos <= 5)
            asesor["saldo_capital"] += saldo
            asesor["provision_requerida"] += provision
            asesor["capital_no_devenga"] += no_devenga
            asesor["capital_vencido"] += vencido

        asesores = [
            _construir_asesor(codigo, datos)
            for codigo, datos in sorted(
                por_asesor.items(),
                key=lambda item: (-item[1]["saldo_capital"], item[1]["asesor"]),
            )
        ]
        mora_total = capital_no_devenga + capital_vencido
        return ResumenCarteraSnapshot(
            fecha=fecha,
            operaciones=operaciones,
            creditos_en_mora=creditos_en_mora,
            creditos_dias_vencidos_1=creditos_dias_vencidos_1,
            saldo_capital=round(saldo_capital, 2),
            provision_requerida=round(provision_requerida, 2),
            morosidad_monto=round(mora_total, 2),
            morosidad_porcentaje=(
                round(mora_total / saldo_capital * 100, 2) if saldo_capital else 0.0
            ),
            asesores=asesores,
        )

    @staticmethod
    def _indicadores(origen: Any) -> CarteraIndicadores:
        return CarteraIndicadores(
            operaciones=origen.operaciones,
            creditos_en_mora=origen.creditos_en_mora,
            creditos_dias_vencidos_1=origen.creditos_dias_vencidos_1,
            saldo_capital=origen.saldo_capital,
            provision_requerida=origen.provision_requerida,
            morosidad_monto=origen.morosidad_monto,
            morosidad_porcentaje=origen.morosidad_porcentaje,
        )

    @staticmethod
    def _diferencia(hoy: Any, ayer: Any) -> CarteraIndicadores:
        return CarteraIndicadores(
            operaciones=hoy.operaciones - ayer.operaciones,
            creditos_en_mora=hoy.creditos_en_mora - ayer.creditos_en_mora,
            creditos_dias_vencidos_1=(
                hoy.creditos_dias_vencidos_1 - ayer.creditos_dias_vencidos_1
            ),
            saldo_capital=round(hoy.saldo_capital - ayer.saldo_capital, 2),
            provision_requerida=round(
                hoy.provision_requerida - ayer.provision_requerida, 2
            ),
            morosidad_monto=round(hoy.morosidad_monto - ayer.morosidad_monto, 2),
            morosidad_porcentaje=round(
                hoy.morosidad_porcentaje - ayer.morosidad_porcentaje, 2
            ),
        )

    @classmethod
    def _asesores_comparativos(
        cls,
        hoy: ResumenCarteraSnapshot,
        ayer: ResumenCarteraSnapshot | None,
    ) -> list[AsesorCarteraComparativo]:
        hoy_por_codigo = {asesor.codigo_usuario: asesor for asesor in hoy.asesores}
        ayer_por_codigo = {asesor.codigo_usuario: asesor for asesor in ayer.asesores} if ayer else {}
        codigos = list(hoy_por_codigo)
        codigos.extend(codigo for codigo in ayer_por_codigo if codigo not in hoy_por_codigo)

        resultado: list[AsesorCarteraComparativo] = []
        for codigo in codigos:
            asesor_hoy = hoy_por_codigo.get(codigo)
            asesor_ayer = ayer_por_codigo.get(codigo)
            nombre = (asesor_hoy or asesor_ayer).asesor
            if ayer is not None and asesor_hoy is None:
                asesor_hoy = _asesor_vacio(codigo, nombre)
            if ayer is not None and asesor_ayer is None:
                asesor_ayer = _asesor_vacio(codigo, nombre)
            resultado.append(
                AsesorCarteraComparativo(
                    codigo_usuario=codigo,
                    asesor=nombre,
                    hoy=cls._indicadores(asesor_hoy),
                    ayer=cls._indicadores(asesor_ayer) if asesor_ayer else None,
                    cambio=(
                        cls._diferencia(asesor_hoy, asesor_ayer)
                        if asesor_hoy and asesor_ayer
                        else None
                    ),
                )
            )
        return resultado


def _construir_asesor(codigo: str, datos: dict[str, Any]) -> CarteraDiariaAsesor:
    saldo = _numero(datos.get("saldo_capital"))
    mora = _numero(datos.get("capital_no_devenga")) + _numero(
        datos.get("capital_vencido")
    )
    return CarteraDiariaAsesor(
        codigo_usuario=codigo,
        asesor=datos["asesor"],
        operaciones=int(datos["operaciones"]),
        creditos_en_mora=int(datos["creditos_en_mora"]),
        creditos_dias_vencidos_1=int(datos["creditos_dias_vencidos_1"]),
        saldo_capital=round(saldo, 2),
        provision_requerida=round(_numero(datos.get("provision_requerida")), 2),
        morosidad_monto=round(mora, 2),
        morosidad_porcentaje=round(mora / saldo * 100, 2) if saldo else 0.0,
    )


def _asesor_vacio(codigo: str, nombre: str) -> CarteraDiariaAsesor:
    return CarteraDiariaAsesor(
        codigo_usuario=codigo,
        asesor=nombre,
        operaciones=0,
        creditos_en_mora=0,
        creditos_dias_vencidos_1=0,
        saldo_capital=0,
        provision_requerida=0,
        morosidad_monto=0,
        morosidad_porcentaje=0,
    )
