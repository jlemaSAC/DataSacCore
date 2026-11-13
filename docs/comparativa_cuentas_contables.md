# Comparativa de cuentas contables

Pantalla: `/dashboard/analisis-contable/comparativa-cuentas-contables`.
Frontend: `src/app/features/analisis-contable/comparativa-cuentas-contables`.

`POST /analytic/analisis-contable/comparativa-cuentas-contables` requiere Bearer.

```json
{
  "mes_inicio": "2026-05",
  "fecha_corte": "2026-10-15",
  "id_agencia": 0,
  "neteo": 1
}
```

Mes inicio es inclusivo. Fecha de corte es la fecha final de comparación y define
el día de todos los cortes. Este ejemplo consulta mayo a octubre al día 15. Se
admiten de 1 a 24 meses incluidos ambos extremos. Un mes aislado muestra su saldo,
sin comparación anterior. Si el día no existe, se consulta el último día de ese
mes sin alterar el día de los demás meses: enero-marzo con corte 31 produce
31/01, 28/02 (29 en bisiesto), 31/03.

La respuesta incluye contexto de agencia/neteo, `periodos`, `total_cuentas` y
`cuentas`. Cada periodo conserva su fecha efectiva, `fecha_ajustada` y
`cuentas_con_datos`, incluso si todo el corte carece de información. Cada cuenta
incluye código, nombre, padre, nivel jerárquico, estado activo, condición de
movimiento y `valores`, ordenados igual que los periodos.

Cada valor tiene `saldo` y `variacion_absoluta` (saldo menos saldo del corte
anterior), serializados como cadenas decimales o `null`. El primer corte no tiene
variación. Una ausencia interrumpe la comparación: no se busca otro mes con datos.
No se sustituyen fechas sin registros ni se convierten ausencias en cero.

Se devuelven únicamente las cuentas actualmente activas del catálogo de la empresa.
Las cuentas inactivas se conservan en la lectura para resolver la jerarquía y los
ajustes de neteo, pero no aparecen en la respuesta ni en la cobertura por corte.
La pantalla muestra por defecto las cuentas activas con algún saldo
registrado en el intervalo, incluidos ceros. Un filtro permite mostrar también
cuentas activas sin datos. Búsqueda y filtros de tipo y nivel se aplican localmente;
la tabla histórica utiliza la respuesta. El enlace «Ver gráfico» debajo del nombre
de cada cuenta abre su evolución en un diálogo de pantalla completa.
El diálogo alterna entre evolución de saldos y cascada con saldo inicial,
variaciones mensuales y total final. Los saldos base son azules; aumentos verdes
y disminuciones rojas. Un corte ausente interrumpe los conectores: el siguiente
saldo disponible se muestra como nueva base, sin inventar una variación. La
tabla compacta conserva los valores exactos por corte junto al gráfico, con
desplazamiento propio para intervalos largos. No se suman diferencias en el
navegador para reconstruir saldos: los extremos de cada barra utilizan los
saldos recibidos y las etiquetas de variación utilizan el cálculo del backend.
La columna del corte final permanece fija a la derecha. Las variaciones positivas
se presentan en verde y las negativas en rojo, conservando signos y flechas.

La agencia 0 consulta exclusivamente el consolidado contable 1. La lectura usa
`get_db`, tres consultas (agencia, catálogo y saldos de todos los cortes) y
reutiliza `SqlSaldosDiariosRepository`: ceros, signos (incluida la excepción 6/7),
monedas, sustitución de fin de año y el mapa compartido de neteo conservan las
reglas de Cuentas contables. Neteo y diferencias se calculan con Decimal en el
servicio. Los ajustes ausentes se consideran cero; las bases ausentes siguen
siendo null. No se suman padres e hijos ni consolidado con agencias.

Los cortes se pasan mediante parámetros a una tabla VALUES y predicados diarios
sobre FECHA sin transformarla en el filtro. No se realizan consultas por cuenta
ni por mes. El catálogo obtiene el padre más próximo desde CUENTACONTABLE_PADRE;
los ciclos se interrumpen al calcular profundidad.

La ruta lazy utiliza authGuard y menuRouteGuard existentes. Debe existir en el
menú administrado de Mongo bajo Análisis contable, con los permisos de navegación
definidos por la administración. El endpoint no incorpora roles adicionales.

La pantalla limita las fechas a la fecha de sistema de la sesión. La API valida
formato, orden y máximo de meses; una agencia inexistente responde 404 y los
parámetros inválidos 422. Las variaciones de saldos, especialmente en ingresos y
gastos al cruzar cierre anual, no equivalen necesariamente a movimientos del mes.

## Variación anual por meses

El tab «Variación anual por meses» consulta
`POST /analytic/analisis-contable/comparativa-cuentas-contables/anual-por-meses`
con autenticación Bearer:

```json
{
  "periodicidad": "anual_meses",
  "anio_inicio": 2024,
  "fecha_corte": "2026-06-15",
  "id_agencia": 0,
  "neteo": 1
}
```

Incluye todos los meses desde enero del año inicial hasta el mes final, sin el
límite de 24 meses de la comparación mensual. Cada mes compara sus movimientos
netos del día 1 al día indicado por la fecha fin contra el mismo intervalo del
año anterior. Enero de 2024 compara con enero de 2023, incluso siendo la primera
columna. El día se ajusta al último del mes independientemente en cada año,
incluidos los años bisiestos. El frontend conserva el mínimo de 2020 del selector
anual; la API admite desde 1754 para poder consultar el año anterior en SQL Server.

Se suman `TOTALDEBITO - TOTALCREDITO` diarios, sin `SALDOINICIAL`, con el signo
contable, la excepción 6/7, las monedas y la sustitución de fin de año existentes.
El neteo se aplica a cada intervalo antes de comparar. La lectura agrupa cortes
en lotes parametrizados de hasta 500 y no consulta por cuenta ni por mes.
Si un intervalo tiene días sin registros para una cuenta, su movimiento queda
`null`; cero se conserva como dato. Un ajuste de neteo ausente vale cero; un
ajuste presente pero incompleto deja la base sin valor.

La respuesta conserva la estructura habitual y añade `fecha_anterior`,
`fecha_anterior_ajustada` y `cuentas_con_datos_anterior` a cada periodo, y
`saldo_anterior` a cada valor. En este tab `saldo` y `saldo_anterior` representan
movimientos del mes; `variacion_absoluta` es su diferencia calculada con Decimal.
Las columnas y el detalle muestran movimiento actual, movimiento del año anterior,
variación absoluta y porcentaje sobre el valor absoluto del movimiento anterior.
Si la base anterior es cero o falta un dato, el porcentaje queda sin comparación.
Las cuentas con datos únicamente en el año anterior también se muestran.

El gráfico presenta únicamente variaciones: cada barra mensual parte de cero y
termina en la variación absoluta contra el mismo mes del año anterior. Las barras
positivas suben y las negativas bajan. Las etiquetas y el tooltip muestran monto
y porcentaje. Verde indica aumento y rojo disminución. El eje siempre incluye
cero; los ceros se conservan y las comparaciones ausentes quedan vacías. No se
conectan meses ni se suman sus diferencias para reconstruir saldos.

## Estado al navegar entre tabs

Cada tab conserva en memoria su formulario, validación, resultado, error y estado
de carga mientras la pantalla permanece abierta. Las fechas, agencia y neteo de
un tab son independientes de los demás. Cambiar de tab no vuelve a consultar la
API ni borra los resultados.

Las tablas ya consultadas se mantienen montadas y solo se ocultan: conservan la
cuenta seleccionada, los filtros, el orden y el desplazamiento. Cada resultado
mantiene también su instancia del detalle y la selección del tipo de gráfico.
Los controles de las tablas usan identificadores distintos por tab.

Se permite navegar mientras una consulta carga. Cada solicitud guarda su
respuesta o error en el tab desde el que se inició, aunque se haya seleccionado
otro tab. Salir de esta pantalla libera los estados y cancela las suscripciones.
