# Morosidad historica por meses

```text
POST /analytic/cartera-de-credito/morosidad-historica
Authorization: Bearer <token>
Content-Type: application/json
```

## Entrada

```json
{
  "periodo_desde": "2025-01",
  "periodo_hasta": "2025-12"
}
```

Ambos períodos usan el formato `YYYY-MM`. El rango máximo es de 60 meses y
`periodo_hasta` debe ser un mes ya finalizado según la fecha del sistema del
token. Cada período se consulta en `SituacionCrediticia` usando como
`fecha_corte` su último día calendario (`YYYYMMDD`).

## Cálculos

```text
capital_vigente       = saldo_capital - capital_no_devenga - capital_vencido
cartera_improductiva  = capital_no_devenga + capital_vencido
morosidad             = cartera_improductiva / saldo_capital
morosidad_porcentaje  = morosidad * 100
```

Si `saldo_capital` es cero, ambas medidas de morosidad son cero. Las fórmulas
se aplican después de sumar los saldos de cada agrupación; no se promedian
porcentajes individuales.

## Salida

La respuesta incluye:

- los totales del rango;
- `resumen_mensual`, con un elemento por mes y su `fecha_corte`;
- `agrupaciones`, con las mismas dimensiones de colocación histórica;
- `periodos_sin_datos`, para cierres mensuales sin documentos.

Las medidas monetarias disponibles en cada nivel son `saldo_capital`,
`capital_vigente`, `capital_no_devenga`, `capital_vencido` y
`cartera_improductiva`. También se entregan `operaciones`, `morosidad` como
proporción y `morosidad_porcentaje`.

Los totales monetarios del rango suman los saldos de sus cortes mensuales. No
deben interpretarse como el saldo vigente de una única fecha. De la misma
manera, `operaciones` en los totales puede contar un mismo préstamo una vez por
cada cierre mensual en el que forme parte de la cartera.
