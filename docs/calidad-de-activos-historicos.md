# Históricos de calidad de activos

```text
POST /analytic/indicadores-financieros/calidad-de-activos/historico-mensual
POST /analytic/indicadores-financieros/calidad-de-activos/historico-diario
Authorization: Bearer <token>
```

## Entrada

```ts
interface CalidadDeActivosHistoricoRequest {
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
interface CalidadDeActivosHistoricoItem {
  fecha_corte: string; // YYYY-MM-DD
  anio: number;
  mes: number;
  dia: number;
  morosidad_ampliada: number | null;
  morosidad_consumo: number | null;
  morosidad_inmobiliaria: number | null;
  morosidad_micro: number | null;
  activos_improductivos_netos_sobre_activo: number | null;
  cartera_refinanciada_restructurada_sobre_cartera_total: number | null;
  cartera_bruta_sobre_activos: number | null;
  cobertura_cartera_en_riesgo: number | null;
}

interface CalidadDeActivosHistoricoResponse {
  id_agencia: number;
  periodo_desde: string;
  periodo_hasta: string;
  neteo: number;
  datos: CalidadDeActivosHistoricoItem[];
  periodos_sin_datos: string[];
}
```

Los indicadores son proporciones: `0.125` se muestra como `12.5 %`.

`periodos_sin_datos` contiene meses `YYYY-MM` en el histórico mensual y fechas `YYYY-MM-DD` en el diario.

## Uso

```ts
const input: CalidadDeActivosHistoricoRequest = {
  periodo_desde: "2026-01",
  periodo_hasta: "2026-07",
  id_agencia: 1,
};

const response = await fetch(
  "/analytic/indicadores-financieros/calidad-de-activos/historico-mensual",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  },
);

const resultado: CalidadDeActivosHistoricoResponse = await response.json();
```

Para el histórico diario, usa el mismo código cambiando la URL a:

```text
/analytic/indicadores-financieros/calidad-de-activos/historico-diario
```
