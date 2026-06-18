# Universo central de prestamos para Negocios y Cobranza

## Objetivo

Este documento resume la revision de:

```text
routers/cobranza
services/negocios
schemas/cobranza
schemas/negocios
```

Tambien se revisaron las dependencias reales que consumen los routers de cobranza:

```text
services/cobranza/cobranza_analisis_service.py
services/cobranza/cobranza_ranking_service.py
services/cobranza/cobranza_recaudacion_acumulada_service.py
```

La recomendacion central es construir un solo universo de prestamos reutilizable para Negocios, Cobranza y Riesgos:

```text
SQL Core = fuente transaccional
Mongo historico = cortes cerrados
Mongo actual = snapshot operativo casi en tiempo real
Python = filtros, agregaciones, comparaciones y simulaciones
```

El objetivo no es reemplazar SQL como fuente de verdad. El objetivo es dejar de ejecutar SPs distintos para cada pantalla y partir de un mismo conjunto de prestamos, con filtros consistentes y datos normalizados.

## Lectura rapida

Si se quiere centralizar bien, no conviene partir de agregados por asesor, agencia o recuperacion. Conviene partir de documentos por prestamo.

Orden correcto:

```text
prestamos filtrados
  -> snapshots por prestamo
  -> eventos de recuperacion por prestamo
  -> calculos Python
  -> agregaciones por dimension
  -> respuesta del endpoint
```

Orden que se debe evitar:

```text
SP agregado
  -> filtros parciales
  -> comparacion
```

Ese orden impide usar bien filtros combinados porque la informacion del prestamo ya se perdio.

## Endpoints revisados

### Cobranza: recuperacion

Archivo:

```text
routers/cobranza/cobranza_analisis_router.py
```

Endpoints:

```text
POST /cobranza/recuperacion/filtros-contexto
POST /cobranza/recuperacion/filtros-contexto/usuarios-responsable-control
POST /cobranza/recuperacion/prestamos-recaudados-acumulados
POST /cobranza/recuperacion/analisis-agrupado
POST /cobranza/recuperacion/totales-al-dia-mes-anterior
POST /cobranza/recuperacion/totales-al-mes-anterior
```

Filtros usados:

```text
fecha_inicio
fecha_fin
id_agencia
filtrar_diferidos
codigo_usuario_responsable_control
codigo_usuario_cobranza_apoyo
codigo_usuario_asignado
id_cargo_asesor
calificaciones
```

Metricas usadas:

```text
CapitalPagado
InteresPagado
InteresMoraPagado
SeguroPagado
OtrosPagado
TotalRecuperado
CantidadRubros
```

Campos de detalle usados en `prestamos-recaudados-acumulados`:

```text
IdPrestamo
IdEmpresa
Agencia
Socio / Cliente
NumeroPrestamo
CodigoUsuarioAsignado
NombreUsuarioAsignado
CodigoUsuarioCobranzaApoyo
NombreUsuarioCobranzaApoyo
NombreCliente
IdentificacionDeudor
Division politica del deudor
CodigoEstado
EstadoPrestamo
CalificacionAnterior
CalificacionActual
DiaUltimoPago
DiasMoraAnterior
DiasMoraActual
SaldoCapitalAnterior
SaldoCapitalActual
ValorAlDia
CobroHastaCuota
PendientePago
PendientePagoMasCuotaPorVencer
CuotasPagadas
TotalCuotas
ProvisionCierreMes
ProvisionActual
ProvisionConCobroUnaCuota
```

### Cobranza: rankings

Archivo:

```text
routers/cobranza/cobranza_ranking_router.py
```

Endpoints:

```text
POST /cobranza/ranking/total-recuperado
POST /cobranza/ranking/asesores-recuperacion
```

Dimensiones de ranking:

```text
Agencia
UsuarioResponsableControl
EstadoPrestamo
Calificacion
Producto
TipoPrestamo
CargoAsesor
NombreAsesor
```

Comparaciones en ranking de asesores:

```text
SaldoCapitalFinMes
SaldoCapitalActual
VariacionSaldoCapital
ProvisionFinMes
ProvisionActual
VariacionProvision
NumeroOperacionesFinMes
NumeroOperacionesActual
VariacionNumeroOperaciones
TotalRecuperado
TotalCobroParaBajarUnaCuota
```

Tambien compara por:

```text
Asesor
UsuarioControl
CobranzaApoyo
CalificacionAnterior -> CalificacionActual
```

### Cobranza: division politica

Archivo:

```text
routers/cobranza/division_politica_router.py
```

Endpoint:

```text
GET /cobranza/division-politica
```

Esto puede mantenerse en SQL o moverse a catalogo cacheado. No es el centro del universo de prestamos, pero si sirve para filtros de zona.

### Negocios

Archivo:

```text
routers/negocios/negocios_router.py
```

Endpoints relevantes:

```text
GET  /negocios/evaluacion-negocios/situacion-crediticia
GET  /negocios/evaluacion-negocios/situacion-crediticia/totales-mongo
GET  /negocios/evaluacion-negocios/situacion-crediticia/asesores-comparacion
GET  /negocios/evaluacion-negocios/situacion-crediticia/apoyo-comparacion
GET  /negocios/evaluacion-negocios/filtros/cargos-activos
POST /negocios/evaluacion-negocios/matriz-transicion/tiempo-real
POST /negocios/evaluacion-negocios/cambios-calificacion/tiempo-real
```

Filtros actuales:

```text
id_agencia
filtrar_diferidos
codigo_usuario_control
filtros
filtrosSql
aplicar_filtros_en
excluir_estados
calificacion_anterior
calificacion_nueva
ids_prestamos
```

Dimensiones usadas:

```text
Agencia
TipoPrestamo
Producto
Provincia
Segmento
Calificacion
CargoAsesor
CodigoAsesor / NombreAsesor
UsuarioControl
CobranzaApoyo
Abogados
EstadoPrestamo
```

Metricas usadas:

```text
Operaciones
Clientes
SaldoCapital
CapitalVigente
CapitalNoDevenga
CapitalVencido
ProvisionRequerida
ProvisionConstituida
CarteraImproductiva
CarteraDiferida
CarteraCastigada
Mora
MoraPorcentaje
ExigibleCapital
ExigibleInteres
ExigibleMora
ExigibleOtros
ValorParaEstarAlDia
ValorHastaCuotaActual
ValorCancelarTotal
```

## Problemas actuales detectados

### 1. Hay varios universos distintos

Ejemplos:

- `evaluacion_negocios_matriz_services.py` arma un universo Mongo anterior y SQL actual por `NumeroPrestamo`.
- `cobranza_recaudacion_acumulada_service.py` ya tiene `_obtener_numeros_prestamo_universo_combinado`.
- `cobranza_ranking_service.py` arma universos de control y recuperacion dentro de consultas SQL.
- `evaluacion_negocios_services.py` usa SPs agregados para dashboard y asesores.
- `evaluacion_apoyo_services.py` usa un SP de detalle, pero luego vuelve a consultar Mongo por numeros de prestamo.

Todos intentan resolver lo mismo con formas distintas.

### 2. Los filtros no tienen un contrato unico

Cobranza usa:

```text
codigo_usuario_responsable_control
codigo_usuario_cobranza_apoyo
codigo_usuario_asignado
id_cargo_asesor
```

Negocios usa:

```text
CodigoAsesor
NombreAsesor
CargoAsesor
EstadoPrestamo
filtros
filtrosSql
```

La pantalla puede terminar enviando filtros equivalentes con nombres distintos.

### 3. Mongo historico no tiene todos los campos normalizados

En el codigo se leen variantes como:

```text
ESDIFERIDO
EsDiferido
Diferido
ProvisionConsituida
ProvisionConstituida
CodigoUsuario
CodigoAsesor
NombreCompleto
NombreAsesor
```

Esto obliga a duplicar normalizaciones en cada servicio.

### 4. Los reportes de cobranza recalculan eventos desde SQL

Los endpoints de recuperacion vuelven a leer:

```text
FINANCIERO.MOVIMIENTO_TRANSACCION
FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE
COLOCACION.PRESTAMO_MOVIMIENTOTRANSACCIONDETALLE
COLOCACION.PRESTAMO_RUBRO_MOVIMIENTOTRANSACCIONDETALLE
COLOCACION.RUBRO
COLOCACION.TIPO_RUBRO
```

Esto es correcto como fuente, pero pesado para dashboards.

### 5. Cobranza importa helpers privados de Negocios

`cobranza_ranking_service.py` importa funciones privadas de `evaluacion_negocios_services.py`, por ejemplo:

```text
_agregado_mongo_asesores
_fecha_cierre_mes_anterior
_map_reasignaciones_asesor
_to_float_safe_mongo
```

Eso es una senal clara de que falta un modulo comun.

## Colecciones Mongo recomendadas

### 1. `SituacionCrediticiaActual`

Uso:

Snapshot actual operativo por prestamo. Debe permitir responder rapido a filtros, dashboards, matriz, comparaciones y rankings.

Granularidad:

```text
1 documento por prestamo
```

Clave recomendada:

```text
IdPrestamo
NumeroPrestamo
```

Documento sugerido:

```json
{
  "IdPrestamo": 123,
  "NumeroPrestamo": "00012345",
  "IdEmpresa": 1,
  "IdAgencia": 2,
  "Agencia": "AGENCIA CENTRO",

  "Cliente": 456,
  "NumeroCliente": 456,
  "IdPersona": 789,
  "NombreCliente": "CLIENTE EJEMPLO",
  "Identificacion": "0102030405",

  "CodigoEstadoPrestamo": "V",
  "EstadoPrestamo": "VIGENTE",
  "EsCancelado": false,
  "EsCanceladoPeriodo": false,
  "FechaCancelacion": null,

  "CodigoTipoPrestamo": "MIC",
  "TipoPrestamo": "MICROCREDITO",
  "Producto": "MICROCREDITO MINORISTA",
  "Segmento": "MICRO",
  "Provincia": "AZUAY",
  "Canton": "CUENCA",
  "Parroquia": "EL SAGRARIO",

  "CodigoAsesor": "JPEREZ",
  "CodigoUsuario": "JPEREZ",
  "NombreAsesor": "JUAN PEREZ",
  "NombreCompleto": "JUAN PEREZ",
  "IdCargoAsesor": 10,
  "CargoAsesor": "ASESOR DE NEGOCIOS",

  "CodigoUsuarioControl": "MLOPEZ",
  "UsuarioControl": "MARIA LOPEZ",
  "CodigoUsuarioCobranzaApoyo": "CCRUZ",
  "CobranzaApoyo": "CARLOS CRUZ",
  "Abogados": "SIN ABOGADO",

  "FechaAdjudicacion": "2025-11-10",
  "FechaVencimiento": "2027-11-10",
  "UltimoPago": "2026-06-15",
  "FechaUltimoPago": "2026-06-15",

  "Calificacion": "A-1",
  "CalificacionCore": "A-1",
  "DiasVencidos": 0,
  "Condicion": "NORMAL",
  "TipoCondicion": "NORMAL",
  "EsDiferido": false,

  "SaldoCapital": 1000.0,
  "CapitalVigente": 1000.0,
  "CapitalNoDevenga": 0.0,
  "CapitalVencido": 0.0,
  "CarteraImproductiva": 0.0,
  "CarteraDiferida": 0.0,
  "CarteraCastigada": 0.0,
  "Mora": 0.0,
  "MoraPorcentaje": 0.0,

  "ProvisionRequerida": 10.0,
  "ProvisionConstituida": 10.0,

  "ExigibleCapital": 0.0,
  "ExigibleInteres": 0.0,
  "ExigibleMora": 0.0,
  "ExigibleOtros": 0.0,
  "ValorParaEstarAlDia": 0.0,
  "ValorHastaCuotaActual": 120.0,
  "ValorCancelarTotal": 1010.0,

  "NumeroCuotaActualNoPagada": 5,
  "CobroHastaCuota": 120.0,
  "CuotasPagadas": 4,
  "TotalCuotas": 24,
  "SaldoCapitalConCobroUnaCuota": 930.0,
  "DiasMoraConCobroUnaCuota": 0,
  "CalificacionConCobroUnaCuota": "A-1",

  "source": "sql_core",
  "as_of": "2026-06-18T10:30:00",
  "data_version": "20260618-1030",
  "updated_at": "2026-06-18T10:30:05"
}
```

Campos minimos obligatorios:

```text
IdPrestamo
NumeroPrestamo
IdAgencia
Agencia
CodigoEstadoPrestamo
EstadoPrestamo
CodigoAsesor
NombreAsesor
IdCargoAsesor
CargoAsesor
CodigoUsuarioControl
UsuarioControl
CodigoUsuarioCobranzaApoyo
CobranzaApoyo
Calificacion
DiasVencidos
EsDiferido
SaldoCapital
ProvisionRequerida
ProvisionConstituida
ExigibleCapital
ExigibleInteres
ExigibleMora
ExigibleOtros
ValorParaEstarAlDia
ValorHastaCuotaActual
ValorCancelarTotal
as_of
data_version
```

### 2. `SituacionCrediticia`

Uso:

Cortes historicos cerrados. Ya existe y se usa en todos los comparativos.

Recomendacion:

Mantenerla como historico inmutable por `fecha_corte`, pero normalizar campos hacia adelante.

Campos que deben quedar consistentes en los nuevos cortes:

```text
fecha_corte
IdPrestamo
NumeroPrestamo
IdAgencia
Agencia
CodigoEstadoPrestamo
EstadoPrestamo
CodigoAsesor
CodigoUsuario
NombreAsesor
NombreCompleto
IdCargoAsesor
CargoAsesor
CodigoUsuarioControl
UsuarioControl
CodigoUsuarioCobranzaApoyo
CobranzaApoyo
Abogados
Cliente
NumeroCliente
NombreCliente
Identificacion
CodigoTipoPrestamo
TipoPrestamo
Producto
Segmento
Provincia
Canton
Parroquia
Calificacion
DiasVencidos
EsDiferido
SaldoCapital
CapitalVigente
CapitalNoDevenga
CapitalVencido
CarteraImproductiva
CarteraDiferida
CarteraCastigada
ProvisionRequerida
ProvisionConstituida
ExigibleCapital
ExigibleInteres
ExigibleMora
ExigibleOtros
ValorParaEstarAlDia
ValorHastaCuotaActual
ValorCancelarTotal
FechaAdjudicacion
FechaVencimiento
UltimoPago
FechaUltimoPago
Condicion
TipoCondicion
data_version
```

Compatibilidad:

Durante una transicion se pueden seguir leyendo alias viejos:

```text
ESDIFERIDO
Diferido
ProvisionConsituida
```

pero el ETL nuevo deberia escribir `EsDiferido` y `ProvisionConstituida`.

### 3. `RecuperacionEventos`

Uso:

Eventos normalizados de recuperacion/pago. Esta coleccion evita recalcular siempre desde tablas financieras.

Granularidad recomendada:

```text
1 documento por movimiento detalle / rubro / prestamo
```

Documento sugerido:

```json
{
  "IdMovimientoTransaccion": 1001,
  "IdMovimientoTransaccionDetalle": 2001,
  "IdPrestamo": 123,
  "NumeroPrestamo": "00012345",
  "IdRubro": 55,
  "CodigoTipoRubro": "CAP",
  "Rubro": "CAPITAL",
  "FechaPago": "2026-06-18T09:15:00",
  "IdTransaccion": 8,
  "EsReverso": false,
  "EsValidoDashboard": true,

  "Valor": 50.0,
  "CapitalPagado": 50.0,
  "InteresPagado": 0.0,
  "InteresMoraPagado": 0.0,
  "SeguroPagado": 0.0,
  "OtrosPagado": 0.0,
  "TotalRecuperado": 50.0,

  "IdAgencia": 2,
  "Agencia": "AGENCIA CENTRO",
  "CodigoAsesor": "JPEREZ",
  "NombreAsesor": "JUAN PEREZ",
  "IdCargoAsesor": 10,
  "CargoAsesor": "ASESOR DE NEGOCIOS",
  "CodigoUsuarioControl": "MLOPEZ",
  "UsuarioControl": "MARIA LOPEZ",
  "CodigoUsuarioCobranzaApoyo": "CCRUZ",
  "CobranzaApoyo": "CARLOS CRUZ",

  "CodigoEstadoPrestamo": "V",
  "EstadoPrestamo": "VIGENTE",
  "Calificacion": "A-1",
  "Producto": "MICROCREDITO",
  "TipoPrestamo": "MICROCREDITO",
  "EsDiferido": false,

  "source": "sql_core",
  "created_at_source": "2026-06-18T09:15:00",
  "synced_at": "2026-06-18T09:16:00",
  "data_version": "20260618-0916"
}
```

Nota importante:

El codigo actual excluye `T.ID <> 12`. Esa regla debe quedar expresada en `EsValidoDashboard` o en el proceso de carga, para no repetirla en cada endpoint.

### 4. `RecuperacionDiariaPrestamo`

Uso:

Preagregado diario opcional para dashboards rapidos.

Granularidad:

```text
1 documento por fecha + prestamo
```

Documento sugerido:

```json
{
  "fecha": "2026-06-18",
  "IdPrestamo": 123,
  "NumeroPrestamo": "00012345",
  "CapitalPagado": 50.0,
  "InteresPagado": 5.0,
  "InteresMoraPagado": 1.0,
  "SeguroPagado": 0.0,
  "OtrosPagado": 0.0,
  "TotalRecuperado": 56.0,
  "CantidadRubros": 3,
  "data_version": "20260618-0916"
}
```

Esto no reemplaza `RecuperacionEventos`. Es un acelerador.

### 5. `PrestamoResponsableHistorial`

Uso:

Resolver correctamente usuario control y cobranza apoyo segun fecha.

Motivo:

El codigo actual a veces usa responsable actual y a veces busca historico con `PRESTAMO_USUARIO_CONTROL_HISTORICO` segun una fecha. Para reportes de cobranza por rango, esto importa.

Documento sugerido:

```json
{
  "IdPrestamo": 123,
  "NumeroPrestamo": "00012345",
  "CodigoUsuarioControl": "MLOPEZ",
  "UsuarioControl": "MARIA LOPEZ",
  "CodigoUsuarioCobranzaApoyo": "CCRUZ",
  "CobranzaApoyo": "CARLOS CRUZ",
  "Nivel": 1,
  "FechaInicio": "2026-01-01",
  "FechaFin": "2026-12-31",
  "Activo": true
}
```

### 6. `AsesorPrestamoCambio`

Uso:

Normalizar reasignaciones entre cierre historico y actual.

Motivo:

`asesores-comparacion` usa `COLOCACION.ASESOR_PRESTAMO_CAMBIO` para mover prestamos historicos al asesor destino y evitar diferencias falsas. Esa regla debe ser comun.

Documento sugerido:

```json
{
  "IdPrestamo": 123,
  "NumeroPrestamo": "00012345",
  "CodigoUsuarioOrigen": "JPEREZ",
  "CodigoUsuarioDestino": "MLOPEZ",
  "FechaRef": "2026-06-10T08:00:00",
  "IdCambio": 999
}
```

### 7. `ProvisionReglas`

Uso:

Cache de reglas para calculo Python de provisiones.

Fuente:

```text
CalificacionPrestamoInformacion
```

La logica de `cobranza_recaudacion_acumulada_service.py` ya calcula una provision simulada con:

```text
calificacion simulada
dias mora simulados
saldo capital simulado
provision actual
saldo capital actual
```

Esa logica debe pasar a un motor comun.

Documento sugerido:

```json
{
  "IdEmpresa": 1,
  "Calificacion": "A-1",
  "DiaInicio": 0,
  "DiaFin": 15,
  "EsPorcentajeFijo": true,
  "PorcentajeFijo": 1.0,
  "PorcentajeMinimo": 1.0,
  "PorcentajeMaximo": 1.0,
  "Activo": true
}
```

### 8. `CatalogosNegocios`

Uso:

Catalogos chicos y filtros base.

Puede incluir:

```text
Agencias
EstadoPrestamo
Cargos
Usuarios
TipoPrestamo
Producto
DivisionPolitica
Calificaciones
```

No es obligatorio mover todo a Mongo al inicio, pero ayuda a evitar consultas repetitivas para filtros.

## Indices recomendados

### `SituacionCrediticiaActual`

```javascript
db.SituacionCrediticiaActual.createIndex({ NumeroPrestamo: 1 }, { unique: true })
db.SituacionCrediticiaActual.createIndex({ IdPrestamo: 1 }, { unique: true })
db.SituacionCrediticiaActual.createIndex({ IdAgencia: 1, EstadoPrestamo: 1 })
db.SituacionCrediticiaActual.createIndex({ IdAgencia: 1, CodigoAsesor: 1 })
db.SituacionCrediticiaActual.createIndex({ CodigoUsuarioControl: 1 })
db.SituacionCrediticiaActual.createIndex({ CodigoUsuarioCobranzaApoyo: 1 })
db.SituacionCrediticiaActual.createIndex({ IdCargoAsesor: 1 })
db.SituacionCrediticiaActual.createIndex({ Calificacion: 1 })
db.SituacionCrediticiaActual.createIndex({ Producto: 1 })
db.SituacionCrediticiaActual.createIndex({ TipoPrestamo: 1 })
db.SituacionCrediticiaActual.createIndex({ Provincia: 1 })
db.SituacionCrediticiaActual.createIndex({ EsDiferido: 1 })
db.SituacionCrediticiaActual.createIndex({ as_of: 1 })
```

### `SituacionCrediticia`

```javascript
db.SituacionCrediticia.createIndex({ fecha_corte: 1, NumeroPrestamo: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, IdPrestamo: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, Agencia: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, IdAgencia: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, EstadoPrestamo: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, CodigoAsesor: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, CodigoUsuarioControl: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, CodigoUsuarioCobranzaApoyo: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, IdCargoAsesor: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, Calificacion: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, EsDiferido: 1 })
```

### `RecuperacionEventos`

```javascript
db.RecuperacionEventos.createIndex({ FechaPago: 1, IdPrestamo: 1 })
db.RecuperacionEventos.createIndex({ NumeroPrestamo: 1, FechaPago: 1 })
db.RecuperacionEventos.createIndex({ IdAgencia: 1, FechaPago: 1 })
db.RecuperacionEventos.createIndex({ CodigoAsesor: 1, FechaPago: 1 })
db.RecuperacionEventos.createIndex({ CodigoUsuarioControl: 1, FechaPago: 1 })
db.RecuperacionEventos.createIndex({ CodigoUsuarioCobranzaApoyo: 1, FechaPago: 1 })
db.RecuperacionEventos.createIndex({ IdCargoAsesor: 1, FechaPago: 1 })
db.RecuperacionEventos.createIndex({ Calificacion: 1, FechaPago: 1 })
db.RecuperacionEventos.createIndex({ EsDiferido: 1, FechaPago: 1 })
db.RecuperacionEventos.createIndex({ IdMovimientoTransaccionDetalle: 1, IdRubro: 1 }, { unique: true })
```

### `RecuperacionDiariaPrestamo`

```javascript
db.RecuperacionDiariaPrestamo.createIndex({ fecha: 1, IdPrestamo: 1 }, { unique: true })
db.RecuperacionDiariaPrestamo.createIndex({ fecha: 1, NumeroPrestamo: 1 })
```

### `PrestamoResponsableHistorial`

```javascript
db.PrestamoResponsableHistorial.createIndex({ IdPrestamo: 1, FechaInicio: 1, FechaFin: 1 })
db.PrestamoResponsableHistorial.createIndex({ CodigoUsuarioControl: 1, FechaInicio: 1, FechaFin: 1 })
db.PrestamoResponsableHistorial.createIndex({ CodigoUsuarioCobranzaApoyo: 1, FechaInicio: 1, FechaFin: 1 })
```

## Contrato unico de filtros

Crear un schema comun, por ejemplo:

```python
class PrestamoUniverseRequest(BaseModel):
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    fecha_corte_anterior: datetime | None = None
    fecha_corte_actual: datetime | None = None

    ids_prestamo: list[int] = []
    numeros_prestamo: list[str] = []

    agencias: list[int] = []
    agencia_nombres: list[str] = []
    codigos_asesor: list[str] = []
    codigos_usuario_control: list[str] = []
    codigos_usuario_cobranza_apoyo: list[str] = []
    ids_cargo_asesor: list[int] = []

    estados_prestamo: list[str] = []
    calificaciones: list[str] = []
    productos: list[str] = []
    tipos_prestamo: list[str] = []
    provincias: list[str] = []

    filtrar_diferidos: bool | None = None
    excluir_cancelados: bool = True
    incluir_cancelados_periodo: bool = False

    aplicar_filtros_en: Literal["actual", "historico", "ambos"] = "actual"
```

Reglas:

- `agencias` debe ser preferido para actual.
- `agencia_nombres` solo debe usarse como compatibilidad historica si el corte Mongo no tiene `IdAgencia`.
- `codigos_asesor` debe normalizar `CodigoUsuario`, `CodigoAsesor` y `CODIGOUSUARIO`.
- `filtrar_diferidos` debe operar sobre `EsDiferido` booleano.
- `excluir_cancelados` debe mapear `CodigoEstadoPrestamo = 'C'` y `EstadoPrestamo = 'CANCELADO'`.
- `incluir_cancelados_periodo` es importante para reportes de cobranza que comparan cierre anterior contra actual.

## Servicios comunes recomendados

### 1. `services/common/fechas.py`

```python
fecha_corte_actual()
cierre_mes_anterior(base)
validar_rango_fechas(fecha_inicio, fecha_fin, fecha_sistema)
mismo_mes(fecha_inicio, fecha_fin)
rango_mismo_dia_mes_anterior(fecha_inicio, fecha_fin)
rango_cierre_mes_anterior(fecha_fin)
```

### 2. `services/common/numeros.py`

```python
to_float_safe(value)
to_int_safe(value)
round_money(value)
normalizar_numero_prestamo(value)
```

### 3. `services/prestamos/universe_filters.py`

```python
normalizar_filtros(request)
resolver_agencias(db, filtros)
resolver_estados(db, filtros)
build_mongo_match_actual(filtros)
build_mongo_match_historico(filtros)
filtros_hash(filtros)
```

### 4. `services/prestamos/snapshot_service.py`

```python
obtener_snapshot_actual(filtros) -> dict[numero_prestamo, PrestamoSnapshot]
obtener_snapshot_historico(fecha_corte, filtros) -> dict[numero_prestamo, PrestamoSnapshot]
obtener_snapshot_actual_por_numeros(numeros)
obtener_snapshot_historico_por_numeros(fecha_corte, numeros)
```

### 5. `services/prestamos/universe_service.py`

```python
obtener_universo_actual(filtros) -> set[str]
obtener_universo_historico(fecha_corte, filtros) -> set[str]
obtener_universo_combinado(fecha_corte, filtros) -> set[str]
obtener_universo_interseccion(fecha_corte, filtros) -> set[str]
```

### 6. `services/prestamos/dimensions.py`

```python
agregar_por_dimension(snapshot, dimension)
comparar_por_dimension(actual, historico, dimension)
agregar_metricas_cartera(items)
agregar_metricas_recuperacion(eventos)
```

### 7. `services/prestamos/provision_engine.py`

```python
calcular_provision_requerida(snapshot, reglas)
calcular_provision_con_cobro(snapshot, escenario, reglas)
calcular_variacion_provision(snapshot_anterior, snapshot_actual)
```

### 8. `services/cobranza/recuperacion_eventos_service.py`

```python
obtener_eventos_recuperacion(fecha_inicio, fecha_fin, universo, filtros)
agregar_recuperacion_por_prestamo(eventos)
agregar_recuperacion_por_dimension(eventos, snapshots, dimension)
```

## Flujo correcto para un solo universo

### Flujo para dashboard de Negocios

```text
Request
  -> normalizar filtros
  -> consultar SituacionCrediticiaActual
  -> obtener universo actual
  -> agregar por dimensiones:
       Agencia
       Producto
       Provincia
       Calificacion
       CargoAsesor
       NombreAsesor
  -> calcular totales
  -> responder
```

### Flujo para asesores-comparacion

```text
Request
  -> normalizar filtros
  -> cierre anterior = ultimo dia mes anterior
  -> universo historico Mongo
  -> universo actual Mongo actual
  -> aplicar reasignaciones de asesor entre cortes
  -> agregar historico por asesor/agencia
  -> agregar actual por asesor/agencia
  -> comparar
  -> responder
```

### Flujo para apoyo-comparacion

```text
Request
  -> normalizar filtros
  -> universo combinado actual + historico
  -> snapshots historico y actual por NumeroPrestamo
  -> agregar por:
       Abogados
       UsuarioControl
       CobranzaApoyo
  -> comparar
  -> responder
```

### Flujo para matriz de transicion

```text
Request
  -> normalizar filtros
  -> snapshot historico por fecha_corte_anterior
  -> snapshot actual desde SituacionCrediticiaActual
  -> filtrar segun aplicar_filtros_en
  -> cruzar por NumeroPrestamo
  -> calcular matriz CalificacionAnterior -> CalificacionActual
  -> calcular saldos, provisiones, exigibles y variaciones
  -> responder
```

### Flujo para cambios de calificacion

```text
Request con ids/numeros
  -> resolver ids/numeros en snapshot actual
  -> buscar historico por NumeroPrestamo
  -> construir detalle anterior/nuevo
  -> responder
```

### Flujo para recuperacion acumulada

```text
Request
  -> normalizar filtros
  -> universo actual/historico segun periodo
  -> recuperar eventos desde RecuperacionEventos o RecuperacionDiariaPrestamo
  -> agrupar por NumeroPrestamo
  -> unir con snapshot anterior y actual
  -> calcular:
       variacion dias mora
       variacion saldo
       provision actual
       provision cierre
       provision con cobro una cuota
  -> enriquecer datos de persona/garantes si el detalle lo requiere
  -> responder
```

### Flujo para ranking total recuperado

```text
Request
  -> normalizar filtros
  -> universo actual filtrado
  -> eventos recuperacion por fecha
  -> unir eventos con snapshot actual
  -> agregar TotalRecuperado por:
       Agencia
       UsuarioResponsableControl
       EstadoPrestamo
       Calificacion
       Producto
       TipoPrestamo
       CargoAsesor
       NombreAsesor
  -> responder
```

### Flujo para ranking asesores recuperacion

```text
Request
  -> normalizar filtros
  -> cierre anterior = cierre mes anterior relativo al inicio
  -> universo historico + actual
  -> eventos recuperacion por fecha
  -> snapshots historico y actual
  -> agregar por:
       asesor
       usuario control
       cobranza apoyo
       calificacion anterior/nueva
  -> calcular saldo/provision/operaciones/recuperacion
  -> responder
```

## Como mantener "tiempo real"

Hay que distinguir dos niveles:

### Tiempo real exacto

Consulta directa a SQL Core en el momento.

Ventajas:

- Exactitud transaccional.

Problemas:

- Lento para dashboards.
- Carga alta.
- Cada pantalla termina con SQL propio.

### Tiempo real operativo recomendado

Mongo actual actualizado cada pocos minutos o por cambios incrementales.

Ventajas:

- Rapido.
- Consistente entre pantallas.
- Permite filtros ricos.
- Permite cache y agregaciones.

Recomendacion:

```text
Usar Mongo actual por defecto.
Permitir refresh SQL puntual por NumeroPrestamo o por agencia cuando se necesite exactitud inmediata.
```

El documento de respuesta debe exponer:

```json
{
  "data_as_of": "2026-06-18T10:30:00",
  "data_version": "20260618-1030",
  "source": "mongo_actual"
}
```

Si la data esta vencida:

```text
si as_of > TTL permitido
  -> refrescar snapshot actual
  -> o responder 409/202 segun politica del endpoint
```

TTL sugeridos:

```text
Filtros contextuales: 10 a 30 minutos
Dashboard negocios: 1 a 5 minutos
Ranking recuperacion: 1 a 5 minutos
Detalle critico por prestamo: refresh SQL puntual
Historicos cerrados: horas o dias
```

## Sincronizacion recomendada

### Job 1: snapshot actual de prestamos

Frecuencia:

```text
cada 1 a 5 minutos
```

Proceso:

```text
leer prestamos activos y cancelados recientes desde SQL
leer calificacion/provision actual
leer rubros exigibles
leer datos de cuotas
leer responsable control/cobranza apoyo
leer asesor/cargo/agencia/producto/cliente/division politica
calcular metricas normalizadas
upsert en SituacionCrediticiaActual
marcar prestamos ausentes como inactivos si aplica
```

### Job 2: eventos de recuperacion

Frecuencia:

```text
cada 1 a 5 minutos
```

Proceso:

```text
leer movimientos nuevos por IdMovimientoTransaccionDetalle o FechaSistema
clasificar rubros en capital/interes/mora/seguro/otros
excluir reversos/transaccion no valida segun regla actual
upsert en RecuperacionEventos
actualizar RecuperacionDiariaPrestamo
```

### Job 3: responsables historicos

Frecuencia:

```text
cada 15 a 60 minutos o por cambio
```

Proceso:

```text
leer PRESTAMO_USUARIO_CONTROL y PRESTAMO_USUARIO_CONTROL_HISTORICO
upsert en PrestamoResponsableHistorial
```

### Job 4: cierre historico

Frecuencia:

```text
mensual/cierre
```

Proceso:

```text
generar SituacionCrediticia con fecha_corte
validar conteos/totales contra SQL
marcar corte como cerrado
no modificar salvo reproceso con nueva data_version
```

## Orden de migracion recomendado

### Fase 1: normalizar lectura sin cambiar respuestas

1. Crear `PrestamoUniverseRequest`.
2. Crear servicios comunes de fechas, numeros, filtros, snapshots y dimensiones.
3. No tocar aun los endpoints publicos.
4. Migrar helpers privados compartidos a modulos comunes.

### Fase 2: crear Mongo actual

1. Crear `SituacionCrediticiaActual`.
2. Implementar job de carga inicial.
3. Implementar indices.
4. Comparar totales contra `COLOCACION.SITUACION_CREDITICIA_DATASAC_DASHBOARD`.

### Fase 3: migrar Negocios

1. Migrar `situacion-crediticia` para agregar desde `SituacionCrediticiaActual`.
2. Migrar `asesores-comparacion` para comparar `SituacionCrediticiaActual` vs `SituacionCrediticia`.
3. Migrar `apoyo-comparacion` para agregar por usuario control/cobranza apoyo/abogados desde snapshots.
4. Migrar filtros de negocios a filtros contextuales desde universo.

### Fase 4: migrar matriz y cambios

1. Sustituir el SP actual de matriz por `SituacionCrediticiaActual`.
2. Mantener fallback SQL mientras se valida.
3. Cambios de calificacion deben leer snapshots por `ids_prestamo` o `numeros_prestamo`.

### Fase 5: migrar Cobranza

1. Crear `RecuperacionEventos`.
2. Migrar `ranking/total-recuperado`.
3. Migrar `recuperacion/filtros-contexto`.
4. Migrar `ranking/asesores-recuperacion`.
5. Migrar `prestamos-recaudados-acumulados`.

### Fase 6: motor de provisiones Python

1. Extraer reglas de provision.
2. Crear `provision_engine.py`.
3. Validar contra resultados actuales de SQL/secundario.
4. Usarlo en Negocios, Cobranza y Riesgos.

## Validaciones necesarias

Antes de reemplazar cada endpoint:

```text
comparar conteo de prestamos
comparar saldo capital total
comparar provision requerida total
comparar operaciones por agencia
comparar recuperacion total por rango
comparar top 20 asesores
comparar filtros disponibles
comparar faltantes en mongo/sql
```

Tolerancia sugerida para dinero:

```text
0.01 por prestamo
1.00 a 5.00 en totales grandes, segun redondeos
```

## Decision final recomendada

Guardar en Mongo:

1. Snapshot actual por prestamo: `SituacionCrediticiaActual`.
2. Snapshot historico mensual por prestamo: `SituacionCrediticia`.
3. Eventos de recuperacion: `RecuperacionEventos`.
4. Preagregado diario por prestamo: `RecuperacionDiariaPrestamo`.
5. Historial de responsables: `PrestamoResponsableHistorial`.
6. Cambios de asesor: `AsesorPrestamoCambio`.
7. Reglas de provision o cache de reglas: `ProvisionReglas`.
8. Catalogos chicos: `CatalogosNegocios`.

Con eso, el universo unico puede responder:

```text
Negocios situacion crediticia
Asesores comparacion
Apoyo comparacion
Matriz de transicion
Cambios de calificacion
Filtros contextuales
Cobranza recuperacion acumulada
Ranking total recuperado
Ranking asesores recuperacion
```

La regla de arquitectura debe ser:

```text
Todo reporte parte de NumeroPrestamo / IdPrestamo.
Todo filtro se aplica antes de agregar.
Toda agregacion se deriva del mismo snapshot/eventos.
SQL queda como fuente transaccional y fallback de exactitud.
Mongo queda como read model operativo y rapido.
```

