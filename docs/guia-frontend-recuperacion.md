# Guía de frontend: recuperación histórica

## Patrón de referencia

`colocacion-historico/rango` entrega `agrupaciones` listas para graficar. El
frontend conserva la respuesta, filtra por agencia y asesor, y sus componentes
agrupan por período y por la dimensión seleccionada.

Recuperación usa el mismo patrón de filtros y gráficos. Las recuperaciones
históricas incluyen el contexto que quedó guardado en el cobro y el diccionario
de préstamos entrega dimensiones calculadas para `fecha_hasta`:

```text
POST /analytic/recuperacion/recuperacion-historico
```

```json
{
  "fecha_desde": "2026-06-01",
  "fecha_hasta": "2026-06-30"
}
```

## Contrato y modelo recomendado

```ts
export interface RecuperacionHistoricoRequest {
  fecha_desde: string; // YYYY-MM-DD
  fecha_hasta: string; // YYYY-MM-DD
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

export interface RecuperacionMovimiento {
  fecha_cobro: string;
  periodo: string; // YYYY-MM
  anio: number;
  mes: number;
  numero_prestamo: string;
  tipo_cobro: string;
  tipo_transaccion: string;
  valor_recuperado: number;
  agencia: string;
  asesor: string;
  abogado_externo: string;
  codigo_cobranza_apoyo: string;
  nombre_cobranza_apoyo: string;
  estado_prestamo_cobro: string;
  calificacion_cobro: string;
}

export interface RecuperacionHistoricoResponse {
  fecha_desde: string;
  fecha_hasta: string;
  total_recuperado: number;
  resumen_mensual: Array<{
    periodo: string;
    anio: number;
    mes: number;
    fecha_desde: string;
    fecha_hasta: string;
    total_recuperado: number;
  }>;
  prestamos_por_numero: Record<string, PrestamoRecuperacion>;
  recuperaciones: RecuperacionMovimiento[];
}

export type RecuperacionHecho = RecuperacionMovimiento & Partial<PrestamoRecuperacion>;
```

`prestamos_por_numero` es un diccionario: su clave es exactamente
`numero_prestamo`. Se llena para todos los préstamos recuperados con la
información de `fecha_hasta`. Si esa fecha es actual, se consulta
`SituacionCrediticiaActual`; de lo contrario, `SituacionCrediticia`. No debe
convertirse en lista ni buscarse con `.find()`.

El contexto histórico (`agencia`, asesor, abogado, cobranza, estado y
calificación) corresponde al día del cobro. Las dimensiones que no hayan sido
guardadas aún en la recuperación no deben inventarse.

## Unir una vez y reutilizar

Al recibir la respuesta, construir los hechos una sola vez en un `computed`.
Los componentes y filtros trabajan sobre `hechos`, igual que colocación trabaja
sobre `agrupaciones`.

```ts
const hechos = computed<RecuperacionHecho[]>(() => {
  const respuesta = response();
  if (!respuesta) return [];

  return respuesta.recuperaciones.map((movimiento) => {
    const prestamo = respuesta.prestamos_por_numero[movimiento.numero_prestamo];
    return prestamo ? { ...prestamo, ...movimiento } : movimiento;
  });
});
```

No se debe sumar `total_recuperado` con los valores de `resumen_mensual`: ambos
representan los mismos movimientos. El importe para gráficos y tablas es
`valor_recuperado`.

## Agrupar y filtrar

1. Obtener filtros distintos desde `hechos` (`agencia`, `asesor`, producto,
   tipo de cobro, estado inicial/final, etc.).
2. Aplicar filtros sobre `hechos`.
3. Agrupar por `periodo` y la dimensión del gráfico; sumar
   `valor_recuperado`.

Ejemplo: recuperación por agencia y mes.

```ts
const totalPorAgenciaMes = new Map<string, number>();

for (const hecho of hechosFiltrados) {
  const clave = `${hecho.periodo}|${hecho.agencia}`;
  totalPorAgenciaMes.set(
    clave,
    (totalPorAgenciaMes.get(clave) ?? 0) + hecho.valor_recuperado,
  );
}
```

`tipo_cobro` y `tipo_transaccion` son parte del hecho de recuperación, por lo
que pueden ser filtros o series de un gráfico apilado. No se expone ni calcula
la métrica de operaciones: la única métrica analítica es `valor_recuperado`.

## Catálogo de agrupaciones

El catálogo objetivo es el mismo visible en colocación:

```text
agencia, asesor, tipo_prestamo, condicion, producto, segmento,
provincia, canton, parroquia, educacion, edad, garantia,
monto, tasa, tasa_real, plazo
```

Además, recuperación incorpora las etiquetas propias del hecho:

```text
tipo_cobro, tipo_transaccion, estado_prestamo_inicio, estado_prestamo_fin
```

En el histórico actualmente quedan garantizados en el propio movimiento:
`agencia`, `asesor`, abogado, cobranza, `estado_prestamo_cobro` y
`calificacion_cobro`. Las demás dimensiones solo deben habilitarse en filtros
cuando existan; para garantizarlas en históricos antiguos deben persistirse en
`RecuperacionCrediticia` durante el ETL.

Si los gráficos deben mostrar los mismos rangos de edad, monto, tasa o plazo
que colocación, definirlos en una configuración compartida del frontend. No
duplicar los límites dentro de cada componente.

## Controles de consistencia

Antes de renderizar, verificar estas invariantes:

```text
sum(recuperaciones.valor_recuperado) = total_recuperado
sum(resumen_mensual.total_recuperado) = total_recuperado
```

Registrar los movimientos sin una entrada en `prestamos_por_numero` como un
problema de calidad de datos: normalmente todos los préstamos recuperados deben
tener un complemento del corte final.

## Volumen y experiencia de uso

La respuesta contiene hechos sin agrupar. Para rangos grandes:

- construir `hechos` una vez mediante `computed`;
- aplicar filtros y agrupaciones en memoria, sin volver a unir préstamos;
- mostrar estado de carga y un mensaje claro cuando no existan movimientos;
- si el tamaño de la respuesta deja de ser aceptable, incorporar paginación o
  una exportación, sin cambiar la semántica del modelo.

## Reglas importantes

- `valor_recuperado` ya es el valor de un solo tipo de cobro y siempre se debe
  sumar, nunca multiplicar por datos del préstamo.
- Tratar `null` numéricos como datos no disponibles; no como cero para tasas,
  monto o plazo.
- Mantener `periodo` como llave temporal (`YYYY-MM`) y ordenar por
  `anio * 100 + mes`, como en colocación.
- Si falta el préstamo en el diccionario, excluir ese movimiento del gráfico y
  registrar el caso para revisión; no asignar dimensiones ficticias.
