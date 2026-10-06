# Feature Specification: 001-basic-tasks-auth

**Feature Branch**: `001-basic-tasks-auth`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "Especifica el primer incremento funcional de TaskControl: gestión básica de tareas con autenticación de usuarios. Este incremento cubre HU-01 a HU-04 y HU-12–HU-13 del backlog del proyecto."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registro de Usuario (HU-12) (Priority: P1)

Como nuevo usuario del sistema, quiero registrarme ingresando mi correo electrónico y una contraseña segura, para tener una cuenta personal y acceder al gestor de tareas.

**Why this priority**: Es la base de identidad del sistema. Sin registro de usuario no se puede autenticar ni aislar las tareas por propietario.

**Independent Test**: Puede probarse registrando un nuevo correo y contraseña válida mediante el formulario/endpoint de registro y verificando que el usuario quede persistido con su contraseña cifrada (hash) y pueda iniciar sesión.

**Acceptance Scenarios**:
1. **Given** un correo no registrado previamente y una contraseña válida, **When** el usuario envía el formulario de registro, **Then** la cuenta se crea exitosamente, la contraseña se almacena hasheada y se redirige al inicio de sesión o panel principal.
2. **Given** un correo que ya existe en el sistema, **When** un usuario intenta registrarse con ese mismo correo, **Then** el sistema rechaza el registro con un mensaje de error claro indicando que el correo ya está en uso.
3. **Given** un formato de correo inválido o contraseña vacía, **When** el usuario envía el registro, **Then** el sistema rechaza la solicitud indicando los errores de validación.

---

### User Story 2 - Inicio y Cierre de Sesión (HU-13) (Priority: P1)

Como usuario registrado, quiero iniciar y cerrar sesión con mis credenciales, para proteger el acceso a mis tareas y garantizar que solo yo pueda visualizarlas o modificarlas.

**Why this priority**: Garantiza la seguridad y la verificación de identidad requerida por el Principio VII de la constitución en cada petición.

**Independent Test**: Puede probarse iniciando sesión con credenciales correctas para obtener una sesión activa, accediendo a rutas protegidas, y luego cerrando sesión para comprobar que el acceso a dichas rutas queda bloqueado.

**Acceptance Scenarios**:
1. **Given** un usuario registrado con credenciales correctas, **When** envía el formulario de inicio de sesión, **Then** se establece una sesión segura y se le redirige al listado de sus tareas.
2. **Given** credenciales incorrectas (correo inexistente o contraseña equivocada), **When** se intenta iniciar sesión, **Then** el sistema muestra un mensaje de error de autenticación genérico y no inicia sesión.
3. **Given** un usuario con sesión activa, **When** selecciona "Cerrar sesión", **Then** se destruye la sesión y cualquier intento posterior de modificar tareas es rechazado con redirección o código 401.

---

### User Story 3 - Creación de Tareas (HU-01) (Priority: P2)

Como usuario autenticado, quiero crear una tarea indicando un título obligatorio y opcionalmente descripción y fecha límite, para registrar el trabajo que tengo pendiente.

**Why this priority**: Constituye la funcionalidad nuclear de entrada de datos del dominio de gestión de tareas.

**Independent Test**: Puede probarse creando una tarea con sesión activa y verificando que quede guardada con estado inicial "pendiente", asociada al usuario actual y con un registro de auditoría asociado.

**Acceptance Scenarios**:
1. **Given** un usuario autenticado y datos válidos (título no vacío, descripción y fecha límite opcionales), **When** envía el formulario de creación, **Then** la tarea se guarda con estado "pendiente", vinculada a su cuenta, y se genera un log de auditoría con actor, acción `TASK_CREATED`, id de entidad y timestamp.
2. **Given** un usuario autenticado que envía un título vacío o compuesto solo por espacios, **When** envía la solicitud, **Then** el sistema rechaza la creación y exige un título válido.
3. **Given** un usuario no autenticado, **When** intenta crear una tarea, **Then** la petición es denegada con código 401 o redirección a login.

---

### User Story 4 - Listado de Tareas (HU-02) (Priority: P2)

Como usuario autenticado, quiero ver el listado de mis propias tareas con su título, estado y fecha límite, y poder filtrarlas por estado, para tener visibilidad y control sobre mis pendientes.

**Why this priority**: Permite al usuario inspeccionar su carga de trabajo de forma organizada y segura sin fuga de información de otros usuarios.

**Independent Test**: Puede probarse creando tareas para el Usuario A y para el Usuario B; al iniciar sesión como Usuario A solo deben listarse las tareas del Usuario A, y aplicar filtros debe mostrar únicamente las tareas que coincidan con el estado seleccionado.

**Acceptance Scenarios**:
1. **Given** un usuario autenticado con tareas creadas, **When** accede al listado principal, **Then** visualiza sus tareas mostrando título, estado y fecha límite.
2. **Given** tareas pertenecientes a otros usuarios en la base de datos, **When** el usuario autenticado consulta su listado, **Then** bajo ninguna circunstancia se muestran tareas de terceros.
3. **Given** un usuario que aplica un filtro por estado ("pendiente", "en progreso", "completada"), **When** consulta el listado, **Then** se muestran únicamente las tareas que coincidan con dicho estado.

---

### User Story 5 - Cambio de Estado de Tareas (HU-03) (Priority: P2)

Como usuario autenticado, quiero cambiar el estado de una de mis tareas (entre pendiente, en progreso y completada), para reflejar su avance real en el flujo de trabajo.

**Why this priority**: Modifica el ciclo de vida nuclear de la tarea y activa la auditoría obligatoria de mutaciones de estado.

**Independent Test**: Puede probarse cambiando una tarea de "pendiente" a "en progreso" y luego a "completada", comprobando la actualización en base de datos y la generación de logs de auditoría para cada transición.

**Acceptance Scenarios**:
1. **Given** una tarea en estado "pendiente", **When** el usuario propietario solicita la transición a "en progreso", **Then** el estado se actualiza y se emite un log de auditoría con acción `STATUS_CHANGED`.
2. **Given** una tarea en estado "en progreso", **When** el usuario propietario solicita la transición a "completada", **Then** el estado se actualiza a "completada" y se audita el cambio.
3. **Given** una tarea en estado "completada", **When** se solicita la transición directa a "pendiente", **Then** el sistema rechaza la solicitud porque la reapertura está fuera de alcance de este incremento (reservada para HU-06).
4. **Given** un usuario intentando cambiar el estado de una tarea que pertenece a otro usuario, **When** envía la petición, **Then** el sistema responde con error 403 Forbidden o 404 Not Found.

---

### User Story 6 - Edición de Tareas (HU-04) (Priority: P3)

Como usuario autenticado, quiero editar el título, descripción o fecha límite de una tarea propia existente, para corregir o actualizar su información.

**Why this priority**: Permite corregir detalles sin alterar el ciclo de vida de la tarea.

**Independent Test**: Puede probarse modificando campos de una tarea existente y verificando que los cambios persistan y que las validaciones de título no vacío se mantengan vigentes.

**Acceptance Scenarios**:
1. **Given** una tarea existente de un usuario autenticado, **When** el usuario modifica el título o descripción con datos válidos, **Then** la tarea se actualiza y se audita la modificación.
2. **Given** una edición con título vacío, **When** se envía la actualización, **Then** se rechaza con error de validación y la tarea conserva sus datos anteriores.
3. **Given** una tarea de otro usuario, **When** se intenta editar, **Then** se rechaza la operación por falta de autorización.

---

### Edge Cases

- **Correo duplicado concurrente**: Si dos peticiones de registro con el mismo correo llegan simultáneamente, la restricción de unicidad en la base de datos debe impedir duplicados y devolver error controlado 409 Conflict o validación de formulario.
- **Fechas límites en formatos anómalos o pasadas**: El sistema debe aceptar cadenas de fecha ISO-8601 válidas (o vacías) y rechazar cadenas malformadas con error 400.
- **Peticiones maliciosas sin sesión o con sesión expirada**: Cualquier endpoint de mutación (`POST`, `PUT`, `PATCH`) debe retornar 401 Unauthorized sin procesar la lógica de negocio.
- **Acceso cruzado entre usuarios (IDOR)**: Si un usuario intenta acceder por ID a una tarea ajena (`/tasks/<id>`), el sistema debe responder con 404 (o 403) sin revelar metadatos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir el registro de usuarios mediante correo y contraseña.
- **FR-002**: El sistema DEBE validar el formato del correo electrónico y asegurar su unicidad a nivel de servicio y base de datos.
- **FR-003**: El sistema DEBE almacenar las contraseñas utilizando un algoritmo de hashing criptográfico seguro (ej. bcrypt / scrypt / pbkdf2), nunca en texto plano.
- **FR-004**: El sistema DEBE proveer inicio de sesión mediante verificación de correo y contraseña, manteniendo una sesión segura en el backend (cookies firmadas / session Flask).
- **FR-005**: El sistema DEBE proveer cierre de sesión invalidando la sesión del usuario.
- **FR-006**: El sistema DEBE verificar autenticación activa en el backend en todo endpoint que consulte o modifique tareas.
- **FR-007**: El sistema DEBE permitir a un usuario autenticado crear tareas con título (obligatorio, máximo 150 caracteres, no vacío), descripción (opcional, texto) y fecha límite (opcional, fecha).
- **FR-008**: Toda tarea nueva DEBE crearse obligatoriamente con estado inicial "pendiente" (`pending`).
- **FR-009**: El sistema DEBE listar únicamente las tareas creadas por el usuario autenticado, mostrando título, estado y fecha límite.
- **FR-010**: El sistema DEBE permitir filtrar el listado de tareas por su estado actual (`pending`, `in_progress`, `completed`).
- **FR-011**: El sistema DEBE permitir la transición de estado de una tarea únicamente entre combinaciones válidas para este incremento: `pending` → `in_progress`, `in_progress` → `completed`, `pending` → `completed`. La transición desde `completed` hacia `pending` o `in_progress` queda explícitamente bloqueada en este incremento.
- **FR-012**: El sistema DEBE permitir editar el título, descripción y fecha límite de una tarea propia, aplicando las mismas reglas de validación que en la creación.
- **FR-013**: El sistema DEBE registrar un log de auditoría estructurado en cada operación que cree o muta una tarea (`TASK_CREATED`, `TASK_UPDATED`, `STATUS_CHANGED`), incluyendo: `actor_id`, `action`, `entity_id` y `timestamp` ISO-8601 UTC.

### Exclusiones Explícitas (Fuera de Alcance)
- Eliminación física o lógica de tareas (`HU-05`).
- Reapertura de tareas completadas (`HU-06`).
- Asignación de prioridad (`HU-07`) y categorías (`HU-08`).
- Indicación de tareas vencidas (`HU-09`).
- Asignación a otros usuarios y notificaciones (`HU-10`, `HU-11`).
- Recuperación de contraseña (`HU-14`).
- Interacción asíncrona sin recarga y drag-and-drop (`HU-15`, `HU-16`).

### Key Entities

- **User**: Representa a la persona registrada en el sistema.
  - Atributos: `id` (entero/UUID autoincremental), `email` (cadena única obligatoria), `password_hash` (cadena con hash seguro), `created_at` (timestamp UTC).
- **Task**: Representa una unidad de trabajo asignada a un usuario.
  - Atributos: `id` (entero/UUID), `user_id` (clave foránea a User), `title` (cadena obligatoria no vacía), `description` (texto opcional), `due_date` (fecha opcional), `status` (enum: `pending`, `in_progress`, `completed`), `created_at`, `updated_at`.
- **AuditLog**: Representa el registro inmutable de auditoría para observabilidad.
  - Atributos: `id`, `actor_id` (entero, usuario que ejecuta la acción), `action` (cadena: `TASK_CREATED`, `STATUS_CHANGED`, `TASK_UPDATED`), `entity_id` (id de la tarea), `timestamp` (UTC ISO-8601), `details` (opcional / JSON estructurado).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario nuevo puede completar su registro e iniciar sesión en menos de 1 minuto.
- **SC-002**: El 100% de las peticiones a endpoints que crean, editan o cambian estado de tareas sin sesión válida son rechazadas con código 401.
- **SC-003**: Cero fugas de información de tareas entre usuarios distintos (cobertura del 100% en pruebas de autorización y aislamiento).
- **SC-004**: El 100% de las mutaciones de tareas generan un evento auditable estructurado con los 4 campos obligatorios (`actor_id`, `action`, `entity_id`, `timestamp`).
- **SC-005**: La suite de pruebas de dominio (modelos y servicios) pasa al 100% antes de la integración en la capa HTTP.

## Assumptions

- Se utiliza base de datos relacional SQLite para desarrollo local y ejecución rápida de pruebas, con SQLAlchemy como ORM.
- Las sesiones web en Flask se gestionan mediante cookies de sesión firmadas criptográficamente (`flask.session`) con clave secreta provista por variable de entorno.
- Las plantillas Jinja2 renderizan las vistas de autenticación (login, registro) y el panel de tareas con formularios tradicionales HTTP (POST) y enlaces de filtro.
