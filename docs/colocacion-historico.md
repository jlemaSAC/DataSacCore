# Histórico de colocación por rango

```text
POST /analytic/colocacion/colocacion-historico/rango
Authorization: Bearer <token>
Content-Type: application/json
```

## Entrada

```ts
interface ColocacionHistoricoRangoRequest {
  fecha_desde: string; // YYYY-MM-DD
  fecha_hasta: string; // YYYY-MM-DD
}
```

- `fecha_hasta` debe ser igual o posterior a `fecha_desde`.
- `fecha_hasta` no puede superar la fecha del sistema.
- El rango máximo permitido es de 24 meses.

## Salida

```ts
interface ResumenRangoColocacion {
  periodo: string; // YYYY-MM
  anio: number;
  mes: number; // 1 a 12
  fecha_desde: string; // Inicio efectivo del segmento mensual
  fecha_hasta: string; // Fin efectivo del segmento mensual
  operaciones: number;
  saldo_inicial: number;
}

interface ColocacionHistoricoAgrupacion {
  periodo: string; // YYYY-MM
  anio: number;
  mes: number;
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
  edad: string;
  garantia: string;
  monto: string;
  tasa: string;
  plazo: string;
  operaciones: number;
  saldo_inicial: number;
}

interface ColocacionHistoricoRangoResponse {
  fecha_desde: string;
  fecha_hasta: string;
  total_operaciones: number;
  total_saldo_inicial: number;
  resumen_mensual: ResumenRangoColocacion[];
  agrupaciones: ColocacionHistoricoAgrupacion[];
}
```

`saldo_inicial` es la suma de `DeudaInicial` de los préstamos adjudicados; no
representa el saldo de capital vigente.

`resumen_mensual` contiene un elemento por cada mes incluido en el rango. Si el
primer o último mes es parcial, `fecha_desde` y `fecha_hasta` indican los límites
efectivos utilizados.

`agrupaciones` contiene una fila por cada combinación única de dimensiones.
Cada fila puede representar varias operaciones.

Los valores posibles de `edad` son:

```text
HASTA 20
HASTA 30
HASTA 40
HASTA 50
HASTA 60
HASTA 70
HASTA 80
HASTA 90
HASTA 100
MAS DE 100
SIN DATOS
```

`monto`, `tasa` y `plazo` son rangos acumulativos: cada etiqueta incluye el
límite indicado y comienza después del límite anterior. Valores inválidos o un
plazo mayor de 10 años se reportan como `SIN DATOS`.

## Uso

```ts
const input: ColocacionHistoricoRangoRequest = {
  fecha_desde: "2025-12-15",
  fecha_hasta: "2026-02-10",
};

const response = await fetch(
  "/analytic/colocacion/colocacion-historico/rango",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  },
);

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail ?? "No se pudo consultar la colocación histórica");
}

const resultado: ColocacionHistoricoRangoResponse = await response.json();
```

Para construir una serie mensual:

```ts
const serieMensual = resultado.resumen_mensual.map((item) => ({
  periodo: item.periodo,
  monto: item.saldo_inicial,
  operaciones: item.operaciones,
}));
```

Para filtrar una agencia y un período:

```ts
const detalle = resultado.agrupaciones.filter(
  (item) => item.periodo === "2026-01" && item.agencia === "MATRIZ",
);
```

No uses `agrupaciones.length` como cantidad de préstamos. Debes sumar el campo
`operaciones`.

No sumes simultáneamente `total_saldo_inicial`, `resumen_mensual` y
`agrupaciones`: representan el mismo universo con diferentes niveles de detalle.

## Mes actual

- MongoDB aporta desde el inicio efectivo del rango hasta el corte de ayer.
- SQL Server aporta las adjudicaciones del día actual.
- Si el rango comienza hoy, el mes actual se obtiene únicamente desde SQL Server.
