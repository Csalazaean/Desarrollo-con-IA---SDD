# Implementation Plan: 004-user-collaboration

**Feature**: Colaboración entre usuarios (HU-10, HU-11)
**Entrada**: `spec.md`
**Prerrequisito**: Incrementos 1, 2 y 3 implementados.
**Stack**: Flask + SQLAlchemy + Alembic + Jinja2 (sin framework SPA), según la constitución.

---

## 1. Estructura de carpetas (Principio II)

Se mantiene la separación por capas ya establecida; este incremento solo añade archivos, no reorganiza nada:

```
src/taskcontrol/
├── models/
│   └── notification.py          ← NUEVO (entidad Notification)
├── services/
│   └── notification_service.py  ← NUEVO (lógica de notificaciones)
├── routes/
│   └── notifications.py         ← NUEVO (blueprint notifications_bp)
└── templates/
    └── notifications/
        └── index.html           ← NUEVO (centro de notificaciones)
```

La asignación de tareas no justifica un servicio propio: es una operación sobre el ciclo de vida de la tarea y vive en `task_service.py`, junto a las demás mutaciones de `Task`.

---

## 2. Modelo de datos

### 2.1. `Task` — creador y asignado como campos separados

**Decisión**: se añade `assigned_to_id` como columna independiente en lugar de reinterpretar `user_id`.

**Justificación**: `user_id` es el creador y es inmutable (`Assumptions` de `spec.md`). Reinterpretarlo haría que reasignar una tarea cambiara su propietario, con dos consecuencias inaceptables: el creador perdería el control de su propia tarea (FR-003 exige que pueda retirar la asignación) y el historial de auditoría del Incremento 1 quedaría huérfano, porque los eventos `TASK_CREATED` apuntan a un actor que ya no figuraría como dueño. Dos columnas separadas preservan ambas relaciones.

| Campo | Tipo | Restricciones |
|---|---|---|
| `assigned_to_id` | `Integer` | FK (`users.id`, `ondelete='SET NULL'`), Nullable, Index |

Relaciones en el ORM: `creator` (vía `user_id`) y `assignee` (vía `assigned_to_id`). Ambas requieren `foreign_keys` explícito porque hay dos claves foráneas hacia la misma tabla `users`.

### 2.2. `Notification` (nueva)

| Campo | Tipo | Restricciones |
|---|---|---|
| `id` | `Integer` | PK, autoincrement |
| `recipient_id` | `Integer` | FK (`users.id`), Not Null, Index |
| `sender_id` | `Integer` | FK (`users.id`), Not Null |
| `task_id` | `Integer` | FK (`tasks.id`, `ondelete='SET NULL'`), Nullable |
| `message` | `String(255)` | Not Null |
| `is_read` | `Boolean` | Not Null, Default `False`, Index |
| `read_at` | `DateTime` | Nullable, UTC |
| `created_at` | `DateTime` | Not Null, Default UTC, Index |

El `message` se **persiste redactado** en el momento de la asignación en lugar de componerse al leerlo. Así la notificación conserva su sentido aunque la tarea se elimine después (`task_id` queda en `NULL` por el `SET NULL`), que es justo lo que pide el Edge Case de eliminación lógica.

### 2.3. Nuevas acciones de `AuditLog`

| Acción | Entidad | Evento |
|---|---|---|
| `TASK_ASSIGNED` | `task.id` | Asignación o reasignación a un usuario |
| `TASK_UNASSIGNED` | `task.id` | Retiro de la asignación |

---

## 3. Contrato de endpoints

Detallado en `contracts/assignment-contracts.md` y `contracts/notification-contracts.md`. Resumen:

| Método y ruta | Propósito |
|---|---|
| `POST /tasks/<id>/assign` | Asignar o reasignar por correo; cadena vacía desasigna |
| `GET /tasks?scope=created\|assigned\|all` | Listado extendido con filtro por autoría |
| `GET /notifications` | Centro de notificaciones del usuario autenticado |
| `POST /notifications/<id>/read` | Marcar una notificación como leída |
| `POST /notifications/read-all` | Marcar todas como leídas, de forma atómica |

---

## 4. Atomicidad de asignación y notificación

`TaskService.assign_task_to_user` ejecuta en **una sola transacción**: validación del destinatario → actualización de `assigned_to_id` → creación de la notificación → evento de auditoría → un único `commit`.

**Justificación**: FR-008 exige que toda asignación a un tercero genere su notificación. Si fueran dos transacciones separadas, un fallo entre ambas dejaría una tarea asignada de la que el destinatario nunca se entera — exactamente el defecto que la historia pretende evitar. Al compartir transacción, o se persisten las dos cosas o ninguna.

La notificación se omite deliberadamente cuando `assigned_to_id == user_id` (autoasignación), según el Edge Case correspondiente.

---

## 5. Validación del destinatario (Principio VII)

La asignación recibe un **correo electrónico**, no un id. El backend resuelve ese correo contra la tabla `users` y rechaza la operación si no existe, **antes** de tocar la tarea. Un selector en el frontend no es garantía: la petición puede fabricarse a mano.

Autorización: **solo el creador** (`task.user_id`) puede asignar o reasignar. Un tercero recibe **403 Forbidden**, distinto del 404 que devuelve una tarea inexistente — el escenario 5 de la historia 1 lo pide así explícitamente.

---

## 6. Migraciones (Principio VI)

Una migración añade:
- Columna `assigned_to_id` a `tasks` (nullable, indexada) con FK nombrada `fk_tasks_assigned_to_id`.
- Tabla `notifications` con sus índices y claves foráneas nombradas.

Las claves foráneas se nombran explícitamente: sin nombre, el `downgrade` falla en SQLite. Las tareas existentes quedan con `assigned_to_id = NULL`, que es el estado correcto (sin asignar).

---

## 7. Estrategia de pruebas (Principio IV)

**Bloqueantes a nivel de modelo/servicio**:
- Asignar a un correo no registrado se rechaza y **no** modifica la tarea.
- Una asignación a un tercero genera **exactamente una** notificación.
- La autoasignación **no** genera notificación.
- La reasignación notifica al nuevo destinatario y retira la tarea del listado "asignadas a mí" del anterior.
- El listado del destinatario incluye la tarea asignada.
- Marcar como leída es **idempotente** y preserva el `read_at` original.
- Una notificación leída **sigue existiendo** (FR-013).
- Ningún usuario accede ni modifica notificaciones ajenas (FR-014).

**A nivel de ruta HTTP**: códigos de estado del contrato, en particular la distinción 403 (no es el creador) frente a 404 (la tarea no existe), y el aislamiento de notificaciones.
