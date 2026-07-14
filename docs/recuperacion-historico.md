# Recuperación histórica desde MongoDB

```text
POST /analytic/recuperacion/recuperacion-historico
```

La consulta usa exclusivamente las colecciones `RecuperacionCrediticia` y
`SituacionCrediticia` de la base Mongo `DataSac`. SQL Server participa solo en
la carga incremental de `RecuperacionCrediticia`.

## Solicitud

```json
{
  "fecha_desde": "2026-01-01",
  "fecha_hasta": "2026-07-12"
}
```

La respuesta siempre incluye y agrupa por todas las dimensiones: tipo de cobro,
tipo de transacción, estados de inicio y fin, agencia, condición, tipo de
préstamo, producto, segmento, asesor, ubicación, educación, edad, garantía,
monto, tasas y plazo.

Las recuperaciones se almacenan con granularidad
`fecha_corte + préstamo + tipo_transaccion`, y con importes pivotados como
`CAPITAL`, `INTERES`, `INTERES_MORA`, `SEGURO`, entre otros. La consulta los
desagrupa internamente para poder agrupar por `tipo_cobro`.

Para dimensiones históricas, el cruce se realiza por:

```text
RecuperacionCrediticia.NUMERO_PRESTAMO = SituacionCrediticia.NumeroPrestamo
```

El cruce usa el mismo `NumeroPrestamo` y el mismo `fecha_corte` de la
recuperación. Los estados de inicio y fin usan los cortes exactos de
`fecha_desde` y `fecha_hasta`.

## Índices requeridos

```javascript
db.RecuperacionCrediticia.createIndex(
  { fecha_corte: 1, ID_PRESTAMO: 1, TIPO_TRANSACCION: 1 },
  { unique: true }
)

db.SituacionCrediticia.createIndex(
  { fecha_corte: 1, NumeroPrestamo: 1 },
  { unique: true }
)
```
