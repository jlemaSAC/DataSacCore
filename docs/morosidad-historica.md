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
  cuota: string;
  operaciones: number;
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

`operaciones` corresponde al número de créditos representados por cada
agrupación mensual y se calcula en MongoDB mediante `{ $sum: 1 }`.

## Cuota aproximada

La dimensión `cuota` se calcula durante la consulta usando los campos
`DeudaInicial`, `TasaNominal` y `Plazo` disponibles en ambas colecciones:

```text
tasa_mensual = (TasaNominal / 100) / 12
cuota_aproximada = DeudaInicial * tasa_mensual
                    / (1 - (1 + tasa_mensual) ^ -Plazo)
```

Si la tasa es cero, `cuota_aproximada = DeudaInicial / Plazo`. Valores sin
capital, tasa o plazo válido se clasifican como `SIN DATOS`.

Rangos:

```text
Hasta 100
Hasta 300
Hasta 500
Hasta 700
Hasta 900
Hasta 1.100
Hasta 1.300
Hasta 1.500
Hasta 1.700
Hasta 1.900
Mas de 1.900
```

Los límites superiores son inclusivos; por ejemplo, `Hasta 300` representa
`100 < cuota <= 300`, porque el rango anterior finaliza en 100.

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
