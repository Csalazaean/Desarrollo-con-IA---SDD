# Feature Specification: 003-task-organization-priority

**Feature Branch**: `003-task-organization-priority`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Especifica el tercer incremento funcional de TaskControl: organización y priorización de tareas. Este incremento cubre HU-07, HU-08 y HU-09 del backlog, y asume que los Incrementos 1 y 2 ya están implementados."

## Clarifications

### Session 2026-10-06

- Q: Cuando un usuario elimina una categoría mientras, en otra pestaña, tiene abierta la edición de una tarea asignada a esa misma categoría, ¿qué debe pasar al intentar guardar esa tarea? → A: Guardar la tarea igual, con `category_id = NULL` automáticamente (la categoría ya no existe, se ignora silenciosamente; nunca bloquea el guardado).
- Q: Cuando dos o más tareas comparten el mismo nivel de prioridad, ¿en qué orden deben aparecer entre sí dentro del listado ordenado por prioridad? → A: Desempate por fecha límite (`due_date`), la más próxima primero; las tareas sin `due_date` se ubican al final del grupo de su prioridad (tratadas como sin urgencia de fecha).
- Q: ¿El campo `color` de una categoría debe validarse con un formato hexadecimal estricto (`#RRGGBB`), o se acepta cualquier texto de hasta 7 caracteres sin validar su formato? → A: Validar formato hexadecimal estricto `#RRGGBB` (6 dígitos hex tras `#`); rechazar con 400 si no cumple.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prioridad de Tareas y Ordenamiento (HU-07) (Priority: P1)

Como usuario autenticado, quiero asignar un nivel de prioridad (alta, media o baja) a cada una de mis tareas y ordenar el listado según este criterio, para planificar y decidir en qué orden ejecutar mis actividades.

**Why this priority**: Facilita la toma de decisiones inmediata sobre la carga de trabajo y es el núcleo de la organización de tareas antes de estructurarlas en grupos o proyectos.

**Independent Test**: Puede probarse creando tareas con diferentes prioridades (verificando que si no se especifica una, se asigna automáticamente "media"), cambiando la prioridad de una tarea existente y ordenando el listado por prioridad para verificar que se respete la jerarquía (alta → media → baja o viceversa).

**Acceptance Scenarios**:
1. **Given** un usuario autenticado que crea una tarea sin indicar prioridad, **When** la tarea se guarda, **Then** el sistema le asigna explícitamente la prioridad por defecto "media".
2. **Given** un usuario que crea o edita una tarea propia, **When** selecciona un nivel de prioridad válido ("alta", "media" o "baja"), **Then** el valor se actualiza, persiste en el sistema y se registra el evento en el log de auditoría.
3. **Given** un usuario con múltiples tareas activas con distintas prioridades, **When** solicita ordenar su listado por prioridad, **Then** el sistema presenta las tareas organizadas respetando el orden de importancia (alta, media, baja) manteniendo activos los filtros por estado ya existentes.
4. **Given** una tarea perteneciente a otro usuario, **When** se intenta cambiar su prioridad, **Then** el sistema rechaza la operación por falta de autorización.

---

### User Story 2 - Agrupación por Categorías o Proyectos (HU-08) (Priority: P1)

Como usuario autenticado, quiero crear categorías personalizadas y asociar mis tareas a ellas, para clasificar mi trabajo por áreas temáticas o proyectos sin correr el riesgo de que mis tareas se borren si decido eliminar una categoría.

**Why this priority**: Permite la organización contextual de alto nivel requerida para usuarios que gestionan múltiples responsabilidades y proyectos en simultáneo.

**Independent Test**: Puede probarse creando categorías personales, asignando tareas a una categoría (comprobando que una tarea pertenezca como máximo a una), filtrando tareas por categoría, y finalmente eliminando la categoría para verificar que todas sus tareas asociadas permanezcan intactas con su categoría en estado "sin categoría" (desasociadas, sin borrado en cascada).

**Acceptance Scenarios**:
1. **Given** un usuario autenticado, **When** crea una categoría indicando un nombre obligatorio y único para su cuenta, **Then** la categoría queda creada y disponible para su uso personal.
2. **Given** un usuario autenticado que crea o edita una tarea, **When** selecciona una de sus categorías existentes, **Then** la tarea queda vinculada a dicha categoría (máximo una categoría por tarea).
3. **Given** una tarea asociada a una categoría, **When** el usuario decide retirarla de la categoría, **Then** la tarea queda en estado "sin categoría" y continúa visible en el listado general.
4. **Given** una categoría que contiene varias tareas asociadas, **When** el usuario propietario elimina dicha categoría, **Then** la categoría se elimina del sistema y el 100% de las tareas vinculadas quedan automáticamente "sin categoría" (huérfanas de categoría), sin sufrir eliminación física ni lógica.
5. **Given** una categoría creada por el Usuario A, **When** el Usuario B intenta consultar, modificar o asignarse dicha categoría a una de sus tareas, **Then** el sistema rechaza la operación impidiendo el acceso a categorías ajenas.

---

### User Story 3 - Indicación Confiable de Tareas Vencidas (HU-09) (Priority: P2)

Como usuario autenticado, quiero ver una indicación clara de cuáles de mis tareas tienen su fecha límite superada y aún no han sido finalizadas, para atender urgentemente el trabajo atrasado sin inconsistencias horarias.

**Why this priority**: Proporciona retroalimentación visual crítica de plazos y cumplimiento de compromisos temporales.

**Independent Test**: Puede probarse registrando tareas con fechas límites en el pasado y en el futuro, con estados "pendiente", "en progreso" y "completada", y verificando que el indicador de vencimiento se compute en el servidor exclusivamente para las tareas no completadas cuya fecha límite ya expiró.

**Acceptance Scenarios**:
1. **Given** una tarea con fecha límite anterior a la fecha actual y con estado "pendiente" o "en progreso", **When** el usuario consulta su listado de tareas, **Then** el sistema expone y resalta la tarea con el indicador de "vencida".
2. **Given** una tarea con fecha límite posterior a la fecha actual, **When** se consulta el listado, **Then** la tarea NO se marca como vencida.
3. **Given** una tarea cuya fecha límite ya pasó, pero cuyo estado es "completada", **When** se consulta el listado, **Then** el sistema NUNCA la marca como vencida.
4. **Given** una tarea cuya fecha límite ya pasó, pero que fue eliminada lógicamente, **When** se evalúa su estado, **Then** el sistema NUNCA la considera como vencida.
5. **Given** la consulta de tareas desde clientes en diferentes zonas horarias, **When** se evalúa el vencimiento, **Then** el resultado es determinado estrictamente por el backend bajo el estándar UTC sin depender de la configuración horaria del navegador o cliente.

---

### Edge Cases

- **Nombres de categorías duplicados para el mismo usuario**: Si un usuario intenta crear una categoría con el mismo nombre que otra que ya posee (incluso variando mayúsculas/minúsculas), el sistema debe rechazar la creación indicando duplicidad.
- **Nombres de categorías idénticos entre usuarios distintos**: Dos usuarios distintos deben poder tener categorías con el mismo nombre (ej. "Trabajo") sin colisión ni visibilidad compartida.
- **Eliminación concurrente de categoría durante edición de tarea**: Si un usuario elimina una categoría en una pestaña mientras edita una tarea asignada a esa categoría en otra, al guardar la tarea el sistema DEBE asignarle `category_id = NULL` automáticamente e ignorar silenciosamente la categoría ya inexistente — nunca rechaza el guardado por este motivo (ver Clarifications, Session 2026-10-06).
- **Tareas con fecha límite fijada exactamente al día actual**: La comparación de vencimiento debe considerar la fecha completa en UTC para que una tarea del día en curso no se considere vencida hasta que concluya la jornada.
- **Ordenamiento combinado con filtros**: Si el usuario filtra por estado `in_progress` y ordena por prioridad descendente, el sistema debe aplicar primero el filtro de estado y luego el orden jerárquico de prioridad.
- **Valores inválidos de prioridad en peticiones manipuladas**: Si se envía un valor distinto de "alta", "media" o "baja", la petición debe ser rechazada con código de validación 400.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE asignar a toda tarea nueva un nivel de prioridad entre tres valores permitidos: "alta" (`high`), "media" (`medium`) o "baja" (`low`).
- **FR-002**: Si al crear una tarea no se especifica una prioridad, el sistema DEBE asignar por defecto el nivel "media" (`medium`).
- **FR-003**: El sistema DEBE permitir a un usuario autenticado modificar el nivel de prioridad de cualquiera de sus tareas no eliminadas en cualquier momento.
- **FR-004**: El sistema DEBE permitir ordenar el listado de tareas por prioridad (respetando la precedencia: alta > media > baja, y viceversa), manteniendo la compatibilidad con los filtros por estado existentes. Dentro de un mismo nivel de prioridad, el desempate se hace por `due_date` ascendente (la más próxima primero); las tareas sin `due_date` se ubican al final de su grupo de prioridad (ver Clarifications, Session 2026-10-06).
- **FR-005**: El sistema DEBE permitir a un usuario autenticado crear categorías indicando un nombre obligatorio (máximo 50 caracteres) y opcionalmente color/descripción. Si se provee `color`, DEBE cumplir el formato hexadecimal estricto `#RRGGBB`; de lo contrario la petición se rechaza con 400 (ver Clarifications, Session 2026-10-06).
- **FR-006**: El sistema DEBE garantizar la unicidad del nombre de categoría por usuario (un usuario no puede tener dos categorías con el mismo nombre).
- **FR-007**: El sistema DEBE permitir a un usuario listar, editar y eliminar sus propias categorías.
- **FR-008**: El sistema DEBE permitir que una tarea pertenezca a máximo una categoría (relación opcional, puede no tener categoría).
- **FR-009**: Al eliminar una categoría, el sistema NUNCA DEBE eliminar las tareas asociadas; las tareas DEBEN quedar sin categoría (`category_id = NULL`), preservando toda su información y su historial de auditoría.
- **FR-010**: El sistema DEBE impedir que un usuario asocie una tarea propia a una categoría creada por otro usuario.
- **FR-011**: El sistema DEBE calcular el estado de vencimiento de las tareas exclusivamente en el backend bajo una referencia temporal estándar (UTC).
- **FR-012**: El sistema DEBE marcar una tarea como vencida (`is_overdue = true`) si y solo si: posee fecha límite (`due_date` no nula), la fecha límite es menor a la fecha actual del sistema, su estado es distinto de "completada" (`status != 'completed'`) y no está eliminada lógicamente (`is_deleted = false`).
- **FR-013**: El sistema NUNCA DEBE delegar el cálculo de vencimiento a la lógica de JavaScript del cliente ni depender de la hora del navegador.
- **FR-014**: El sistema DEBE incluir el indicador de vencimiento (`is_overdue`) en el contrato de datos expuesto para el renderizado del listado de tareas.
- **FR-015**: El sistema DEBE registrar logs estructurados de auditoría para la creación, actualización y eliminación de categorías (`CATEGORY_CREATED`, `CATEGORY_UPDATED`, `CATEGORY_DELETED`).

---

### Exclusiones Explícitas (Fuera de Alcance)

- Asignación de tareas a otros usuarios del sistema (`HU-10`).
- Sistema interno de notificaciones en la aplicación al vencer o asignar tareas (`HU-11`).
- Interacción asíncrona sin recarga de página para completar tareas (`HU-15`).
- Reordenamiento visual mediante arrastrar y soltar (drag and drop) (`HU-16`).
- Pertenencia de una tarea a múltiples categorías simultáneas (relación estrictamente 0 a 1).

---

### Key Entities

- **Category**:
  - Representa un grupo temático o proyecto creado por un usuario.
  - Atributos: `id` (entero PK), `user_id` (FK a User, no nulo), `name` (cadena no nula, máx 50), `description` (texto opcional), `color` (cadena opcional, máx 7, formato estricto `#RRGGBB` si se provee), `created_at` (timestamp UTC).
  - Restricción de unicidad: `(user_id, name)` único.
- **Task (Actualización)**:
  - Nuevos atributos y relaciones:
    - `priority`: enum/cadena no nula (`high`, `medium`, `low`), por defecto `medium`.
    - `category_id`: FK nullable a Category con comportamiento `ON DELETE SET NULL`.
  - Atributo computado en backend:
    - `is_overdue`: booleano calculado dinámicamente (`due_date < current_date and status != 'completed' and not is_deleted`).
- **AuditLog**:
  - Incorpora nuevas acciones: `CATEGORY_CREATED`, `CATEGORY_UPDATED`, `CATEGORY_DELETED`, además de auditar el cambio de prioridad dentro de `TASK_UPDATED`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las tareas creadas sin prioridad explícita se persisten con prioridad "media".
- **SC-002**: El listado ordenado por prioridad agrupa y ordena el 100% de las tareas en la jerarquía correspondiente sin alterar los filtros por estado seleccionados.
- **SC-003**: Cero tareas eliminadas cuando se elimina una categoría: el 100% de las tareas pertenecientes a una categoría borrada conservan su existencia y quedan desvinculadas sin pérdida de datos.
- **SC-004**: Cero inconsistencias en el cálculo de tareas vencidas provocadas por la zona horaria del cliente (precisión del 100% determinada en backend).
- **SC-005**: 0% de tareas completadas o eliminadas marcadas erróneamente como vencidas.
- **SC-006**: Cobertura de pruebas automatizadas del 100% sobre la lógica de ordenamiento, desvinculación `SET NULL` y cálculo de vencimiento antes de la integración en la interfaz.

---

## Assumptions

- Las prioridades se gestionan como valores normalizados: `high` (Alta), `medium` (Media), `low` (Baja).
- La fecha límite (`due_date`) almacena una fecha calendario (YYYY-MM-DD); una tarea se considera vencida cuando el día calendario actual en UTC es estrictamente posterior a la fecha límite asignada y la tarea permanece sin completar.
- Las categorías son estrictamente personales: un usuario solo ve y gestiona sus propias categorías.
- El ordenamiento por defecto del listado, si el usuario no especifica orden por prioridad, continúa siendo por fecha de creación o fecha límite.
- La separación de responsabilidades (Principio II) se mantiene con la creación del modelo `Category`, el servicio `CategoryService` y el blueprint `categories_bp`.
