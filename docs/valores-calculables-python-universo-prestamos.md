# Valores calculables en Python para el universo de prestamos

## Regla general

La regla recomendada es:

```text
Traer de la base datos fuente/crudos.
Calcular en Python derivados, variaciones, porcentajes, agregados y simulaciones.
```

Esto permite que Negocios, Cobranza y Riesgos usen las mismas formulas, evita duplicacion en SPs y hace que los filtros funcionen sobre un mismo universo de prestamos.

## Valores que si conviene calcular en Python

### Capital vigente

Formula:

```text
CapitalVigente = SaldoCapital - CapitalNoDevenga - CapitalVencido
```

Insumos requeridos:

```text
SaldoCapital
CapitalNoDevenga
CapitalVencido
```

### Cartera improductiva

Formula:

```text
CarteraImproductiva = CapitalNoDevenga + CapitalVencido
```

Insumos requeridos:

```text
CapitalNoDevenga
CapitalVencido
```

### Mora

Formula:

```text
Mora = CarteraImproductiva / SaldoCapital
```

Regla:

```text
Si SaldoCapital = 0, Mora = 0
```

### Mora porcentaje

Formula:

```text
MoraPorcentaje = Mora * 100
```

### Variacion de saldo capital

Formula:

```text
VariacionSaldoCapital = SaldoCapitalActual - SaldoCapitalAnterior
```

Insumos requeridos:

```text
SaldoCapitalActual
SaldoCapitalAnterior
```

### Variacion de provision

Formula:

```text
VariacionProvision = ProvisionActual - ProvisionCierreMes
```

Insumos requeridos:

```text
ProvisionActual
ProvisionCierreMes
```

### Variacion de dias de mora

Formula:

```text
VariacionDiasMora = DiasMoraActual - DiasMoraAnterior
```

Insumos requeridos:

```text
DiasMoraActual
DiasMoraAnterior
```

### Numero de operaciones

Formula:

```text
NumeroOperaciones = conteo de prestamos del universo filtrado
```

Regla:

```text
Contar por NumeroPrestamo o IdPrestamo normalizado.
```

### Clientes

Formula:

```text
Clientes = conteo distinct de Cliente / NumeroCliente / IdCliente
```

Regla:

```text
Usar el identificador mas estable disponible.
Preferir IdCliente o NumeroCliente antes que nombre.
```

### Total recuperado

Formula:

```text
TotalRecuperado =
    CapitalPagado
  + InteresPagado
  + InteresMoraPagado
  + SeguroPagado
  + OtrosPagado
```

Insumos requeridos:

```text
CapitalPagado
InteresPagado
InteresMoraPagado
SeguroPagado
OtrosPagado
```

### Cartera diferida

Formula:

```text
CarteraDiferida = SaldoCapital si EsDiferido = true
CarteraDiferida = 0 si EsDiferido = false
```

Insumos requeridos:

```text
SaldoCapital
EsDiferido
```

### Operacion cancelada

Formula:

```text
OperacionEsCancelada =
    CodigoEstadoPrestamo == "C"
    o EstadoPrestamo == "CANCELADO"
```

Insumos requeridos:

```text
CodigoEstadoPrestamo
EstadoPrestamo
```

### Faltantes en Mongo

Formula:

```text
FaltantesEnMongo = claves_actuales - claves_historicas
```

Uso:

Comparativos entre SQL/Mongo actual y Mongo historico.

### Faltantes en actual

Formula:

```text
FaltantesEnActual = claves_historicas - claves_actuales
```

Uso:

Detectar prestamos o agrupaciones que estaban en cierre anterior y ya no aparecen en el corte actual.

### Matriz de transicion

Formula conceptual:

```text
Agrupar CalificacionAnterior -> CalificacionActual por NumeroPrestamo
```

Se puede calcular en Python si se tiene:

```text
NumeroPrestamo
CalificacionAnterior
CalificacionActual
SaldoCapitalAnterior
SaldoCapitalActual
ProvisionAnterior
ProvisionActual
```

### Diferencias entre metricas

Formula:

```text
Diferencia = ValorActual - ValorHistorico
```

Aplica para:

```text
Operaciones
Clientes
SaldoCapital
CapitalVigente
CapitalNoDevenga
CapitalVencido
ProvisionRequerida
CarteraImproductiva
Mora
MoraPorcentaje
TotalRecuperado
```

### Agregaciones por dimension

Se pueden calcular en Python agrupando el universo filtrado por:

```text
Agencia
Asesor
CargoAsesor
UsuarioControl
CobranzaApoyo
EstadoPrestamo
Calificacion
Producto
TipoPrestamo
Provincia
Segmento
Abogados
```

Regla:

```text
Primero aplicar filtros.
Luego agregar.
Nunca agregar antes de filtrar.
```

### Provision con cobro de una cuota

Esta es una simulacion y conviene calcularla en Python.

Insumos requeridos:

```text
reglas de provision
calificacion simulada
dias mora simulados
saldo capital simulado
provision actual
saldo capital actual
```

Formula general:

```text
ProvisionConCobroUnaCuota = saldo capital simulado * porcentaje provision aplicable
```

Si no existe una regla aplicable, puede usarse una proporcion:

```text
ProvisionConCobroUnaCuota =
    (ProvisionActual / SaldoCapitalActual) * SaldoCapitalSimulado
```

Regla:

```text
Si SaldoCapitalSimulado <= 0, la provision simulada debe ser 0.
```

### Provision requerida

Tambien puede calcularse en Python si se tienen completas las reglas por:

```text
empresa
calificacion
rango de dias de mora
saldo base
porcentaje fijo/minimo/maximo
```

Recomendacion:

```text
Al inicio mantener ProvisionRequerida actual desde fuente/secundario para validacion.
Usar Python primero para simulaciones, variaciones y comparativos.
Luego migrar ProvisionRequerida a Python cuando las reglas esten completamente validadas.
```

## Valores que no conviene calcular en Python como primera fuente

Estos valores deberian venir desde SQL/Mongo fuente o desde un snapshot ya validado.

### Saldo capital

Motivo:

Es un dato fuente del prestamo y depende del estado transaccional del core.

### Capital no devenga

Motivo:

Depende de rubros, clasificacion de cartera y reglas contables.

### Capital vencido

Motivo:

Depende de rubros, clasificacion y vencimientos.

### Dias vencidos / dias mora actual

Motivo:

Depende del calendario, rubros, pagos, vencimientos y reglas del core.

### Calificacion actual

Motivo:

Puede calcularse en Python solo si estan completas todas las reglas. Al inicio debe venir desde fuente o tabla secundaria de provisiones.

### Estado del prestamo

Motivo:

Es estado fuente del core.

### Fecha ultimo pago

Motivo:

Debe venir desde movimientos o consolidado validado.

### Valor para estar al dia

Motivo:

Depende de rubros exigibles, intereses, mora y reglas del core.

### Valor hasta cuota actual

Motivo:

Depende de cuotas, vencimientos y rubros pendientes.

### Valor cancelar total

Motivo:

Depende de saldo, intereses, rubros y reglas de cancelacion.

### Rubros calculado/cobrado base

Motivo:

Son datos transaccionales del core.

### Eventos de pago base

Motivo:

Los pagos deben venir desde movimientos financieros. Python puede clasificarlos y agregarlos, pero no inventarlos.

## Tabla resumen

| Valor | Calcular en Python | Traer de base | Comentario |
| --- | --- | --- | --- |
| SaldoCapital | No | Si | Dato fuente del prestamo. |
| CapitalNoDevenga | No inicialmente | Si | Depende de rubros/clasificacion. |
| CapitalVencido | No inicialmente | Si | Depende de rubros/clasificacion. |
| CapitalVigente | Si | Opcional | Derivado de saldos. |
| CarteraImproductiva | Si | Opcional | Derivado simple. |
| Mora | Si | Opcional | Derivado simple. |
| MoraPorcentaje | Si | Opcional | Derivado simple. |
| ProvisionRequerida | Si, luego de validar reglas | Si inicialmente | Mantener fuente para validacion. |
| ProvisionConCobroUnaCuota | Si | No | Simulacion. |
| VariacionProvision | Si | No | Derivado comparativo. |
| VariacionSaldoCapital | Si | No | Derivado comparativo. |
| VariacionDiasMora | Si | No | Derivado comparativo. |
| TotalRecuperado | Si | No | Suma de componentes pagados. |
| CapitalPagado | No | Si | Viene de eventos de pago. |
| InteresPagado | No | Si | Viene de eventos de pago. |
| InteresMoraPagado | No | Si | Viene de eventos de pago. |
| SeguroPagado | No | Si | Viene de eventos de pago. |
| OtrosPagado | No | Si | Viene de eventos de pago. |
| NumeroOperaciones | Si | No | Conteo del universo filtrado. |
| Clientes | Si | No | Distinct del universo filtrado. |
| FaltantesEnMongo | Si | No | Diferencia de conjuntos. |
| MatrizTransicion | Si | No | Agrupacion por calificacion anterior/nueva. |

## Recomendacion de implementacion

Crear un modulo comun:

```text
services/prestamos/metricas.py
services/prestamos/provision_engine.py
```

`metricas.py` debe resolver derivados simples:

```text
CapitalVigente
CarteraImproductiva
Mora
MoraPorcentaje
Variaciones
Totales
Agregaciones
```

`provision_engine.py` debe resolver:

```text
ProvisionRequerida calculada
ProvisionConCobroUnaCuota
Porcentaje aplicable
Fallback proporcional
```

## Criterio para migrar ProvisionRequerida a Python

No migrar `ProvisionRequerida` completa a Python hasta cumplir:

```text
1. Las reglas de provision estan cargadas y versionadas.
2. Se comparo Python vs fuente actual por una muestra amplia.
3. Las diferencias estan explicadas por redondeo o reglas conocidas.
4. Se tiene trazabilidad de regla aplicada por prestamo.
5. La respuesta puede exponer regla/porcentaje usado si se necesita auditar.
```

Hasta entonces:

```text
ProvisionRequerida actual = fuente/secundario
Provision simulada = Python
VariacionProvision = Python
```

