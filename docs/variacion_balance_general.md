# Variación del balance general

Pantalla: `/dashboard/evolucion-de-cuentas/variacion-balance-general`.
Backend: `app/modules/analytic/evolucion_cuentas/variacion_balance_general`.

`POST /analytic/evolucion-de-cuentas/variacion-balance-general` requiere Bearer.

```json
{"tipo":"mensual","fecha_desde":"2026-03-30","fecha_hasta":"2026-03-31","id_agencia":0,"neteo":1}
```

Cada día del rango inclusivo compara las cuentas 1, 2 y 3 con el mismo día del
mes anterior (`mensual`) o del año anterior (`anual`). Cuando el día no existe,
se usa el último día del mes anterior correspondiente. La variación es saldo
actual menos saldo anterior, en dólares; sin porcentajes. El rango máximo es de
un año para mensual y cuatro años para anual, con fecha final anterior al
aniversario del inicio. Se rechazan fechas futuras.

Se reutiliza el repositorio compartido de Balance General, con neteo aplicado
independientemente a cada fecha y 0 como consolidado contable 1. Las consultas
se dividen en lotes de hasta 500 fechas. La respuesta devuelve la fecha de
comparación y tres diferencias decimales. Si falta uno de los saldos base, la
variación es `null` y se identifica la cuenta; no se sustituyen datos faltantes
por cero. El gráfico muestra las variaciones; la tabla incluye ambas fechas.

En variación anual, `dia_mes` es opcional y acepta un entero entre 1 y 31.
Si se omite o es `null`, se muestran todos los días. Si se especifica, se
selecciona un corte por mes dentro del rango; cuando ese día no existe se usa
el último día del mes. Cada corte seleccionado se compara con su fecha
equivalente del año anterior, también ajustada si es necesario. Un rango sin
cortes seleccionados devuelve una lista vacía. El parámetro solo admite el
tipo anual.

La pantalla ofrece cuatro pestañas con estado independiente:

- Variación mensual (`tipo: mensual_cortes`): mes de inicio y fecha de corte.
  Para cada mes se usa el día de corte, ajustado al fin de mes cuando es
  necesario, y se compara con ese mismo día del mes anterior, también ajustado.
- Variación anual por meses (`tipo: anual_meses`): año de inicio y fecha de fin.
  Desde enero se generan cortes mensuales con el día de la fecha de fin; cada
  corte se compara con el día equivalente del año anterior, ajustando cada
  fecha de forma independiente.
- Variación anual por días (`tipo: anual`): fechas de inicio y fin inclusivas;
  cada día se compara con el día equivalente del año anterior.
- Variación mensual por días (`tipo: mensual`): fechas de inicio y fin inclusivas;
  cada día se compara con el día equivalente del mes anterior. El rango admite
  hasta un año, con fecha final anterior al aniversario del inicio.

Las otras tres modalidades admiten hasta cuatro años; `dia_mes` sigue siendo opcional para
`anual`, aunque la pantalla ya no utiliza ese selector.
