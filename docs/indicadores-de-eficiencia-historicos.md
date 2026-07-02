# Históricos de indicadores de eficiencia

```text
POST /analytic/indicadores-financieros/indicadores-de-eficiencia/historico-mensual
POST /analytic/indicadores-financieros/indicadores-de-eficiencia/historico-diario
Authorization: Bearer <token>
```

## Entrada

```ts
interface IndicadoresDeEficienciaHistoricoRequest {
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
interface IndicadoresDeEficienciaHistoricoItem {
  fecha_corte: string; // YYYY-MM-DD
  anio: number;
  mes: number;
  dia: number;
  gasto_operativo_estimado_sobre_activo_promedio: number | null;
  gasto_personal_estimado_sobre_activo_promedio: number | null;
  margen_intermediacion_estimado_sobre_patrimonio_promedio: number | null;
  margen_intermediacion_estimado_sobre_activo_promedio: number | null;
}

interface IndicadoresDeEficienciaHistoricoResponse {
  id_agencia: number;
  periodo_desde: string;
  periodo_hasta: string;
  neteo: number;
  datos: IndicadoresDeEficienciaHistoricoItem[];
  periodos_sin_datos: string[];
}
```

Los indicadores son proporciones: `0.125` se muestra como `12.5 %`. Para cada fecha se utilizan los promedios acumulados desde el 1 de enero.

`periodos_sin_datos` contiene meses `YYYY-MM` en el histórico mensual y fechas `YYYY-MM-DD` en el diario.

## Uso

```ts
const input: IndicadoresDeEficienciaHistoricoRequest = {
  periodo_desde: "2026-01",
  periodo_hasta: "2026-07",
  id_agencia: 1,
};

const response = await fetch(
  "/analytic/indicadores-financieros/indicadores-de-eficiencia/historico-mensual",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  },
);

if (!response.ok) throw new Error("No se pudieron consultar los indicadores de eficiencia");

const resultado: IndicadoresDeEficienciaHistoricoResponse = await response.json();
```

Para el histórico diario, usa el mismo código cambiando la URL a:

```text
/analytic/indicadores-financieros/indicadores-de-eficiencia/historico-diario
```
