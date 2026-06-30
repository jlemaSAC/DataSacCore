# Indicadores de liquidez históricos

```text
POST /analytic/indicadores-financieros/indicadores-de-liquidez/historico-mensual
Authorization: Bearer <token>
```

## Entrada

```ts
interface LiquidezHistoricoRequest {
  periodo_desde: string; // YYYY-MM
  periodo_hasta: string; // YYYY-MM
  id_agencia: number;
}
```

Los meses anteriores se consultan al último día del mes. Para el mes actual se usa la fecha actual. No se aceptan meses futuros.

## Salida

```ts
interface LiquidezMensual {
  fecha_corte: string; // YYYY-MM-DD
  anio: number;
  mes: number;
  dia: number;
  fondos_disponibles_sobre_depositos_corto_plazo: number | null;
  liquidez_sobre_obligaciones_publico: number | null;
  liquidez_inversiones_sobre_depositos_vista_plazo: number | null;
  activos_liquidos_sobre_pasivos_exigibles: number | null;
  inversiones_sobre_obligaciones_publico: number | null;
  activos_liquidos_sobre_obligaciones_publico: number | null;
  liquidez_primera_linea: number | null;
  liquidez_segunda_linea: number | null;
}

interface LiquidezHistoricoResponse {
  id_agencia: number;
  periodo_desde: string;
  periodo_hasta: string;
  neteo: number;
  datos: LiquidezMensual[];
  periodos_sin_datos: string[]; // YYYY-MM
}
```

Los indicadores son proporciones: `0.4232` se muestra como `42.32 %`.

## Uso

```ts
const response = await fetch(
  "/analytic/indicadores-financieros/indicadores-de-liquidez/historico-mensual",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      periodo_desde: "2025-01",
      periodo_hasta: "2026-06",
      id_agencia: 1,
    } satisfies LiquidezHistoricoRequest),
  },
);

const resultado: LiquidezHistoricoResponse = await response.json();
```
