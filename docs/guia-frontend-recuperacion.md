# Recuperación histórica: contrato para frontend

`POST /analytic/recuperacion/recuperacion-historico` conserva el rango y el
resumen mensual, pero la respuesta ahora separa el hecho de recuperación de las
dimensiones del préstamo.

## Estructura final

```ts
export interface RecuperacionHistoricoResponse {
  p: Record<string, PrestamoRecuperacion>; // préstamos por número
  r: RecuperacionMovimiento[]; // recuperaciones
}

export interface RecuperacionMovimiento {
  an: number; // año
  me: number; // mes
  np: string; // número de préstamo
  tc: string; // tipo de cobro
  tx: string; // transacción
  v: number; // valor recuperado

  // Contexto registrado al momento del cobro.
  ag: string; // agencia
  as: string; // asesor
  ae?: string; // abogado externo
  ap?: string; // cobranza apoyo
  ea: string; // estado anterior
  ec: string; // estado actual
  ca: string; // calificación anterior
  cc: string; // calificación actual
}

export interface PrestamoRecuperacion {
  co: string; // condición
  tp: string; // tipo de préstamo
  pr: string; // producto
  sg: string; // segmento
  pv: string; // provincia
  cn: string; // cantón
  pq: string; // parroquia
  ed: string; // educación
  e: number | null; // edad
  ga: string; // garantía
  mo: number | null; // monto
  tn: number | null; // tasa nominal
  tr: number | null; // tasa real
  pl: number | null; // plazo en meses
}
```

## Cambio importante

`r` contiene un registro por `tc`, por lo que `v` es la métrica que se suma
en gráficas y tablas.

Las dimensiones analíticas viven en `p` y se consultan con la llave `np`. No se
debe buscar con `.find()` ni solicitar datos
adicionales al backend.

```ts
const prestamo = respuesta.p[movimiento.np];
const hecho = { ...prestamo, ...movimiento };
```

El orden anterior conserva los campos del cobro (`tc`, `tx`, responsables,
estado y calificación) y agrega las
dimensiones del préstamo para filtrar o agrupar.

Para los filtros y gráficos de `ag` y `as`, usar siempre los valores
de `RecuperacionMovimiento`. Representan la agencia y el asesor al momento del
cobro. No usar los valores homónimos de `PrestamoRecuperacion`, porque
corresponden al préstamo en `fecha_hasta`.

## Campos nuevos disponibles

Del movimiento de recuperación:

- `tc`, `tx`
- `ae` (ABOGADO), `ap` (COBRANZA APOYO)
- `ea`, `ec`, `ca`, `cc`

Del préstamo indexado:

- `co`, `tp`, `pr`, `sg`, `pv`, `cn`, `pq`, `ed`
- `e`, `ga`, `mo`, `tn`, `tr`, `pl`

Para ordenar períodos, usar `an * 100 + me`.
