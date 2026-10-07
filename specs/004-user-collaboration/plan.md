# Implementation Plan: 004-user-collaboration

**Branch**: `004-user-collaboration` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-user-collaboration/spec.md` (ya incorpora 3 clarificaciones de `/speckit-clarify`, Session 2026-10-06)

---

## Summary

Implementar el cuarto incremento funcional del monolito **TaskControl**:
1. **Asignación de tareas (`HU-10`)**: el creador de una tarea la asigna a otro usuario registrado identificándolo por **correo electrónico** (ver Clarifications Q1), quien pasa a verla en su propio listado. Solo el creador puede asignar/reasignar/desasignar — nunca el asignatario ni terceros.
2. **Notificaciones internas (`HU-11`)**: toda asignación exitosa a un tercero (nunca autoasignación) genera una notificación interna persistida, consultable en `/notifications`, marcable como leída individualmente o en bloque, y que nunca se descarta tras la lectura.

Todo el desarrollo se integra sobre los cimientos de los Incrementos 1-3, respetando la constitución del proyecto (monolito, migraciones Alembic, test-first bloqueante).

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy, Flask-Migrate (Alembic), Jinja2
**Storage**: Base de datos relacional SQLite (desarrollo/pruebas) / PostgreSQL-compatible
**Testing**: pytest (pytest-flask)
**Target Platform**: Linux / Windows / macOS server (proceso monolítico único)
**Project Type**: Monolito web (Jinja2 en servidor + JavaScript vanilla en cliente)
**Performance Goals**: SC-003 (notificación persistida en la misma transacción síncrona) cumplido por diseño — sin prueba de rendimiento dedicada (ver Clarifications Q3; Principio V, YAGNI)
**Constraints**:
- Arquitectura monolítica estricta, sin colas de mensajería ni servicios de notificación externos (Principio I; FR-009).
- Separación de responsabilidades: `NotificationService` propio, independiente de `TaskService` (Principio II).
- Contratos explícitos para asignación y notificaciones (Principio III).
- Test-first bloqueante para reglas de autorización (solo el creador asigna/desasigna) y persistencia de notificaciones (Principio IV).
- Simplicidad: notificaciones solo dentro de la app, sin SMTP/push (Principio V, FR-009).
- Migraciones reproducibles para `assigned_to_id` y la nueva tabla `notifications` (Principio VI).
- Validación backend obligatoria de que el correo asignado exista como usuario registrado (Principio VII, FR-002).
- Auditoría estructurada de `TASK_ASSIGNED` y `TASK_UNASSIGNED` (Principio VIII).
**Scale/Scope**: 2 Historias de Usuario (HU-10, HU-11)

---

## Constitution Check

*GATE: Evaluado antes del diseño y re-verificado tras la definición técnica.*

| Principio Constitucional | Estado | Justificación y Mecanismo de Cumplimiento |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | Notificaciones persistidas en la misma base de datos relacional y mismo proceso Flask; sin colas externas (FR-009). |
| **II. Separación de responsabilidades** | **PASS** | `NotificationService` encapsula su propia lógica (`models/notification.py` → `services/notification_service.py` → `routes/notifications.py` → `templates/notifications/`); `TaskService` solo invoca a `NotificationService`, nunca accede a su tabla directamente. |
| **III. Contrato explícito** | **PASS** | Endpoints de asignación/desasignación y de notificaciones documentados en `contracts/` antes de implementarse. |
| **IV. Test-first en lógica de negocio** | **PASS** | Reglas bloqueantes: solo el creador asigna/desasigna, el correo debe existir, autoasignación no notifica, aislamiento de notificaciones por usuario — todas especificadas como pruebas antes del código. |
| **V. Simplicidad sobre generalidad (YAGNI)** | **PASS** | Sin cola de notificaciones, sin WebSockets/polling en tiempo real, sin prueba de rendimiento dedicada para SC-003 (Clarifications Q3). Mensaje de notificación se guarda como texto plano denormalizado (sin motor de plantillas de notificación). |
| **VI. Integridad de datos y migraciones** | **PASS** | Migración versionada agregando `assigned_to_id` a `tasks` y creando la tabla `notifications`, ambas compatibles con datos existentes (nullable, sin romper Incrementos 1-3). |
| **VII. Seguridad por defecto** | **PASS** | Validación backend de existencia del usuario asignado (FR-002); solo el creador (nunca el asignatario ni terceros) puede asignar/reasignar/desasignar (Acceptance Scenario US1 #5); aislamiento estricto de notificaciones por `recipient_id` (FR-014). |
| **VIII. Observabilidad mínima viable** | **PASS** | `TASK_ASSIGNED` y `TASK_UNASSIGNED` registrados con actor, entidad y detalle en cada mutación. |

---

## Project Structure

### Documentation (this feature)

```text
specs/004-user-collaboration/
├── spec.md              # Especificación funcional validada (con Clarifications)
├── plan.md              # Este plan de implementación técnica
├── research.md          # Investigación técnica y decisiones arquitectónicas (Fase 0)
├── data-model.md        # Esquema de datos, ERD y atributos detallados (Fase 1)
├── quickstart.md        # Guía de inicialización, migraciones y pruebas E2E (Fase 1)
├── contracts/           # Contratos explícitos de endpoints HTTP (Fase 1)
│   ├── assignment-contracts.md
│   └── notification-contracts.md
└── checklists/
    └── requirements.md  # Checklist de calidad de especificación
```

### Source Code Impact

```text
src/
└── taskcontrol/
    ├── models/
    │   ├── task.py                 # Incorporación de assigned_to_id y relación 'assignee'
    │   ├── notification.py         # Nuevo modelo Notification
    │   └── audit.py                # Nuevas constantes TASK_ASSIGNED, TASK_UNASSIGNED
    ├── services/
    │   ├── task_service.py         # assign_task, unassign_task; get_user_tasks con parámetro view
    │   ├── notification_service.py # Nuevo: creación, listado, conteo no leídas, marcado de lectura
    │   └── audit_service.py        # Sin cambios de código; reutilizado
    ├── routes/
    │   ├── tasks.py                 # POST /tasks/<id>/assign, POST /tasks/<id>/unassign, GET /tasks?view=
    │   └── notifications.py         # Nuevo blueprint notifications_bp
    ├── templates/
    │   ├── base.html                 # Contador de notificaciones no leídas en la navbar
    │   ├── tasks/
    │   │   └── index.html            # Pestañas Todas/Creadas por mí/Asignadas a mí, badge de asignación, formulario de asignación
    │   └── notifications/
    │       └── index.html            # Nuevo: listado de notificaciones y acciones de lectura
    └── static/
        └── js/
            └── main.js                # Confirmación para desasignar (patrón data-confirm ya existente)

tests/
├── services/
│   ├── test_task_service.py          # Pruebas de asignación, desasignación, autorización, vistas del listado
│   └── test_notification_service.py  # Nuevo: creación, aislamiento, conteo, marcado de lectura
└── functional/
    ├── test_task_routes.py           # Pruebas HTTP de asignación/desasignación
    └── test_notification_routes.py   # Nuevo: pruebas HTTP de notificaciones
```

---

## Detalle Técnico de los Puntos del Incremento

### 1. Extensión del Modelo `Task` para Asignación

- **Nueva Columna en `src/taskcontrol/models/task.py`**:
  ```python
  assigned_to_id = db.Column(
      db.Integer, db.ForeignKey('users.id'), nullable=True, index=True
  )
  ```
- **Relación ORM explícita** (Task ya tiene una FK a `users.id` vía `user_id`/creador; se requiere `foreign_keys` explícito para evitar ambigüedad entre ambas relaciones):
  ```python
  assignee = db.relationship('User', foreign_keys=[assigned_to_id])
  ```
- **Regla de autorización (Acceptance Scenario US1 #5)**: `assign_task` y `unassign_task` verifican `task.user_id == requesting_user_id` (el creador, nunca el asignatario actual ni terceros) antes de cualquier mutación — reutilizan una búsqueda por creador, NO la búsqueda ampliada de `get_user_tasks` que incluye tareas asignadas.

---

### 2. Resolución de Destinatario por Correo y Reglas de Asignación

- **`TaskService.assign_task(task_id, user_id, assigned_to_email)`**:
  1. Obtiene la tarea verificando que `user_id` sea el creador (`TaskNotFoundError` si no, igual que el resto de operaciones de creador-propietario).
  2. Resuelve `assigned_to_email` contra `User.query.filter_by(email=...)`; si no existe, `AssigneeNotFoundError` → `404 Not Found` (FR-002; nunca se asume válido solo porque el frontend lo envió).
  3. Actualiza `task.assigned_to_id`.
  4. Registra auditoría `TASK_ASSIGNED` con `actor_id=user_id`, detalle `{"assigned_to_email": ...}`.
  5. **Si `assigned_to_id != user_id`** (no autoasignación): invoca `NotificationService.create_notification(...)`. Si el creador se autoasigna, se omite la notificación (Edge Case "Autoasignación").
- **`TaskService.unassign_task(task_id, user_id)`**:
  1. Verifica propiedad igual que `assign_task`.
  2. Pone `assigned_to_id = None`.
  3. Registra auditoría `TASK_UNASSIGNED`.
  4. **Nunca genera notificación** (Clarifications Q2) — la desasignación es silenciosa, visible de inmediato porque la tarea desaparece de "Asignadas a mí" del usuario afectado.

---

### 2.1. Autorización del Asignatario sobre la Tarea Delegada

> **Agregado tras `/speckit-analyze` (hallazgo E1, crítico)**: la spec promete que el asignatario "visualiza y gestiona" la tarea, pero ningún FR ni tarea lo operacionalizaba — `get_task_by_id` filtraba estrictamente por `user_id == creador`, lo que habría provocado un 404 al asignatario al intentar cambiar el estado de su propia tarea delegada.

- **Decisión**: el asignatario puede **únicamente cambiar el estado** de la tarea (pendiente/en progreso/completada). Editar título/descripción, prioridad, categoría, eliminar y reasignar permanecen exclusivos del creador (ver spec FR-004).
- **Implementación**: `TaskService.update_task_status` deja de usar `get_task_by_id` (creador-only) y usa una búsqueda ampliada:
  ```python
  task = Task.query.filter(
      Task.id == task_id,
      Task.is_deleted.is_(False),
      db.or_(Task.user_id == user_id, Task.assigned_to_id == user_id),
  ).first()
  if not task:
      raise TaskNotFoundError(...)
  ```
  Todos los demás métodos (`update_task_details`, `update_task_priority`, `delete_task`, `assign_category`, `assign_task`, `unassign_task`) **siguen usando** `get_task_by_id` (creador-only), sin cambios.

---

### 3. Modelo de Datos de `Notification`

- **Modelo `src/taskcontrol/models/notification.py`**:
  ```python
  class Notification(db.Model):
      __tablename__ = 'notifications'
      id = db.Column(db.Integer, primary_key=True)
      recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
      sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
      task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
      message = db.Column(db.String(255), nullable=False)
      is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
      read_at = db.Column(db.DateTime, nullable=True)
      created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
  ```
- **Mensaje denormalizado**: `message` se construye y persiste como texto plano en el momento de la creación (ej. `"{email_remitente} te asignó la tarea '{titulo}'"`), **no** se recalcula dinámicamente a partir de la tarea en cada lectura — así las notificaciones históricas preservan su texto íntegro aunque la tarea cambie o sea eliminada lógicamente después (Edge Case "Eliminación lógica de tarea asignada"; Principio V, evita un join obligatorio en cada lectura del historial).
- **`NotificationService.create_notification(recipient_id, sender_id, task, )`**: construye el mensaje, persiste el registro, y es la única vía de escritura de notificaciones (nunca se crean directamente desde `routes/`, per Principio II).

---

### 4. Listado de Tareas con Pestañas Creadas/Asignadas

- **Extensión de `TaskService.get_user_tasks`**: nuevo parámetro `view: str = 'all'`:
  ```python
  if view == 'created':
      query = query.filter_by(user_id=user_id)
  elif view == 'assigned':
      query = query.filter_by(assigned_to_id=user_id)
  else:  # 'all' (default)
      query = query.filter(db.or_(Task.user_id == user_id, Task.assigned_to_id == user_id))
  ```
- **Contrato de salida**: cada tarea en `to_dict()` incluye `assigned_to` (objeto `{id, email}` o `null`) y `is_owner` (booleano: `task.user_id == current_user_id`, para que el frontend distinga "Creada por mí" vs. "Asignada por [correo]" sin volver a consultar).

---

### 5. Contador y Gestión de Notificaciones

- **`NotificationService.get_unread_count(user_id)`**: `Notification.query.filter_by(recipient_id=user_id, is_read=False).count()`.
- **`NotificationService.list_user_notifications(user_id)`**: ordenado por `created_at.desc()` (FR-010).
- **`NotificationService.mark_as_read(notification_id, user_id)`**: verifica `recipient_id == user_id` (`NotificationNotFoundError` si no — nunca revela si la notificación existe para otro usuario); si ya estaba leída, la operación es idempotente (Edge Case "Concurrencia en marcado de lectura") — no falla, simplemente no vuelve a escribir `read_at`.
- **`NotificationService.mark_all_as_read(user_id)`**: `UPDATE` atómico de todas las no leídas del usuario en una sola transacción (FR-012).

---

### 6. Contratos de Nuevos Endpoints

#### A. Asignación
- `POST /tasks/<int:task_id>/assign` — Payload: `{"assigned_to_email": "..."}`. `200 OK`/`302 Found`, `400 Bad Request` (email vacío), `404 Not Found` (tarea ajena o email no registrado), `403 Forbidden` (usuario autenticado no es el creador).
- `POST /tasks/<int:task_id>/unassign` — Sin payload. `200 OK`/`302 Found`, `403 Forbidden`, `404 Not Found`.
- `GET /tasks?view=all|created|assigned` — Extiende el listado existente (Incrementos 1-3), por defecto `all`.

#### B. Notificaciones (`notifications_bp`)
- `GET /notifications` — Lista cronológica descendente con `unread_count` en la respuesta.
- `POST /notifications/<int:notification_id>/read` — Marca una notificación como leída. `200 OK`, `404 Not Found` (ajena o inexistente).
- `POST /notifications/mark-all-read` — Marca todas las no leídas del usuario. `200 OK`.

---

### 7. Migraciones sobre el Esquema Existente (Principio VI)

```powershell
flask db migrate -m "asignacion de tareas y notificaciones internas"
```
- Agrega `tasks.assigned_to_id` (nullable, index, FK a `users.id`) — las tareas existentes de Incrementos 1-3 quedan con `assigned_to_id = NULL` (sin asignar) automáticamente, sin romper datos.
- Crea la tabla `notifications` completa con sus índices (`recipient_id`, `is_read`).

---

### 8. Pruebas Automatizadas Bloqueantes a Nivel de Modelo/Servicio (Principio IV)

1. `test_assign_task_success_creates_notification_and_audit_log` (BLOQUEANTE)
2. `test_assign_task_to_nonexistent_email_rejected`
3. `test_only_creator_can_assign_task` (BLOQUEANTE) — ni el asignatario actual ni un tercero pueden reasignar.
4. `test_self_assignment_succeeds_without_notification` (Edge Case)
5. `test_unassign_task_success_no_notification_generated` (Clarifications Q2)
6. `test_assigned_task_visible_in_assignee_task_list`
7. `test_get_user_tasks_view_created_vs_assigned_vs_all`
8. `test_create_notification_persists_and_links_task`
9. `test_notification_isolation_between_users` (BLOQUEANTE, Cero IDOR)
10. `test_mark_notification_as_read_updates_is_read_and_read_at`
11. `test_mark_notification_as_read_is_idempotent` (Edge Case concurrencia)
12. `test_mark_all_as_read_updates_all_pending_atomically`
13. `test_unread_count_reflects_pending_notifications`
14. `test_reassignment_notifies_new_assignee_and_old_assignee_loses_access` (Edge Case reasignación sucesiva)
15. `test_assignee_can_update_task_status` (hallazgo E1 de `/speckit-analyze`, BLOQUEANTE)
16. `test_assignee_cannot_edit_delete_priority_category_or_reassign_task` (hallazgo E1, BLOQUEANTE)
17. `test_read_notification_remains_in_history` (hallazgo M1 de `/speckit-analyze`)
18. `test_notification_survives_soft_deleted_task` (hallazgo M2 de `/speckit-analyze`)
