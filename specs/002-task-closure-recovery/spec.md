# Feature Specification: 002-task-closure-recovery

**Feature Branch**: `002-task-closure-recovery`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Especifica el segundo incremento funcional de TaskControl: cierre de la gestión básica de tareas y recuperación de acceso. Este incremento cubre HU-05, HU-06 y HU-14 del backlog, y asume que el Incremento 1 (registro, login/logout, creación, listado, cambio de estado y edición de tareas) ya está implementado y en producción."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Eliminación Lógica de Tareas (HU-05) (Priority: P1)

Como usuario autenticado, quiero eliminar una de mis tareas que ya no sea relevante o necesaria, para mantener mi listado de trabajo limpio y enfocado, garantizando que su historial e integridad se conserven para fines de auditoría.

**Why this priority**: Cierra el ciclo de vida básico de las tareas permitiendo al usuario descartar elementos obsoletos, protegiendo al mismo tiempo la trazabilidad histórica del sistema requerida por el Principio VI y Principio VIII.

**Independent Test**: Puede probarse creando una tarea, solicitando su eliminación como usuario propietario y verificando que:
1. Deje de figurar en el listado habitual de tareas del usuario.
2. Su registro permanezca almacenado internamente marcado como eliminado sin borrado físico.
3. Se registre un evento de auditoría específico de eliminación con actor, identificador de tarea y fecha.

**Acceptance Scenarios**:
1. **Given** una tarea activa perteneciente al usuario autenticado, **When** el usuario solicita su eliminación, **Then** la tarea queda marcada como eliminada lógicamente, deja de mostrarse en el listado por defecto y se emite un log de auditoría con la acción `TASK_DELETED`.
2. **Given** una tarea que ya se encuentra en estado eliminado, **When** se intenta solicitar nuevamente su eliminación, **Then** el sistema rechaza la operación informando que la tarea ya fue eliminada o no se encuentra disponible (operación no permitida).
3. **Given** una tarea perteneciente a otro usuario, **When** un usuario intenta eliminarla, **Then** el sistema rechaza la solicitud por falta de autorización (403 Forbidden o 404 Not Found) sin alterar el registro ni emitir borrado.
4. **Given** una tarea eliminada lógicamente, **When** se consulta el historial de auditoría de la tarea, **Then** todos los eventos previos (creación, cambios de estado, edición) y el evento de eliminación permanecen intactos y consultables.

---

### User Story 2 - Reapertura de Tareas Completadas (HU-06) (Priority: P1)

Como usuario autenticado, quiero reabrir una tarea que fue marcada como completada por error, para reactivar su progreso sin perder su historial y dejando constancia explícita de que fue reabierta.

**Why this priority**: Resuelve errores operativos habituales en el flujo de trabajo sin corromper el ciclo de vida ni la auditoría, distinguiendo con claridad una reapertura intencional de una creación nueva o de un cambio de estado ordinario.

**Independent Test**: Puede probarse marcando una tarea como completada, ejecutando la acción explícita de reapertura y verificando que su estado retorne a activo ("pendiente") y que en el log de auditoría aparezca registrado el evento `TASK_REOPENED`.

**Acceptance Scenarios**:
1. **Given** una tarea en estado "completada" propiedad del usuario autenticado, **When** el usuario ejecuta la acción de reabrir la tarea, **Then** el estado de la tarea cambia a activo ("pendiente") y se registra en la auditoría un evento con acción `TASK_REOPENED`.
2. **Given** una tarea en estado "pendiente" o "en progreso", **When** se intenta invocar la acción de reapertura, **Then** el sistema rechaza la operación debido a que la tarea ya se encuentra activa.
3. **Given** una tarea eliminada lógicamente (incluso si antes estaba completada), **When** se intenta reabrir, **Then** la operación es rechazada porque las tareas eliminadas no admiten transiciones directas de estado.
4. **Given** el historial de auditoría de una tarea reabierta, **When** un usuario autorizado o auditor lo examina, **Then** se identifica inequívocamente que la tarea pasó por creación, completitud y una reapertura diferenciada de las transiciones ordinarias de estado.

---

### User Story 3 - Recuperación Segura de Contraseña (HU-14) (Priority: P2)

Como usuario que olvidó su contraseña, quiero solicitar el restablecimiento mediante mi correo electrónico registrado y definir una nueva clave de acceso, para recuperar el acceso a mi cuenta sin comprometer la seguridad ni revelar la existencia de mi correo en la plataforma.

**Why this priority**: Restaura el acceso a usuarios legítimos ante olvido de credenciales, cumpliendo estrictamente con las directrices de seguridad (Principio VII: no enumeración de cuentas, tokens de un solo uso con expiración y almacenamiento no reversible).

**Independent Test**: Puede probarse enviando una solicitud con un correo registrado y otra con un correo no registrado:
1. En ambos casos la respuesta al usuario en pantalla debe ser idéntica y neutra.
2. Para el correo registrado se genera un token con tiempo de vida limitado.
3. El uso del token permite actualizar la contraseña una única vez.
4. Cualquier intento posterior de usar el mismo token o uno expirado debe ser rechazado.

**Acceptance Scenarios**:
1. **Given** un usuario que ingresa un correo registrado en el formulario de recuperación, **When** envía la solicitud, **Then** el sistema responde con un mensaje neutro de confirmación, genera un token seguro de un solo uso con expiración temporal y registra el evento `PASSWORD_RESET_REQUESTED`.
2. **Given** una solicitud con un correo que NO existe en el sistema o con formato no registrado, **When** se envía la solicitud, **Then** el sistema muestra exactamente el mismo mensaje neutro de confirmación que para un correo válido, sin generar tokens ni filtrar la inexistencia de la cuenta.
3. **Given** un enlace de recuperación con token válido y vigente, **When** el usuario ingresa su nueva contraseña cumpliendo las políticas de seguridad (longitud mínima de 8 caracteres), **Then** la contraseña se actualiza con hash seguro, el token queda inmediatamente invalidado para futuros usos, se audita `PASSWORD_RESET_COMPLETED` y el usuario puede iniciar sesión con su nueva clave.
4. **Given** un token que ya fue utilizado previamente, **When** se intenta acceder o enviar una nueva contraseña mediante dicho enlace, **Then** el sistema rechaza la solicitud indicando que el enlace es inválido o ya ha sido utilizado.
5. **Given** un token cuyo tiempo límite de validez ha expirado, **When** se intenta utilizar, **Then** el sistema rechaza la solicitud indicando que el enlace ha expirado y requiere solicitar uno nuevo.

---

### Edge Cases

- **Eliminación concurrente de la misma tarea**: Si se reciben dos peticiones simultáneas de eliminación para la misma tarea, la primera marca la eliminación lógica y la segunda es rechazada con un error indicando que la tarea ya no está disponible.
- **Reapertura de tareas eliminadas**: Si una tarea fue completada y posteriormente eliminada lógicamente, cualquier intento de reapertura debe ser bloqueado; el estado de eliminación prevalece sobre el estado de completitud.
- **Uso de token de restablecimiento tras cambio de contraseña exitoso**: El token debe ser invalidado atómicamente en la misma transacción donde se persiste el nuevo hash de la contraseña, impidiendo ataques de condición de carrera (race conditions).
- **Múltiples solicitudes de restablecimiento seguidas**: Si un usuario solicita varias veces el restablecimiento antes de usar el token, cada nueva emisión debe invalidar los tokens pendientes anteriores o tener un límite de emisión para prevenir saturación.
- **Intentos de inyección o manipulación de tokens**: Los tokens alterados, truncados o con firmas/hashes no coincidentes deben ser rechazados de inmediato sin revelar detalles del algoritmo interno.
- **Aislamiento de acceso a tareas eliminadas (IDOR)**: Si un usuario intenta acceder por identificador directo a los detalles o edición de una tarea eliminada, el sistema debe responder con 404 Not Found.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a un usuario autenticado eliminar lógicamente cualquiera de sus tareas propias (soft delete).
- **FR-002**: El sistema NUNCA DEBE eliminar físicamente de la base de datos el registro de una tarea eliminada ni sus registros históricos asociados.
- **FR-003**: El sistema DEBE excluir automáticamente las tareas eliminadas lógicamente de la vista o listado principal de tareas por defecto.
- **FR-004**: El sistema DEBE impedir la eliminación de una tarea que ya haya sido marcada como eliminada previamente, respondiendo con un error de operación no permitida o recurso no encontrado.
- **FR-005**: El sistema DEBE impedir la edición o modificación de atributos de cualquier tarea que se encuentre en estado eliminado.
- **FR-006**: El sistema DEBE permitir a un usuario autenticado reabrir una tarea propia que se encuentre exclusivamente en estado "completada".
- **FR-007**: Al completarse la reapertura de una tarea, el sistema DEBE cambiar su estado a "pendiente" (estado activo inicial del flujo de trabajo).
- **FR-008**: El sistema DEBE impedir la reapertura de tareas que no estén en estado "completada" (rechazar si ya están en "pendiente" o "en progreso").
- **FR-009**: El sistema DEBE registrar un evento de auditoría específico con la acción `TASK_DELETED` cuando se ejecute una eliminación lógica, guardando `actor_id`, `action`, `entity_id` y `timestamp` UTC.
- **FR-010**: El sistema DEBE registrar un evento de auditoría específico con la acción `TASK_REOPENED` cuando se ejecute una reapertura, distinguiéndolo claramente en el log tanto de la creación original (`TASK_CREATED`) como de las transiciones ordinarias (`STATUS_CHANGED`).
- **FR-011**: El sistema DEBE proveer un formulario de solicitud de recuperación de contraseña accesible para usuarios no autenticados mediante ingreso de correo electrónico.
- **FR-012**: La respuesta del sistema a la solicitud de recuperación de contraseña DEBE ser neutra e idéntica independientemente de si el correo existe o no en la base de datos, evitando la enumeración de cuentas.
- **FR-013**: Para solicitudes con correo registrado válido, el sistema DEBE generar un token de restablecimiento criptográficamente seguro con un tiempo de expiración predefinido (ej. 30 minutos).
- **FR-014**: El sistema DEBE almacenar el token de restablecimiento de forma no reversible o protegido mediante hash criptográfico (nunca en texto plano en la base de datos), impidiendo la exposición de secretos en caso de volcado de datos.
- **FR-015**: El sistema DEBE permitir restablecer la contraseña mediante el token válido, exigiendo una nueva contraseña válida (longitud mínima de 8 caracteres) que será hasheada e invalidando inmediatamente el token para evitar cualquier reutilización.
- **FR-016**: El sistema DEBE rechazar cualquier intento de restablecimiento que utilice un token expirado, ya utilizado o inválido.
- **FR-017**: El sistema DEBE registrar eventos de auditoría para la solicitud de restablecimiento (`PASSWORD_RESET_REQUESTED`) y para la culminación exitosa del restablecimiento (`PASSWORD_RESET_COMPLETED`).

---

### Exclusiones Explícitas (Fuera de Alcance)

En estricta concordancia con la definición del incremento y el backlog:
- Asignación de prioridad a tareas (`HU-07`).
- Agrupación por categorías o proyectos (`HU-08`).
- Indicación visual y cálculo de tareas vencidas (`HU-09`).
- Asignación de tareas a otros usuarios (`HU-10`).
- Sistema interno de notificaciones en la aplicación (`HU-11`).
- Interacción asíncrona sin recarga de página para completar tareas (`HU-15`).
- Reordenamiento visual mediante arrastrar y soltar (drag and drop) (`HU-16`).

---

### Key Entities

- **Task (Actualización)**:
  - Extensión de atributos: se añade el control de eliminación lógica (`is_deleted`: booleano, por defecto falso; `deleted_at`: timestamp UTC opcional que registra cuándo ocurrió el borrado lógico).
  - Ciclo de vida: `pending` ↔ `in_progress` → `completed` → (reapertura) → `pending`. Si `is_deleted = true`, la tarea queda fuera del ciclo de vida activo.
- **AuditLog**:
  - Entidad de auditoría inmutable.
  - Nuevas acciones obligatorias incorporadas en este incremento:
    - `TASK_DELETED`: Registra la eliminación lógica de una tarea.
    - `TASK_REOPENED`: Registra la reactivación de una tarea previamente completada.
    - `PASSWORD_RESET_REQUESTED`: Registra la emisión de una solicitud de restablecimiento de contraseña.
    - `PASSWORD_RESET_COMPLETED`: Registra la actualización efectiva de credenciales vía recuperación.
  - Atributos estándar: `id`, `actor_id` (o sistema/anónimo en recuperación), `action`, `entity_id`, `timestamp` (UTC ISO-8601), `details`.
- **PasswordResetToken**:
  - Representa el mecanismo de delegación temporal de restablecimiento de credenciales.
  - Atributos clave: `id`, `user_id` (referencia al usuario), `token_hash` (hash criptográfico seguro del token para no almacenar texto plano), `expires_at` (timestamp UTC de caducidad), `used_at` (timestamp UTC opcional de cuándo fue consumido), `created_at` (timestamp UTC).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las tareas eliminadas conservan intacto su registro en base de datos y la totalidad de su historial previo de auditoría (0% de eliminaciones físicas).
- **SC-002**: Las tareas marcadas como eliminadas tienen una tasa de visibilidad del 0% en la lista principal por defecto para los usuarios.
- **SC-003**: En el 100% de los casos de reapertura de tareas, el historial de auditoría refleja el evento `TASK_REOPENED` distinguible inequívocamente de eventos `TASK_CREATED` y `STATUS_CHANGED`.
- **SC-004**: En las solicitudes de recuperación de contraseña, el tiempo de respuesta y los mensajes presentados al usuario son indistinguibles entre correos existentes y no existentes (0% de fuga de información sobre existencia de cuentas).
- **SC-005**: El 100% de los tokens de restablecimiento de contraseña quedan inutilizables inmediatamente tras su primer uso exitoso o tras superar su tiempo de expiración.
- **SC-006**: Cero secretos o tokens en texto plano almacenados en base de datos o repositorios, cumpliendo plenamente con el Principio VII de la constitución del proyecto.

---

## Assumptions

- Se mantiene la arquitectura monolítica en Python (Flask) con SQLAlchemy y migraciones de esquema mediante Flask-Migrate (Alembic), en cumplimiento con el Principio I, II y VI.
- Para el entorno de desarrollo y pruebas, el enlace de restablecimiento de contraseña y su token se emiten a través de los logs de la aplicación o mecanismo de simulación de correo sin requerir infraestructura externa de mensajería asíncrona, en apego al Principio I y V.
- El tiempo de vida por defecto para los tokens de restablecimiento de contraseña se establece en 30 minutos desde su generación.
- La reapertura de una tarea completada la devuelve al estado inicial "pendiente" (`pending`), permitiendo reiniciar su flujo ordinario de trabajo.
- Toda la lógica de negocio asociada a soft delete, reapertura y recuperación de contraseña se implementa bajo metodología test-first (Principio IV).
