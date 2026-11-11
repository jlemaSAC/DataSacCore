# Resumen de cuentas contables

`POST /analytic/analisis-contable/cuentas-contables` requiere autenticación Bearer.

```json
{
  "fecha_corte": "2026-11-10",
  "id_agencia": 0,
  "neteo": 1
}
```

El módulo pertenece a `app/modules/analytic/analisis_contable/cuentas_contables`,
porque entrega un resumen analítico; usa la sesión principal `get_db` y repositorio
SQL compartido en `app/modules/contabilidad/repositories/sql_resumen_contable_repository.py`.
Se registra mediante el router agrupador de análisis contable
y el router existente de Analytic.

`id_agencia` es opcional y vale `0` (consolidado) por defecto. `0` consulta solamente
la agencia contable `1`, CONSOLIDADO. Los demás IDs consultan la agencia indicada.
No se suman simultáneamente el consolidado y las agencias.

La respuesta contiene `fecha_corte`, `id_agencia`, `id_agencia_contable`,
`nombre_agencia`, `neteo`, `cuentas_sin_saldo` e `indicadores`. Cada indicador incluye
`codigo`, `nombre`, `formula` y `saldo` (decimal serializado como cadena, o `null`).

| Indicador | Cuenta / fórmula |
| --- | --- |
| Activos | 1 |
| Cartera Bruta | 14 − 1499 |
| Cartera Neta | 14 |
| Inversiones | 13 |
| Pasivos | 2 |
| Depósitos a la Vista | 2101 |
| Depósitos a Plazo | 2103 |
| Patrimonio | 3 |
| Capital Social | 31 |
| Reservas | 33 |

Se leen los códigos exactos a la fecha solicitada, sin sumar cuentas hijas ni usar
la última fecha disponible. El saldo respeta `ESDEBITO` y los valores de
`SALDOCONTABLE_FINANIO` cuando existen, como la vista contable. Se suman las monedas
registradas según la convención del repositorio contable existente.
`neteo` acepta `0` o `1` y por defecto vale `1`, igual que en Cuentas contables.
Usa el mapa compartido `MAPA_NETEO_CUENTAS`: Activos aplica `1 − 1908` y Pasivos
aplica `2 − 2908`. Los demás indicadores conservan sus fórmulas. Con `neteo: 0`,
se devuelven los saldos sin esos ajustes. La respuesta muestra las fórmulas
efectivamente aplicadas. Si una cuenta de ajuste no tiene registro, se considera
cero, como en saldos diarios; una cuenta base ausente sigue siendo `null`.
`1499` conserva su signo, incluso cuando es negativo; no se aplica valor absoluto.

Un cero registrado sigue siendo `0.00`. Una cuenta sin registro no se transforma en
cero: el indicador dependiente devuelve `null` y la cuenta aparece en
`cuentas_sin_saldo`. Si no hay registros se devuelven los diez indicadores sin datos.
Una agencia inexistente devuelve HTTP 404 y los parámetros inválidos HTTP 422.

El frontend presenta este resumen en una pantalla independiente en
`/dashboard/analisis-contable/resumen-balance-general`, dentro de
`src/app/features/analisis-contable/resumen-balance-general`, con fecha de corte y
agencia. La pantalla de cuentas contables conserva el detalle por corte y los
históricos en su ruta original.
