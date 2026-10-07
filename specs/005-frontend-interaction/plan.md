# Implementation Plan: 005-frontend-interaction

**Branch**: `005-frontend-interaction` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-frontend-interaction/spec.md` (ya incorpora 3 clarificaciones de `/speckit-clarify`, Session 2026-10-07)

---

## Summary

Implementar el quinto y último incremento funcional del monolito **TaskControl**:
1. **Completar sin recargar (`HU-15`)**: `fetch()` nativo contra el endpoint de cambio de estado ya existente (Incremento 1), con actualización optimista y reversión visual ante fallo.
2. **Reordenar con arrastrar y soltar (`HU-16`)**: API nativa de Drag and Drop del navegador, habilitada únicamente en modo `sort=manual`, persistiendo una posición global por tarea (Clarifications Q1-Q2) y permitiendo reordenar también tareas asignadas, no solo propias (Clarifications Q3).

Ningún framework SPA se introduce — ambas interacciones usan JavaScript vanilla y APIs nativas del navegador, consistente con la restricción técnica del stack.

---

## Technical Context

**Language/Version**: Python 3.11+ (backend) / JavaScript ES6+ vanilla (frontend)
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy, Flask-Migrate (Alembic); sin dependencias nuevas de frontend
**Storage**: Base de datos relacional SQLite (desarrollo/pruebas) / PostgreSQL-compatible
**Testing**: pytest (backend). **Sin infraestructura de pruebas de frontend en el proyecto** (no hay Jest/Playwright/Cypress) — el comportamiento de JavaScript (reversión optimista, arrastrar y soltar) se valida manualmente vía `quickstart.md`, no con pruebas automatizadas, tal como lo permite explícitamente el prompt de este incremento.
**Target Platform**: Navegadores modernos con soporte de Fetch API y HTML5 Drag and Drop API (Chrome, Firefox, Edge, Safari recientes)
**Project Type**: Monolito web (Jinja2 en servidor + JavaScript vanilla en cliente)
**Performance Goals**: Actualización visual percibida como instantánea (optimista, antes de la confirmación del backend); sin bloqueo de interfaz durante la petición
**Constraints**:
- Sin framework SPA (React/Vue/Angular) ni librería de terceros para drag-and-drop — API nativa del navegador (Principio V, restricción técnica del stack).
- HU-15 reutiliza exclusivamente el contrato de `POST /tasks/<id>/status` ya existente — cero endpoints nuevos para esta historia (Principio III).
- HU-16 requiere un único endpoint nuevo para persistir el orden en bloque, con la misma autorización por creador-o-asignatario ya establecida en el Incremento 4 (Principio VII).
- Migración versionada para el nuevo campo de orden, con backfill coherente para tareas existentes (Principio VI).
**Scale/Scope**: 2 Historias de Usuario (HU-15, HU-16)

---

## Constitution Check

*GATE: Evaluado antes del diseño y re-verificado tras la definición técnica.*

| Principio Constitucional | Estado | Justificación y Mecanismo de Cumplimiento |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | Toda la lógica de reordenamiento se resuelve en el mismo proceso Flask y la misma base de datos; el frontend solo consume el contrato HTTP ya existente más un endpoint nuevo. |
| **II. Separación de responsabilidades** | **PASS** | La persistencia del orden vive en `TaskService` (no en la ruta ni en JavaScript); `main.js` solo orquesta DOM + `fetch`, sin lógica de negocio. |
| **III. Contrato explícito** | **PASS** | HU-15 documenta que reutiliza el contrato ya existente; HU-16 documenta su único endpoint nuevo en `contracts/reorder-contracts.md` antes de implementarse. |
| **IV. Test-first en lógica de negocio** | **PASS** | La persistencia del nuevo orden (lógica de servicio) se prueba con pytest antes de implementarse. El comportamiento puramente de JavaScript (sin lógica de dominio propia, solo orquestación de fetch/DOM) se valida manualmente, según lo permite explícitamente este incremento. |
| **V. Simplicidad sobre generalidad (YAGNI)** | **PASS** | Se usa la API nativa de Drag and Drop del navegador en vez de una librería de terceros — cero dependencias nuevas para una interacción que el navegador ya soporta de forma nativa. Sin infraestructura de pruebas E2E de frontend nueva, dado que el proyecto nunca la tuvo y el alcance no lo justifica. |
| **VI. Integridad de datos y migraciones** | **PASS** | Migración versionada agregando `tasks.manual_order`, con backfill determinista para tareas existentes de los Incrementos 1-4. |
| **VII. Seguridad por defecto** | **PASS** | El endpoint de reordenamiento valida en backend que cada tarea enviada pertenezca al usuario (creador o asignatario, Clarifications Q3) antes de persistir cualquier cambio — reutiliza `_get_task_for_creator_or_assignee` del Incremento 4. |
| **VIII. Observabilidad mínima viable** | **PASS** | El cambio de estado sin recarga sigue auditando `STATUS_CHANGED` exactamente igual que antes (mismo endpoint, mismo servicio). El reordenamiento, al ser una preferencia de vista personal sin impacto en el contenido de la tarea, no genera un nuevo evento de auditoría (ver Research §4). |

---

## Project Structure

### Documentation (this feature)

```text
specs/005-frontend-interaction/
├── spec.md              # Especificación funcional validada (con Clarifications)
├── plan.md              # Este plan de implementación técnica
├── research.md          # Investigación técnica y decisiones arquitectónicas (Fase 0)
├── data-model.md        # Esquema de datos (Fase 1)
├── quickstart.md        # Guía de inicialización y validación manual E2E (Fase 1)
├── contracts/           # Contrato explícito del único endpoint nuevo (Fase 1)
│   └── reorder-contracts.md
└── checklists/
    └── requirements.md  # Checklist de calidad de especificación
```

### Source Code Impact

```text
src/
└── taskcontrol/
    ├── models/
    │   └── task.py                # Incorporación de manual_order
    ├── services/
    │   └── task_service.py        # reorder_tasks(); get_user_tasks admite sort='manual'
    ├── routes/
    │   └── tasks.py                # POST /tasks/reorder
    ├── templates/
    │   └── tasks/
    │       └── index.html          # Control "Orden manual", atributos draggable, data-task-id
    └── static/
        └── js/
            └── main.js              # Fetch optimista para completar; Drag and Drop API nativa para reordenar

tests/
└── services/
    └── test_task_service.py        # Pruebas de reorder_tasks y sort='manual'
```

---

## Detalle Técnico de los Puntos del Incremento

### 1. Completar Tareas sin Recargar la Página (HU-15)

- **Estrategia**: Interceptar el `submit` del formulario existente de "Completar" (ya usa `POST /tasks/<id>/status`, Incremento 1) con `e.preventDefault()`, y reemplazarlo por `fetch(form.action, {method: 'POST', body: new FormData(form), headers: {'Accept': 'application/json'}})`.
- **Actualización optimista**: Antes de que la respuesta llegue, actualizar inmediatamente el badge de estado en el DOM y deshabilitar el botón (evita doble envío mientras la petición está en curso).
- **Éxito (`200 OK`)**: Confirmar visualmente el nuevo estado (ya mostrado) y re-habilitar las acciones correspondientes al nuevo estado.
- **Fallo (red o respuesta de error)**: Revertir el badge de estado al valor previo guardado antes de la actualización optimista, re-habilitar el botón, y mostrar un mensaje de error reutilizando el patrón de alertas ya existente (`alert-error`, mismo estilo que los mensajes flash de `main.js`).
- **Por qué sin framework**: La interacción es un único `fetch` + manipulación de 1-2 nodos del DOM — introducir React/Vue solo para esto violaría el Principio V (YAGNI) y la restricción técnica explícita del stack. El patrón ya es consistente con la validación de formularios vanilla que `main.js` usa desde el Incremento 1.

---

### 2. Reordenar Tareas Arrastrándolas (HU-16)

- **Técnica elegida**: API nativa de Drag and Drop del navegador (`draggable="true"`, eventos `dragstart`, `dragover`, `drop`). **No se introduce ninguna librería** (ej. SortableJS) porque la API nativa cubre completamente el caso de uso (reordenar elementos de una lista plana) sin dependencias adicionales ni paso de build nuevo.
- **Por qué no excede "sin framework SPA pesado"**: La API de Drag and Drop es parte del estándar HTML5, soportada nativamente por todos los navegadores objetivo — no es una librería, no agrega peso ni dependencias, y es la opción más alineada con "JavaScript vanilla" de la constitución.
- **Habilitación condicional (Clarifications Q2)**: Los atributos `draggable="true"` y los listeners de arrastre solo se adjuntan a las tarjetas de tarea cuando `current_sort == 'manual'`. Con cualquier otro criterio de orden activo, las tarjetas se renderizan sin `draggable`, visualmente idénticas pero no arrastrables.
- **Al soltar (`drop`)**: Se recalcula el nuevo arreglo de `task_id` en el orden visual resultante del DOM, y se envía completo vía `fetch('/tasks/reorder', {method: 'POST', body: JSON.stringify({task_ids: [...]})})`.

---

### 3. Único Cambio de Backend: Campo de Orden y Endpoint de Reordenamiento

- **Nueva columna en `src/taskcontrol/models/task.py`**:
  ```python
  manual_order = db.Column(db.Integer, nullable=False, default=0, index=True)
  ```
- **`TaskService.reorder_tasks(user_id, task_ids: list[int])`**:
  1. Para cada `task_id` recibido, verifica autorización reutilizando el mismo criterio de `_get_task_for_creator_or_assignee` del Incremento 4 (creador **o** asignatario — Clarifications Q3). Si algún `task_id` no es válido o no autorizado, la operación se aborta **completa** sin persistir ningún cambio (`TaskNotFoundError`, atómico — ver §4).
  2. Asigna `manual_order = índice` según la posición de cada `task_id` dentro de la lista recibida (0, 1, 2, ...).
  3. Persiste todos los cambios en una única transacción (`db.session.commit()` al final, no por tarea).
- **Contrato del endpoint** (ver `contracts/reorder-contracts.md` para el detalle completo):
  - **Ruta y método**: `POST /tasks/reorder`
  - **Payload de entrada**: `{"task_ids": [5, 2, 8, 1]}` (arreglo completo del nuevo orden visual)
  - **Payload de salida**: `{"status": "success", "data": {"updated_count": 4}}`
  - **Códigos**: `200 OK`, `400 Bad Request` (payload vacío o malformado), `404 Not Found` (algún `task_id` no pertenece al usuario como creador o asignatario — aborta todo el lote).
- **Extensión de `GET /tasks?sort=manual`**: nuevo valor de `sort` que ordena por `Task.manual_order.asc()`, siguiendo el mismo patrón ya usado para `priority_desc`/`due_date` (Incremento 3).

---

### 4. Concurrencia y Autorización (Principio VII)

- El orden es un campo **por tarea**, no una secuencia global compartida entre todos los usuarios — cada fila de `tasks` ya tiene su propio `user_id` (creador) y, opcionalmente, `assigned_to_id`. Dos usuarios distintos arrastrando sus propias listas en paralelo nunca compiten por las mismas filas, porque cada uno solo puede enviar `task_ids` que le pertenecen (verificado uno por uno en el paso 1 de `reorder_tasks`).
- **Atomicidad del lote**: si cualquier `task_id` del arreglo no pasa la verificación de autorización, la operación completa se rechaza sin aplicar ningún cambio parcial — evita que un usuario reciba un reordenamiento "a medias" ante un error (por ejemplo, un `task_id` obsoleto si la tarea fue eliminada entre que se cargó la página y se soltó el elemento).
- **Doble arrastre rápido del mismo usuario**: el cliente deshabilita nuevas interacciones de arrastre mientras una petición de reordenamiento está en curso (mismo patrón de bloqueo optimista que HU-15), evitando solicitudes superpuestas sobre el mismo listado.

---

### 5. Migración sobre el Esquema Existente (Principio VI)

```powershell
flask db migrate -m "orden manual persistente de tareas"
```
- Agrega `tasks.manual_order` (`Integer`, `Not Null`, índice).
- **Backfill determinista**: para cada usuario, las tareas existentes de los Incrementos 1-4 reciben un `manual_order` secuencial siguiendo su orden actual por defecto (`created_at` descendente — el mismo que ya ven hoy), para que activar el modo manual por primera vez no reordene nada visualmente de forma sorpresiva (Assumptions de la spec).

---

### 6. Pruebas Automatizadas Bloqueantes (Principio IV)

**A nivel de servicio (bloqueantes)**:
1. `test_reorder_tasks_persists_new_order_for_all_affected_tasks`
2. `test_reorder_rejects_task_not_owned_or_assigned` (BLOQUEANTE)
3. `test_reorder_is_atomic_all_or_nothing` — un `task_id` inválido en el lote no aplica ningún cambio (BLOQUEANTE)
4. `test_get_user_tasks_sort_manual_respects_persisted_order`
5. `test_assignee_can_reorder_assigned_task` (Clarifications Q3)
6. `test_existing_tasks_receive_backfilled_manual_order_after_migration`

**A nivel de JavaScript**: **sin pruebas automatizadas** — el proyecto no tiene infraestructura de pruebas de frontend (Jest/Playwright/Cypress) y este incremento no la introduce (Principio V). La reversión visual ante fallo (HU-15) y la mecánica de arrastrar y soltar (HU-16) se validan manualmente siguiendo los escenarios de `quickstart.md`.
