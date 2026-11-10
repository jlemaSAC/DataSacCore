# FastAPI Basic Starter

Proyecto base mínimo con FastAPI.

## Requisitos

- Python 3.10 o superior

## Crear y activar el entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Instalar dependencias

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configurar conexion a SQL Server

Copia `.env.example` a `.env` y completa las variables de conexion:

```bash
cp .env.example .env
```

La configuracion usa SQLAlchemy con `mssql+pyodbc` y el driver ODBC de SQL Server. El endpoint `/health/db` ejecuta `SELECT 1` para validar la conexion real.
El valor `APP_NAME` se envia como nombre de aplicacion en las conexiones ODBC, para identificar la API en los registros y sesiones de SQL Server (`DataSacCore` por defecto).

La conexion a MongoDB usa `pymongo` y mantiene las bases usadas por `DataSacService`:

- `logs`
- `DataSac`
- `MayorAuxiliar`
- `AnalyticSac`

El endpoint `/health/mongo` ejecuta `ping` para validar la conexion real.

Al iniciar, la aplicacion valida la conexion y muestra en consola:

```text
Conexion con la base de datos establecida correctamente. Check=1
Conexion con MongoDB establecida correctamente. Check=1
```

Si alguna conexion falla, el servicio no arranca. Para desactivar temporalmente estas validaciones:

```env
CHECK_DATABASE_ON_STARTUP=false
CHECK_MONGO_ON_STARTUP=false
```

Variables CORS:

```env
APP_ENV=dev
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Cuando `APP_ENV=dev`, la API permite todos los origenes con `*`. En otros ambientes, `CORS_ALLOWED_ORIGINS` debe contener los origenes permitidos separados por comas.

Variables JWT para autenticacion:

```env
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=180
```

`JWT_SECRET_KEY` debe definirse con una clave larga y privada en cada ambiente.

## Ejecutar en desarrollo

```bash
fastapi dev --port 9100
```

La API queda disponible en:

- http://127.0.0.1:9100
- http://127.0.0.1:9100/docs
- http://127.0.0.1:9100/redoc

Healthchecks:

- http://127.0.0.1:9100/health
- http://127.0.0.1:9100/health/db
- http://127.0.0.1:9100/health/mongo

Auth:

- `POST /auth/login`: login compartido que conserva el contrato usado por AnalyticSac.
- `POST /data-sac-web/auth/login`: login exclusivo de DataSacWeb; valida credenciales contra SQL Server y emite JWT.
- `GET /data-sac-web/auth/menu`: valida el token Bearer y devuelve el menu permitido para los roles del usuario.
- `GET /data-sac-web/auth/menu/completo`: devuelve el arbol completo del menu DataSacWeb, incluidos los items inactivos y roles asignados; requiere el rol administrador `001`.
- `GET /data-sac-web/auth/menu/{id_menu}`, `POST /data-sac-web/auth/menu`, `PATCH /data-sac-web/auth/menu/{id_menu}` y `DELETE /data-sac-web/auth/menu/{id_menu}`: administración de permisos de DataSacWeb; requieren el rol administrador `001`.

La respuesta de `POST /data-sac-web/auth/login` no incluye el campo `menu`. El menu se obtiene por separado desde `GET /data-sac-web/auth/menu`, usando la base MongoDB `DataSacWebAppMenu`: cruza los roles SQL del usuario con las asignaciones activas y construye el arbol del estado de menús vigente.

## Evaluación de cuentas de Ahorro Vista

`POST /negocios/ahorro-vista/evaluacion-cuentas-ahorro-vista` requiere
`Authorization: Bearer <token>` y sirve a la pantalla
`/dashboard/negocios/ahorro-vista/evaluacion-cuentas-ahorro-vista`.

```json
{
  "fecha_inicio": "2026-11-01",
  "fecha_fin": "2026-11-06",
  "id_agencia": 0
}
```

Las fechas deben pertenecer al mismo mes y `fecha_fin` no puede superar la fecha
del sistema. `id_agencia=0` obtiene el consolidado. Se compara el saldo al corte
final con el cierre del mes anterior; `fecha_inicio` no filtra aperturas ni suma
saldos diarios. La respuesta informa las fechas operativas efectivamente usadas.

`comparacion` contiene una fila por usuario oficial, agencia y producto, con clave
`usuario::agencia::producto`. `CodigoProducto` es `AHORROS.TIPO_CUENTA.CODIGO`
(por ejemplo, `002`), y `ProductoAhorro` es su nombre. Estos campos permiten
construir el filtro de productos después de cargar los datos, incluyendo productos
presentes solo en uno de los cortes. No se devuelve cargo ni se filtra por cargo.

`ValoresActual` y `ValoresCierreMesAnterior` contienen `Saldo`, `Cuentas`,
`TasaPromedio` y `SumaTasas`. Después de filtrar, sumar saldo y cuentas y calcular
la tasa como `SUM(SumaTasas) / SUM(Cuentas)`; con cero cuentas, la tasa es `null`.
Así se pueden agrupar los resultados por asesor, agencia o producto sin promediar
promedios. `DiferenciasCierreMesAnterior` resta saldo y cuentas; las diferencias
de tasas son puntos porcentuales y son `null` si falta uno de los valores.

Incluye cuentas activas, inactivas y bloqueadas, excluyendo aportaciones (tipo `001`).
El booleano opcional `es_programado` conserva `false` por defecto para Ahorro Vista.
Con `true` sirve a `/dashboard/negocios/ahorro-restringido/evaluacion-cuentas-restringidas`,
aplicando el mismo filtro al corte actual y al cierre del mes anterior. La tasa por cuenta es
la máxima configurada para su saldo en `ITEMSALDO_TASA`, o cero si no hay una
tasa configurada. Los cortes cerrados consultan las versiones temporales de
cuentas, saldos y tasas usando `FECHACIERREVISTA`; los nombres de asesores,
agencias y productos y los gerentes corresponden al catálogo actual.

Un grupo ausente en un corte tiene valores `null` y aparece en
`faltantes_en_actual` o `faltantes_en_cierre_mes_anterior`. Un corte disponible
sin cuentas devuelve una lista vacía; un corte sin cierre disponible devuelve
`404`. También devuelve `agencias_gerentes_oficina` para el resumen por agencia.

## Depósitos y retiros diarios de Ahorro Vista

`POST /negocios/ahorro-vista/depositos-y-retiros-diarios` requiere Bearer y sirve a
la pantalla `/dashboard/negocios/ahorro-vista/depositos-y-retiros-diarios`.

```json
{
  "fecha_inicio": "2026-11-01",
  "fecha_fin": "2026-11-06",
  "id_agencia": 0
}
```

El rango debe pertenecer a un mismo mes y no superar la fecha del sistema.
`id_agencia=0` consulta el consolidado. No acepta filtros de productos ni cargos:
los productos se filtran localmente sobre la respuesta.

Incluye todos los tipos de operación que agreguen o quiten saldo de una cuenta.
No existe una lista fija de IDs de transacción. Abarca depósitos, retiros,
transferencias, intereses, notas de crédito/débito, cobros, aperturas y cierres
si generan una variación neta distinta de cero en la cuenta.

Se calcula `SUM(créditos) - SUM(débitos)` usando
`MOVIMIENTO_TRANSACCION_DETALLE.VALOR` y `DEBITO`, exclusivamente en los detalles
vinculados a la misma operación (`MOVIMIENTO_TRANSACCION.ID`) y cuenta.
Una variación positiva se suma en `depositos`; una negativa se suma en `retiros`
por su magnitud. Una operación con variación cero queda fuera: así los bloqueos,
desbloqueos y otros traslados internos entre saldos no inflan las dos columnas.
La compensación es por operación y cuenta, no por día: un depósito de 100 y un
retiro posterior de 100 sí aparecen como 100 en cada columna. Una transferencia
entre dos cuentas aparece como salida de la primera y entrada de la segunda;
estos importes representan flujos de cuentas, no solo efectivo externo.

Excluye ahorros programados y aportaciones (`001`). No filtra el estado actual
de la cuenta, para conservar movimientos válidos de cuentas que luego se cerraron.

La fecha de cada flujo es `MOVIMIENTO_TRANSACCION.FECHASISTEMA`. La agencia, el
asesor oficial y el producto pertenecen a la cuenta al corte final consultado;
en fechas cerradas se lee `CUENTA FOR SYSTEM_TIME AS OF FECHACIERREVISTA`.
Los nombres provienen del catálogo actual. Las tablas de movimientos se consultan
directamente por el rango, sin reconstruir saldos ni tasas. La relación
`MOVIMIENTO_TRANSACCION_REVERSO` excluye los movimientos de reversión y los
originales revertidos hasta el corte. Si la reversión tiene fecha posterior al
corte, se conserva el original; no se usa `ESREVERSO=0` como único criterio.

La respuesta incluye `dias` en orden cronológico y `filas` por
`codigo_usuario + id_agencia + codigo_producto`. Cada fila tiene `nombre_asesor`,
`agencia`, `producto_ahorro` y una lista `valores` con el mismo tamaño y orden de
`dias`. Cada elemento contiene `depositos` y `retiros`, sin acumular, completando
ceros. El frontend puede agrupar por agencia para Resumen y por asesor para
Detalle, sumando los productos seleccionados. No hay duplicados adicionales de
resúmenes ni un endpoint para el diálogo de operaciones.

Cada día incluye también `transacciones`, agrupadas por tipo y sentido dentro
del mismo asesor, agencia y producto. `id_transaccion` identifica el tipo en
`FINANCIERO.TRANSACCION`, no una operación individual; `tipo_transaccion` es su
nombre del catálogo actual. `valor` siempre es positivo y `es_debito=true`
indica salida; `false`, crédito o entrada. El sentido se deriva de la variación
real de la cuenta, no del campo `DEBITO` del catálogo de tipos. Un mismo tipo
puede aparecer dos veces en el día si hubo entradas y salidas, sin compensarlas.
Los días sin movimientos contienen `transacciones: []`. Por ejemplo, un
elemento de `valores` puede ser:

```json
{
  "depositos": 100,
  "retiros": 40,
  "transacciones": [
    {"id_transaccion": 2, "tipo_transaccion": "DEPOSITO", "valor": 100, "es_debito": false},
    {"id_transaccion": 3, "tipo_transaccion": "RETIRO", "valor": 40, "es_debito": true}
  ]
}
```

Un rango disponible sin movimientos devuelve `filas: []` y conserva `dias`.
Si falta el cierre necesario, responde `404`. `fecha_corte` identifica el último
corte operativo usado. Si este es anterior al final solicitado, los ceros
posteriores no representan actividad confirmada de esos días.

Ante un deadlock de SQL Server (error nativo `1205`), el repositorio hace
`rollback` y repite la lectura completa, incluido el corte, hasta tres intentos
en total, con una espera breve y aleatoria entre intentos. Otros errores SQL no
se reintentan. Si el deadlock persiste, responde `503` con `Retry-After: 2`.
Es una recuperación ante conflictos transitorios; no elimina su causa en SQL
Server ni cambia el aislamiento de lectura o la configuración de la base.

La consulta filtra primero fechas y reversos, calcula la variación por operación
y cuenta, agrega por cuenta/día y luego por asesor/agencia/producto. No utiliza tablas temporales,
funciones de ventana ni un `ORDER BY` final; el servicio ordena la respuesta.

## Ejecutar pruebas

```bash
pytest
```

## Desplegar con Docker

La imagen usa la imagen oficial de Python, instala el driver oficial `msodbcsql18` requerido por `pyodbc` para SQL Server y ejecuta FastAPI con:

```bash
fastapi run app/main.py --host 0.0.0.0 --port 9100
```

Construir la imagen:

```bash
docker build -t datasac-core:latest .
```

Ejecutar con las variables de entorno del archivo `.env`:

```bash
docker run --rm --env-file .env -p 9100:9100 datasac-core:latest
```

O usando Compose:

```bash
docker compose up -d --build
```

La API quedara disponible en:

- http://127.0.0.1:9100
- http://127.0.0.1:9100/docs
- http://127.0.0.1:9100/health

Notas para produccion:

- No copiar `.env` dentro de la imagen; pasar secretos como variables de entorno, secret manager o variables del orquestador.
- Usar `APP_ENV=production` y definir `CORS_ALLOWED_ORIGINS` con los dominios reales del frontend.
- Mantener `CHECK_DATABASE_ON_STARTUP=true` y `CHECK_MONGO_ON_STARTUP=true` si se quiere impedir que la API arranque sin SQL Server o MongoDB.
- Publicar solo el puerto interno `9100` detras de un proxy/reverse proxy o balanceador con TLS.

## Publicacion de la imagen

El workflow `.github/workflows/docker-publish.yml` se ejecuta en cada pull
request y push dirigido a `main`:

1. Ejecuta las pruebas automatizadas.
2. Construye la imagen Docker.
3. En un push a `main`, publica la imagen en GitHub Container Registry.

Imagenes generadas:

```text
ghcr.io/jlemasac/datasaccore:latest
ghcr.io/jlemasac/datasaccore:sha-<commit>
```

La etiqueta SHA es la recomendada para despliegues reproducibles y rollback.

## Despliegue en servidor

Si el paquete GHCR es privado, iniciar sesion con un token que tenga unicamente
el permiso `read:packages`:

```bash
docker login ghcr.io -u USUARIO_GITHUB
```

Crear, por ejemplo, `/opt/datasac-core/compose.yaml`:

```yaml
services:
  api:
    image: ghcr.io/jlemasac/datasaccore:latest
    env_file:
      - .env
    environment:
      APP_ENV: production
    ports:
      - "9100:9100"
    restart: unless-stopped
```

El archivo `/opt/datasac-core/.env` debe crearse directamente en el servidor.
Luego iniciar el servicio:

```bash
cd /opt/datasac-core
docker compose pull
docker compose up -d
docker compose logs -f api
```

Validar el despliegue:

```bash
curl http://localhost:9100/health
```

Para actualizar a una imagen nueva:

```bash
docker compose pull
docker compose up -d
```

Para fijar o restaurar una version, reemplazar `latest` en `compose.yaml` por
la etiqueta correspondiente:

```text
ghcr.io/jlemasac/datasaccore:sha-<commit>
```

## Estructura

```text
.
├── app
│   ├── __init__.py
│   ├── core
│   │   └── settings.py
│   ├── db
│   │   ├── base.py
│   │   ├── mongo.py
│   │   └── session.py
│   ├── main.py
│   ├── models
│   │   └── ...
│   ├── modules
│   │   └── auth
│   │       ├── repositories
│   │       ├── dependencies.py
│   │       ├── router.py
│   │       ├── schemas.py
│   │       ├── security.py
│   │       └── service.py
│   ├── repositories
│   │   ├── mongo
│   │   └── sql
│   └── routers
│       ├── __init__.py
│       └── health.py
├── tests
│   └── test_main.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Modelos

`app/models` contiene los modelos de persistencia SQLAlchemy migrados desde `DataSacService`, organizados por dominio. Los modelos importan `Base` o `BaseSecundaria` desde `app.db.base`; no deben abrir conexiones ni contener reglas de negocio.

Las consultas deben vivir en `app/repositories/sql` o `app/repositories/mongo`, y la logica de negocio debe construirse encima en servicios.

Para modulos nuevos de negocio, preferir la organizacion por modulo en `app/modules/<modulo>`:

- `router.py`: solo dependencias, request/response y delegacion al service.
- `service.py`: reglas de negocio, validaciones y transacciones.
- `repositories/`: consultas SQL o Mongo sin reglas de negocio.
- `schemas.py`: entradas y salidas Pydantic.

Convenciones para nuevos modelos:

- No usar `relationship`; las relaciones se resuelven con `join()` explicitos en repositorios.
- Mantener `ForeignKey` cuando exista en la tabla.
- Declarar cada `Column(...)` en una sola linea.
- Mantener `__tablename__`, `__table_args__` y `primary_key=True`.


## Gestión de menús y permisos de DataSacWeb

La administración conserva los menús y las asignaciones previamente existentes en
la base Mongo configurada para DataSacWeb. Los cargos que
intervienen en autorización son los roles de `SEGURIDAD.ROL`; los identificadores
numéricos de `NOMINA.CARGO` no se convierten en códigos de rol.

- `/dashboard/seguridad/menus`: estructura, edición y configuración del menú.
- `/dashboard/seguridad/permisos/permisos-por-cargo`: perspectiva predeterminada.
- `/dashboard/seguridad/permisos/permisos-por-menu`: las mismas asignaciones por menú.
- `GET /seguridad/permisos`: árbol completo, cargos y versión del estado.
- `PATCH /seguridad/permisos`: diferencias explícitas y versión original.

Los endpoints requieren Bearer y verifican en SQL que el usuario siga habilitado
y tenga el rol administrativo existente `001`. No se crean roles ni permisos
administrativos adicionales. Los enlaces de las dos herramientas se añaden al
menú de ese administrador sin modificar los documentos de navegación existentes.

Ejemplo de lote (el identificador y la versión se obtienen del GET):

```json
{
  "version": "<sha256 devuelto por GET>",
  "cambios": [
    { "menu_id": "<id del menú>", "rol_codigo": "036", "conceder": true }
  ]
}
```

El servidor rechaza relaciones repetidas, cargos inexistentes y concesiones a
cargos inactivos. Los padres reciben acceso efectivo desde sus hijos sin conceder
acceso a hermanos ni a menús futuros. El permiso propio del padre se conserva por
separado. Las asignaciones históricas sin marca de acceso directo se conservan
al editar; no se ejecuta una migración destructiva al consultar.

### Guardado atómico con MongoDB independiente

La API puede funcionar con la instancia MongoDB independiente existente. No
requiere replica set: guarda el estado completo de menús, permisos y relaciones
en el documento `menu_estado` con `_id: "actual"`. La creación y las ediciones
usan una única escritura atómica, con una revisión que impide sobrescribir cambios
concurrentes. MongoDB limita el tamaño de un documento BSON a 16 MiB; la API
rechaza el guardado antes de llegar a 15 MiB para dejar margen.

Antes del primer cambio, la API lee `menu`, `permisos` y `rol_permisos` sin
modificarlos. El primer guardado copia su estado completo al nuevo documento y
aplica la operación en la misma escritura. En adelante `menu_estado/actual` es
la fuente de verdad para la navegación, la administración de menús y ambas vistas
de permisos. Los identificadores, códigos y asignaciones se conservan. Las tres
colecciones originales permanecen como respaldo de la migración y ya no reflejan
cambios posteriores; no deben usarse como fuente de permisos ni modificarse.

Para el cambio de versión, detener las escrituras administrativas y actualizar
todas las instancias de DataSacCore y cualquier consumidor externo que lea o
escriba esas tres colecciones. La aplicación anterior continuaría leyendo datos
antiguos después de la migración, incluso si se revoca un acceso. Tras actualizar
todos los consumidores, reiniciar la API y comprobar un lote en ambas vistas.
La API comprueba la huella de las colecciones originales y devuelve `503` si
detecta que otro proceso las modificó; resolver la divergencia antes de continuar.
Las colecciones originales no constituyen un respaldo actualizado para revertir
la aplicación después de guardar cambios en el nuevo documento: cualquier vuelta
atrás debe reconciliar primero el estado vigente.

La copia inicial exige que las colecciones originales permanezcan sin escrituras
durante el cambio de versión. MongoDB no ofrece una lectura y creación atómica de
varias colecciones en una instancia independiente, por lo que esta condición debe
coordinarse con los demás procesos. No activar el nuevo documento mientras una
versión anterior de la API siga sirviendo tráfico.

Una versión desactualizada devuelve `409` antes de cambiar asignaciones. El
frontend conserva el borrador y su resumen para revisar, descartar y recargar.
Después de guardar, ambas perspectivas reciben el mismo estado confirmado y se
refresca la navegación de la sesión del administrador. Las sesiones de otros
usuarios reciben el nuevo menú en su siguiente actualización; sus tokens no se
reescriben.

Validación específica:

```bash
.venv/bin/python -m pytest tests/test_auth.py tests/test_seguridad_permisos.py tests/test_permisos_mongo_independiente.py tests/test_seguridad_roles.py
```

Las pruebas incluyen fallos antes de publicar, conflictos de versión, preservación
de accesos históricos, autorización y ambas perspectivas. El guardado se puede
validar en una base de prueba aislada de la misma instancia independiente.


## Resúmenes de ahorro vista y restringido

`POST /negocios/ahorro-vista/resumen-ahorro-vista` requiere Bearer y recibe
`fecha_inicio`, `fecha_fin` (del mismo mes), `agencias` y el booleano opcional
`es_programado`. El valor predeterminado `false` conserva el resumen de ahorro
vista; `true` sirve al resumen de ahorro restringido en
`/dashboard/negocios/ahorro-restringido/resumen-ahorro-restringido`.

El filtro se aplica al corte actual, los comparativos SQL/Mongo y los saldos
diarios. Se mantienen las dimensiones por agencia, asesor, estado y producto,
la tasa ponderada por cuentas y los cierres faltantes como `null`.

## Control diario de cancelación de ahorro restringido

`POST /negocios/ahorro-restringido/control-diario-cancelacion-restringidos` requiere
Bearer y recibe `fecha_inicio`, `fecha_fin` del mismo mes e `id_agencia` (`0` para
consolidado). Devuelve `fecha_corte`, `dias` y `filas` por asesor, agencia y producto;
cada día contiene `monto` y `cuentas`. Sirve a la ruta frontend del mismo nombre.

El universo son cuentas con `TIPO_CUENTA.ESPROGRAMADO=1` y estado `C` al corte.
Se toma el último cierre válido por cuenta (transacción `30`, CIERRE DE CUENTAS),
excluyendo reversos vigentes al corte. El monto suma los débitos de ítems con
`ITEMSALDO.SUMASALDO=1`; los débitos internos de provisiones de interés no se
vuelven a sumar. El estado guardado en el movimiento puede seguir siendo `A`.
No se determina una cancelación por `CUENTA_PROGRAMADO.ACTIVO` ni por solicitudes
de anulación del contrato. Se utiliza `FECHACIERREVISTA` para cuentas e ítems
históricos; sin cierre se devuelve `404`, y un corte vacío devuelve `filas: []`.

`POST /negocios/ahorro-restringido/control-diario-cancelacion-restringidos/detalle`
conserva el rango/corte y agrega `fecha` (null para el período), `codigo_usuario`,
`cargos` y códigos `productos`. Devuelve `total_registros`, `total_monto` e `items`
con cuenta, cliente principal, producto, agencia, asesor, fecha y monto de salida.
Los nombres/cargos corresponden al catálogo actual. No se reutilizan condiciones
nuevo/renovado, préstamos, tasas ni intereses de los depósitos a plazo.

## Control de vencimiento de ahorro restringido

`POST /negocios/ahorro-restringido/control-vencimiento-restringido` requiere Bearer
y recibe `fecha_inicio`, `fecha_fin` e `id_agencia` (`0` para consolidado). El rango
filtra vencimientos, incluye ambos días y admite fechas futuras y varios meses.
Devuelve `saldo_total` y `filas` por agencia, asesor y producto, con responsables
actuales. Sirve a `/dashboard/negocios/ahorro-restringido/control-vencimiento-restringido`.

El universo incluye `TIPO_CUENTA.ESPROGRAMADO=1`, estados de cuenta `A/I/B` y
contratos con `CUENTA_PROGRAMADO.ACTIVO=1`. Si hubiera varios contratos activos
para una cuenta, se elige el de mayor `FECHAINICIO` e `ID` antes de filtrar fechas.
Las cuentas sin contrato activo quedan fuera, incluso cuando conservan saldo.
El saldo actual suma únicamente ítems con `ITEMSALDO.SUMASALDO=1`, redondeado a
centavos por cuenta. Se mantienen cuentas con saldo cero. No es saldo proyectado
al vencimiento ni reconstrucción de un corte histórico.

`POST /negocios/ahorro-restringido/control-vencimiento-restringido/detalle`
comparte el universo del resumen y agrega `codigo_usuario`, `productos` (códigos de tipo de cuenta), `pagina`,
`tamano_pagina` y `sin_paginacion`. Devuelve `total_registros`, `total_saldo` e
`items` con cliente principal, agencia, asesor, producto, cuenta, saldo actual,
tasa del contrato, vencimiento, estado e indicador de préstamo no cancelado.
`sin_paginacion=true` devuelve todas las filas para filtrar y ordenar en Angular.

La ruta Angular conserva `menuRouteGuard`: el nodo de tipo ruta debe estar activo
en el menú administrado, bajo Negocios > Ahorro restringido, con el título
`Control vencimiento restringido` y los roles que se definan en la administración
de permisos. No se conceden permisos por el mero registro de la ruta.
