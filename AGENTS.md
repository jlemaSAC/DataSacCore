# AGENTS.md

## Alcance

Estas reglas aplican a todo el proyecto `DataSacCore`. Es una API FastAPI en Python 3.10+ que integra SQL Server, MongoDB, Redis y servicios ETL.

## Arquitectura estándar

- `app/main.py` es el punto de composición: configura la aplicación y registra los routers de primer nivel.
- `app/core/` contiene configuración y lectura de variables de entorno.
- `app/db/` contiene la infraestructura de persistencia: sesiones SQL (`get_db` y `get_secondary_db`), clientes MongoDB y Redis.
- `app/models/` contiene modelos SQLAlchemy de persistencia. Deben importar `Base` o `BaseSecundaria` desde `app.db.base`; no deben abrir conexiones ni contener reglas de negocio.
- `app/modules/` contiene la lógica organizada por dominio o funcionalidad. Los submódulos pueden agruparse mediante routers, por ejemplo `analytic`, `nomina` y `seguridad`.
- `tests/` contiene las pruebas unitarias y de integración de cada funcionalidad.

El flujo de dependencias esperado es:

```text
router -> dependencies -> service -> repository/client -> base de datos o servicio externo
```

Responsabilidades:

- `router.py`: contrato HTTP, parámetros, autenticación, códigos de error y delegación al servicio. No colocar consultas ni reglas de negocio.
- `dependencies.py`: construir servicios, repositorios y clientes mediante inyección de dependencias de FastAPI.
- `service.py`: reglas de negocio, validaciones, orquestación entre fuentes, transformaciones y transacciones.
- `repositories/`: consultas SQL o MongoDB y mapeo de persistencia. No duplicar aquí reglas de negocio.
- `schemas.py`: modelos Pydantic de entrada y salida de la API.
- `domain.py`, `constants.py` o clientes específicos: usarlos solo cuando la funcionalidad los necesite.

Para código nuevo, preferir repositorios dentro del módulo (`app/modules/<modulo>/repositories/`). Mantener `app/repositories/` para componentes compartidos o código existente que ya dependa de esa ubicación.

Los endpoints nuevos deben usar autenticación Bearer mediante `get_current_auth_context`. Por el momento no se deben inventar validaciones adicionales de roles o permisos; agregarlas únicamente cuando el requerimiento las defina.

## Crear un módulo nuevo

1. Definir el dominio, los endpoints, la fuente de datos y confirmar que los endpoints usarán autenticación Bearer.
2. Consultar primero el esquema real de SQL con el MCP `datasac_sql` cuando la funcionalidad dependa de SQL Server.
3. Crear el paquete en `app/modules/<modulo>/` con `__init__.py`. Para una funcionalidad agrupada, usar la misma estructura en un subpaquete.
4. Crear únicamente los archivos necesarios, normalmente:

   ```text
   app/modules/<modulo>/
   ├── __init__.py
   ├── router.py
   ├── dependencies.py
   ├── schemas.py
   ├── service.py
   └── repositories/
       ├── __init__.py
       └── sql_<funcionalidad>_repository.py
   ```

   Agregar repositorio Mongo, `domain.py`, `constants.py` o cliente ETL solo si el caso lo requiere.

5. Si usa SQL, elegir la sesión correcta: `get_db` para la base principal y `get_secondary_db` para la secundaria. Usar `Base` o `BaseSecundaria` solo si se necesita un modelo SQLAlchemy nuevo.
6. Implementar el repositorio con consultas parametrizadas y joins explícitos. No usar `relationship` en los modelos.
7. Implementar el servicio recibiendo repositorios/clientes por constructor para que pueda probarse con fakes.
8. Implementar `dependencies.py` para ensamblar las dependencias reales.
9. Crear el router y agregarlo al router agrupador del dominio. Si es un dominio de primer nivel, registrarlo también en `app/main.py` con `include_router`.
10. Crear o actualizar pruebas en `tests/test_<funcionalidad>.py`, cubriendo servicio y endpoint cuando corresponda.

## MCP de SQL disponible

Está disponible el MCP `datasac_sql` para inspección y consultas de solo lectura. Usarlo para conocer tablas, columnas, relaciones y datos antes de modelar o escribir repositorios. Herramientas principales:

- `list_schemas`, `search_tables`, `describe_table`, `search_columns`.
- `get_primary_keys`, `get_foreign_keys`, `trace_table_relationships`, `get_indexes`.
- `select_rows` para leer filas de una tabla con filtros parametrizados.
- `execute_select` para una única consulta `SELECT` o CTE que termine en `SELECT`.
- `list_views`, `list_procedures`, `list_functions` y sus herramientas de definición o búsqueda.

El MCP rechaza escrituras, DDL, permisos, ejecución de procedimientos y múltiples sentencias. Las consultas devuelven como máximo 500 filas. Usar nombres exactos de esquema y tabla, limitar resultados y no incluir secretos en las consultas.

El MCP sirve para investigar y validar el origen de datos; la lógica permanente debe quedar en un repositorio del proyecto, no en scripts ad hoc ni en el router.

## Convenciones y calidad

- Usar nombres `snake_case` para módulos y archivos, y `PascalCase` para clases.
- Mantener autenticación con las dependencias existentes, especialmente `get_current_auth_context`, cuando el endpoint lo requiera.
- Mantener los contratos Pydantic y las respuestas HTTP explícitos.
- No abrir conexiones manualmente dentro de routers, servicios o modelos.
- No modificar archivos `.env` ni exponer credenciales.
- Ejecutar al menos `pytest` o las pruebas específicas del módulo antes de entregar cambios.
