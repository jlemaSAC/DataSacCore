# Evaluacion negocios: asesores-comparacion y control central de prestamos

## Alcance

Este documento revisa especificamente el endpoint:

```text
GET /negocios/evaluacion-negocios/situacion-crediticia/asesores-comparacion
```

En el router local la ruta aparece como:

```text
/evaluacion-negocios/situacion-crediticia/asesores-comparacion
```

pero `main.py` monta `routers/negocios/negocios_router.py` con prefijo `/negocios`, por eso la ruta publica completa queda con `/negocios`.

El objetivo del endpoint actual es comparar la cartera vigente por asesor entre:

- SQL Server/core actual: corte del dia de ejecucion.
- Mongo `DataSac.SituacionCrediticia`: cierre del mes anterior.

Desde esta revision se propone partir hacia un control central basado en universo de prestamos, para que asesores, matriz de transicion, cambios de calificacion, apoyo, cobranza y filtros usen una misma forma de buscar, filtrar y comparar.

## Archivos involucrados

```text
main.py
routers/negocios/negocios_router.py
services/negocios/evaluacion_negocios_services.py
services/negocios/filtros_negocios_services.py
services/negocios/evaluacion_negocios_matriz_services.py
schemas/negocios/evaluacion_negocios_schema.py
schemas/riesgo/riesgos_schema.py
storedProcedures/COLOCACION. SITUACION_CREDITICIA_DATASAC_DASHBOARD_ASESORES.sql
docs/arquitectura-reportes-negocios-cobranza.md
```

## Contrato actual del endpoint

### Metodo y parametros

```text
GET /negocios/evaluacion-negocios/situacion-crediticia/asesores-comparacion
```

Query params:

| Parametro | Tipo | Default | Uso |
| --- | --- | ---: | --- |
| `id_agencia` | `int` | `0` | `0` significa consolidado. Si es mayor a 0, filtra una agencia especifica. |
| `filtrar_diferidos` | `bool | null` | `null` | `null` incluye todo, `true` solo diferidos, `false` excluye diferidos. |

No recibe body. Por eso hoy no puede aplicar filtros dinamicos como asesor, cargo, estado, calificacion, producto, provincia o lista de prestamos.

### Respuesta

El schema principal es `SituacionCrediticiaAsesoresResponse`:

```text
fecha_corte_sp
fecha_corte_mongo
comparacion[]
agencias_gerentes_oficina[]
faltantes_en_mongo[]
faltantes_en_sp[]
```

Cada item de `comparacion` incluye:

```text
CodigoUsuario
NombreAsesorSP
CargoAsesorSP
NombreAsesorMongo
AgenciaSP
AgenciaMongo
ValoresSP
ValoresMongo
Diferencias
```

Las metricas comparadas son:

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
```

## Flujo actual paso a paso

### 1. Router

`routers/negocios/negocios_router.py` define el endpoint y delega directamente al servicio:

```python
return obtener_situacion_crediticia_dashboard_asesores(
    db, id_agencia=id_agencia, filtrar_diferidos=filtrar_diferidos
)
```

No existe validacion adicional en el router. La sesion SQL viene de `get_db_saccore`.

### 2. Calculo de fechas

En `obtener_situacion_crediticia_dashboard_asesores`:

- `fecha_corte_sp` se calcula con `datetime.now().strftime("%Y%m%d")`.
- `fecha_corte_mongo` se calcula con `_fecha_cierre_mes_anterior()`.
- Si hoy fuera `2026-06-17`, entonces:
  - `fecha_corte_sp = "20260617"`
  - `fecha_corte_mongo = "20260531"`

Este comportamiento es importante: el endpoint siempre compara "hoy SQL" contra "ultimo cierre mensual Mongo".

### 3. Modo consolidado vs agencia

```python
separar_por_agencia = id_agencia == 0
```

Cuando `id_agencia = 0`, la clave interna no es solo el codigo de asesor. Se arma como:

```text
CodigoUsuario::Agencia
```

Esto evita que un mismo usuario en agencias distintas se sobreescriba en el mapa interno. En la respuesta, sin embargo, se expone principalmente `CodigoUsuario`, por lo que puede haber filas con el mismo codigo si el asesor aparece en varias agencias.

Cuando `id_agencia > 0`, primero se resuelve el nombre de la agencia en SQL:

```sql
SELECT NOMBRE
FROM GENERAL.AGENCIA WITH (NOLOCK)
WHERE ID = ?
```

Ese nombre se usa para filtrar Mongo por `Agencia`.

### 4. Reasignaciones de asesor entre cortes

Antes de comparar, el servicio consulta `COLOCACION.ASESOR_PRESTAMO_CAMBIO` con `_map_reasignaciones_asesor`.

La funcion construye un mapa:

```text
NumeroPrestamo -> CodigoUsuarioDestino
```

tomando el ultimo cambio entre:

```text
fecha_corte_mongo <= cambio <= fecha_corte_sp
```

Uso practico:

- Si un prestamo estaba en Mongo con asesor A al cierre anterior.
- Pero fue reasignado a asesor B antes del corte SQL actual.
- Al agregar Mongo, ese prestamo se puede mover al asesor B mediante `codigo_override`.

Esto reduce diferencias falsas por cambios de asesor entre cortes.

### 5. Corte actual en SQL Server

El servicio ejecuta:

```sql
SET NOCOUNT ON;
EXEC COLOCACION.SITUACION_CREDITICIA_DATASAC_DASHBOARD_ASESORES
    @IdAgencia = ?,
    @FiltrarDiferidos = ?;
```

Luego convierte cada fila en un item del mapa `sp_map`.

Clave interna:

```text
CodigoUsuario
```

o, en consolidado:

```text
CodigoUsuario::Agencia
```

Valores normalizados:

- Si `CapitalVigente` no viene util, se calcula como `SaldoCapital - (CapitalNoDevenga + CapitalVencido)`.
- `CarteraImproductiva = CapitalNoDevenga + CapitalVencido`.
- `Mora = CarteraImproductiva / SaldoCapital`.
- `MoraPorcentaje = Mora * 100`.

### 6. Logica del stored procedure de asesores

El SP `COLOCACION.SITUACION_CREDITICIA_DATASAC_DASHBOARD_ASESORES` hace:

1. Define `@FechaCorte` con `GETDATE()` en formato `YYYYMMDD`.
2. Crea `#UltimaCalificacion`.
3. Consulta la ultima calificacion desde el linked server `[192.168.1.205]`, base `SAC_PROVICIONES`, tabla `COLOCACION.PRESTAMO_CALIFICACION`.
4. Calcula rubros no devenga y vencidos desde:
   - `COLOCACION.PRESTAMO_RUBRO`
   - `COLOCACION.PRESTAMO_RUBRO_CLASIFICACION`
   - `COLOCACION.CLASIFICACION_CARTERA`
   - `COLOCACION.TIPO_VENCIMIENTO`
5. Identifica diferidos con:

```sql
COLOCACION.PRESTAMO_CUOTADIFERIDA_AGREGADA
WHERE FECHASISTEMA >= '20241111'
```

6. Arma una base de prestamos activos:

```sql
P.CODIGOESTADO <> 'C'
AND (@IdAgencia = 0 OR A.ID = @IdAgencia)
AND ASE.USUARIO IS NOT NULL
```

7. Aplica diferidos si corresponde:

```sql
@FiltrarDiferidos IS NULL
OR (@FiltrarDiferidos = 1 AND DIF.IDPRESTAMO IS NOT NULL)
OR (@FiltrarDiferidos = 0 AND DIF.IDPRESTAMO IS NULL)
```

8. Agrupa por:

```text
IdAgencia
Agencia
CodigoUsuario
NombreAsesor
CargoAsesor
```

El SP ya devuelve datos agregados por asesor. No devuelve detalle por prestamo.

### 7. Corte historico en Mongo

El servicio usa `_agregado_mongo_asesores`.

Coleccion:

```text
DataSac.SituacionCrediticia
```

Filtro base:

```python
{
    "fecha_corte": fecha_corte_mongo,
    "EstadoPrestamo": {"$ne": "CANCELADO"}
}
```

Si se pidio agencia especifica, agrega:

```python
{"Agencia": agencia_nombre}
```

Campos proyectados:

```text
NumeroPrestamo
CodigoUsuario
CodigoAsesor
NombreAsesor
ESDIFERIDO / EsDiferido / Diferido
CargoAsesor
Agencia
Cliente
SaldoCapital
CapitalNoDevenga
CapitalVencido
ProvisionRequerida
```

El filtro de diferidos se aplica en Python, no dentro del query Mongo:

```python
if filtrar_diferidos is True and not _es_diferido_mongo(doc): continue
if filtrar_diferidos is False and _es_diferido_mongo(doc): continue
```

Despues aplica reasignacion si existe:

```text
codigo_usuario = codigo_override or CodigoUsuario or CodigoAsesor
```

y agrega por la misma clave que SQL:

```text
CodigoUsuario
CodigoUsuario::Agencia en consolidado
```

### 8. Comparacion

El servicio toma la union de claves:

```python
codigos = sorted(set(sp_map.keys()) | set(mongo_map.keys()))
```

Para cada clave arma:

- `ValoresSP`
- `ValoresMongo`
- `Diferencias = ValoresSP - ValoresMongo`

Luego ordena poniendo primero los asesores con cargo exacto:

```text
ASESOR DE NEGOCIOS
```

Finalmente calcula:

- `agencias_gerentes_oficina`: busca gerente de oficina por agencia detectada en la comparacion.
- `faltantes_en_mongo`: asesores que aparecen en SQL y no en Mongo.
- `faltantes_en_sp`: asesores que aparecen en Mongo y no en SQL.

## Diagnostico del estado actual

### Lo que esta bien resuelto

- Tiene una comparacion clara entre corte SQL actual y cierre Mongo anterior.
- Maneja agencias en consolidado con una clave interna compuesta.
- Considera reasignaciones de asesor entre cortes para reducir diferencias falsas.
- Normaliza metricas de cartera en un solo formato de salida.
- Expone faltantes en ambos lados.
- Ya existe un endpoint de filtros de negocios: `/negocios/evaluacion-negocios/filtros/cargos-activos`.

### Limitaciones actuales

1. El endpoint solo acepta filtros simples:

```text
id_agencia
filtrar_diferidos
```

No puede filtrar por cargo, asesor, estado, producto, provincia, calificacion o lista de prestamos.

2. El SP devuelve agregados, no prestamos.

Esto impide aplicar filtros dinamicos despues de ejecutar SQL sin perder precision. Por ejemplo, si se quiere filtrar por estado o producto, el agregado por asesor ya vino cerrado.

3. Mongo se filtra principalmente por fecha y agencia.

Campos como diferido se filtran en memoria. Para volumen alto, conviene construir filtros Mongo mas selectivos e indices compuestos.

4. No hay contrato unico de filtros.

`filtros_negocios_services.py` arma catalogos de cargos, estados y asesores. `evaluacion_negocios_matriz_services.py` acepta `filtros` y `filtrosSql`. `asesores-comparacion` no usa ninguno de esos contratos.

5. Hay logica repetida.

Funciones como normalizacion de numeros, diferidos, fechas, metricas y agregaciones aparecen duplicadas entre servicios.

6. La respuesta puede ocultar parte de la clave interna.

En consolidado se separa por `CodigoUsuario::Agencia`, pero el schema expone `CodigoUsuario`. Para una pantalla que use la fila como identificador, conviene exponer tambien una `clave` o `CodigoClave`.

7. El endpoint es GET, pero el siguiente paso requiere body.

Para busquedas complejas basadas en prestamos, conviene introducir un POST nuevo y dejar el GET como compatibilidad.

## Punto de partida recomendado: control central por universo de prestamos

La idea central es separar el problema en dos capas:

1. Construir un universo de prestamos segun filtros.
2. Ejecutar reportes sobre ese universo.

Hoy cada reporte decide por su cuenta como buscar. El control central deberia producir un conjunto estable de prestamos:

```text
NumeroPrestamo
IdPrestamo
datos normalizados de filtro
metricas principales
origen/corte
```

Luego cada reporte solo agrega, compara o detalla.

### Flujo propuesto

```text
Request
  -> normalizar filtros
  -> resolver catalogos y equivalencias
  -> construir universo anterior Mongo
  -> construir universo actual SQL
  -> aplicar reglas comunes de diferidos, agencia, estado, asesor, cargo, producto
  -> cruzar por NumeroPrestamo / IdPrestamo
  -> entregar snapshots reutilizables
  -> reporte especifico agrega por dimension o devuelve detalle
```

## Contrato propuesto para filtros centrales

Crear un schema comun, por ejemplo:

```python
class PrestamosBusquedaFiltros(BaseModel):
    fecha_corte_anterior: datetime | None = None
    fecha_corte_actual: datetime | None = None
    origen_actual: Literal["sql_actual"] = "sql_actual"
    origen_anterior: Literal["mongo_historico"] = "mongo_historico"

    agencias: list[int] | None = None
    agencia_nombres: list[str] | None = None
    codigos_asesor: list[str] | None = None
    cargos_asesor: list[str] | None = None
    estados_prestamo: list[str] | None = None
    calificaciones: list[str] | None = None
    productos: list[str] | None = None
    provincias: list[str] | None = None
    segmentos: list[str] | None = None
    numeros_prestamo: list[str] | None = None
    ids_prestamo: list[int] | None = None

    filtrar_diferidos: bool | None = None
    aplicar_filtros_en: Literal["actual", "anterior", "ambos"] = "actual"
    excluir_estados: list[str] = ["CANCELADO"]
```

Notas:

- `agencias` debe trabajar con ids para SQL.
- `agencia_nombres` debe existir para Mongo historico cuando no haya id en documentos antiguos.
- `numeros_prestamo` e `ids_prestamo` permiten que una busqueda previa alimente muchas pantallas.
- `aplicar_filtros_en` replica la idea ya usada en matriz de transicion, pero con nombres mas orientados al dominio: `actual`, `anterior`, `ambos`.

## Servicios sugeridos

### 1. `services/negocios/prestamos_filters.py`

Responsabilidad:

- Normalizar texto, codigos, listas y booleanos.
- Resolver estado por codigo/nombre.
- Resolver agencia id/nombre.
- Resolver asesor por `CodigoUsuario`, `CodigoAsesor` o nombre.
- Generar una clave estable de filtros para cache.

Funciones:

```python
def normalizar_filtros_prestamos(db: Session, filtros: PrestamosBusquedaFiltros) -> FiltrosPrestamosNormalizados: ...
def filtro_hash(filtros: FiltrosPrestamosNormalizados) -> str: ...
def es_diferido(value: Any) -> bool: ...
```

### 2. `services/negocios/prestamos_universe_service.py`

Responsabilidad:

- Construir el universo central de prestamos.
- Devolver snapshots por corte.
- Evitar que cada reporte vuelva a leer y normalizar todo.

Funciones:

```python
def obtener_snapshot_sql_actual(db: Session, filtros: FiltrosPrestamosNormalizados) -> dict[str, PrestamoSnapshot]: ...
def obtener_snapshot_mongo(fecha_corte: str, filtros: FiltrosPrestamosNormalizados) -> dict[str, PrestamoSnapshot]: ...
def obtener_universo_comparativo(db: Session, filtros: PrestamosBusquedaFiltros) -> UniversoPrestamosComparativo: ...
```

Clave recomendada:

```text
NumeroPrestamo
```

Usar `IdPrestamo` como soporte cuando este disponible, pero para cruzar SQL actual contra Mongo historico el numero suele ser mas portable.

### 3. `services/negocios/prestamos_metrics.py`

Responsabilidad:

- Calcular metricas de cartera una sola vez.
- Evitar diferencias entre servicios.

Funciones:

```python
def cartera_metrics_from_doc(doc: Mapping[str, Any]) -> CarteraMetrics: ...
def sumar_metricas(items: Iterable[CarteraMetrics]) -> CarteraMetrics: ...
def diferencia_metricas(actual: CarteraMetrics, anterior: CarteraMetrics) -> CarteraMetrics: ...
```

### 4. `services/negocios/prestamos_dimensions.py`

Responsabilidad:

- Agregar snapshots por dimensiones reutilizables.

Dimensiones iniciales:

```text
Agencia
CodigoAsesor / NombreAsesor
CargoAsesor
EstadoPrestamo
Calificacion
Producto
Provincia
Segmento
UsuarioControl
CobranzaApoyo
Abogado
```

Funciones:

```python
def agregar_por_dimension(snapshot: dict[str, PrestamoSnapshot], dimension: DimensionSpec) -> list[AgregadoDimension]: ...
def comparar_agregados(actual, anterior, dimension: DimensionSpec) -> list[ComparacionDimension]: ...
```

### 5. `services/negocios/prestamos_filter_catalog_service.py`

Responsabilidad:

- Generar opciones de filtros desde el universo resultante, no desde consultas aisladas.
- Devolver conteos para que la interfaz sepa que filtros tienen datos.

Endpoint sugerido:

```text
POST /negocios/evaluacion-negocios/prestamos/filtros
```

Ejemplo de respuesta:

```json
{
  "fecha_corte_actual": "20260617",
  "fecha_corte_anterior": "20260531",
  "filtros": {
    "agencias": [],
    "asesores": [],
    "cargos_asesor": [],
    "estados_prestamo": [],
    "calificaciones": [],
    "productos": [],
    "provincias": []
  },
  "conteos": {
    "actual": 12500,
    "anterior": 12410,
    "comunes": 12100,
    "solo_actual": 400,
    "solo_anterior": 310
  }
}
```

## Nuevo endpoint recomendado para asesores

Mantener el GET actual para compatibilidad y crear:

```text
POST /negocios/evaluacion-negocios/situacion-crediticia/asesores-comparacion/buscar
```

Payload:

```json
{
  "fecha_corte_anterior": "2026-05-31T00:00:00",
  "agencias": [1, 2],
  "codigos_asesor": ["JLOPEZ", "MPEREZ"],
  "cargos_asesor": ["ASESOR DE NEGOCIOS"],
  "estados_prestamo": ["VIGENTE", "VENCIDO"],
  "calificaciones": ["A1", "B2"],
  "filtrar_diferidos": null,
  "aplicar_filtros_en": "ambos"
}
```

Proceso interno:

```text
POST buscar
  -> obtener_universo_comparativo(...)
  -> aplicar reasignaciones de asesor si corresponde
  -> agregar actual por asesor
  -> agregar anterior por asesor
  -> comparar
  -> devolver el mismo formato que el GET, pero con metadatos de filtros
```

Respuesta extendida recomendada:

```json
{
  "fecha_corte_sp": "20260617",
  "fecha_corte_mongo": "20260531",
  "filtros_aplicados": {},
  "resumen_universo": {
    "actual": 100,
    "anterior": 95,
    "comunes": 90,
    "solo_actual": 10,
    "solo_anterior": 5
  },
  "comparacion": [],
  "faltantes_en_mongo": [],
  "faltantes_en_sp": []
}
```

## Como conectar con lo que ya existe

### Reusar matriz de transicion como referencia

`services/negocios/evaluacion_negocios_matriz_services.py` ya tiene piezas utiles:

- `InputMatrizTransicionFiltros` acepta `filtros`, `filtrosSql`, `aplicar_filtros_en`, `excluir_estados`, `filtrar_diferidos`, `calificacion_anterior`, `calificacion_nueva`.
- Lee Mongo anterior por `NumeroPrestamo`.
- Lee SQL actual por SP.
- Normaliza campos como `CodigoAsesor`, `NombreAsesor`, `CargoAsesor`, `EstadoPrestamo`.
- Cruza prestamos por `NumeroPrestamo`.

Esto no deberia copiarse tal cual; deberia extraerse a un servicio comun de universo.

### Reusar filtros existentes

`services/negocios/filtros_negocios_services.py` ya obtiene:

- Cargos activos.
- Estados de prestamo.
- Asesores.

El siguiente paso es que esos filtros sean contextuales al universo central. Es decir, si el usuario ya selecciono agencia y estado, el catalogo de asesores debe salir de los prestamos que sobreviven a esos filtros.

## Orden de implementacion recomendado

### Fase 1: documentar y estabilizar contrato

1. Mantener el GET actual sin romper clientes.
2. Crear schemas nuevos para filtros centrales.
3. Agregar tests unitarios para normalizacion de filtros, fechas, diferidos y metricas.
4. Exponer `CodigoClave` o `clave_comparacion` en la respuesta nueva para evitar ambiguedad en consolidado.

### Fase 2: crear universo central

1. Extraer helpers repetidos:
   - fechas
   - numeros
   - diferidos
   - metricas
   - normalizacion de asesor/estado/cargo
2. Crear `prestamos_universe_service.py`.
3. Implementar snapshot Mongo con filtros indexables.
4. Implementar snapshot SQL actual. Idealmente debe devolver detalle por prestamo, no solo agregados.
5. Agregar resumen de universo.

### Fase 3: migrar asesores-comparacion

1. Crear endpoint POST nuevo.
2. Implementar comparacion por asesor usando el universo.
3. Validar que con filtros vacios el resultado sea equivalente al GET actual.
4. Mantener el GET como wrapper:

```python
return buscar_asesores_comparacion(
    filtros={
        "agencias": [id_agencia] if id_agencia else None,
        "filtrar_diferidos": filtrar_diferidos,
    }
)
```

### Fase 4: migrar busquedas adicionales

Usar el mismo universo para:

- `matriz-transicion/tiempo-real`
- `cambios-calificacion/tiempo-real`
- `apoyo-comparacion`
- filtros contextuales de negocios
- reportes de cobranza que parten de cartera

### Fase 5: cache y telemetria

Agregar cache por:

```text
reporte + fecha_corte_actual + fecha_corte_anterior + filtros_hash
```

TTL sugerido:

- Comparativos actual vs cierre anterior: 5 a 15 minutos.
- Filtros contextuales: 10 a 30 minutos.
- Historicos cerrados: horas o dias.

Registrar:

```text
report_name
endpoint
duration_ms
cache_hit
cache_key
row_count
id_agencia/agencias
filtrar_diferidos
fecha_corte_actual
fecha_corte_anterior
filtros_hash
```

## Indices recomendados para Mongo

Para que el universo Mongo no lea demasiado por fecha, revisar o crear indices compuestos segun uso real:

```javascript
db.SituacionCrediticia.createIndex({ fecha_corte: 1, EstadoPrestamo: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, Agencia: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, CodigoAsesor: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, CargoAsesor: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, NumeroPrestamo: 1 })
db.SituacionCrediticia.createIndex({ fecha_corte: 1, Calificacion: 1 })
```

Si `ESDIFERIDO`, `EsDiferido` y `Diferido` estan mezclados, conviene normalizar el ETL a un solo campo booleano:

```text
EsDiferido: true | false
```

## Decision tecnica clave

Para que el control central funcione correctamente, los reportes nuevos deben partir de detalle por prestamo, no de agregados por asesor.

El endpoint actual puede seguir usando el SP agregado, pero cualquier busqueda con filtros dinamicos necesita este orden:

```text
prestamos filtrados -> agregacion -> comparacion
```

No este orden:

```text
agregacion -> filtros
```

La segunda forma produce resultados incompletos o imposibles de auditar cuando el filtro depende de campos del prestamo.

## Resultado esperado al centralizar

Con el control central, la pantalla podria hacer:

1. Pedir filtros disponibles segun agencia/corte.
2. Seleccionar filtros.
3. Obtener un universo de prestamos.
4. Usar ese mismo universo para:
   - comparacion por asesores,
   - matriz de transicion,
   - detalle de cambios de calificacion,
   - apoyo/cobranza,
   - totales y tarjetas resumen.

Esto reduce diferencias entre reportes porque todos parten del mismo conjunto de prestamos y de las mismas reglas de normalizacion.

