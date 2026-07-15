# Recuperación crediticia desde MongoDB

```text
POST /analytic/recuperacion/recuperacion-historico
```

La consulta no usa SQL Server. Para fechas cerradas lee los movimientos y el
contexto de cobro guardado en `RecuperacionCrediticia`. Si el rango incluye la
fecha del sistema, esa fecha se lee desde `RecuperacionCrediticiaActual`.

`prestamos_por_numero` se construye con todos los préstamos recuperados. Sus
dimensiones corresponden a `fecha_hasta`: si es una fecha cerrada se consulta
`SituacionCrediticia` en lotes; si es la fecha actual se consulta SQL Server
directamente por los números de préstamo recuperados. El estado inicial se toma
del corte de `fecha_desde`.

## Solicitud

```json
{
  "fecha_desde": "2026-06-01",
  "fecha_hasta": "2026-06-30"
}
```

## Resultado

Cada movimiento histórico incluye además el contexto de cobro guardado en la
recuperación. El cliente usa `prestamos_por_numero[numero_prestamo]` para las
dimensiones del corte final:

```json
{
  "prestamos_por_numero": {
    "2020112000639": {
      "agencia": "MATRIZ",
      "estado_prestamo_inicio": "AL DIA"
    }
  },
  "recuperaciones": [
    {
      "fecha_cobro": "2026-06-01",
      "numero_prestamo": "2020112000639",
      "tipo_cobro": "COBRANZA",
      "tipo_transaccion": "ABONO PRESTAMO AUTOMATICO",
      "valor_recuperado": 0.01,
      "agencia": "MATRIZ",
      "asesor": "ANA ASESORA",
      "estado_prestamo_cobro": "AL DIA",
      "calificacion_cobro": "A-1"
    }
  ]
}
```

Los valores de cobro `0` no se devuelven. La consulta usa los índices que
inician por `fecha_corte` de las colecciones históricas y, cuando el corte final
es actual, el índice de `SituacionCrediticiaActual.NumeroPrestamo`.
