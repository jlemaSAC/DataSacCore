# Primer paso para el universo central de prestamos

## Decision

El primer paso no debe ser migrar un endpoint ni crear directamente todas las colecciones Mongo.

El primer paso debe ser crear el contrato y los servicios base del universo central de prestamos:

```text
schemas/prestamos/universo_prestamos_schema.py
services/prestamos/
```

Objetivo:

```text
Definir una sola forma de expresar filtros, normalizar campos y representar un prestamo antes de consultar Mongo, SQL o generar reportes.
```

## Por que este debe ser el primer paso

Hoy Negocios y Cobranza ya trabajan con la misma realidad de negocio, pero con nombres y reglas distintas.

Ejemplos:

```text
CodigoAsesor
CodigoUsuario
codigo_usuario_asignado
NombreAsesor
NombreCompleto
CargoAsesor
id_cargo_asesor
CodigoUsuarioControl
codigo_usuario_responsable_control
CodigoUsuarioCobranzaApoyo
codigo_usuario_cobranza_apoyo
ESDIFERIDO
Diferido
EsDiferido
```

Si se crea Mongo actual antes de definir este contrato, se corre el riesgo de volver a guardar datos con nombres inconsistentes. Si se migra un endpoint primero, se duplicara otra vez la logica de filtros, diferidos, fechas, provisiones y agregaciones.

Por eso la base debe ser:

```text
Contrato unico -> normalizacion -> universo -> snapshots/eventos -> reportes
```

## Que se debe crear primero

### 1. Paquete transversal

Crear un paquete fuera de `negocios` y `cobranza`, porque el universo sera compartido:

```text
services/prestamos/
```

Archivos iniciales sugeridos:

```text
services/prestamos/__init__.py
services/prestamos/normalizadores.py
services/prestamos/filtros.py
services/prestamos/metricas.py
services/prestamos/universo_service.py
services/prestamos/snapshot_service.py
services/prestamos/provision_engine.py
```

No todos deben quedar completos en el primer commit. El primer commit puede crear solo los contratos y helpers base.

### 2. Schema comun de filtros

Crear:

```text
schemas/prestamos/universo_prestamos_schema.py
```

Con un contrato base como:

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PrestamoUniverseRequest(BaseModel):
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    fecha_corte_anterior: datetime | None = None
    fecha_corte_actual: datetime | None = None

    ids_prestamo: list[int] = Field(default_factory=list)
    numeros_prestamo: list[str] = Field(default_factory=list)

    agencias: list[int] = Field(default_factory=list)
    agencia_nombres: list[str] = Field(default_factory=list)

    codigos_asesor: list[str] = Field(default_factory=list)
    codigos_usuario_control: list[str] = Field(default_factory=list)
    codigos_usuario_cobranza_apoyo: list[str] = Field(default_factory=list)
    ids_cargo_asesor: list[int] = Field(default_factory=list)

    estados_prestamo: list[str] = Field(default_factory=list)
    calificaciones: list[str] = Field(default_factory=list)
    productos: list[str] = Field(default_factory=list)
    tipos_prestamo: list[str] = Field(default_factory=list)
    provincias: list[str] = Field(default_factory=list)

    filtrar_diferidos: bool | None = None
    excluir_cancelados: bool = True
    incluir_cancelados_periodo: bool = False

    aplicar_filtros_en: Literal["actual", "historico", "ambos"] = "actual"
```

Este schema debe reemplazar gradualmente contratos sueltos como:

```text
InputRecuperacionAnalisisCobranza
InputPrestamosRecaudadosAcumuladosCobranza
InputMatrizTransicionFiltros
filtrosSql
filtros
```

No se deben borrar esos schemas al inicio. Se deben adaptar progresivamente al contrato comun.

### 3. Modelo interno de snapshot

Crear un modelo interno que represente un prestamo normalizado. Puede ser `BaseModel` o `dataclass`.

Ejemplo:

```python
class PrestamoSnapshot(BaseModel):
    id_prestamo: int | None = None
    numero_prestamo: str

    id_agencia: int | None = None
    agencia: str | None = None

    codigo_estado_prestamo: str | None = None
    estado_prestamo: str | None = None
    es_cancelado: bool = False
    es_diferido: bool = False

    codigo_asesor: str | None = None
    nombre_asesor: str | None = None
    id_cargo_asesor: int | None = None
    cargo_asesor: str | None = None

    codigo_usuario_control: str | None = None
    usuario_control: str | None = None
    codigo_usuario_cobranza_apoyo: str | None = None
    cobranza_apoyo: str | None = None

    calificacion: str | None = None
    producto: str | None = None
    tipo_prestamo: str | None = None
    provincia: str | None = None

    saldo_capital: float = 0.0
    capital_vigente: float = 0.0
    capital_no_devenga: float = 0.0
    capital_vencido: float = 0.0
    provision_requerida: float = 0.0
    provision_constituida: float = 0.0

    exigible_capital: float = 0.0
    exigible_interes: float = 0.0
    exigible_mora: float = 0.0
    exigible_otros: float = 0.0
    valor_para_estar_al_dia: float = 0.0
    valor_hasta_cuota_actual: float = 0.0
    valor_cancelar_total: float = 0.0

    data_version: str | None = None
```

Este modelo es importante porque obliga a decidir nombres canonicos.

## Helpers que deben salir primero

Antes de tocar endpoints, extraer helpers repetidos.

### `normalizadores.py`

Debe contener:

```python
normalizar_texto(value, default="")
normalizar_numero_prestamo(value)
normalizar_codigo_usuario(value)
to_float_safe(value)
to_int_safe(value)
es_diferido(value)
normalizar_estado_prestamo(value)
normalizar_calificacion(value)
```

Motivo:

Estos helpers hoy estan repetidos en Negocios y Cobranza. Si se centralizan primero, los siguientes cambios reducen riesgo.

### `filtros.py`

Debe contener:

```python
normalizar_universe_request(request)
build_mongo_match_actual(filtros)
build_mongo_match_historico(filtros)
filtros_hash(filtros)
```

Motivo:

Los filtros deben ser iguales para:

```text
Negocios
Cobranza
Riesgos
Mongo actual
Mongo historico
SQL fallback
```

### `metricas.py`

Debe contener:

```python
calcular_cartera_improductiva(capital_no_devenga, capital_vencido)
calcular_capital_vigente(saldo_capital, capital_no_devenga, capital_vencido)
calcular_mora(saldo_capital, capital_no_devenga, capital_vencido)
sumar_metricas_cartera(items)
diferencia_metricas(actual, historico)
```

Motivo:

Actualmente cada servicio calcula mora, cartera improductiva o diferencias por su cuenta.

## Que NO hacer en el primer paso

No crear todavia todos los jobs de sincronizacion.

No migrar todavia `asesores-comparacion`.

No reemplazar todavia SPs.

No cambiar respuestas publicas.

No borrar los schemas actuales.

No hacer que todos los endpoints usen el universo en el primer cambio.

El primer paso debe ser una base sin impacto funcional externo.

## Primer cambio recomendado

El primer PR o commit deberia hacer solo esto:

```text
1. Crear schemas/prestamos/universo_prestamos_schema.py
2. Crear services/prestamos/normalizadores.py
3. Crear services/prestamos/metricas.py
4. Crear services/prestamos/filtros.py con funciones iniciales
5. Agregar tests simples de normalizacion si el proyecto ya tiene estructura de tests
6. No modificar endpoints publicos
```

Resultado esperado:

```text
El proyecto sigue funcionando igual, pero ya existe una base canonica para filtros, nombres de campos y metricas.
```

## Por que esto habilita Mongo actual

Una vez definido el contrato comun, `SituacionCrediticiaActual` ya puede nacer con nombres correctos.

Sin este contrato, la coleccion podria terminar con mezclas como:

```text
CodigoAsesor vs CodigoUsuario
ESDIFERIDO vs EsDiferido
ProvisionConsituida vs ProvisionConstituida
UsuarioResponsableControl vs UsuarioControl
```

Con el contrato definido, el documento Mongo actual debe seguir los nombres canonicos:

```text
IdPrestamo
NumeroPrestamo
IdAgencia
Agencia
CodigoAsesor
NombreAsesor
IdCargoAsesor
CargoAsesor
CodigoUsuarioControl
UsuarioControl
CodigoUsuarioCobranzaApoyo
CobranzaApoyo
EstadoPrestamo
Calificacion
EsDiferido
SaldoCapital
ProvisionRequerida
ProvisionConstituida
```

## Segundo paso despues de la base

Luego de crear el contrato y helpers, el segundo paso debe ser:

```text
Crear SituacionCrediticiaActual y un job/proceso de carga inicial desde SQL.
```

Ese job debe cargar pocos campos primero:

```text
IdPrestamo
NumeroPrestamo
IdAgencia
Agencia
EstadoPrestamo
CodigoAsesor
NombreAsesor
CargoAsesor
CodigoUsuarioControl
CodigoUsuarioCobranzaApoyo
Calificacion
EsDiferido
SaldoCapital
ProvisionRequerida
updated_at
data_version
```

Luego se agregan exigibles, cuotas, valores para estar al dia, recuperacion y provisiones simuladas.

## Criterio de terminado del primer paso

El primer paso se considera completo cuando:

```text
Existe un contrato comun de filtros.
Existe un snapshot canonico de prestamo.
Existen helpers comunes para normalizar texto, numeros, diferidos y metricas.
Los helpers privados duplicados ya tienen una alternativa central.
No se rompio ningun endpoint actual.
La siguiente tarea puede crear SituacionCrediticiaActual usando esos nombres canonicos.
```

## Resumen

Primero se crea la base comun:

```text
schema + normalizadores + metricas + filtros
```

Despues se crea Mongo actual:

```text
SituacionCrediticiaActual
```

Despues se migran endpoints:

```text
Negocios -> Cobranza -> Riesgos
```

Esta secuencia evita rehacer trabajo y permite que todos los reportes partan del mismo universo de prestamos.

