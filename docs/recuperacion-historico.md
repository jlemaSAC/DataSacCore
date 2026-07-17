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

## Consulta agregada para analítica

```text
POST /analytic/recuperacion/recuperacion-historico-agrupado
```

Este endpoint está destinado a gráficas y tablas de alto volumen. MongoDB
agrupa primero los cobros por préstamo y periodo, consolida todos los periodos
del préstamo, resuelve una sola vez las dimensiones del corte final y devuelve
únicamente la matriz mensual. Los movimientos individuales nunca se
materializan en Python ni se transfieren al cliente.

### Solicitud agregada

```json
{
  "fecha_desde": "2026-01-01",
  "fecha_hasta": "2026-06-30",
  "dimension": "asesor",
  "agencias": ["MATRIZ"],
  "asesores": [],
  "tipos_prestamo": ["MICROCREDITO"]
}
```

`dimension` solo admite las dimensiones declaradas por el contrato Pydantic.
Los filtros se normalizan a mayúsculas, eliminan duplicados y tienen un máximo
de 500 valores por campo.

### Resultado agregado

```json
{
  "dimension": "asesor",
  "periodos": [
    {"clave": "2026-01", "anio": 2026, "mes": 1, "etiqueta": "Ene 2026"}
  ],
  "series": [
    {
      "clave": "ANA ASESORA",
      "etiqueta": "ANA ASESORA",
      "valores": [12500.5],
      "total": 12500.5
    }
  ],
  "totales_por_periodo": [12500.5],
  "total_general": 12500.5,
  "catalogos": {
    "agencias": ["MATRIZ"],
    "asesores": ["ANA ASESORA"],
    "tipos_prestamo": ["MICROCREDITO"]
  },
  "resumen": {"cantidad_movimientos": 120, "cantidad_series": 1}
}
```

Los catálogos son dependientes: agencias considera todo el rango, asesores
respeta las agencias seleccionadas y tipos de préstamo respeta agencias y
asesores.

### Índices requeridos

```javascript
db.RecuperacionCrediticia.createIndex({ fecha_corte: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, NumeroPrestamo: 1 })
db.SituacionCrediticiaActual.createIndex({ NumeroPrestamo: 1 }, { unique: true })
```

Antes de habilitar rangos anuales en producción se debe confirmar con
`explain("executionStats")` que el primer `$match` y los `$lookup` utilizan
estos índices.
