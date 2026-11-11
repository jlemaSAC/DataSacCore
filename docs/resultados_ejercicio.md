# Resultados del ejercicio: corte e históricos

Pantalla: `/dashboard/analisis-contable/resumen-resultados-del-ejercicio`.
Frontend: `src/app/features/analisis-contable/resumen-resultados-del-ejercicio`.
Backend: `app/modules/analytic/analisis_contable/resumen_resultados_del_ejercicio`.

Los tres endpoints son `POST`, usan Bearer mediante `get_current_auth_context` y
pertenecen al router agrupador de análisis contable:

| Endpoint bajo `/analytic/analisis-contable/resumen-resultados-del-ejercicio` | Consulta |
| --- | --- |
| `/fecha-corte` | Una fecha exacta |
| `/historico-mensual` | Cierres mensuales; el mes actual usa hoy en Ecuador |
| `/historico-diario` | Todos los días del rango, inclusive |

Cuerpo de fecha de corte:

```json
{ "fecha_corte": "2026-09-30", "id_agencia": 0, "neteo": 1 }
```

Cuerpo de los históricos:

```json
{
  "fecha_desde": "2026-08-01",
  "fecha_hasta": "2026-10-31",
  "id_agencia": 0,
  "neteo": 1
}
```

`id_agencia` es opcional, por defecto `0`, y consulta exclusivamente la agencia
contable `1`, CONSOLIDADO. Los demás IDs consultan esa agencia. `neteo` acepta
`0` o `1` y por defecto está activado. Se admiten hasta 366 días inclusivos.
Los cierres mensuales fuera del rango o en meses futuros se omiten. Las reglas
coinciden con Cuentas contables, incluyendo el uso de la fecha actual de Ecuador
para el mes en curso.

Los valores son **saldos acumulados a cada fecha**, no movimientos del día ni
diferencias entre meses. No se sustituye una fecha ausente por la última disponible.
El repositorio SQL compartido obtiene todos los códigos y fechas en una consulta,
usando `get_db`, parámetros y joins explícitos. Respeta signos, monedas y cierre
anual mediante `SALDOCONTABLE_FINANIO`. Las fórmulas se comparten con Balance de
Resultados mediante `calculos_resultados.py`.

La respuesta contiene `fecha_desde`, `fecha_hasta`, `id_agencia`,
`id_agencia_contable`, `nombre_agencia`, `neteo`, `fechas`, `filas`, `datos` y
`total_registros`. `filas` define el orden, la cuenta, el signo de presentación,
el nombre, la fórmula efectiva y si es un subtotal. `datos` contiene
`fecha`, `codigo_fila` y `saldo`, como cadena decimal o `null`.

Se conservan las 22 filas del estado de resultados y las fechas consultadas, aun
cuando falte un saldo. Un cero registrado sigue siendo `0.00`; un dato ausente
o un subtotal que depende de él queda en `null` y se presenta como `—`. La pantalla
informa cuando no hay saldos. No hay paginación ni truncamiento de registros.

| Orden | Cuenta / cálculo | Concepto |
| --- | --- | --- |
| 1 | 5 | Ingresos |
| 2 | 51 | Intereses y descuentos ganados |
| 3 | − 41 | Intereses causados |
| 4 | 51 − 41 | Margen Neto de Intereses |
| 5 | + 52 | Comisiones ganadas |
| 6 | + 54 | Ingresos por servicios |
| 7 | − 42 | Comisiones causadas |
| 8 | + 53 | Utilidades financieras |
| 9 | − 43 | Pérdidas financieras |
| 10 | Margen Neto de Intereses + 52 + 54 − 42 + 53 − 43 | Margen Bruto Financiero |
| 11 | − 44 | Provisiones |
| 12 | Margen Bruto Financiero − 44 | Margen Neto Financiero |
| 13 | − 45 | Gastos de operación |
| 14 | Margen Neto Financiero − 45 | Margen de Intermediación |
| 15 | + 55 | Otros ingresos operacionales |
| 16 | − 46 | Otras pérdidas operacionales |
| 17 | Margen de Intermediación + 55 − 46 | Margen Operacional |
| 18 | + 56 | Otros ingresos |
| 19 | − 47 | Otros gastos y pérdidas |
| 20 | Margen Operacional + 56 − 47 | Ganancia antes de Impuestos |
| 21 | − 48 | Impuestos y participación a empleados |
| 22 | Ganancia antes de Impuestos − 48 | Ganancia o Pérdida del Ejercicio |

El neteo aplica el mapa compartido: `5` y `51` descuentan `51909005`, mientras
`41` descuenta `41019005`. Un ajuste sin registro se considera cero, igual que
en Cuentas contables. El signo de la primera columna expresa la operación sobre
el subtotal; no cambia artificialmente el signo del saldo presentado.

La tabla tiene columnas por fecha, conserva los subtotales en su orden, resalta
los resultados y permite desplazamiento horizontal. Cada pestaña conserva su
propio formulario, carga y respuesta. No presenta una sección de validación de
utilidad.

Referencia comprobada: CONSOLIDADO, 30/09/2026, neteo activado. Las 22 filas
coinciden con la imagen aportada, incluida Ganancia o Pérdida del Ejercicio de
`242895.04`.
