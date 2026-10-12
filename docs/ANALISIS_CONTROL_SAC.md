# CONTROL SAC — Análisis de arquitectura de información orientada al control

Fecha: 12 de octubre de 2026. Alcance: código local de `DataSacCore` y del repositorio hermano `DataSacWebApp`, con énfasis en NEGOCIOS.

## 1. Resumen ejecutivo

**Control SAC tiene capacidades reales de supervisión: permite comparar cortes, localizar diferencias por agencia y asesor, analizar transiciones y consultar operaciones. La cadena de control está parcialmente conectada.** La principal limitación funcional no es la ausencia de indicadores, sino la continuidad entre una señal agregada, sus operaciones explicativas y la verificación posterior de lo ocurrido.

El aplicativo supera un inventario de estadísticas en Control de Cartera Improductiva y Matriz de Transición: una selección conduce a préstamos con información entre cortes. También las evaluaciones de colocación y recuperación permiten abrir detalles de una agrupación. Sin embargo, Resumen Cooperativa, Resumen Cartera y Evaluación Asesores no ofrecen una investigación encadenada hacia esas otras pantallas con el contexto seleccionado. [E04](#e04), [E06](#e06), [E08](#e08), [E10](#e10), [E12](#e12), [E15](#e15), [E19](#e19).

Las cinco capacidades presentan este balance:

| Capacidad | Balance funcional en NEGOCIOS |
|---|---|
| OBSERVAR | Implementada en las diez pantallas examinadas, dentro del universo y fecha de cada consulta. |
| COMPARAR | Implementada mediante referencias explícitas, aunque no homogéneas: cierre anterior, día anterior, mismo rango del mes anterior, mes completo y año completo. |
| DETECTAR | Parcialmente implementada en general: ordenamientos, diferencias y colores requieren lectura del usuario. La matriz clasifica mejora, deterioro y conservación, con una limitación en entradas `NA`. |
| INVESTIGAR | Implementada dentro de algunos módulos; parcial en la visión global. La existencia de un endpoint de detalle no garantiza acceso desde todas las pantallas. |
| DAR SEGUIMIENTO | Parcialmente implementada: hay evolución cuantitativa y comparación de préstamos, pero no se identificó registro de situaciones, gestiones, compromisos y cierre en el flujo revisado. |

**Tres precauciones afectan la interpretación del control:** comparar períodos de distinta duración puede producir una señal engañosa; algunas vistas convierten ausencia en cero; y el detalle de recuperación mezcla cobros del período con situación operativa actual de SQL. También se encontró una clasificación de préstamos nuevos como mejora en la matriz. Son hallazgos sustentados en código, no afirmaciones sobre resultados de producción. [E05](#e05), [E08](#e08), [E11](#e11), [E12](#e12), [E13](#e13), [E17](#e17), [E18](#e18).

### Alcance, método y grado de certeza

Se revisaron rutas, páginas, componentes consumidos, stores, contratos, servicios, dependencias, repositorios y pruebas existentes. Se siguió el recorrido **pantalla → API → servicio → fuente**, comprobando que el detalle estuviera invocado por la pantalla. No se ejecutó el aplicativo contra servicios reales ni se consultó SQL, MongoDB, Redis o producción; no se inspeccionaron secretos ni se instalaron dependencias.

El análisis toma el estado de trabajo local, incluidos los cambios ya presentes en cuatro archivos del frontend: `menu-analytic.store.ts`, `menu-opcion-card.component.ts`, `menu-section.page.ts` y `app.topbar.ts`. Por ello describe ese estado local, sin afirmar correspondencia con una versión desplegada. No se modificó código existente.

En todo el documento:

- **Funcionalidad verificada:** recorrido o cálculo identificado en código. No implica disponibilidad o calidad de datos reales.
- **Limitación verificada:** contrato, cálculo o recorrido revisado que restringe una pregunta concreta.
- **Hipótesis:** necesidad funcional o efecto probable que requiere contraste con usuarios o datos.
- **Recomendación conceptual:** criterio para una futura organización; no es una implementación ni un diseño.

Se ejecutaron pruebas existentes con fakes, sin el arranque de `app.main`, mediante `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_matriz_transicion.py tests/test_cartera_improductiva.py -q`. Resultado: **22 aprobadas y 1 fallida**. La falla es `test_descarta_solo_cancelados_del_corte_anterior`: esperaba una respuesta, pero el servicio descartó el préstamo y devolvió HTTP 422 al quedar sin pares ni entradas. Esto evidencia un desacuerdo entre la expectativa de esa prueba y el comportamiento actual; no se corrigió porque el alcance autoriza únicamente este documento. [E25](#e25).

## 2. Propósito actual del aplicativo

El propósito funcional verificable es **consultar y contrastar información de negocio crediticio**, con tres perspectivas principales:

1. **Estado y exposición:** saldo de cartera, morosidad, cartera improductiva, provisiones y operaciones.
2. **Producción y resultados:** colocaciones adjudicadas y cobros recuperados en un período.
3. **Localización y detalle:** distribución por agencia, asesor, producto u otra dimensión y consulta de determinados préstamos.

La información permite supervisión analítica y preparación de decisiones: localizar un asesor con deterioro, revisar qué créditos explican una transición, examinar importes pendientes y estimar el efecto de cobrar una cuota. No se identificó en los servicios, contratos y páginas de NEGOCIOS un circuito persistente de asignación de problemas, ejecución de acciones y verificación de cierre. Los botones de cerrar diálogos y la notificación local de cambios de filtros no son seguimiento de gestión. [E01](#e01), [E09](#e09), [E11](#e11), [E20](#e20), [E21](#e21).

La separación temática Cartera → Colocación → Recuperación es reconocible y útil, pero no equivale a una explicación integrada: colocar más, recuperar más y tener menos mora son hechos relacionados que requieren un universo, responsable y fecha compatibles. Su coincidencia en una pantalla no demuestra causalidad.

**Hipótesis de uso:** el jefe de agencia necesita convertir variaciones en prioridades de supervisión; el asesor necesita convertirlas en una selección de operaciones para revisar. Ambas necesidades encajan con los datos existentes, pero el acceso real de cada cargo no puede deducirse del nombre del cargo ni de que el componente esté implementado.

## 3. Mapa de módulos y funcionalidades

### 3.1. Pantallas reales y contratos consumidos

Las URLs de pantalla parten de `/dashboard/negocios/`. Las rutas backend siguientes ya incluyen `/negocios/`; todas las consultas de esta tabla son POST. La tabla usa nombres funcionales respaldados por rutas, breadcrumbs y páginas. Los nombres y el orden exactos del menú autorizado se reciben del backend y no son verificables sin sus datos. [E01](#e01), [E03](#e03).

| Módulo | Pantalla | Ruta frontend, después de `/dashboard/negocios/` | Endpoint principal | Funcionalidad comprobada |
|---|---|---|---|---|
| NEGOCIOS | Resumen Cooperativa | `resumen-cooperativa` | `/negocios/cartera-de-credito/resumen-actual`, `/negocios/colocacion/resumen-actual`, `/negocios/recuperacion/resumen-actual` | Composición de tres consultas; visión consolidada con comparativos. |
| Cartera de Crédito | Resumen Actual de Cartera | `cartera-de-credito/resumen-actual` | `/negocios/cartera-de-credito/resumen-actual` | Cortes diarios, cierres de referencia, métricas, evolución y tabla por dimensiones. |
| Cartera de Crédito | Evaluación de Asesores | `cartera-de-credito/evaluacion-asesores` | `/negocios/cartera-de-credito/situacion-crediticia/asesores-comparacion` | Fin seleccionado contra cierre mensual anterior; detalle por asesor y resumen por agencia/cargo. |
| Cartera de Crédito | Matriz de Transición | `cartera-de-credito/matriz-de-transicion` | `/negocios/cartera-de-credito/matriz-transicion` | Calificación de origen/destino, conteos, probabilidades, importes y préstamos de una celda. |
| Cartera de Crédito | Control de Cartera Improductiva | `cartera-de-credito/control-cartera-improductiva` | `/negocios/cartera-de-credito/cartera-improductiva` | Inicio, fin y día anterior al fin; agencia/asesor y detalle de préstamos. |
| Colocación | Resumen de Colocación | `colocacion/resumen-colocacion` | `/negocios/colocacion/resumen-actual-adjudicados` | Totales, tasas, acumulado anual y colocación diaria con detalle del día. |
| Colocación | Evaluación de Colocación | `colocacion/evaluacion-colocacion` | `/negocios/colocacion/evaluacion-colocacion` | Comparaciones por dimensiones y operaciones de una fila. |
| Recuperación | Resumen de Recuperación | `recuperacion/resumen-recuperacion` | `/negocios/recuperacion/resumen` | Recuperación total y por tipo de cobro, referencias y distribución diaria. |
| Recuperación | Cobranza Pendiente de Pago | `recuperacion/cobranza-pendiente-pago` | `/negocios/recuperacion/recaudacion-acumulada` | Situación entre cortes, cobros del rango, pendientes, cuotas, escenario de cobro y exportación. |
| Recuperación | Evaluación de Recuperación | `recuperacion/evaluacion-recuperacion` | `/negocios/recuperacion/evaluacion-recuperacion` | Comparaciones por dimensiones y detalle operativo paginado. |

**Diferencias de nomenclatura verificadas:** `matriz-de-transicion` es el slug frontend y `matriz-transicion` el backend; `control-cartera-improductiva` consume `cartera-improductiva`; Cobranza Pendiente de Pago consume `recaudacion-acumulada`; Evaluación Asesores consume `situacion-crediticia/asesores-comparacion`. Resumen Cooperativa conserva la carpeta `resumen-actual` y un breadcrumb «Resumen actual de negocios». Son correspondencias existentes, no propuestas de cambio.

### 3.2. Capacidades relacionadas que no deben contarse como nuevas pantallas

- **Inicio:** `/dashboard` y `/dashboard/inicio` cargan `DashboardPage → InicioPage → InicioBienvenidaComponent`. El control activo construye accesos desde el menú y datos de sesión. Existen `InicioStore`, `InicioApi`, métricas y `/negocios/inicio` con hoy/ayer, pero la página activa revisada no consume ese store. No corresponde atribuirle un tablero financiero hoy/ayer visible solo por encontrar esos archivos. [E23](#e23).
- **Universo de préstamos:** POST `/prestamos/universo/buscar` entrega snapshots actuales e históricos y filtros por préstamos, agencias y responsables. No se identificó su consumo en las pantallas de NEGOCIOS revisadas. Es capacidad backend, no una investigación integrada ya disponible al usuario. [E24](#e24).
- **Analítica:** el backend registra comparativo de cartera, morosidad histórica, colocación histórica, recuperación histórica y otros indicadores. Parte de esa lógica es reutilizada por NEGOCIOS. `app.routes.ts` no identifica páginas específicas de Analítica equivalentes a estas; el comodín muestra `MenuSectionPage`. No se acredita una pantalla de histórico independiente a partir de un router o un nodo dinámico. [E01](#e01), [E05](#e05), [E16](#e16), [E22](#e22).

## 4. Capacidades actuales de control

### 4.1. Criterio de evaluación

Las capacidades se evalúan **desde la pantalla y dentro de su propósito**, no por la mera existencia de datos en otro módulo:

- **Implementada:** recorrido verificable que responde la pregunta dentro del alcance descrito.
- **Parcialmente implementada:** responde una parte, requiere traslado manual, o tiene una limitación material de interpretación.
- **No identificada:** no se encontró soporte en los contratos, componentes y flujo revisados. No significa imposibilidad en sistemas externos.
- **No verificable:** depende de datos, asignaciones, despliegue o comportamiento real que este análisis no consultó.

Detectar no exige notificaciones automáticas: una clasificación explícita puede bastar dentro de una pantalla. Sin embargo, mostrar valores y permitir ordenarlos se considera detección parcial cuando el usuario debe establecer por sí mismo qué diferencia amerita atención. Dar seguimiento incluye evolución de indicadores; se clasifica parcial cuando no hay continuidad de una situación seleccionada y de las acciones sobre ella.

### 4.2. Matriz de evaluación funcional

| Módulo | Pantalla | Qué controla | Qué permite detectar | Información principal | Nivel de análisis |
|---|---|---|---|---|---|
| NEGOCIOS | Resumen Cooperativa | Balance de exposición, producción y cobros | Aumento agregado de mora/provisión y cambios en producción o cobros | Cartera, colocación, recuperación y referencias | Institución; distribución de colocación por agencia |
| Cartera | Resumen Actual | Estado y concentración de cartera | Aumento de mora y exposición por agrupación | Saldo, capital vigente/no devenga/vencido, improductiva, provisión y operaciones | Institución/agencia y ocho dimensiones |
| Cartera | Evaluación Asesores | Cambio de cartera atribuida al asesor del corte final | Asesores/agencias con mayor mora, improductiva o aumento de provisión | Cinco métricas visibles con cierre, fin y variación | Agencia, cargo y asesor |
| Cartera | Matriz de Transición | Migración de calificaciones en el universo final | Deterioro, mejora y conservación; importes de las transiciones | Conteos, probabilidad e importes entre categorías | Universo filtrado → celda → préstamo |
| Cartera | Control Cartera Improductiva | Cambio de exposición improductiva | Aumento diario o entre extremos por agencia, asesor y préstamo | Saldo, improductiva y morosidad en tres cortes | Agencia → asesor/grupo → préstamo |
| Colocación | Resumen Colocación | Flujo adjudicado y composición diaria | Caídas, concentración diaria y cambios de monto/tasas | Monto, operaciones, promedio, tasas, acumulado anual y adjudicados | Agencia/producto/tipo/asesor; día → registros adjudicados |
| Colocación | Evaluación Colocación | Producción y composición por dimensión | Caída o concentración por agencia, asesor, producto, segmento o tasa | Monto/operaciones del rango, mes previo y mismo rango previo | Agrupación → operación |
| Recuperación | Resumen Recuperación | Flujo recuperado y rubros | Menor recuperación o cambios de distribución diaria y por tipo | Total, tipos de cobro y serie diaria | Universo consultado → día/rubro |
| Recuperación | Cobranza Pendiente Pago | Situación de préstamos y necesidades de cobro | Más mora/provisión, pendientes, falta de cobros dentro del rango | Cortes, importes recuperados, cuotas, pendientes y simulación | Agencia/asesor → préstamo; deudor y garantes en reportes |
| Recuperación | Evaluación Recuperación | Resultado de cobros por dimensión | Menor recuperación por responsable, producto, rubro o abogado | Monto, operaciones, referencias y desglose de cobros | Agrupación → préstamos con cobros |

### 4.3. Clasificación y justificación de las cinco capacidades

| Pantalla | Observar | Comparar | Detectar | Investigar | Dar seguimiento | Justificación y limitación principal |
|---|---|---|---|---|---|---|
| Resumen Cooperativa | Implementada | Implementada | Parcialmente implementada | Parcialmente implementada | Parcialmente implementada | Tres resúmenes con variaciones y distribución de colocación por agencia; no transmite una selección a un detalle de préstamos. Referencias de stocks y flujos distintas. [E04](#e04), [E13](#e13), [E17](#e17). |
| Resumen Actual Cartera | Implementada | Implementada | Parcialmente implementada | Parcialmente implementada | Parcialmente implementada | Serie diaria y cierres; tabla por dimensiones y colores de mora. No hay selección de fila hacia préstamos ni gestión de una señal. [E05](#e05), [E06](#e06). |
| Evaluación Asesores | Implementada | Implementada | Parcialmente implementada | Parcialmente implementada | Parcialmente implementada | Ordena métricas y diferencias; pasa de resumen a asesores, sin detalle operativo. Compara cierre mensual con fin, no cada día del rango. [E07](#e07), [E08](#e08). |
| Matriz de Transición | Implementada | Implementada | Parcialmente implementada | Implementada | Parcialmente implementada | Clasifica migraciones y abre préstamos de una celda con los filtros; `NA` puede contarse como mejora y no cubre salidas del universo final. No sigue una secuencia de gestiones. [E11](#e11), [E12](#e12). |
| Control Cartera Improductiva | Implementada | Implementada | Parcialmente implementada | Implementada | Parcialmente implementada | Compara tres cortes, ordena variaciones y abre préstamos de grupos seleccionados. Explica contribución cuantitativa, sin explicar causas de negocio ni registrar intervención. [E09](#e09), [E10](#e10). |
| Resumen Colocación | Implementada | Implementada | Parcialmente implementada | Parcialmente implementada | Parcialmente implementada | Gráfico diario abre adjudicados del día, pero su respuesta no incluye número de préstamo/cliente; no conecta con estado posterior. [E13](#e13), [E14](#e14). |
| Evaluación Colocación | Implementada | Implementada | Parcialmente implementada | Implementada | Parcialmente implementada | Selección de fila conserva dimensión/agencia/asesor y abre operaciones paginadas. No verifica calidad posterior de esos créditos. [E13](#e13), [E15](#e15), [E16](#e16). |
| Resumen Recuperación | Implementada | Implementada | Parcialmente implementada | Parcialmente implementada | Parcialmente implementada | Consulta serie y detalle diario por rubro, sin operaciones del día. Días sin filas se completan con cero. [E17](#e17), [E18](#e18). |
| Cobranza Pendiente Pago | Implementada | Implementada | Parcialmente implementada | Implementada | Parcialmente implementada | Préstamos, diferencias, pendientes y escenario de cuota; filtros y reportes para examinarlos. Sin bitácora de gestiones ni garantía de cobertura de créditos desaparecidos. [E20](#e20), [E21](#e21). |
| Evaluación Recuperación | Implementada | Implementada | Parcialmente implementada | Implementada | Parcialmente implementada | Fila → préstamos paginados y datos SQL; cubos permiten filtro local por asesor/cargo. Detalle de cobros del período con situación SQL actual, sin seguimiento de una cohorte sin cobros. [E19](#e19), [E22](#e22). |

Las clasificaciones «Implementada» no certifican suficiencia para cualquier pregunta. Por ejemplo, investigar operaciones colocadas está implementado en Evaluación Colocación; investigar su deterioro meses después no está identificado en ese mismo recorrido.

| Aspecto transversal | Estado | Evidencia y alcance |
|---|---|---|
| Registro de situaciones, acciones, compromisos y resolución en NEGOCIOS | No identificada | Contratos y servicios de los módulos consultan información; stores y páginas conservan consultas y diálogos, sin circuito de casos. [E01](#e01), [E10](#e10), [E19](#e19), [E20](#e20). |
| Metas, tolerancias configuradas, alertas persistentes y priorización compartida | No identificada | Hay colores/diferencias y reglas locales; no se identificó una fuente de metas o reglas institucionales en los flujos revisados. [E06](#e06), [E08](#e08), [E12](#e12). |
| Acceso efectivo de JEFE DE AGENCIA y ASESOR DE NEGOCIOS a cada pantalla | No verificable | Menú por roles, oficinas de consulta y asignaciones dependen de SQL/Mongo y de la sesión concreta. [E02](#e02), [E03](#e03). |
| Actualización, completitud y conciliación real de cortes | No verificable | Se conoce cómo se consultan fuentes; no se comprobó su contenido ni el proceso de carga desplegado. [E05](#e05), [E16](#e16), [E17](#e17), [E22](#e22). |

## 5. Evaluación funcional por pantalla

### 5.1. Resumen Cooperativa

**Pregunta principal:** ¿cómo están la exposición crediticia, la colocación y la recuperación de la cooperativa en el contexto seleccionado?

**Propósito de control:** orientar la revisión inicial hacia el área cuyo comportamiento requiere explicación. Su valor diferencial es reunir dominios, no resolver cada investigación.

- **Información principal:** morosidad, cartera improductiva, capital vencido/no devenga y provisión; monto/operaciones de colocación y total recuperado. Esos indicadores distinguen exposición y resultados.
- **Información secundaria:** tasas y montos promedio, distribución de colocación por agencia y composición de recuperación por rubro, útiles para contextualizar el total.
- **Mayor atención funcional:** aumento de improductiva y provisión combinado con caída de recuperación. Esto es una hipótesis de prioridad de supervisión; el sistema no formula por sí mismo ese diagnóstico conjunto.
- **Cambios verificables:** variaciones de cartera contra cierres; colocación del rango contra mes previo y acumulado anual contra año previo en sus indicadores; recuperación del rango contra mes/año completos anteriores.
- **Problemas y decisiones:** permite advertir un cambio agregado y decidir qué dominio examinar. No prueba incumplimiento de una meta ni identifica por sí sola qué préstamos explican la mora.
- **Investigación y detalle:** llega a distribución por agencia en colocación, no a una selección de préstamos originada en las métricas de cartera/recuperación. No hay un recorrido intermodular con selección preservada identificado.
- **Seguimiento:** se puede volver a consultar; no se identificó comparación persistida de una situación investigada o de su acción posterior.
- **Información compartida:** utiliza los mismos endpoints/servicios de resúmenes de los dominios; cartera fuerza `filtrar_diferidos: null`. La página envía siempre `agencias: []`, de modo que el nombre Cooperativa corresponde a un consolidado, no a un resumen personalizado de agencia.

**Limitación verificada:** un rango común no significa una fecha efectiva común. Cartera elige el último corte disponible; los flujos acumulan el rango pedido. El store consulta secuencialmente y mantiene errores por sección, por lo que puede existir una vista parcialmente respondida. La hora de consulta del navegador no certifica la actualización de las fuentes. [E04](#e04), [E05](#e05), [E13](#e13), [E17](#e17).

### 5.2. Resumen Actual de Cartera

**Pregunta principal:** ¿cuál es el estado de la cartera y cómo cambió frente a los cierres de referencia y durante el mes consultado?

**Propósito de control:** valorar exposición y localizar concentraciones por agencia, responsable, calificación, producto o territorio.

- **Principal:** morosidad e improductiva junto al saldo base; capital vencido/no devenga y provisión requerida. La proporción debe interpretarse junto al importe, porque un índice puede aumentar por reducción del denominador.
- **Secundaria:** operaciones, clientes y participación de saldo dentro de cada agrupación; ayudan a dimensionar concentración y carga.
- **Mayor atención:** variación de morosidad en puntos porcentuales y aumento de capital vencido/improductiva/provisión; los colores ayudan a señalar, sin sustituir una regla institucional validada.
- **Comparación:** puntos diarios del rango, cierre del mes anterior y 31 de diciembre del año anterior. La tabla usa el último corte disponible del rango, no una serie histórica por cada dimensión.
- **Qué detecta y decide:** puede mostrar si aumenta la exposición y dónde se concentra la mora del corte. Facilita decidir qué agencia, asesor o segmento revisar, no qué gestión ejecutar sobre cada préstamo.
- **Investigación:** tabla con agencia, asesor, usuario responsable de control, calificación, provincia, producto, tipo de préstamo y cargo del asesor. Se puede ordenar por saldo, mora, provisión y otras métricas; no se identifica apertura de préstamos desde la fila.
- **Seguimiento:** evolución diaria agregada implementada; continuidad de una agrupación o situación hasta resolución no identificada.
- **Comparte:** mismo contrato de cartera con Resumen Cooperativa y lógica de Analítica. Coinciden varios indicadores con Evaluación Asesores e Improductiva, pero estos añaden atribución o detalle operativo.

**Limitaciones verificadas:** el rango debe pertenecer al mismo mes; oficinas del usuario alimentan los filtros, con opción de consolidado. El servicio usa la fecha del token para limitar el rango, sin cotejar las agencias solicitadas con oficinas autorizadas. El gauge usa umbrales 5/7/9 y la tabla 5/10, por lo que un mismo porcentaje puede recibir diferente énfasis. [E05](#e05), [E06](#e06).

### 5.3. Evaluación de Asesores

**Pregunta principal:** ¿qué asesores, agencias o cargos muestran mayor exposición o deterioro frente al cierre del mes anterior?

**Propósito de control:** localizar responsables de una variación y orientar la supervisión del equipo.

- **Principal visible:** saldo capital, cartera improductiva, provisión, mora porcentual y operaciones, cada una con cierre, fin y variación.
- **Secundaria:** cargo y referencia de gerente de oficina en resúmenes; contextualizan responsabilidad. El contrato contiene clientes y componentes de capital adicionales, pero la tabla activa solo presenta cinco métricas.
- **Mayor atención:** asesores con alta mora y aumento de improductiva/provisión. Se puede ordenar por valores finales o diferencias; el orden inicial es saldo capital, no deterioro.
- **Cambios:** fin seleccionado versus cierre del mes anterior. `fecha_inicio` fija el mes de referencia; no representa una comparación efectiva entre ambos extremos del rango.
- **Decisiones:** seleccionar asesores/agencias para revisión; contrastar mejora o empeoramiento cuantitativo. No determina responsabilidad causal ni cumplimiento de una meta.
- **Investigación:** resumen por agencia/cargo y vista Detalle por asesor. Aquí «Detalle» no significa préstamos: no se identifica un endpoint ni una acción operativa vinculados a una fila de asesor en esta funcionalidad.
- **Seguimiento:** comparación de dos estados y nuevas consultas; sin serie de comportamiento por asesor ni registro de compromisos.
- **Comparte:** códigos de usuario, agencias, saldo, mora, improductiva y provisión con Improductiva; consume snapshots actuales/históricos usados también por otros análisis de cartera.

| Pregunta de control | Respuesta actual |
|---|---|
| ¿Qué asesores tienen mayor morosidad? | Sí, ordenando `MoraPorcentaje` final. |
| ¿Quiénes aumentaron su cartera improductiva? | Sí, ordenando su diferencia. |
| ¿Quiénes aumentaron específicamente capital vencido? | El backend lo devuelve, pero esa métrica no es columna de la tabla activa; no se acredita respuesta directa desde esta pantalla. |
| ¿Quiénes mejoraron? | Sí, por diferencias de las cinco métricas visibles, con el significado de cada una. |
| ¿Quién requiere seguimiento? | Selección analítica manual; no hay estado explícito de «requiere atención» o asignación de seguimiento identificado. |
| ¿Qué préstamos explican el incremento? | No desde la fila. Improductiva ofrece esa capacidad en otra pantalla, con selección manual del contexto. |

**Limitación verificada de atribución:** el servicio reasigna históricos al asesor del corte final cuando encuentra cambio de responsable. Es útil para controlar la cartera hoy asignada, pero no representa necesariamente el desempeño del asesor que la gestionaba en el cierre anterior. Valores faltantes se convierten en cero al presentar métricas; la fila sin valores finales recibe un color distinto, pero ausencia y reducción económica no son equivalentes. [E07](#e07), [E08](#e08).

### 5.4. Matriz de Transición

**Pregunta principal:** ¿qué préstamos cambiaron de calificación y qué exposición representa cada migración?

**Propósito de control:** reconocer deterioro/conservación/mejora y pasar de una transición a créditos concretos.

- **Principal:** conteos por origen/destino y montos de saldo/provisión asociados. La probabilidad es una frecuencia de transición por fila del universo consultado; no se identificó un modelo predictivo.
- **Secundaria:** otros importes exigibles y de cancelación; enriquecen el análisis del esfuerzo de recuperación y exposición.
- **Mayor atención:** transiciones hacia peores categorías y su importe, no solo su cantidad. La clasificación visible de mejora/deterioro es verificable, pero necesita considerar la limitación de entradas `NA`.
- **Cambios:** dos cortes seleccionados, incluso de meses distintos; filtros de agencia, asesor, cargo, estado y diferido aplican al corte nuevo.
- **Decisiones:** elegir transiciones para revisar; dimensionar exposición; consultar condiciones de cobro de sus préstamos. No atribuye una causa económica del deterioro.
- **Investigación:** selección de celda → `/matriz-transicion/prestamos`, con filtros y calificaciones de origen/destino. El servicio complementa información con el repositorio de cuotas y devuelve el contrato operativo utilizado en cobranza.
- **Seguimiento:** compara el mismo préstamo entre los dos cortes y permite revisar nuevos pares de fechas; no ofrece una cronología persistida de una intervención.
- **Comparte:** `NumeroPrestamo`, responsable, agencia, estado/calificación, provisión y exigibles con Cobranza Pendiente de Pago; hay reutilización real del contrato y de infraestructura de detalle, sin una navegación intermodular demostrada.

**Limitaciones verificadas:** parte de los préstamos presentes al final; no incluye un conjunto independiente de préstamos que solo estaban al inicio. Excluye cancelados del corte anterior. `NA` significa ausencia en el corte anterior, no necesariamente nueva originación comprobada. Las categorías se ordenan alfabéticamente y la UI determina mejora por posición; `NA → A1` puede incrementar «Mejora», aunque no existía calificación comparable. Estos límites impiden leer la matriz como reconciliación completa de entradas, salidas y desempeño. El listado por celda no tiene paginación backend. [E11](#e11), [E12](#e12), [E25](#e25).

### 5.5. Control de Cartera Improductiva

**Pregunta principal:** ¿en qué agencia, asesor y préstamos aumentó la cartera improductiva entre el inicio, el fin y el día previo al fin?

**Propósito de control:** descomponer una variación de riesgo hasta sus contribuciones operativas.

- **Principal:** saldo capital, cartera improductiva y morosidad en tres cortes, con variaciones de improductiva y mora.
- **Secundaria:** cargo, gerente de oficina, identidad del cliente y referencias de la consulta; útiles para ubicar responsabilidad y préstamo.
- **Mayor atención:** importes que aumentan frente al día anterior y al inicio. Una alta mora de bajo saldo no tiene necesariamente el mismo impacto que un gran aumento de improductiva.
- **Cambios:** admite rango que cruza meses. El tercer corte es `fecha_fin - 1 día`, no el día anterior a la fecha actual del navegador.
- **Decisiones:** revisar grupos o créditos que explican el aumento; seleccionar operaciones para contrastar con información de cobranza en otro módulo.
- **Investigación:** fila de agencia/asesor → diálogo de préstamos; detalle conserva fechas, diferidos y grupos, ofrece filtro de solo improductivos y orden de variaciones. La unión por número permite mostrar préstamos ausentes en alguno de los tres cortes.
- **Seguimiento:** se observan tres estados del préstamo y del grupo; falta un historial continuo y el estado de la gestión de la situación.
- **Comparte:** código de usuario, agencia y métricas de riesgo con Evaluación Asesores; número de préstamo con Matriz/Cobranza. El detalle de esta pantalla no incluye por sí mismo la recuperación acumulada de ese crédito.

**Limitación verificada:** reaplica la atribución del asesor del corte final a históricos; no basta una variación por asesor para afirmar desempeño personal. No se identifica control de alcance de agencias en el servicio, pues el router autentica pero no le entrega el contexto. Detalle sin paginación backend: la capacidad de investigar existe, pero la manejabilidad con muchos préstamos no se verificó. [E09](#e09), [E10](#e10), [E25](#e25).

### 5.6. Resumen de Colocación

**Pregunta principal:** ¿cuánto se adjudicó, en qué días y con qué características generales?

**Propósito de control:** seguir el ritmo de producción y contextualizarlo con operaciones, tasas y tamaño promedio.

- **Principal:** monto colocado, operaciones y colocación acumulada anual; distribución diaria de monto/operaciones.
- **Secundaria:** tasa nominal/real promedio y monto promedio; distribución de monto por agencia, producto, tipo de préstamo y asesor. Las tasas son promedios por operaciones válidas, no tasas ponderadas por monto colocado.
- **Mayor atención:** caída de monto u operaciones y concentración en pocos días; variaciones de tasa/producto que merezcan una revisión. El código no las contrasta con una meta institucional.
- **Comparaciones:** rango actual contra mes anterior completo; acumulado desde 1 de enero hasta fin contra año anterior completo en los indicadores anuales.
- **Decisiones:** decidir qué día o producción revisar; contrastar la evolución del flujo. No demuestra desviación frente a meta ni calidad del crédito adjudicado.
- **Investigación:** gráficos de composición construidos desde `prestamos_adjudicados`; seleccionar día en el gráfico temporal abre producto, valor, agencia, tipo de préstamo y asesor, bajo el contexto de fecha del día. La respuesta no incluye número de operación ni cliente, aun cuando la fuente interna utiliza número para deduplicar.
- **Seguimiento:** serie diaria y nuevas consultas del mismo mes; sin vinculación de la cohorte colocada con su cartera/mora o cobros posteriores.
- **Comparte:** métricas agregadas con Resumen Cooperativa y dimensiones de producción con Evaluación Colocación. El detalle identificable de operación está en la evaluación, no en los adjudicados de este resumen.

**Limitaciones verificadas:** adjudicados sin paginación y registros de día sin identificador de préstamo expuesto. Una lista vacía de agencias representa consolidado; una sola oficina en la sesión fuerza su nombre en la UI. No es equivalente a garantizar ese alcance en la API. [E13](#e13), [E14](#e14), [E16](#e16).

### 5.7. Evaluación de Colocación

**Pregunta principal:** ¿qué agencias, asesores o segmentos explican la variación de colocación?

**Propósito de control:** atribuir y descomponer producción para investigar las operaciones que forman un resultado.

- **Principal:** monto/operaciones y sus referencias por dimensión: agencia, asesor, tipo de préstamo, producto, segmento, condición, tasa nominal y rangos de tasa real.
- **Secundaria:** tasas y condiciones del detalle; ayudan a entender la mezcla de producción y posibles cambios comerciales.
- **Mayor atención:** descensos en el mismo rango del mes anterior y concentración de producción. Una comparación contra el mes completo aporta contexto, pero no mide por sí misma caída del ritmo.
- **Cambios:** período actual, mes anterior completo y mismas fechas desplazadas al mes previo. El servicio ajusta fechas cuando el mes previo es más corto.
- **Decisiones:** elegir agrupaciones y asesores que deben revisarse; analizar qué productos/condiciones componen el cambio. No evalúa rentabilidad ni riesgo futuro de las colocaciones.
- **Investigación:** selección de fila → detalle paginado, con número de operación, cliente, agencia, asesor, condición, producto, tipo, segmento, tasas y monto. El request conserva dimensión, asesores y agencia correspondiente; rangos de tasa real también se trasladan.
- **Seguimiento:** comparaciones de producción y nuevas consultas; no se identificó seguimiento posterior de esos mismos créditos en cartera y recuperación.
- **Comparte:** monto, operaciones, fecha de adjudicación y dimensiones con Resumen Colocación; `numero_operacion` se obtiene de `NumeroPrestamo` en Mongo y de `Prestamo.numero` en SQL, permitiendo una relación conceptual con cartera. No se comprobó conciliación real entre fuentes.

**Limitación verificada:** los filtros de asesor usan etiquetas textuales; hay número de operación en detalle, pero no una acción identificada que lo lleve a su evolución en otro módulo. La producción observada no equivale a cumplimiento de objetivos, pues no se identifica una meta en el contrato. [E13](#e13), [E15](#e15), [E16](#e16).

### 5.8. Resumen de Recuperación

**Pregunta principal:** ¿cuánto se recuperó en el rango, cómo se distribuye por rubro y cómo varía por día?

**Propósito de control:** seguir el flujo de cobros y advertir cambios en su volumen y composición.

- **Principal:** recuperación total, capital e interés y evolución diaria. Una reducción en capital recuperado es distinta de un cambio del total causado por otros rubros.
- **Secundaria:** interés de mora, seguro, castigo, cobranza, judicial, diferido y otros; sus nombres son tipos de cobro del catálogo, no evidencia de recuperación de capital ni diagnóstico de deterioro.
- **Mayor atención:** menor total/capital, concentración temporal y cambios de composición. La recuperación agregada no indica por sí sola si se cobraron las operaciones más problemáticas.
- **Comparaciones:** rango dentro del mismo mes contra mes anterior completo y año anterior completo.
- **Decisiones:** revisar días/rubros y decidir si conviene investigar responsables en Evaluación Recuperación o pendientes en Cobranza; ese traslado es manual.
- **Investigación:** selección del día en el gráfico abre distribución por tipo de cobro e importes, no los préstamos de ese día.
- **Seguimiento:** serie diaria agregada implementada; no se sigue una operación o una selección de deudores desde el resumen.
- **Comparte:** mismo servicio y componente de recuperación que Resumen Cooperativa; la pantalla añade serie diaria y filtros por oficinas de consulta.

**Limitación verificada:** días sin filas se rellenan con ceros; el contrato no distingue ausencia de carga y ausencia de cobros. El repositorio excluye la transacción `CASTIGO DE PRÉSTAMO`; el rubro `CASTIGO` del catálogo no permite suponer que sí incorpora esa transacción. [E17](#e17), [E18](#e18).

### 5.9. Cobranza Pendiente de Pago

**Pregunta principal:** ¿qué préstamos requieren cobro, cómo cambió su situación y qué importe podría mejorarla?

**Propósito de control:** preparar la revisión operativa de cobro y verificar cambios cuantitativos por préstamo.

- **Principal:** días de mora, calificación, provisión y saldo entre cierre anterior y fin; recuperado del rango; importe para estar al día, más cuota por vencer y cancelación total.
- **Secundaria:** cuotas pagadas/pendientes, último pago del rango, agencia/asesor, identidad deudor/garantes y datos para reportes.
- **Mayor atención:** préstamos con pendientes, deterioro y mayor exposición; ausencia de cobros en el rango. El último pago informado proviene de cobros dentro de ese rango, no necesariamente del último pago de toda la vida del préstamo.
- **Cambios:** comparación del cierre del mes previo con fin; recuperación entre inicio/fin; simulación de calificación, mora, saldo y provisión al cobrar una cuota. La simulación es un cálculo, no un cobro registrado ni un compromiso aceptado.
- **Decisiones:** seleccionar préstamos para revisar/contactar, dimensionar esfuerzo de cobro y contrastar el potencial de una cuota. No acredita ejecución de contacto ni permite confirmar una promesa de pago cumplida.
- **Investigación:** filtros por número de préstamo, agencia, asesor, estados y calificaciones; ordenamiento y totales; reportes Excel y PDF, con información de deudor/garantes y resumen. No se identificó trazabilidad de gestiones dentro del módulo.
- **Seguimiento:** comparación de situación y cobros del período por préstamo; requiere nuevas consultas, sin historial de acciones.
- **Comparte:** contrato operativo con detalle de Matriz y fuentes de situación/cobros con otros módulos. No todo préstamo listado tiene pago pendiente: el backend arma un universo del corte final y no filtra exclusivamente `pendiente_pago > 0`.

**Limitaciones verificadas:** el universo nace del corte final, incluye cancelados si constaban al cierre anterior y no reconstruye préstamos ausentes del final. La situación anterior es cierre mensual, no `fecha_inicio`. Los cálculos de cuotas se enriquecen con SQL operativo, por lo que un rango histórico no garantiza que todos los campos sean históricos. El listado no tiene paginación backend y se ordena inicialmente por total recuperado, no por riesgo o pendiente. [E20](#e20), [E21](#e21).

### 5.10. Evaluación de Recuperación

**Pregunta principal:** ¿qué responsables y dimensiones explican el volumen o cambio de cobros?

**Propósito de control:** localizar resultados de recuperación y revisar los préstamos que los componen.

- **Principal:** monto recuperado y operaciones por agencia, asesor, cargo, tipo de préstamo, producto, condición, tipo de cobro y abogado; referencias y diferencias.
- **Secundaria:** desglose por tipo de cobro y campos operativos del detalle para comprender qué se recuperó y qué sigue pendiente.
- **Mayor atención:** disminución frente al mismo rango previo y resultado concentrado en pocos responsables o rubros. No basta el total para afirmar eficacia respecto a todo lo que debía cobrarse.
- **Cambios:** período actual, mes anterior completo y mismo rango desplazado al mes anterior.
- **Decisiones:** elegir responsables o agrupaciones para revisión; examinar sus préstamos con cobros y saldo/pendiente operativo. No cubre por sí sola la cartera que no realizó ningún pago.
- **Investigación:** selección de fila conserva dimensión/agencia y filtros asesor/cargo; diálogo paginado de préstamos con socio, nombre, estado, calificación, último cobro del período, saldo, recuperado, pendiente, cuotas y diferido. Los cubos de filtro se solicitan cuando se usan filtros locales.
- **Seguimiento:** compara flujos por responsable; detalle del período con situación actual, sin evolución completa de cada operación ni registros de intervención.
- **Comparte:** cobros y dimensiones con Resumen Recuperación; número de préstamo y campos pendientes con Cobranza. Los totales de página del detalle no son totales de toda la selección; el contrato los distingue.

**Limitación verificada:** el servicio enriquece solo la página de cobros con datos actuales de SQL. Un préstamo no localizado en SQL se presenta con `SIN DATOS` y montos operativos cero, lo que no demuestra saldo o pendiente real cero. La atribución de recuperación y la cartera asignada no pueden asumirse idénticas solo porque se visualiza el mismo nombre de asesor. [E19](#e19), [E22](#e22).

## 6. Información repetida

La repetición es útil cuando cambia la pregunta, el nivel o la capacidad de investigar. No hay evidencia suficiente para eliminar pantallas solo por compartir indicadores.

| Información repetida | Dónde | Por qué y qué aporta | Evaluación funcional |
|---|---|---|---|
| Saldo, improductiva, mora y provisión | Resumen Cooperativa / Resumen Cartera | Visión conjunta de dominios versus evolución y concentración de cartera | Repetición necesaria; Resumen Cartera añade serie y dimensiones. [E04](#e04), [E06](#e06). |
| Saldo, mora, improductiva y provisión | Resumen Cartera / Evaluación Asesores | Estado por dimensión versus cambio atribuido por responsable/cargo | Útil si se diferencia corte de concentración y variación por asesor. Las tablas pueden parecer similares, pero la evaluación añade cierre/diferencia. [E07](#e07), [E08](#e08). |
| Mora/improductiva por asesor/agencia | Evaluación Asesores / Control Improductiva | Comparación mensual amplia versus tres cortes y préstamos explicativos | Hay solapamiento, con aporte real del detalle y cambio diario en Improductiva. [E09](#e09), [E10](#e10). |
| Monto, operaciones, promedios y tasas | Resumen Cooperativa / Resumen Colocación | Contexto global versus ritmo diario y adjudicados | Repetición justificada; existe similitud de indicadores, pero el resumen de dominio agrega análisis diario. [E13](#e13), [E14](#e14). |
| Monto/operaciones por agencia/asesor | Resumen Colocación / Evaluación Colocación | Flujo temporal versus composición y operaciones identificables | Necesidades diferentes. El detalle del día del resumen es menos identificable que el de la evaluación. [E14](#e14), [E15](#e15). |
| Recuperado total y por rubro | Resumen Cooperativa / Resumen Recuperación | Vista conjunta versus serie diaria | Comparten servicio/componente; la serie aporta capacidad distinta, aunque la síntesis repetida puede exigir reaprender contexto. [E17](#e17), [E18](#e18). |
| Recuperado por rubro/responsable | Resumen Recuperación / Evaluación Recuperación | Composición temporal versus atribución y préstamos con cobros | Repetición útil; no son universos automáticamente equivalentes al de cobranza. [E19](#e19), [E22](#e22). |
| Préstamo, mora, calificación, provisión y exigibles | Matriz / Cobranza / Improductiva | Migración / esfuerzo de cobro / contribución a improductiva | Necesario mantener relación. No implica que cada detalle muestre todos los campos o use la misma fecha efectiva. [E09](#e09), [E11](#e11), [E20](#e20). |

**Duplicación innecesaria verificada:** no se identifica una pantalla completa que replique exactamente otra sin aportar propósito o capacidad adicional. **Hipótesis de fricción:** se repiten bloques de síntesis y consultas sin continuidad de contexto; usuarios podrían repetir selección de fechas y agencias para reconstruir una misma investigación. Esto requiere observar tareas reales, no solo contar componentes.

**Ubicación conceptual:** la síntesis de dominios pertenece al contexto cooperativo; evolución/concentración de cartera al control de exposición; diferencias por responsable a evaluación; importes de cobro y escenarios al contexto operativo. La repetición de un indicador debe preservar su definición y aclarar qué universo se está controlando.

## 7. Relaciones entre módulos

### 7.1. Relaciones e identificadores disponibles

| Entidad compartida | Identificadores observados | Relación disponible | Límite verificado o no verificable |
|---|---|---|---|
| Agencia | `id_agencia`, `Agencia`, nombres en listas `agencias`, `oficinas_consulta` | SQL resuelve ID/nombre; filtros agrupan snapshots y hechos | Algunos contratos usan nombres normalizados; equivalencia y asignaciones reales no verificadas. |
| Asesor | `CodigoUsuario`, `CodigoAsesor`, `codigo_usuario`, nombres `NombreAsesor`/`asesor` | Evaluación/Improductiva conservan códigos; Matriz dispone de filtros; colocación/recuperación agrupan por etiquetas | No todos los detalles exponen código estable. Nombre igual no acredita identidad ni igual responsabilidad temporal. |
| Préstamo/operación | `NumeroPrestamo`, `NUMERO_PRESTAMO`, `numero_prestamo`, `numero_operacion` | Unión de cortes y cobros; en colocación `numero_operacion` proviene del número de préstamo | Resumen Colocación omite ese número en adjudicados; conciliación real entre fuentes no verificable. |
| Socio/cliente | `Cliente`, `socio`, `numero_socio`, `numero_cliente` | Identificación en detalles SQL/Mongo y conteo de clientes | No hay perfil transversal o historial por cliente identificado en el recorrido NEGOCIOS. |
| Responsabilidad de control | Usuario responsable de control, cargo, gerente y asesor | Dimensión del resumen de cartera y responsables en algunas agrupaciones | No equivale a asignación de un caso ni a reglas de visibilidad por cargo. |
| Fecha/corte | Fecha de sistema del token, cortes `YYYYMMDD`, fecha de adjudicación/pago | Comparaciones y hechos por período | Hay servicios que usan reloj del servidor o último corte disponible; no existe garantía de una fecha efectiva común. |

Fuentes: [E02](#e02), [E05](#e05), [E07](#e07), [E09](#e09), [E11](#e11), [E13](#e13), [E16](#e16), [E20](#e20), [E22](#e22), [E24](#e24).

### 7.2. Endpoints que permiten profundizar

| Endpoint | Profundización | ¿Está conectado a una acción de pantalla? |
|---|---|---|
| POST `/negocios/cartera-de-credito/cartera-improductiva/prestamos` | Grupos de asesor/agencia a préstamos de tres cortes | Sí, diálogo desde fila en Control Improductiva. |
| POST `/negocios/cartera-de-credito/matriz-transicion/filtros` | Catálogos encontrados en un corte | Sí, filtros avanzados; no es por sí mismo un detalle de operación. |
| POST `/negocios/cartera-de-credito/matriz-transicion/prestamos` | Celda origen/destino a préstamos | Sí, selección de celda. |
| POST `/negocios/colocacion/evaluacion-colocacion/detalle` | Dimensión seleccionada a operaciones/cliente | Sí, selección de fila y paginación. |
| POST `/negocios/colocacion/resumen-actual-adjudicados` | Agregados más adjudicados para distribución diaria | Sí, resumen diario; identidad de operación no expuesta en este contrato. |
| POST `/negocios/recuperacion/evaluacion-recuperacion/detalle` | Dimensión a préstamos con cobros y campos SQL | Sí, selección de fila y paginación. |
| POST `/negocios/recuperacion/recaudacion-acumulada/asesores` | Agencias a catálogo de asesores | Sí, prepara filtro de Cobranza. |
| POST `/negocios/recuperacion/recaudacion-acumulada` | Universo filtrado a situación/cobros por préstamo | Sí, consulta principal de Cobranza; no se invoca desde una señal de Resumen Cartera. |
| POST `/prestamos/universo/buscar` | Préstamos y snapshots por muchos filtros | No identificado en las pantallas revisadas. |

Fuentes: [E09](#e09), [E10](#e10), [E11](#e11), [E12](#e12), [E13](#e13), [E14](#e14), [E15](#e15), [E19](#e19), [E20](#e20), [E21](#e21), [E24](#e24).

### 7.3. Recorrido de control que realmente puede reconstruirse

Ejemplo conceptual aplicado a funcionalidades verificadas: **un jefe identifica aumento de morosidad**.

1. Resumen Cartera permite ver cambio agregado y distribución de mora al corte; no calcula desde esa tabla una lista de préstamos causantes del aumento.
2. Evaluación Asesores permite localizar responsables con aumento mensual de improductiva/mora, reingresando fechas/agencia. Si la señal original era diaria, esta comparación mensual no es la misma pregunta.
3. Control Improductiva permite comparar los extremos pertinentes y el día anterior al fin, elegir grupos y consultar sus préstamos. Aquí sí existe atribución cuantitativa de la diferencia en ese universo.
4. Matriz permite investigar cambios de calificación de operaciones del universo final, configurando nuevamente los cortes/filtros. No se identificó transferencia desde el diálogo de Improductiva.
5. Cobranza permite filtrar por préstamo y examinar cobros/pendientes; el usuario debe reconstruir la consulta y localizarlo. Evaluación Recuperación aporta préstamos con cobros, no necesariamente todos los que causaron el aumento de mora.
6. Una consulta posterior permite contrastar estados; no conserva dentro de ese recorrido la señal inicial, una actuación y su resultado.

**Resultado:** la investigación es posible por reconstrucción manual y por profundizaciones locales. No está implementada como una cadena continua entre módulos. Identificar préstamos que contribuyen a una diferencia no identifica automáticamente sus causas: desempleo del deudor, promesas incumplidas, reasignación u otras razones no se demuestran con esos agregados.

En las páginas revisadas no se identificaron navegación intermodular ni lectura de parámetros de otra pantalla para transportar fecha/agencia/asesor/préstamo. El menú ofrece acceso a módulos, pero no acredita enlaces de investigación entre resultados. [E04](#e04), [E06](#e06), [E08](#e08), [E10](#e10), [E12](#e12), [E15](#e15), [E19](#e19), [E21](#e21).

## 8. Evaluación por tipo de usuario

### 8.1. Qué puede afirmarse sobre autorización

**Verificado:** la sesión contiene cargo, agencia, roles, oficinas de consulta y menú. `AuthService` obtiene roles/oficinas desde SQL y menú según roles desde Mongo. `menuRouteGuard` comprueba que la ruta pertenezca al menú recibido; `authGuard` protege dashboard. El guard por rol `001` aparece para administración de permisos, no como regla explícita JEFE/ASESOR en NEGOCIOS. [E01](#e01), [E02](#e02), [E03](#e03).

**Verificado:** las pantallas de dominio toman opciones de `oficinas_consulta`; varias fijan la única oficina o filtran selecciones. Resumen Cooperativa envía un consolidado sin selector de agencia. No se identificó en estas páginas una restricción de datos al asesor autenticado basada en `usuario.sub` o en el cargo de sesión. Filtrar una tabla por cargo de los asesores mostrados no es una regla de autorización del usuario que consulta.

**Limitación verificada en el código de los endpoints revisados:** Bearer valida identidad, pero no acredita alcance por oficina/asesor. Comparativo, Colocación, Recuperación y Recaudación usan el contexto principalmente para fecha de sistema; los routers de Situación de Asesores, Improductiva y Matriz autentican con `_` y no pasan ese contexto al servicio. No se identifica allí cotejo de las agencias solicitadas con las oficinas del usuario. Tampoco se conoce si existe una restricción externa en el despliegue. No se realizó una prueba de acceso a datos reales. [E05](#e05), [E07](#e07), [E09](#e09), [E11](#e11), [E13](#e13), [E17](#e17), [E19](#e19), [E20](#e20).

**No verificable:** qué roles/códigos y permisos posee un jefe o asesor concreto, qué oficinas puede consultar, qué opciones recibe y si el menú desplegado coincide con rutas locales. Por tanto, la evaluación siguiente es condicional a que esa pantalla esté autorizada.

### 8.2. Jefe de agencia

| Necesidad inicial — hipótesis funcional | Soporte verificable si tiene acceso | Limitación para ejercer control |
|---|---|---|
| Supervisar su agencia | Filtros de oficina en resúmenes/evaluaciones; Improductiva por agencia | Resumen Cooperativa es consolidado; alcance real del jefe no verificado. |
| Comparar comportamiento de asesores | Evaluación Asesores, Improductiva y evaluaciones de producción/cobros | Criterios temporales y atribución distintos; no hay una lectura conjunta por asesor identificada. |
| Detectar cambios relevantes | Variaciones, ordenamientos, colores y matriz | No hay prioridad común ni metas verificadas; selección requiere juicio manual. |
| Identificar operaciones | Detalles de Improductiva, Matriz, Colocación y Recuperación | Saltos manuales; algunas señales no abren operaciones; recuperación se centra en créditos con cobros. |
| Verificar mejora tras supervisión | Tres cortes, matriz, series y nuevas consultas | No se enlaza una instrucción o compromiso con resultado y cierre. |

La herramienta apoya revisión del equipo y exposición, pero no permite atribuir todo deterioro al desempeño de un asesor: la reasignación histórica cambia la perspectiva del responsable, y las dimensiones de cobro/colocación no siempre expresan el mismo rol de gestión. [E07](#e07), [E09](#e09), [E16](#e16), [E22](#e22).

### 8.3. Asesor de negocios

| Necesidad inicial — hipótesis funcional | Soporte verificable si tiene acceso | Limitación para ejercer control |
|---|---|---|
| Ver sus indicadores | Seleccionar su agrupación en Evaluación Asesores o producción/cobros | No se identifica una vista automáticamente restringida/personalizada a él; sus permisos concretos son desconocidos. |
| Controlar su cartera | Improductiva y filtros de Matriz/Cobranza | Debe construir el contexto; la reasignación al corte final no es historial de autoría. |
| Identificar pagos pendientes | Cobranza: préstamos, cuotas, importes, datos deudor/garantes y reportes | Listado no filtra únicamente pendientes; no registra contactos o promesas de pago. |
| Seguir colocaciones | Resumen diario y evaluación con operaciones | No hay continuidad hacia la calidad o recuperación posterior de sus originaciones. |
| Seguir recuperación | Cobros y pendientes por préstamo; evaluación por asesor | Una lista de cobros no muestra toda la cartera sin pagos ni acredita una gestión ejecutada. |

**Hipótesis por validar con usuarios:** el jefe necesita priorización transversal del equipo y el asesor una selección accionable de operaciones. Antes de usar esas hipótesis como arquitectura definitiva deben contrastarse con responsabilidades reales, reglas de asignación y permisos existentes; este documento no inventa controles de roles adicionales.

## 9. Limitaciones para detectar e investigar problemas

| Hallazgo | Tipo | Efecto sobre control | Evidencia |
|---|---|---|---|
| Señales sin traslado de contexto entre módulos | Limitación verificada | Requiere repetir filtros y reconciliar manualmente las investigaciones | Páginas/stores y recorridos de detalle de [E04](#e04), [E06](#e06), [E08](#e08), [E10](#e10), [E12](#e12), [E15](#e15), [E19](#e19), [E21](#e21). |
| Referencias temporales heterogéneas | Limitación verificada | Un signo de variación puede reflejar duración, no deterioro del ritmo | Servicios de [E05](#e05), [E07](#e07), [E09](#e09), [E13](#e13), [E17](#e17), [E19](#e19). |
| Umbrales visuales de mora distintos | Limitación verificada | Diferentes énfasis para el mismo porcentaje; no se prueba una política común | Gauge 5/7/9 y tabla 5/10 en [E06](#e06). |
| Entradas `NA` clasificables como mejora | Limitación verificada por composición del código | Sobreestima mejora si se interpreta como desempeño de préstamos comparables | `_categorias` ordena y añade `NA`; `relationFor` usa índices; `totales` suma esa relación sin excepción. [E11](#e11), [E12](#e12). |
| Matriz y cobranza parten del universo final | Limitación verificada | No explican por sí solas cancelaciones/salidas que ya no están presentes | `_obtener_cortes` y `obtener_recaudacion_acumulada`. [E11](#e11), [E20](#e20). |
| Históricos reasignados al asesor del corte final | Funcionalidad verificada con límite de interpretación | Sirve para exposición asignada al fin; no acredita desempeño del responsable original | `_obtener_reasignaciones` y agrupación. [E07](#e07), [E09](#e09). |
| Ausencia convertida en cero | Limitación verificada | Puede parecer mejora/ausencia de deuda donde faltan datos | Gauge `?? 0`, tabla Asesores, días de recuperación y fallback SQL del detalle. [E06](#e06), [E08](#e08), [E17](#e17), [E19](#e19). |
| Mezcla de situación actual y rango histórico | Limitación verificada | Un estado/calificación del detalle no explica necesariamente el estado al cobrar | SQL actual en Evaluación Recuperación y cuotas operativas en Cobranza/Matriz. [E11](#e11), [E20](#e20), [E22](#e22). |
| Métricas disponibles pero no visibles en evaluación | Limitación verificada | No se responde directamente quién elevó capital vencido, aunque el backend lo devuelva | Contrato versus cinco columnas activas en [E07](#e07), [E08](#e08). |
| Adjudicados diarios sin identificador expuesto | Limitación verificada | El registro del día no puede utilizarse directamente para localizar su préstamo | `PrestamoAdjudicadoResponse`. [E13](#e13), [E14](#e14). |
| Detalle de recuperación incluye préstamos con cobros | Limitación del universo verificada | Menor cobro no se investiga completamente sin la cartera que no pagó | Detalle desde hechos de recuperación. [E19](#e19), [E22](#e22). |
| No se identifica ciclo de atención/gestión | Capacidad no identificada | Reconsultar indicadores no prueba qué se hizo ni si una situación quedó resuelta | Flujos de NEGOCIOS de [E01](#e01), [E10](#e10), [E19](#e19), [E20](#e20). |
| Detalles completos sin paginación en algunos módulos | Limitación de contrato verificada; impacto UX no verificable | Grandes universos pueden dificultar revisión; no se midió rendimiento real | Matriz, Improductiva, adjudicados y Recaudación. [E09](#e09), [E11](#e11), [E13](#e13), [E20](#e20). |
| Acceso por cargo/oficina no acreditado de extremo a extremo | Limitación de evidencia y controles revisados | No puede afirmarse que cada cargo ve exclusivamente su ámbito | [E02](#e02), [E03](#e03) y análisis de §8.1. |

### Ejemplos que delimitan lo que se puede concluir

- Consultar del 1 al 12 de octubre y obtener menos recuperación que en todo septiembre **no demuestra** caída del ritmo. Evaluación Recuperación sí entrega también el mismo rango de septiembre; Resumen Recuperación no utiliza esa referencia equivalente.
- Un cambio de mora de 6 % a 7 % es **1 punto porcentual**; no es lo mismo que una variación relativa de aproximadamente 16,7 %. El gauge resta porcentajes y rotula el resultado con `%`, lo que deja ambigua la unidad para quien supervisa. [E06](#e06).
- Un préstamo ausente en el corte inicial que aparece en `NA → A1` es una entrada al universo observado. La implementación puede sumarlo en mejora; eso no prueba recuperación de calidad de un préstamo previamente calificado.
- Si un crédito tiene cobros históricos y no aparece en el enriquecimiento SQL, los campos operativos cero del detalle son un fallback. No justifican concluir que su deuda fue cancelada. [E19](#e19).

**No verificable sin evidencia adicional:** puntualidad de las cargas, montos reconciliados entre fuentes, unicidad real de identificadores, impacto de reasignaciones en producción, magnitud de listados, políticas de umbrales, cumplimiento de metas y cobertura efectiva para cada cargo. Estos puntos no se presentan como defectos de producción comprobados.

## 10. Clasificación conceptual de la información

### 10.1. Qué pertenece funcionalmente a cada ámbito

| Ámbito conceptual | Información que le corresponde | Funcionalidades actuales relacionadas | Relación que debe entenderse, sin cambiar navegación |
|---|---|---|---|
| Síntesis de negocio | Situación global y balance de exposición/producción/cobros | Resumen Cooperativa | Señal agregada y dominio que la explica |
| Exposición crediticia | Saldo, vencido/no devenga, improductiva, mora y provisión | Resumen Cartera, Evaluación Asesores, Improductiva | Agencia/responsable/préstamo y fecha efectiva |
| Cambio de calidad | Calificaciones, migraciones, conteos e importes | Matriz de Transición | Cohorte comparable, entradas y salidas |
| Producción crediticia | Adjudicación, monto, operaciones, condiciones/tasas/productos | Resumen y Evaluación Colocación | Originación y comportamiento posterior de la misma operación |
| Resultado de recuperación | Flujos de cobro, rubros, dimensiones y variaciones | Resumen y Evaluación Recuperación | Cobro, préstamo, responsable y exposición pendiente |
| Necesidad operativa de cobro | Cuotas, pendientes, exigibles, deudor/garantes y escenarios | Cobranza; detalles de Matriz | Operación revisada y potencial efecto cuantitativo de un cobro |
| Seguimiento de gestión | Situación detectada, acción, responsable, plazo, resultado y cierre | No identificado como circuito en NEGOCIOS | Distinguir evolución de datos y comprobación de intervención |
| Alcance autorizado | Cargo, agencia, roles, oficinas y menú | Autenticación y controles de acceso | Disponibilidad de pantalla y universo visible de datos |

Es una clasificación del significado y responsabilidades de la información; no define menús, URLs, componentes ni organización física nueva.

### 10.2. Stocks, flujos, cambios y escenarios

| Tipo | Ejemplos existentes | Regla de interpretación |
|---|---|---|
| Stock al corte | Saldo capital, improductiva y provisión | Comparar fechas efectivas; no sumar saldos diarios como producción. |
| Ratio al corte | Morosidad = improductiva / saldo | Leer monto y denominador; diferenciar puntos porcentuales y cambio relativo. |
| Flujo del período | Adjudicaciones y cobros | Comparar períodos equivalentes y explicitar composición y universo. |
| Variación | Diferencia de saldo, mora, provisión o monto | Identificar referencia y si cambia población o responsable. |
| Distribución | Agencia, asesor, producto, cargo, territorio y rubro | Localiza exposición/resultados; no demuestra causalidad. |
| Transición | Calificación anterior/nueva y probabilidad observada | Distinguir pares comparables, entradas y salidas; no confundir frecuencia con predicción. |
| Escenario | Cobro de una cuota y provisión/calificación simuladas | Resultado hipotético, separado del estado efectivo y del pago registrado. |
| Metadato de calidad/contexto | Corte, fuente, faltantes y hora de consulta | Determinar comparabilidad y confianza; la hora de consulta no es fecha de actualización del dato. |

### 10.3. Información importante con visibilidad limitada

1. **Identidad de operación:** visible en evaluaciones y cobranza, omitida en adjudicados del resumen diario.
2. **Componentes específicos de deterioro:** capital vencido/no devenga y clientes llegan en el contrato de Evaluación Asesores, pero no son columnas de su tabla activa.
3. **Ausencias de cortes:** existen listas de faltantes en Asesores/Improductiva y valores nulos; no todas las vistas los expresan sin convertirlos en cero.
4. **Responsabilidad temporal:** ajustes de históricos al responsable final afectan el significado del análisis, aunque el usuario vea simplemente cierre y fin.
5. **Fechas efectivas del detalle:** recuperación del período y situación SQL actual necesitan interpretarse como tiempos distintos.
6. **Responsable de control:** es dimensión de cartera, pero no equivale a un caso con responsable y cierre.

Fuentes: [E05](#e05), [E06](#e06), [E07](#e07), [E08](#e08), [E09](#e09), [E13](#e13), [E19](#e19), [E22](#e22).

**Pantallas principalmente de síntesis/reporte:** Resumen Cooperativa, Resumen Cartera y Resumen Recuperación. **Evaluación con localización, sin operación:** Evaluación Asesores. **Control con investigación operativa local:** Improductiva, Matriz, Evaluación Colocación, Evaluación Recuperación y Cobranza. **Síntesis con investigación diaria limitada:** Resumen Colocación. Esta clasificación describe capacidad de uso, no valor inferior de los reportes.

## 11. Oportunidades de mejora

Las siguientes son **recomendaciones conceptuales**, pendientes de definición funcional. No incluyen interfaces, componentes, menús, rutas, endpoints ni refactorizaciones.

| Prioridad conceptual | Oportunidad | Motivo sustentado | Pregunta que permitiría resolver |
|---|---|---|---|
| Alta | Acordar significado de corte, período, variación, universo y responsable | Referencias/atribuciones diferentes y ceros de ausencia | ¿Estoy viendo un cambio comparable o un cambio de fecha, población o responsabilidad? |
| Alta | Distinguir entradas, salidas y cambios de calidad en el significado de la matriz | Universo final y clasificación `NA` | ¿Cuánto se deterioró la cartera comparable y cuánto cambió su composición? |
| Alta | Definir continuidad funcional entre señal, responsable y operación | Profundizaciones locales existentes, traslado manual intermodular | ¿Qué préstamos explican esta misma señal y qué recuperación tienen? |
| Alta | Contrastar alcance de acceso con cargos y responsabilidades reales | Menú, oficinas y Bearer no acreditan por sí solos alcance de datos | ¿Qué agencia y cartera corresponde supervisar a esta persona? |
| Alta | Establecer criterios de atención con responsables del negocio | Colores locales y diferencias sin metas verificadas | ¿Qué cambio exige revisión y con qué importancia frente a otros? |
| Media | Definir seguimiento de una situación e intervención | Comparar estados no acredita acción/resolución | ¿Lo detectado mejoró después de la actuación y puede darse por cerrado? |
| Media | Relacionar originación, calidad posterior y cobros por identidad de operación | Dimensiones y número compartidos, sin recorrido de cohorte | ¿La colocación de una agencia/asesor mantiene calidad y recuperación? |
| Media | Acordar lectura por cargo, preservando hipótesis de uso como hipótesis | Jefe evalúa equipo; asesor revisa operaciones, acceso no verificado | ¿Cuál es la pregunta de control cotidiana de cada cargo? |
| Media | Determinar cuándo una repetición aporta contexto y cuándo genera reconstrucción | Bloques compartidos con distintos niveles de análisis | ¿La segunda vista añade comparación o investigación útil? |

Antes de una futura arquitectura UX/UI conviene contrastar, con escenarios de trabajo y sin asumir permisos: significado institucional de improductiva/mora/provisión; criterio temporal de evaluación de un asesor; si se necesita cohorte de asignación o de originación; tratamiento de entradas/cancelados; quién atiende qué desviación; qué significa resolución; y qué información está autorizada para cada cargo.

**Hipótesis para validar:** los responsables valorarán más una continuidad de investigación con fechas/universo claros que otro conjunto de métricas agregadas. El código demuestra disponibilidad de piezas para esa continuidad, pero no demuestra preferencias de usuarios ni el resultado de una solución futura.

## 12. Conclusiones

1. **El aplicativo sí permite control analítico.** Hay comparaciones, localización y detalles operativos verificables; no corresponde describirlo como una simple colección de estadísticas.
2. **El control está organizado principalmente por dominio y por consulta.** La secuencia OBSERVAR → COMPARAR → DETECTAR → INVESTIGAR funciona dentro de algunos módulos y requiere reconstrucción manual entre ellos.
3. **El seguimiento cuantitativo existe; el seguimiento de gestión no se identificó.** Series, pares y tres cortes ayudan a comprobar evolución, pero no enlazan situación, acción y cierre.
4. **La repetición de indicadores tiene en general una función válida.** Debe evaluarse por contexto y capacidad añadida, no eliminarse por igualdad de nombres.
5. **La claridad del significado es una condición del control.** Períodos desiguales, entradas `NA`, ausencia convertida en cero, reasignación y mezcla de estado actual/histórico limitan conclusiones posibles.
6. **La evaluación por cargo sigue condicionada por evidencia pendiente.** Existen roles, oficinas y menú autorizado; no se verificaron asignaciones reales ni un alcance de datos garantizado de extremo a extremo para JEFE DE AGENCIA/ASESOR DE NEGOCIOS.

El siguiente trabajo debería partir de estas preguntas y relaciones funcionales comprobadas. Este documento no prescribe un sistema nuevo ni implementa cambios.

### Evidencia de código consultada

Los enlaces backend se resuelven desde `DataSacCore/docs` hacia `../app` o `../tests`; los frontend hacia `../../DataSacWebApp/src`. Cada grupo identifica archivos concretos y símbolos que sustentan los hallazgos. Los enlaces corresponden al estado local revisado.

<a id="e01"></a>
**E01 — Composición y rutas.** [Backend main](../app/main.py), [router NEGOCIOS](../app/modules/negocios/router.py), [router Analítica](../app/modules/analytic/router.py), [rutas raíz frontend](../../DataSacWebApp/src/app/app.routes.ts), [rutas NEGOCIOS](../../DataSacWebApp/src/app/features/negocios/negocios.routes.ts). `include_router`, `NEGOCIOS_ROUTES`, `loadComponent/loadChildren` y ruta comodín.

<a id="e02"></a>
**E02 — Sesión y alcance declarado.** [Dependencia Bearer](../app/modules/auth/dependencies.py), [schemas autenticación](../app/modules/auth/schemas.py), [AuthService](../app/modules/auth/service.py), [repositorio SQL autenticación](../app/modules/auth/repositories/sql_auth_repository.py), [repositorio Mongo menú](../app/modules/auth/repositories/mongo_menu_repository.py). `get_current_auth_context`, `_get_roles_out`, `_get_oficinas_consulta`, `_get_menu_for_roles` y `UsuarioTokenPayload`.

<a id="e03"></a>
**E03 — Acceso y menú frontend.** [MenuRouteGuard](../../DataSacWebApp/src/app/core/access/guards/menu-route.guard.ts), [MenuAnalyticStore](../../DataSacWebApp/src/app/core/access/state/menu-analytic.store.ts), [AuthStore](../../DataSacWebApp/src/app/core/auth/auth.store.ts), [RoleGuard](../../DataSacWebApp/src/app/core/access/guards/role.guard.ts). `canAccessRoute`, menú de sesión y guard por roles.

<a id="e04"></a>
**E04 — Resumen Cooperativa.** [Página](../../DataSacWebApp/src/app/features/negocios/resumen-actual/pages/resumen-actual-negocios.page.ts), [API](../../DataSacWebApp/src/app/features/negocios/resumen-actual/shared/services/resumen-actual-negocios.api.ts), [store](../../DataSacWebApp/src/app/features/negocios/resumen-actual/shared/services/resumen-actual-negocios.store.ts), [métricas](../../DataSacWebApp/src/app/features/negocios/resumen-actual/shared/utils/resumen-actual-negocios.utils.ts), [bloque colocación](../../DataSacWebApp/src/app/features/negocios/resumen-actual/pages/components/colocacion-resumen.component.ts). `consultar`, tres solicitudes con `concat`, errores por sección y `agencias: []`.

<a id="e05"></a>
**E05 — Comparativo de cartera backend.** [Router Resumen Actual](../app/modules/negocios/cartera_de_credito/resumen_actual/router.py), [servicio compartido](../app/modules/analytic/cartera_de_credito/comparativo_cartera/service.py), [schemas](../app/modules/analytic/cartera_de_credito/comparativo_cartera/schemas.py), [repositorio Mongo](../app/modules/analytic/cartera_de_credito/comparativo_cartera/repositories/mongo_comparativo_cartera_repository.py). `obtener_comparativo`, `_resumir_morosidad`, `fecha_corte_resumen`, puntos, agencias y dimensiones.

<a id="e06"></a>
**E06 — Resumen Cartera frontend.** [Página](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/resumen-actual/pages/resumen-actual/resumen-actual.page.ts), [tabla dimensional](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/resumen-actual/pages/resumen-actual/components/resumen-cartera-tabla.component.ts), [gauge morosidad](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/resumen-actual/pages/resumen-actual/components/morosidad-gauge.component.ts), [gráfico evolución](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/resumen-actual/pages/resumen-actual/components/evolucion-cartera-chart.component.ts), [utilidades](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/resumen-actual/shared/utils/resumen-actual.utils.ts). `tabs`, `colorFinalRango`, `valorActual`, variaciones y filtros de oficinas.

<a id="e07"></a>
**E07 — Evaluación Asesores backend.** [Router](../app/modules/negocios/cartera_de_credito/situacion_crediticia_asesores/router.py), [service](../app/modules/negocios/cartera_de_credito/situacion_crediticia_asesores/service.py), [schemas](../app/modules/negocios/cartera_de_credito/situacion_crediticia_asesores/schemas.py). `obtener`, `_obtener_reasignaciones`, `_agrupar_por_asesor`, `_provision_requerida`, diferencias y faltantes.

<a id="e08"></a>
**E08 — Evaluación Asesores frontend.** [Página](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/evaluacion-asesores/pages/evaluacion-asesores/evaluacion-asesores.page.ts), [tabla](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/evaluacion-asesores/pages/evaluacion-asesores/components/evaluacion-asesores-tabla.component.ts), [store](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/evaluacion-asesores/shared/services/evaluacion-asesores.store.ts), [API](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/evaluacion-asesores/shared/services/evaluacion-asesores.api.ts). Cinco `metricas`, `tono`, `valor`, resúmenes por agencia/cargo y consulta sin detalle de préstamos.

<a id="e09"></a>
**E09 — Improductiva backend.** [Router](../app/modules/negocios/cartera_de_credito/cartera_improductiva/router.py), [service](../app/modules/negocios/cartera_de_credito/cartera_improductiva/service.py), [schemas](../app/modules/negocios/cartera_de_credito/cartera_improductiva/schemas.py). `_preparar_cortes`, `obtener_prestamos`, unión por número, selección después de reasignar y filtro `solo_improductivos`.

<a id="e10"></a>
**E10 — Improductiva frontend.** [Página](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/control-cartera-improductiva/pages/control-cartera-improductiva/control-cartera-improductiva.page.ts), [store](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/control-cartera-improductiva/shared/services/control-cartera-improductiva.store.ts), [diálogo](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/control-cartera-improductiva/pages/control-cartera-improductiva/components/control-cartera-improductiva-prestamos-dialog.component.ts), [tabla](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/control-cartera-improductiva/pages/control-cartera-improductiva/components/control-cartera-improductiva-tabla.component.ts). `filaSeleccionada`, `abrirDetalle`, `consultarDetalle` y orden de variaciones.

<a id="e11"></a>
**E11 — Matriz backend.** [Router](../app/modules/negocios/cartera_de_credito/matriz_transicion/router.py), [service](../app/modules/negocios/cartera_de_credito/matriz_transicion/service.py), [schemas](../app/modules/negocios/cartera_de_credito/matriz_transicion/schemas.py). `_obtener_cortes`, `_construir_matriz`, `_categorias`, `obtener_prestamos` y `_construir_prestamo`.

<a id="e12"></a>
**E12 — Matriz frontend.** [Página](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/matriz-de-transicion/pages/matriz-de-transicion/matriz-de-transicion.page.ts), [conteo](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/matriz-de-transicion/pages/matriz-de-transicion/components/matriz-transicion-conteo.component.ts), [utilidades](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/matriz-de-transicion/shared/utils/matriz-transicion.utils.ts), [store](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/matriz-de-transicion/shared/services/matriz-transicion.store.ts), [métricas](../../DataSacWebApp/src/app/features/negocios/cartera-de-credito/matriz-de-transicion/shared/matriz-transicion.config.ts). `seleccionarCelda`, `relationFor`, `totales` y detalle de préstamos.

<a id="e13"></a>
**E13 — Colocación backend.** [Router](../app/modules/negocios/colocacion/resumen/router.py), [service](../app/modules/negocios/colocacion/resumen/service.py), [schemas](../app/modules/negocios/colocacion/resumen/schemas.py), [dependencias](../app/modules/negocios/colocacion/resumen/dependencies.py). `_construir_periodos`, `obtener_resumen_actual`, `obtener_resumen_actual_con_adjudicados`, `obtener_detalle` y `PrestamoAdjudicadoResponse`.

<a id="e14"></a>
**E14 — Resumen Colocación frontend.** [Página](../../DataSacWebApp/src/app/features/negocios/colocacion/resumen-colocacion/pages/resumen-colocacion/resumen-colocacion.page.ts), [API](../../DataSacWebApp/src/app/features/negocios/colocacion/resumen-colocacion/shared/services/resumen-colocacion-actual.api.ts), [indicadores](../../DataSacWebApp/src/app/features/negocios/colocacion/resumen-colocacion/pages/resumen-colocacion/components/resumen-colocacion-indicadores.component.ts), [colocación por día](../../DataSacWebApp/src/app/features/negocios/colocacion/resumen-colocacion/pages/resumen-colocacion/components/colocacion-por-dia.component.ts). `dias`, `onClick`, diálogo diario e indicadores anuales con `acumulado_anual`.

<a id="e15"></a>
**E15 — Evaluación Colocación frontend.** [Página](../../DataSacWebApp/src/app/features/negocios/colocacion/evaluacion-colocacion/pages/evaluacion-colocacion/evaluacion-colocacion.page.ts), [store](../../DataSacWebApp/src/app/features/negocios/colocacion/evaluacion-colocacion/shared/services/resumen-colocacion.store.ts), [API](../../DataSacWebApp/src/app/features/negocios/colocacion/evaluacion-colocacion/shared/services/resumen-colocacion.api.ts), [diálogo](../../DataSacWebApp/src/app/features/negocios/colocacion/evaluacion-colocacion/pages/evaluacion-colocacion/components/resumen-colocacion-detalle-dialog.component.ts). `abrirDetalle`, dimensiones, filtros y paginación.

<a id="e16"></a>
**E16 — Fuentes compartidas de colocación.** [Servicio histórico](../app/modules/analytic/colocacion/colocacion_historico/service.py), [repositorio Mongo](../app/modules/analytic/colocacion/colocacion_historico/repositories/mongo_colocacion_historico_repository.py), [repositorio SQL](../app/modules/analytic/colocacion/colocacion_historico/repositories/sql_colocacion_historico_repository.py). Totales y detalle por rango, uso de `NumeroPrestamo`/`Prestamo.numero` y deduplicación interna de adjudicados.

<a id="e17"></a>
**E17 — Resumen Recuperación backend.** [Router](../app/modules/negocios/recuperacion/resumen_recuperacion/router.py), [service](../app/modules/negocios/recuperacion/resumen_recuperacion/service.py), [schemas](../app/modules/negocios/recuperacion/resumen_recuperacion/schemas.py), [repositorio Mongo](../app/modules/negocios/recuperacion/resumen_recuperacion/repositories/mongo_resumen_recuperacion_repository.py), [tipos de cobro](../app/modules/negocios/recuperacion/resumen_recuperacion/constants.py). `obtener_resumen`, rangos completos, diario completado con `_ceros` y transacción excluida.

<a id="e18"></a>
**E18 — Resumen Recuperación frontend.** [Página](../../DataSacWebApp/src/app/features/negocios/recuperacion/resumen-recuperacion/pages/resumen-recuperacion/resumen-recuperacion.page.ts), [API](../../DataSacWebApp/src/app/features/negocios/recuperacion/resumen-recuperacion/shared/services/resumen-recuperacion.api.ts), [gráfico diario](../../DataSacWebApp/src/app/features/negocios/recuperacion/resumen-recuperacion/pages/resumen-recuperacion/components/recuperacion-diaria.component.ts), [componente compartido](../../DataSacWebApp/src/app/features/negocios/shared/components/recuperacion-resumen.component.ts), [utilidades compartidas](../../DataSacWebApp/src/app/features/negocios/shared/utils/recuperacion-resumen.utils.ts). `detalleDia`, distribución por rubros y variaciones mes/año.

<a id="e19"></a>
**E19 — Evaluación Recuperación.** [Router backend](../app/modules/negocios/recuperacion/evaluacion_recuperacion/router.py), [service backend](../app/modules/negocios/recuperacion/evaluacion_recuperacion/service.py), [schemas](../app/modules/negocios/recuperacion/evaluacion_recuperacion/schemas.py), [página](../../DataSacWebApp/src/app/features/negocios/recuperacion/evaluacion-recuperacion/pages/evaluacion-recuperacion/evaluacion-recuperacion.page.ts), [store](../../DataSacWebApp/src/app/features/negocios/recuperacion/evaluacion-recuperacion/shared/services/evaluacion-recuperacion.store.ts), [API](../../DataSacWebApp/src/app/features/negocios/recuperacion/evaluacion-recuperacion/shared/services/evaluacion-recuperacion.api.ts). `obtener_evaluacion`, `obtener_detalle`, `abrirDetalle`, cubos, totales de página y fallback sin datos SQL.

<a id="e20"></a>
**E20 — Cobranza backend.** [Router](../app/modules/negocios/recuperacion/recaudacion_acumulada/router.py), [service](../app/modules/negocios/recuperacion/recaudacion_acumulada/service.py), [schemas](../app/modules/negocios/recuperacion/recaudacion_acumulada/schemas.py), [repositorio Mongo](../app/modules/negocios/recuperacion/recaudacion_acumulada/repositories/mongo_recaudacion_acumulada_repository.py), [repositorio SQL cuotas](../app/modules/negocios/recuperacion/recaudacion_acumulada/repositories/sql_detalle_cuotas_repository.py). Universo final, cierre anterior, recuperaciones, cuotas y escenario; `PrestamoRecaudadoAcumulado`.

<a id="e21"></a>
**E21 — Cobranza frontend.** [Página](../../DataSacWebApp/src/app/features/negocios/recuperacion/cobranza-pendiente-pago/pages/cobranza-pendiente-pago/cobranza-pendiente-pago.page.ts), [tabla](../../DataSacWebApp/src/app/features/negocios/recuperacion/cobranza-pendiente-pago/pages/cobranza-pendiente-pago/components/cobranza-pendiente-pago-tabla.component.ts), [store](../../DataSacWebApp/src/app/features/negocios/recuperacion/cobranza-pendiente-pago/shared/services/cobranza-pendiente-pago.store.ts), [Excel](../../DataSacWebApp/src/app/features/negocios/recuperacion/cobranza-pendiente-pago/shared/services/cobranza-pendiente-pago-excel.service.ts), [PDF](../../DataSacWebApp/src/app/features/negocios/recuperacion/cobranza-pendiente-pago/pages/cobranza-pendiente-pago/components/prestamos-pdf-dialog/prestamos-pdf-dialog.service.ts). Filtros, totales, exportaciones y selección de agencias/asesores.

<a id="e22"></a>
**E22 — Fuentes de evaluación de recuperación.** [Servicio histórico](../app/modules/analytic/recuperacion/recuperacion_historico/service.py), [repositorio Mongo](../app/modules/analytic/recuperacion/recuperacion_historico/repositories/mongo_recuperacion_historico_repository.py), [detalle SQL actual](../app/modules/negocios/recuperacion/evaluacion_recuperacion/repositories/sql_detalle_recuperacion_repository.py), [dependencias](../app/modules/negocios/recuperacion/evaluacion_recuperacion/dependencies.py). Hechos por rango, agrupación, detalle y `obtener_datos_actuales`.

<a id="e23"></a>
**E23 — Inicio activo y capacidad adicional.** [DashboardPage](../../DataSacWebApp/src/app/features/dashboard/dashboard.page.ts), [InicioPage](../../DataSacWebApp/src/app/features/dashboard/inicio/pages/inicio.page.ts), [control de bienvenida](../../DataSacWebApp/src/app/features/dashboard/inicio/shared/services/inicio-bienvenida-control.service.ts), [InicioStore](../../DataSacWebApp/src/app/features/dashboard/inicio/shared/services/inicio.store.ts), [servicio backend Inicio](../app/modules/negocios/inicio/service.py), [cartera hoy/ayer](../app/modules/negocios/cartera_de_credito/resumen_diario_asesores/service.py), [colocación hoy/ayer](../app/modules/negocios/colocacion/diaria_asesores/service.py). La composición activa de bienvenida no invoca el store financiero.

<a id="e24"></a>
**E24 — Universo de préstamos backend.** [Router](../app/modules/prestamos/router.py), [schemas](../app/modules/prestamos/schemas.py), [service](../app/modules/prestamos/service.py), [repositorio Mongo](../app/modules/prestamos/repositories/mongo_universo_repository.py). `/universo/buscar`, snapshots y filtros por identidades/responsables.

<a id="e25"></a>
**E25 — Pruebas ejecutadas y límite de validación.** [Tests de Matriz](../tests/test_matriz_transicion.py), [tests de Improductiva](../tests/test_cartera_improductiva.py). Fakes, contratos y unión/reasignación; resultado 22 aprobadas y una falla descrita en §1. No se ejecutaron pruebas contra bases de datos ni se verificó UI en una sesión real.
