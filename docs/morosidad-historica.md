# Morosidad histórica

## Endpoint

```text
POST /analytic/cartera-de-credito/morosidad-historica
Authorization: Bearer <token>
Content-Type: application/json
```

## Entrada

```ts
interface MorosidadHistoricaRequest {
  periodo_desde: string; // YYYY-MM
  periodo_hasta: string; // YYYY-MM
}
```

Ejemplo:

```json
{
  "periodo_desde": "2025-01",
  "periodo_hasta": "2025-12"
}
```

- El rango máximo es de 60 meses.
- `periodo_hasta` debe ser igual o posterior a `periodo_desde`.
- No se aceptan meses posteriores al mes actual.
- Los meses cerrados consultan `SituacionCrediticia` en su último día calendario.
- El mes actual consulta `SituacionCrediticiaActual` y se identifica con la
  fecha del sistema incluida en el token.
- Se excluyen préstamos con `EstadoPrestamo = CANCELADO`.
- En meses cerrados, `plazo` se obtiene de las fechas de adjudicación y
  vencimiento. En el mes actual, se clasifica usando `Plazo` en meses.

## Salida

```ts
interface MorosidadHistoricaAgrupacion {
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
  tasa_real: string;
  plazo: string;
  saldo_capital: number;
  cartera_improductiva: number;
  provision_requerida: number;
}

interface MorosidadHistoricaResponse {
  agrupaciones: MorosidadHistoricaAgrupacion[];
}
```

## Cálculo de morosidad

El backend calcula:

```text
cartera_improductiva = CapitalNoDevenga + CapitalVencido
```

`provision_requerida` corresponde a la suma de `ProvisionRequerida` dentro de
cada agrupación.

El frontend calcula por cada agrupación:

```text
morosidad = cartera_improductiva / saldo_capital
morosidad_porcentaje = morosidad * 100
```

Si `saldo_capital` es cero:

```text
morosidad = 0
morosidad_porcentaje = 0
```

Ejemplo TypeScript:

```ts
const morosidad = agrupacion.saldo_capital === 0
  ? 0
  : agrupacion.cartera_improductiva / agrupacion.saldo_capital;

```
