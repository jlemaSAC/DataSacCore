# Revisión técnica de DataSacCore y DataSacWebApp

Fecha: **19 de noviembre de 2026**. Código revisado: Core `e1df028`, WebApp `47d7f7e`. Complementa la [guía para el equipo](GUIA_DESARROLLO_EQUIPO.md).

## Alcance y conclusión

Se revisaron estructura, manifiestos, instrucciones de arquitectura, composición de rutas y dependencias, persistencia, autenticación, providers de estado, una funcionalidad completa, pruebas y archivos de despliegue. Se ejecutaron las suites locales y el build frontend. No se modificó lógica de aplicación ni configuración de credenciales.

La estructura existente permite incorporar desarrolladores con un patrón reconocible en ambos repositorios. Core aplica capas dentro de dominios; WebApp utiliza funcionalidades con páginas, stores, APIs y componentes. Hay pruebas amplias en ambos proyectos. Los pendientes más concretos son sincronizar documentación y entorno, clasificar las pruebas que fallan y hacer explícitas las decisiones de sesión y validación automatizada.

Esto es una revisión de arquitectura y funcionamiento del código local. No certifica todas las fórmulas de negocio, seguridad integral, rendimiento bajo carga ni conectividad con servicios desplegados. No se consultaron bases reales ni se ejecutaron procesos ETL.

## Inventario observado

| Medida de archivos fuente | DataSacCore | DataSacWebApp |
| --- | --- | --- |
| Archivos Python bajo `app/modules` | 440 | — |
| Archivos llamados `router.py` | 67 | — |
| Archivos llamados `service.py` | 58 | — |
| Modelos `*_model.py` | 194 | — |
| Pruebas `tests/test_*.py` | 58 | — |
| Archivos TypeScript bajo `src/app` | — | 402 |
| Archivos `*.page.ts` | — | 31 |
| Archivos `*.store.ts` | — | 31 |
| Archivos `*.api.ts` | — | 27 |
| Archivos `*.spec.ts` | — | 69 |

Son conteos por nombre y ubicación, no cantidades de endpoints, dominios ni cobertura de pruebas. No se midió cobertura.

## Patrones que conviene conservar

- Composición central de Core en `app/main.py`, con routers agrupadores por dominio.
- Infraestructura de conexiones en `app/db`, contratos Pydantic y repositorios locales por funcionalidad.
- Servicios con colaboradores sustituibles, como los del caso de depósitos y retiros diarios.
- Separación en WebApp entre HTTP, estado y presentación, con TypeScript y templates estrictos.
- Composición de stores por providers hasta `AppLayout`, que permite conservar filtros al navegar.
- Menú dinámico y controles administrativos en servidor, además de guards de navegación.
- Imágenes Docker independientes para API y frontend y publicación existente en GHCR.

No todas las capas son totalmente independientes del framework. Por ejemplo, servicios de Core usan `HTTPException`, y `AuthService` conserva compatibilidad construyendo algunos colaboradores a partir de su sesión. Conviene documentar esas particularidades al usarlas como referencia para código nuevo.

## Diferencias y acciones propuestas

| Hallazgo comprobado | Evidencia | Implicación y siguiente paso |
| --- | --- | --- |
| Puerto local inconsistente | README Core: 9100; `WebApp/src/environments/environment.development.ts`: 8000 | Acordar un puerto para onboarding o explicar ambas opciones. La guía usa 8000 para desarrollo y 9100 para Docker. |
| Documento de auth antiguo | `WebApp/CAMBIOS_AUTH.md` menciona `/auth/menu/data-sac-web`; `core/auth/auth.service.ts` consume `/data-sac-web/auth/menu` | Usar router y cliente actuales como referencia; actualizar o marcar como histórico el documento anterior. |
| El README Core aún se presenta como starter | Encabezado `FastAPI Basic Starter` y descripción mínima | Dar entrada a la arquitectura real y a la guía de incorporación. |
| Diferencia entre comando Docker documentado y ejecutado | README Core muestra `fastapi run`; Dockerfile ejecuta Uvicorn con `--no-access-log` | Explicar que el logging HTTP lo realiza el middleware propio. |
| Persistencia de sesión requiere decisión explícita | `WebApp/src/app/core/auth/auth.service.ts::getStorage` usa `localStorage`; `AGENTS.md` pide excepción revisada/documentada | Confirmar y registrar la decisión con el equipo. No se encontró una excepción explícita en los documentos revisados. |
| Publicación sin pasos explícitos de pruebas | Workflows Docker de ambos repositorios | Añadir validación de PR como trabajo independiente; publicar una imagen no acredita que la suite pase. |
| Backend sin lockfile de dependencias localizado | Rangos en `pyproject.toml`, `requirements.txt` y `requirements.prod.txt` | Acordar reproducibilidad y mantener sincronizadas las declaraciones; el entorno revisado usa Python 3.13 y Docker usa 3.12. |
| E2E descrito sin target configurado | README WebApp incluye `ng e2e`; `angular.json` solo tiene build, serve y test | No presentarlo al equipo como una suite operativa hasta configurarla. |
| Archivos con muchas responsabilidades potenciales | Repositorio Mongo de recuperación histórica: 1914 líneas; tabla de cobranza pendiente: 1283 líneas | Revisar su cohesión cuando se trabaje en ellos. El tamaño es una señal para revisar, no prueba suficiente de un defecto. |

Las acciones de esta tabla son propuestas. Esta revisión no cambia puertos, almacenamiento de sesión, fórmulas, tests ni workflows.

## Verificaciones ejecutadas

Entorno local observado: Python **3.13.15** en `.venv`, Node **22.22.3**, Yarn **1.22.22**. Las dependencias ya estaban instaladas; no se instalaron paquetes.

| Proyecto | Comando | Resultado |
| --- | --- | --- |
| Core | `.venv/bin/python -m pytest -q` | 743 pruebas correctas, 4 fallidas, 5 advertencias |
| WebApp | `yarn test --watch=false` | 416 pruebas correctas, 16 fallidas; 60 archivos correctos y 9 fallidos |
| WebApp | `yarn build` | No completado: el proceso termina con `SIGABRT`; uno de los intentos registra un deadlock interno de esbuild |
| WebApp | `NG_BUILD_MAX_WORKERS=1 yarn build` | También termina con `SIGABRT` |

Los fallos se observaron antes de escribir la guía y sin cambios en la lógica. No deben atribuirse automáticamente a errores de producción: algunos son diferencias entre fixtures/expectativas y el comportamiento actual.

El build se comprobó inicialmente junto con las suites y después por separado; también se redujo el número de workers sin modificar archivos del proyecto. No se determinó la causa del aborto. No se puede dar por verificada la compilación de producción ni atribuir este resultado a un error específico del código. La compilación previa a la ejecución de tests sí terminó, pero utiliza una configuración distinta y no sustituye el build de producción.

### Backend: cuatro pruebas fallidas

| Prueba | Observación |
| --- | --- |
| `tests/test_main.py::test_model_columns_are_single_line` | La comprobación exige `Column(...)` en una sola línea; encontró una declaración multilínea en `app/models/inversion/temporizacion_inversion_model.py`. |
| `tests/test_matriz_transicion.py::test_descarta_solo_cancelados_del_corte_anterior` | El servicio devuelve HTTP 422 al no encontrar préstamos pareados o nuevos bajo esos datos/filtros. Revisar el caso de negocio y la expectativa. |
| `tests/test_recuperacion_historico.py::test_etiqueta_columnas_de_cobro_sin_lookup` | La prueba espera `$project` en una posición del pipeline y recibe una estructura distinta (`KeyError`). |
| `tests/test_resumen_diario_cartera_asesores.py::test_resumen_diario_cartera_calcula_morosidad_por_agencia_y_asesor` | Diferencia en `creditos_dias_vencidos_1`: resultado 2, esperado 1. Requiere verificar la definición del indicador. |

Las advertencias incluyen una deprecación de TestClient/httpx y cuatro relativas al adaptador de fechas SQLite bajo Python reciente. No se cambió ninguna dependencia para esta revisión.

### Frontend: dieciséis pruebas fallidas en nueve archivos

Los nombres siguientes se refieren a archivos `*.spec.ts` bajo `src/app/features`:

| Archivo | Fallos | Observación |
| --- | --- | --- |
| `cartera-de-credito/.../control-cartera-improductiva.page.spec.ts` | 2 | El doble de store no expone `ultimaConsulta()` que ahora consume la página. |
| `cartera-de-credito/.../evaluacion-asesores.page.spec.ts` | 2 | Mismo error de `ultimaConsulta()` en el doble de store. |
| `recuperacion/.../cobranza-pendiente-pago.page.spec.ts` | 4 | Mismo error de `ultimaConsulta()` en el doble de store. |
| `recuperacion/.../resumen-recuperacion.page.spec.ts` | 2 | El formulario no llega a la consulta esperada y devuelve validación de fechas/agencia autorizada antes del mensaje esperado. |
| `cartera-de-credito/.../evaluacion-asesores-tabla.component.spec.ts` | 1 | No se proporciona el input requerido `columnasVisibles`. |
| `cartera-de-credito/.../evolucion-cartera-chart.component.spec.ts` | 1 | La prueba espera dos llamadas a `roundRect`; se registra una. |
| `depositos-a-plazos/.../resumen-depositos-a-plazo.spec.ts` | 1 | Texto de pestaña distinto al esperado. |
| `seguridad/permisos/pages/gestion-permisos.page.spec.ts` | 2 | Las dos vistas esperan un título que no aparece en el texto renderizado. |
| `recuperacion/.../evaluacion-castigo.integration.spec.ts` | 1 | Diferencia de mayúsculas en el texto esperado del diálogo. |

Las rutas abreviadas de cartera y recuperación están dentro de sus respectivos dominios de `negocios`. También se emitieron mensajes de jsdom sobre `HTMLCanvasElement.getContext()` sin implementar. No se instaló `canvas` ni se cambió la infraestructura de pruebas.

## Orden propuesto para resolver pendientes

1. Alinear onboarding: puertos, documentación de auth y comandos de ejecución.
2. Clasificar los fallos: fixtures incompletos, expectativas visuales y reglas de negocio. Resolver las diferencias de indicadores con su responsable funcional.
3. Confirmar el build de producción y registrar tamaño y advertencias en un entorno reproducible.
4. Acordar y documentar la estrategia de persistencia de sesión.
5. Incorporar pruebas y build a la validación de PR, y definir si se necesita una suite e2e.

No se desplegó ni publicó ningún cambio. La guía es utilizable para explicar la arquitectura actual; la línea base de pruebas debe acompañar cualquier afirmación de calidad del estado revisado.
