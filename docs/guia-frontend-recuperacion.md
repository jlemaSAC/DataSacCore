# Recuperación histórica: contrato para frontend

`POST /analytic/recuperacion/recuperacion-historico` conserva el rango y el
resumen mensual, pero la respuesta ahora separa el hecho de recuperación de las
dimensiones del préstamo.

## Estructura final

```ts
export interface RecuperacionHistoricoResponse {
  fecha_desde: string;
  fecha_hasta: string;
  total_recuperado: number;
  resumen_mensual: ResumenMensualRecuperacion[];
  prestamos_por_numero: Record<string, PrestamoRecuperacion>;
  recuperaciones: RecuperacionMovimiento[];
}

export interface RecuperacionMovimiento {
  fecha_cobro: string;
  periodo: string; // YYYY-MM
  anio: number;
  mes: number;
  numero_prestamo: string;
  tipo_cobro: string;
  tipo_transaccion: string;
  valor_recuperado: number;

  // Contexto registrado al momento del cobro.
  agencia: string;
  asesor: string;
  abogado_externo: string;
  codigo_cobranza_apoyo: string;
  nombre_cobranza_apoyo: string;
  estado_prestamo_cobro: string;
  calificacion_cobro: string;
}

export interface PrestamoRecuperacion {
  numero_prestamo: string;
  agencia: string;
  condicion: string;
  tipo_prestamo: string;
  producto: string;
  segmento: string;
  asesor: string;
  provincia: string;
  canton: string;
  parroquia: string;
  educacion: string;
  edad: number | null;
  garantia: string;
  monto: number | null;
  tasa: number | null;
  tasa_real: number | null;
  plazo: number | null;
  estado_prestamo_inicio: string;
  estado_prestamo_fin: string;
}
```

## Cambio importante

`recuperaciones` contiene un registro por `tipo_cobro`, por lo que
`valor_recuperado` es la métrica que se suma en gráficas y tablas.

Las dimensiones analíticas viven en `prestamos_por_numero` y se consultan con
la llave `numero_prestamo`. No se debe buscar con `.find()` ni solicitar datos
adicionales al backend.

```ts
const prestamo = respuesta.prestamos_por_numero[movimiento.numero_prestamo];
const hecho = { ...prestamo, ...movimiento };
```

El orden anterior conserva los nuevos campos del cobro (`tipo_cobro`,
`tipo_transaccion`, responsables, estado y calificación) y agrega las
dimensiones del préstamo para filtrar o agrupar.

Para los filtros y gráficos de `agencia` y `asesor`, usar siempre los valores
de `RecuperacionMovimiento`. Representan la agencia y el asesor al momento del
cobro. No usar los valores homónimos de `PrestamoRecuperacion`, porque
corresponden al préstamo en `fecha_hasta`.

## Campos nuevos disponibles

Del movimiento de recuperación:

- `tipo_cobro`
- `tipo_transaccion`
- `abogado_externo` (ABOGADO)
- `codigo_cobranza_apoyo` 
- `nombre_cobranza_apoyo` COBRANZA APOYO
- `estado_prestamo_cobro` ESTADO PRESTAMO
- `calificacion_cobro` CALIFICACION 

Del préstamo indexado:

- `condicion`, `tipo_prestamo`, `producto`, `segmento`
- `provincia`, `canton`, `parroquia`, `educacion`
- `edad`, `garantia`, `monto`, `tasa`, `tasa_real`, `plazo`
- `estado_prestamo_inicio`, `estado_prestamo_fin`(Ya no usarlo de esta manera)

Para ordenar períodos, usar `anio * 100 + mes`; `periodo` se mantiene para
etiquetas y agrupaciones mensuales.
