# Resumen del balance de resultados

Pantalla: `/dashboard/analisis-contable/resumen-balance-de-resultados`.
Código Angular: `src/app/features/analisis-contable/resumen-balance-de-resultados`.

`POST /analytic/analisis-contable/resumen-balance-de-resultados` requiere Bearer.

```json
{
  "fecha_corte": "2026-11-10",
  "id_agencia": 0,
  "neteo": 1
}
```

El módulo del backend se encuentra en
`app/modules/analytic/analisis_contable/resumen_balance_de_resultados`, registrado
por el router de análisis contable. Usa `get_db` y el repositorio compartido
`app/modules/contabilidad/repositories/sql_resumen_contable_repository.py`, que
también consulta el Balance General. No hay consultas SQL en routers o servicios.

`id_agencia` vale `0` por defecto y consulta la agencia contable `1`, CONSOLIDADO;
los otros IDs consultan exclusivamente la agencia indicada. `neteo` acepta `0` o
`1` y por defecto está activado. Fecha exacta, signos, monedas y cierre anual
siguen las mismas reglas que el Balance General. Los saldos cero se conservan y
los saldos base ausentes producen `null` únicamente en sus indicadores dependientes.

La respuesta incluye los filtros, `id_agencia_contable`, `nombre_agencia`,
`cuentas_sin_saldo`, diez `indicadores`, cuatro `margenes` y `validacion_utilidad`.
Los importes se serializan como cadenas decimales o `null`.

| Indicador | Fórmula sin neteo |
| --- | --- |
| Gastos | 4 |
| Intereses Causados | 41 |
| Provisiones | 44 |
| Gasto Operativo | 45 |
| Ingresos | 5 |
| Intereses Ganados | 51 |
| Comisiones Ganadas | 52 |
| Utilidades Financieras | 53 |
| Margen de Intermediación | Margen Financiero Neto − 45 |
| Utilidad | 5 − 4 |

Los cuatro pasos del margen son:

1. Margen Neto de Intereses = 51 − 41.
2. Margen Bruto Financiero = Margen Neto de Intereses + 52 + 54 − 42 + 53 − 43.
3. Margen Financiero Neto = Margen Bruto Financiero − 44.
4. Margen de Intermediación = Margen Financiero Neto − 45.

El neteo reutiliza `MAPA_NETEO_CUENTAS`: se resta `41019005` de `4` y `41`, y
`51909005` de `5` y `51`, antes de todos los cálculos. Cada ajuste se aplica una
sola vez a la cuenta correspondiente. Un ajuste ausente se considera cero, como
en Cuentas contables. Las fórmulas de la respuesta reflejan los ajustes aplicados.

La validación compara la utilidad **sin neteo** (`5 − 4`) con la ecuación contable
`1 − 2 − 3`, también sin neteo y en la misma fecha y agencia. La comprobación
independiente usa saldos originales porque las transferencias internas pueden
modificar el resultado neteado de una agencia. Se devuelve:

- `estado`: `coincide`, `diferencia` o `sin_datos`.
- `utilidad_sin_neteo` y `resultado_contable`.
- `diferencia`: utilidad sin neteo menos resultado contable, comparada exactamente
  en decimal; no se ocultan diferencias de un centavo.
- `ajuste_neteo`: utilidad mostrada menos utilidad sin neteo.
- `cuentas_sin_saldo`: cuentas que faltan exclusivamente para esta conciliación.

La validación se conserva en la API y no se muestra en la pantalla.
Nunca reemplaza el indicador Utilidad. Los asientos de cierre
pueden producir diferencias entre el resultado trasladado al patrimonio y los
saldos disponibles de ingresos/gastos; esas diferencias se informan para revisión.
No se presume que las cuentas patrimoniales `3603/3604` representen el resultado
pendiente del corte: en la inspección SQL estaban en cero en el corte actual.

La investigación de solo lectura contrastó `5 − 4` con `1 − 2 − 3` para el
consolidado y Matriz al 10 de noviembre de 2026: coincidieron antes del neteo.
