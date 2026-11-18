# Evolución del balance general

Pantalla: `/dashboard/evolucion-de-cuentas/evolucion-balance-general`.
Frontend: configuración en `src/app/features/evolucion-cuentas/balance-general` y
componentes compartidos en `src/app/features/evolucion-cuentas/shared/evolucion`.
Backend: `app/modules/analytic/evolucion_cuentas/evolucion_balance_general`.

`POST /analytic/evolucion-de-cuentas/evolucion-balance-general` requiere Bearer
mediante `get_current_auth_context`. El router del dominio está registrado en
`app/modules/analytic/router.py`; `app/main.py` ya registra ese router.

```json
{
  "frecuencia": "mensual",
  "fecha_desde": "2023-01-01",
  "fecha_hasta": "2026-11-17",
  "id_agencia": 0,
  "neteo": 1
}
```

- Mensual: hasta 48 meses calendario inclusivos. Consulta el último día de cada
  mes anterior y, para el mes actual, el día de hoy en Ecuador. El frontend
  permite seleccionar meses y envía el inicio del primer mes y el fin del
  último, o el día actual cuando se selecciona el mes en curso. Por ejemplo,
  septiembre a noviembre de 2026, consultado el 17 de noviembre, devuelve
  30/09, 31/10 y 17/11. El último corte se identifica con `parcial: true` hasta
  que corresponda al fin de mes. No se sustituyen fechas por días con saldo.
  Si el rango no contiene ningún cierre ni el día actual, devuelve 422.
- Diario: hasta un año, con fechas inclusivas y `fecha_hasta` anterior a `fecha_desde + 12 meses`.
  El límite se ajusta al último día del mes destino si ese día no existe.
  Por ejemplo, del 18 de noviembre de 2025 al 17 de noviembre de 2026;
  desde el 29 de febrero de 2024, hasta el 27 de febrero de 2025.
- No permite fechas futuras; la fecha actual se calcula en Ecuador.
- Agencia 0 corresponde a la agencia contable 1 (CONSOLIDADO). No se suman
  agencias ni cuentas hijas. Agencias inexistentes devuelven 404.
- Neteo activado por defecto y seleccionable: se aplica el mapa vigente del
  Balance General (`1 - 1908`, `2 - 2908`; cuenta 3 sin ajuste).

Se reutiliza `SqlResumenContableRepository`, con `get_db`, consultas
parametrizadas y una sola lectura de saldos para todos los cortes. El esquema
real de `SALDOCONTABLE`, `SALDOCONTABLE_FINANIO`, `CUENTACONTABLE` y el consolidado
se verificó con el MCP `datasac_sql`. Se mantienen los signos, suma de monedas
y sustituciones de cierre anual del Balance General existente.

La respuesta incluye filtros, agencia resuelta y `datos`: un registro por fecha,
con `activos`, `pasivos`, `patrimonio`, `parcial` y `cuentas_sin_saldo`. Importes decimales
como cadenas; ausencia como `null`, cero como `"0.00"`. Los ajustes de neteo sin
registro se consideran cero. No se interpolan saldos de días vecinos.

Cada pestaña conserva filtros y estado independientes. La vista Gráfica usa el
diseño de Costo de fondeo: tarjeta amplia, gráfico alto, degradados, etiquetas
de valores y selector lateral de cuentas. Las tres series se muestran al inicio;
se pueden ocultar individualmente o seleccionar todas. La selección se conserva
al cambiar entre Gráfica y Tabla. La tabla mantiene todas las cuentas y los
mismos cortes; los nulos interrumpen las líneas y se
identifican como «Sin datos». Se mantiene el guard de menú habitual: la ruta
debe estar disponible en el menú y acceso configurados para el usuario.

Pruebas: `python -m pytest tests/test_evolucion_balance_general.py -q` y
`npm test -- --watch=false --include='src/app/features/evolucion-cuentas/**/*.spec.ts'`.
