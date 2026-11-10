# Saldos contables diarios

`POST /analytic/contabilidad/saldos-diarios` requiere autenticación Bearer.

```json
{
  "fecha_desde": "2026-10-01",
  "fecha_hasta": "2026-10-07",
  "id_agencia": 0,
  "neteo": 1
}
```

El rango es inclusivo y admite hasta 366 días. `id_agencia: 0` utiliza la agencia contable 1 (CONSOLIDADO); los demás identificadores consultan esa agencia. `neteo` acepta 0 o 1. La respuesta incluye todos los registros, ordenados por fecha y código, y `total_registros` indica la cantidad devuelta.

Cada fecha incluye las cuentas actualmente activas del catálogo de la empresa de la agencia, de movimiento y de agrupación, que tengan un registro de saldo. Se excluyen las cuentas sin registro para la fecha y se conservan los saldos de `0.00`. Cada registro contiene únicamente `fecha`, `codigo_cuenta`, `nombre_cuenta` y `saldo`. Los importes son decimales serializados como cadenas para preservar precisión. Se suman las monedas registradas, de acuerdo con el repositorio contable existente.

Los saldos se calculan con la regla de signo y cierre de año de la vista contable. El neteo reutiliza el mapa vigente del backend y se aplica también a fechas anteriores al 30 de julio de 2024, de acuerdo con ese mapa. El endpoint incluye las cuentas excluidas por las vistas de neteo, por lo que su listado no coincide necesariamente con Power BI. Evitar sumar conjuntamente cuentas de agrupación y sus cuentas hijas.
