from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import HTTPException

from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.schemas import (
    ComparativaCuentasResponse, ConsultaComparativaCuentas,
)
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS


class ComparativaCuentasService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: ConsultaComparativaCuentas) -> ComparativaCuentasResponse:
        inicio = date.fromisoformat(f"{consulta.mes_inicio}-01")
        cantidad = (consulta.fecha_corte.year - inicio.year) * 12 + consulta.fecha_corte.month - inicio.month + 1
        fechas = []
        for desplazamiento in range(cantidad):
            anio, mes_cero = divmod(inicio.year * 12 + inicio.month - 1 + desplazamiento, 12)
            dia = min(consulta.fecha_corte.day, monthrange(anio, mes_cero + 1)[1])
            fechas.append(date(anio, mes_cero + 1, dia))

        id_contable = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        agencia = self.repository.obtener_agencia(id_contable)
        if agencia is None:
            raise HTTPException(status_code=404, detail="Agencia no encontrada.")
        catalogo = self.repository.obtener_cuentas(agencia["id_empresa"])
        filas = self.repository.obtener_saldos(
            fechas=fechas, id_agencia=id_contable, id_empresa=agencia["id_empresa"],
        )
        saldos = {(fila["fecha"], fila["codigo_cuenta"]): fila["saldo"] for fila in filas}
        padres = {c["codigo_cuenta"]: c["codigo_padre"] for c in catalogo}

        def nivel(codigo: str) -> int:
            visitados = {codigo}
            padre = padres.get(codigo)
            while padre in padres and padre not in visitados:
                visitados.add(padre)
                padre = padres.get(padre)
            return len(visitados)

        cuentas = []
        cobertura = {fecha: 0 for fecha in fechas}
        for cuenta in catalogo:
            if not cuenta["activa"]:
                continue
            codigo = cuenta["codigo_cuenta"]
            ajuste = MAPA_NETEO_CUENTAS.get(codigo) if consulta.neteo else None
            valores = []
            anterior = None
            for fecha in fechas:
                saldo = saldos.get((fecha, codigo))
                if saldo is not None:
                    if ajuste:
                        saldo -= saldos.get((fecha, ajuste), Decimal("0.00"))
                    saldo = saldo.quantize(Decimal("0.01"))
                    cobertura[fecha] += 1
                variacion = saldo - anterior if saldo is not None and anterior is not None else None
                valores.append(dict(periodo=fecha.strftime("%Y-%m"), saldo=saldo, variacion_absoluta=variacion))
                # Una ausencia interrumpe la comparación; no se salta al último saldo disponible.
                anterior = saldo
            cuentas.append({**cuenta, "nivel": nivel(codigo), "valores": valores})

        return ComparativaCuentasResponse(
            mes_inicio=consulta.mes_inicio, fecha_corte=consulta.fecha_corte,
            id_agencia=consulta.id_agencia, id_agencia_contable=id_contable,
            nombre_agencia=agencia["nombre"], neteo=consulta.neteo, total_cuentas=len(cuentas),
            periodos=[dict(periodo=f.strftime("%Y-%m"), fecha=f,
                           fecha_ajustada=f.day != consulta.fecha_corte.day,
                           cuentas_con_datos=cobertura[f]) for f in fechas],
            cuentas=cuentas,
        )
