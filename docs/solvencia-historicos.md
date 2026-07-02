# Históricos de solvencia

```text
POST /analytic/indicadores-financieros/solvencia/historico-mensual
POST /analytic/indicadores-financieros/solvencia/historico-diario
Authorization: Bearer <token>
```

## Entrada

```ts
interface SolvenciaHistoricoRequest {
  periodo_desde: string; // YYYY-MM
  periodo_hasta: string; // YYYY-MM
  id_agencia: number;
}
```

- Mensual: usa el último día de cada mes. Para el mes actual usa la fecha actual.
- Diario: usa todos los días de los meses seleccionados. Para el mes actual llega hasta hoy.
- No se aceptan meses futuros.

## Salida

```ts
interface SolvenciaHistoricoItem {
  fecha_corte: string; // YYYY-MM-DD
  anio: number;
  mes: number;
  dia: number;
  solvencia: number | null;
  activos_fijos_sobre_patrimonio_tecnico: number | null;
  patrimonio_sobre_activo: number | null;
  patrimonio_resultados_sobre_activos_improductivos_netos: number | null;
}

interface SolvenciaHistoricoResponse {
  id_agencia: number;
  periodo_desde: string;
  periodo_hasta: string;
  neteo: number;
  datos: SolvenciaHistoricoItem[];
  periodos_sin_datos: string[];
}
```

Los indicadores son proporciones: `0.125` se muestra como `12.5 %`.

`periodos_sin_datos` contiene meses `YYYY-MM` en el histórico mensual y fechas `YYYY-MM-DD` en el diario. Una fecha se incluye ahí cuando faltan saldos contables o provisiones históricas.

## Uso

```ts
const input: SolvenciaHistoricoRequest = {
  periodo_desde: "2025-01",
  periodo_hasta: "2026-06",
  id_agencia: 1,
};

const response = await fetch(
  "/analytic/indicadores-financieros/solvencia/historico-mensual",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  },
);

if (!response.ok) throw new Error("No se pudo consultar la solvencia");

const resultado: SolvenciaHistoricoResponse = await response.json();
```

Para el histórico diario, utiliza el mismo código cambiando la URL a:

```text
/analytic/indicadores-financieros/solvencia/historico-diario
```
