from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.schemas import (
    ComparativaCuentasResponse, ConsultaComparativaCuentas,
    ComparativaAnualMesesResponse, ConsultaComparativaAnualMeses,
)
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS


class ComparativaCuentasService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: ConsultaComparativaCuentas | ConsultaComparativaAnualMeses) -> ComparativaCuentasResponse:
        if isinstance(consulta, ConsultaComparativaAnualMeses):
            mes_inicio = f"{consulta.anio_inicio:04}-01"
            fechas = self._fechas_mensuales(mes_inicio, consulta.fecha_corte)
        elif consulta.periodicidad == "diaria":
            fechas = [consulta.fecha_inicio + timedelta(days=i)
                      for i in range((consulta.fecha_corte - consulta.fecha_inicio).days + 1)]
            mes_inicio = fechas[0].strftime("%Y-%m")
        elif consulta.periodicidad == "anual":
            fechas = [date(anio, consulta.fecha_corte.month,
                           min(consulta.fecha_corte.day, monthrange(anio, consulta.fecha_corte.month)[1]))
                      for anio in range(consulta.anio_inicio, consulta.fecha_corte.year + 1)]
            mes_inicio = fechas[0].strftime("%Y-%m")
        else:
            fechas = self._fechas_mensuales(consulta.mes_inicio, consulta.fecha_corte)
            mes_inicio = consulta.mes_inicio
        return self._comparar(consulta, fechas, mes_inicio)

    @staticmethod
    def _fechas_mensuales(mes_inicio: str, fecha_corte: date) -> list[date]:
        inicio = date.fromisoformat(f"{mes_inicio}-01")
        cantidad = (fecha_corte.year - inicio.year) * 12 + fecha_corte.month - inicio.month + 1
        fechas = []
        for desplazamiento in range(cantidad):
            anio, mes_cero = divmod(inicio.year * 12 + inicio.month - 1 + desplazamiento, 12)
            dia = min(fecha_corte.day, monthrange(anio, mes_cero + 1)[1])
            fechas.append(date(anio, mes_cero + 1, dia))

        return fechas

    def _comparar(self, consulta: ConsultaComparativaCuentas | ConsultaComparativaAnualMeses, fechas: list[date], mes_inicio: str) -> ComparativaCuentasResponse:
        anual_meses = isinstance(consulta, ConsultaComparativaAnualMeses)
        fechas_anteriores = [date(f.year - 1, f.month,
                                 min(consulta.fecha_corte.day, monthrange(f.year - 1, f.month)[1]))
                            for f in fechas] if anual_meses else []
        id_contable = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        agencia = self.repository.obtener_agencia(id_contable)
        if agencia is None:
            raise HTTPException(status_code=404, detail="Agencia no encontrada.")
        catalogo = self.repository.obtener_cuentas(agencia["id_empresa"])
        parametros = dict(fechas=sorted(set(fechas + fechas_anteriores)), id_agencia=id_contable, id_empresa=agencia["id_empresa"])
        if consulta.periodicidad == "diaria":
            parametros["rango_continuo"] = True
        filas = self.repository.obtener_saldos(**parametros)
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
        cobertura = {fecha: 0 for fecha in fechas + fechas_anteriores}
        for cuenta in catalogo:
            if not cuenta["activa"]:
                continue
            codigo = cuenta["codigo_cuenta"]
            ajuste = MAPA_NETEO_CUENTAS.get(codigo) if consulta.neteo else None
            valores = []
            anterior = None

            def obtener_valor(fecha: date) -> Decimal | None:
                saldo = saldos.get((fecha, codigo))
                if saldo is not None:
                    if ajuste:
                        saldo_ajuste = saldos.get((fecha, ajuste), Decimal("0.00"))
                        if saldo_ajuste is None:
                            return None
                        saldo -= saldo_ajuste
                    saldo = saldo.quantize(Decimal("0.01"))
                return saldo

            # Contar cada fecha una vez aunque sea base de otro año del intervalo.
            valores_por_fecha = {fecha: obtener_valor(fecha) for fecha in cobertura}
            for fecha, saldo in valores_por_fecha.items():
                if saldo is not None:
                    cobertura[fecha] += 1

            for i, fecha in enumerate(fechas):
                saldo = valores_por_fecha[fecha]
                if anual_meses:
                    anterior = valores_por_fecha[fechas_anteriores[i]]
                variacion = saldo - anterior if saldo is not None and anterior is not None else None
                valor = dict(periodo=(fecha.isoformat() if consulta.periodicidad == "diaria" else fecha.strftime("%Y-%m")), saldo=saldo, variacion_absoluta=variacion)
                if anual_meses:
                    valor["saldo_anterior"] = anterior
                valores.append(valor)
                # Una ausencia interrumpe la comparación; no se salta al último saldo disponible.
                anterior = saldo
            cuentas.append({**cuenta, "nivel": nivel(codigo), "valores": valores})

        periodos = []
        for i, fecha in enumerate(fechas):
            periodo = dict(periodo=(fecha.isoformat() if consulta.periodicidad == "diaria" else fecha.strftime("%Y-%m")),
                           fecha=fecha, fecha_ajustada=consulta.periodicidad != "diaria" and fecha.day != consulta.fecha_corte.day,
                           cuentas_con_datos=cobertura[fecha])
            if anual_meses:
                fecha_anterior = fechas_anteriores[i]
                periodo.update(fecha_anterior=fecha_anterior,
                               fecha_anterior_ajustada=fecha_anterior.day != consulta.fecha_corte.day,
                               cuentas_con_datos_anterior=cobertura[fecha_anterior])
            periodos.append(periodo)

        response_model = ComparativaAnualMesesResponse if anual_meses else ComparativaCuentasResponse
        return response_model(
            mes_inicio=mes_inicio, fecha_corte=consulta.fecha_corte,
            id_agencia=consulta.id_agencia, id_agencia_contable=id_contable,
            nombre_agencia=agencia["nombre"], neteo=consulta.neteo, total_cuentas=len(cuentas),
            periodos=periodos,
            cuentas=cuentas,
        )
