# Históricos de rentabilidad

```text
POST /analytic/indicadores-financieros/rentabilidad/historico-mensual
POST /analytic/indicadores-financieros/rentabilidad/historico-diario
Authorization: Bearer <token>
```

## Entrada

```ts
interface RentabilidadHistoricoRequest {
  periodo_desde: string; // YYYY-MM
  periodo_hasta: string; // YYYY-MM
  id_agencia: number;
}
```

- Mensual: usa el último día de cada mes; para el mes actual usa hoy.
- Diario: usa todos los días seleccionados; para el mes actual llega hasta hoy.
- No se aceptan meses futuros.

## Salida

```ts
interface RentabilidadHistoricoItem {
  fecha_corte: string; // YYYY-MM-DD
  anio: number;
  mes: number;
  dia: number;
  gasto_operacional_sobre_margen_financiero_neto: number | null;
  roa: number | null;
  roe: number | null;
  gasto_operativo_estimado_sobre_cartera_bruta: number | null;
  costo_promedio_fondeo: number | null;
}

interface RentabilidadHistoricoResponse {
  id_agencia: number;
  periodo_desde: string;
  periodo_hasta: string;
  neteo: number;
  datos: RentabilidadHistoricoItem[];
  periodos_sin_datos: string[];
}
```

Los indicadores son proporciones: `0.125` se muestra como `12.5 %`. Para cada fecha, ROA, ROE y costo de fondeo usan promedios acumulados desde el 1 de enero.

`periodos_sin_datos` contiene meses `YYYY-MM` en el histórico mensual y fechas `YYYY-MM-DD` en el diario.

## Uso

```ts
const input: RentabilidadHistoricoRequest = {
  periodo_desde: "2026-01",
  periodo_hasta: "2026-07",
  id_agencia: 1,
};

const response = await fetch(
  "/analytic/indicadores-financieros/rentabilidad/historico-mensual",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  },
);

if (!response.ok) throw new Error("No se pudo consultar rentabilidad");

const resultado: RentabilidadHistoricoResponse = await response.json();
```

Para el histórico diario, usa el mismo código cambiando la URL a:

```text
/analytic/indicadores-financieros/rentabilidad/historico-diario
```
