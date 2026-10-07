# Implementation Plan: 003-task-organization-priority

**Branch**: `003-task-organization-priority` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-task-organization-priority/spec.md`

---

## Summary

Implementar el tercer incremento funcional del monolito **TaskControl**:
1. **Prioridad de tareas (`HU-07`)**: incorporación de `priority` en `Task` con valor por defecto `'medium'` (`high`, `medium`, `low`), capacidad de actualización en cualquier momento y ordenamiento jerárquico configurable en el listado de tareas.
2. **Categorías o proyectos (`HU-08`)**: nueva entidad `Category` modular (separación en 4 capas según Principio II), relación opcional N:1 con `Task` y garantía de **cero borrados en cascada** mediante clave foránea nullable con `ON DELETE SET NULL`.
3. **Indicador de tareas vencidas (`HU-09`)**: cálculo derivado exclusivamente en el backend (Principio III) bajo estándar UTC, excluyendo explícitamente tareas completadas y eliminadas lógicamente, sin persistir columnas redundantes que requieran sincronización asíncrona.

Todo el desarrollo se integra sobre los cimientos de los Incrementos 1 y 2, respetando rigurosamente la constitución del proyecto (monolito, sin microservicios, migraciones Alembic y desarrollo *test-first* bloqueante).

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy, Flask-Migrate (Alembic), Jinja2  
**Storage**: Base de datos relacional SQLite (desarrollo/pruebas) / PostgreSQL-compatible  
**Testing**: pytest (pytest-flask)  
**Target Platform**: Linux / Windows / macOS server (proceso monolítico único)  
**Project Type**: Monolito web (Jinja2 en servidor + Fetch API vanilla en cliente)  
**Performance Goals**: Ordenamiento jerárquico indexado < 30ms; evaluación dinámica de vencimiento en memoria sin costo de I/O adicional  
**Constraints**:
- Arquitectura monolítica estricta sin servicios externos ni cron jobs asíncronos (Principio I).
- Separación de responsabilidades: introducción de `Category` como módulo completo en 4 capas (Principio II).
- Contratos explícitos con `is_overdue` calculado en backend (Principio III).
- Desarrollo guiado por pruebas (*Test-first*) bloqueante en servicios (Principio IV).
- Simplicidad (YAGNI): sin librerías de calendario pesadas, sin persistencia de campos temporales volátiles (Principio V).
- Migraciones reproducibles con Flask-Migrate garantizando compatibilidad con datos existentes (Principio VI).
- Autorización y aislamiento estricto por usuario en categorías y tareas (Principio VII).
- Auditoría estructurada de mutaciones en categorías y tareas (Principio VIII).  
**Scale/Scope**: 3 Historias de Usuario (HU-07, HU-08, HU-09)  

---

## Constitution Check

*GATE: Evaluado antes del diseño y re-verificado tras la definición técnica.*

| Principio Constitucional | Estado | Justificación y Mecanismo de Cumplimiento |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | Mismo repositorio, mismo proceso Flask y misma base de datos relacional. La nueva entidad `Category` vive en el mismo esquema relacional. El cálculo de vencimiento no requiere workers externos (Celery) ni colas de mensajería. |
| **II. Separación de responsabilidades** | **PASS** | `Category` se estructura en capas completas (`models/category.py` → `services/category_service.py` → `routes/categories.py` → `templates/categories/`). No hay consultas directas del ORM en los controladores HTTP. |
| **III. Contrato explícito** | **PASS** | El cálculo de vencimiento se resuelve en el backend y se formaliza como propiedad `is_overdue` dentro del contrato de datos de `/tasks` (`contracts/task-priority-contracts.md` y `contracts/category-contracts.md`). |
| **IV. Test-first en lógica de negocio** | **PASS** | Las reglas de ordenamiento jerárquico, desvinculación `SET NULL` al eliminar categoría y cálculo de vencimiento se especifican en pruebas automatizadas bloqueantes antes del código funcional. |
| **V. Simplicidad sobre generalidad (YAGNI)** | **PASS** | Se descarta persistir `is_overdue` en BD para evitar la sobreingeniería de sincronización periódica; la relación tarea-categoría es simple (0 a 1). |
| **VI. Integridad de datos y migraciones** | **PASS** | Migración versionada con Alembic agregando columnas con default `'medium'` a `tasks` y creando tabla `categories` con FK `ondelete='SET NULL'`. |
| **VII. Seguridad por defecto** | **PASS** | Validación estricta de propiedad: un usuario no puede asociar tareas propias a categorías de otros usuarios (prevención de IDOR). |
| **VIII. Observabilidad mínima viable** | **PASS** | Logs estructurados generados para `CATEGORY_CREATED`, `CATEGORY_UPDATED`, `CATEGORY_DELETED` y cambios de prioridad en `TASK_UPDATED`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/003-task-organization-priority/
├── spec.md              # Especificación funcional validada
├── plan.md              # Este plan de implementación técnica
├── research.md          # Investigación técnica y decisiones arquitectónicas (Fase 0)
├── data-model.md        # Esquema de datos, ERD y atributos detallados (Fase 1)
├── quickstart.md        # Guía de inicialización, migraciones y pruebas E2E (Fase 1)
├── contracts/           # Contratos explícitos de endpoints HTTP (Fase 1)
│   ├── category-contracts.md
│   └── task-priority-contracts.md
└── checklists/
    └── requirements.md  # Checklist de calidad de especificación
```

### Source Code Impact

```text
src/
└── taskcontrol/
    ├── models/
    │   ├── task.py               # Incorporación de priority, category_id y propiedad is_overdue
    │   ├── category.py           # Nuevo modelo Category
    │   └── audit.py              # Nuevas constantes de acciones de categorías
    ├── services/
    │   ├── task_service.py       # Ordenamiento por prioridad, filtrado por category_id, cambio de prioridad
    │   ├── category_service.py   # Creación, listado, validación de unicidad y desvinculación segura en eliminación
    │   └── audit_service.py      # Registro de auditoría para categorías
    ├── routes/
    │   ├── tasks.py              # Extensión de GET /tasks y endpoints POST /tasks/<id>/priority y /category
    │   └── categories.py         # Nuevo blueprint categories_bp (GET /categories, POST /categories, /delete)
    ├── templates/
    │   ├── tasks/
    │   │   ├── index.html        # Selectores de ordenamiento por prioridad, badges de prioridad, indicación visual de vencida
    │   │   └── edit.html         # Selector de prioridad y categoría
    │   └── categories/
    │       └── index.html        # Gestión y listado de categorías
    └── static/
        └── js/
            └── main.js           # Soporte interactivo para filtros y ordenamiento

tests/
├── services/
│   ├── test_task_service.py      # Pruebas de ordenamiento por prioridad y cálculo de is_overdue
│   └── test_category_service.py  # Pruebas de unicidad de nombre y desvinculación SET NULL sin cascada
└── functional/
    ├── test_task_routes.py       # Pruebas HTTP de ordenamiento, filtros combinados y cambios de prioridad
    └── test_category_routes.py   # Pruebas HTTP de CRUD de categorías y autorización
```

---

## Detalle Técnico de los Puntos del Incremento

### 1. Extensión del Modelo `Task` para Prioridad y Relación con `Category`

- **Nuevas Columnas en `src/taskcontrol/models/task.py`**:
  ```python
  priority = db.Column(db.String(20), default='medium', nullable=False, index=True)
  category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)
  ```
- **Valores Válidos de Prioridad**:
  - `'high'` (Alta)
  - `'medium'` (Media - valor por defecto explícito)
  - `'low'` (Baja)
- **Relación ORM**:
  ```python
  category = db.relationship('Category', backref=db.backref('tasks', lazy='dynamic', passive_deletes=True))
  ```
- **Asignación de prioridad en el momento de creación**: `TaskService.create_task` (Incremento 1) se extiende con un parámetro opcional `priority: str = 'medium'`, validado contra los 3 valores permitidos, para que el formulario de creación de tarea pueda fijar la prioridad en el mismo paso (HU-07, Acceptance Scenario 2: "crea **o** edita").
  > **Corrección post-analyze**: la versión original del plan solo permitía fijar la prioridad mediante `POST /tasks/<id>/priority` después de crear la tarea — hallazgo E2 de `/speckit-analyze`.

---

### 2. Modelo de Datos de `Category` y Política de Desvinculación sin Cascada

- **Modelo `src/taskcontrol/models/category.py`**:
  ```python
  class Category(db.Model):
      __tablename__ = 'categories'
      id = db.Column(db.Integer, primary_key=True)
      user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
      name = db.Column(db.String(50), nullable=False)
      description = db.Column(db.Text, nullable=True)
      color = db.Column(db.String(7), nullable=True)
      created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

      __table_args__ = (
          db.UniqueConstraint('user_id', 'name', name='uq_user_category_name'),
      )
  ```
- **Regla Estricta: Desvinculación en Lugar de Eliminación en Cascada**:
  - **A nivel de Base de Datos**: La clave foránea en `tasks.category_id` se define con `ondelete='SET NULL'`.
  - **A nivel de Servicio (`CategoryService.delete_category`)**: Antes de borrar la categoría, se ejecuta de forma defensiva y atómica en la misma transacción:
    ```python
    Task.query.filter_by(category_id=category_id).update({Task.category_id: None})
    db.session.delete(category)
    db.session.commit()
    ```
  - **Resultado**: El 100% de las tareas vinculadas permanecen en el sistema con `category_id = None` ("sin categoría"), sin borrado físico ni lógico.
  - **Edición concurrente de una tarea cuya categoría fue eliminada** (ver spec Clarifications, Session 2026-10-06, Q1): no requiere lógica adicional — en el momento en que `delete_category` corre el `UPDATE` masivo, cualquier tarea afectada ya queda con `category_id = NULL` a nivel de base de datos antes de que la siguiente petición de guardado la lea. El guardado de una tarea **nunca** se rechaza por esta causa.
- **Validación de Formato de `color`** (ver spec Clarifications, Session 2026-10-06, Q3): `CategoryService.create_category` y `update_category` DEBEN validar `color` con la expresión regular `^#[0-9A-Fa-f]{6}$` cuando el valor no sea `None`/vacío, arrojando `InvalidCategoryColorError` → `400 Bad Request` si no cumple.
  > **Corrección post-clarify**: esta validación no existía en la versión original del plan; el modelo solo declaraba `color = db.Column(db.String(7))` sin ninguna regla de formato.
- **Auditoría obligatoria (Principio VIII)**: `create_category` registra `CATEGORY_CREATED`, `update_category` registra `CATEGORY_UPDATED` y `delete_category` registra `CATEGORY_DELETED` — las 3 mutaciones de la entidad quedan auditadas, sin excepción.
  > **Corrección post-analyze**: la versión original del plan solo mencionaba la auditoría de `delete_category`; `create_category` no tenía esta obligación explícita — hallazgo C1 (violación del Principio VIII) de `/speckit-analyze`.
- **Conteo de tareas por categoría**: `CategoryService.list_user_categories` DEBE incluir `task_count` (número de tareas con `is_deleted=False` asociadas) en cada categoría retornada, tal como ya documentaba `contracts/category-contracts.md`.
  > **Corrección post-analyze**: el plan nunca especificaba cómo se calculaba este campo, aunque el contrato ya lo exponía en su ejemplo de respuesta — hallazgo E3 de `/speckit-analyze`.

---

### 3. Contratos de Nuevos Endpoints y Extensión del Listado Existente

#### A. Extensión de `GET /tasks` (Listado con Orden y Filtros Combinables)
- **Ruta y Método**: `GET /tasks`
- **Query Parameters**:
  - `status`: `'pending'`, `'in_progress'`, `'completed'` (preserva Incrementos 1 y 2).
  - `category_id`: entero ID de categoría, o `'none'` para filtrar tareas sin categoría.
  - `sort`: `'priority_desc'` (alta → media → baja), `'priority_asc'` (baja → media → alta), `'due_date'`, `'created_at'`.
- **Estrategia en `TaskService.get_user_tasks`**:
  Se encadenan los filtros:
  ```python
  query = Task.query.filter_by(user_id=user_id, is_deleted=False)
  if status:
      query = query.filter_by(status=status)
  if category_id == 'none':
      query = query.filter(Task.category_id.is_(None))
  elif category_id:
      query = query.filter_by(category_id=int(category_id))

  if sort == 'priority_desc':
      priority_order = case((Task.priority == 'high', 1), (Task.priority == 'medium', 2), (Task.priority == 'low', 3), else_=4)
      # Desempate dentro del mismo nivel de prioridad: due_date ascendente,
      # con nulos al final del grupo (ver spec Clarifications, Session 2026-10-06)
      query = query.order_by(priority_order.asc(), Task.due_date.is_(None), Task.due_date.asc())
  ```
  > **Corrección post-clarify**: la versión original de este plan usaba `Task.created_at.desc()` como desempate, antes de que `/speckit-clarify` resolviera (Q2) que el criterio correcto es `due_date` ascendente con nulos al final.
- **Contrato de Salida**: Cada objeto de tarea incluye `priority`, `category` (objeto con `id`, `name`, `color` o `null`) e `is_overdue` (booleano).

#### B. Modificación de Prioridad
- **Ruta y Método**: `POST /tasks/<int:task_id>/priority`
- **Payload Entrada**: `{"priority": "high" | "medium" | "low"}`
- **Payload Salida**: `{"status": "success", "data": {"task_id": 101, "priority": "high"}}`
- **Códigos**: `200 OK` / `302 Found`, `400 Bad Request` (valor inválido o tarea eliminada), `404 Not Found`.

#### C. Asignación de Categoría
- **Ruta y Método**: `POST /tasks/<int:task_id>/category`
- **Payload Entrada**: `{"category_id": 2}` (o `{"category_id": null}` para desvincular).
- **Validación de Seguridad**: Verifica que `category_id` pertenezca al usuario autenticado (evita IDOR).
- **Códigos**: `200 OK`, `404 Not Found` (si la categoría o tarea no pertenecen al usuario).

#### D. Endpoints de Categorías (`categories_bp`)
- `GET /categories`: Lista las categorías del usuario autenticado con `task_count` (conteo de tareas activas, `is_deleted=False`, asociadas a cada categoría).
- `POST /categories`: Crea nueva categoría (`{"name": "...", "description": "...", "color": "..."}`). Retorna `201 Created`, `400 Bad Request` si el nombre está duplicado para ese usuario, o `400 Bad Request` si `color` no cumple el formato `#RRGGBB`. Registra auditoría `CATEGORY_CREATED`.
- `POST /categories/<int:category_id>/edit`: Edita nombre, descripción y/o color de una categoría propia (`{"name": "...", "description": "...", "color": "..."}`), reutilizando las mismas validaciones que la creación (unicidad de nombre excluyendo la propia categoría, formato de color). Retorna `200 OK` / `302 Found`, `400 Bad Request` (nombre duplicado o color inválido), `404 Not Found` (categoría ajena o inexistente). Registra auditoría `CATEGORY_UPDATED`.
  > **Corrección post-analyze**: este endpoint no existía en la versión original del plan, aunque FR-007 de la spec exige explícitamente "editar" categorías — hallazgo E1 de `/speckit-analyze`.
- `POST /categories/<int:category_id>/delete`: Elimina la categoría y desvincula las tareas asignadas. Retorna `200 OK` / `302 Found`.

---

### 4. Cálculo del Indicador de Tarea "Vencida" (`is_overdue`)

- **Dónde se implementa**:
  Como propiedad computada del dominio en `src/taskcontrol/models/task.py` y serializada en el payload de respuesta de `TaskService.get_user_tasks` (Principio III):
  ```python
  @property
  def is_overdue(self) -> bool:
      if not self.due_date or self.status == 'completed' or self.is_deleted:
          return False
      current_date = datetime.now(timezone.utc).date()
      return self.due_date < current_date
  ```
- **Por qué NUNCA se persiste como columna en base de datos**:
  - Una columna persistida como `is_overdue BOOLEAN` se volvería obsoleta con el simple paso de las horas/días a menos que se ejecutaran procesos cron periódicos de sincronización.
  - Esto violaría el Principio I (monolito autónomo sin workers ni cron externos) e introduciría inconsistencias de estado.
  - Al calcularse dinámicamente en el backend en el momento de la consulta, la precisión es del 100%, evaluada siempre bajo UTC y sin dependencia del reloj del navegador del cliente (Principio III y HU-09).
- **Exclusiones Explícitas del Vencimiento**:
  1. Si `status == 'completed'`: **NUNCA** se marca como vencida.
  2. Si `is_deleted == True`: **NUNCA** se marca como vencida.
  3. Si `due_date is None`: **NUNCA** se marca como vencida.

---

### 5. Migraciones sobre el Esquema Existente (Principio VI)

- **Comando de Generación**:
  ```powershell
  flask db migrate -m "add_priority_and_category_entity"
  ```
- **Operaciones en el Script de Migración (`upgrade`)**:
  1. Crear la tabla `categories`:
     - Columnas: `id` (PK), `user_id` (FK a `users.id`), `name`, `description`, `color`, `created_at`.
     - Restricción única: `uq_user_category_name` en `(user_id, name)`.
  2. Modificar la tabla `tasks`:
     - `op.add_column('tasks', sa.Column('priority', sa.String(length=20), server_default='medium', nullable=False))`
     - `op.create_index(op.f('ix_tasks_priority'), 'tasks', ['priority'], unique=False)`
     - `op.add_column('tasks', sa.Column('category_id', sa.Integer(), nullable=True))`
     - `op.create_foreign_key('fk_tasks_category_id', 'tasks', 'categories', ['category_id'], ['id'], ondelete='SET NULL')`
     - `op.create_index(op.f('ix_tasks_category_id'), 'tasks', ['category_id'], unique=False)`
- **Garantía para Datos Preexistentes**:
  El parámetro `server_default='medium'` asegura que todas las tareas registradas previamente en los Incrementos 1 y 2 reciban automáticamente la prioridad por defecto `'medium'` sin generar errores de nulidad ni requerir manipulación manual. La columna `category_id` se inicializa como `NULL` de manera transparente.

---

### 6. Pruebas Automatizadas Bloqueantes a Nivel de Modelo/Servicio (Principio IV)

Siguiendo el ciclo *Test-First*, las siguientes pruebas unitarias y de servicio son bloqueantes:

1. **`test_task_priority_default_is_medium`**:
   Crea una tarea sin especificar prioridad y verifica que `task.priority == 'medium'`.
2. **`test_tasks_sorted_by_priority_descending_high_medium_low`**:
   Crea tareas con prioridades baja, alta y media; consulta con `sort='priority_desc'` y verifica que el orden de retorno sea estrictamente: `high` → `medium` → `low`.
3. **`test_tasks_sorted_by_priority_respects_status_filters`**:
   Verifica que filtrar por `status='in_progress'` y ordenar por prioridad solo retorne tareas en progreso ordenadas por su jerarquía de prioridad.
4. **`test_create_category_unique_name_per_user`**:
   Verifica que un usuario pueda crear categorías y que un intento de crear otra con el mismo nombre arroje `DuplicateCategoryNameError`.
5. **`test_different_users_can_have_same_category_name`**:
   Verifica que dos usuarios distintos puedan crear una categoría llamada "Trabajo" sin conflicto.
6. **`test_delete_category_sets_task_category_id_to_null_and_does_not_delete_tasks` (BLOQUEANTE)**:
   Crea una categoría, asigna 3 tareas a dicha categoría, elimina la categoría mediante `CategoryService.delete_category` y verifica:
   - Que las 3 tareas sigan existiendo en base de datos.
   - Que el atributo `category_id` de las 3 tareas sea `None`.
   - Que ninguna tarea haya sido borrada física ni lógicamente.
7. **`test_cannot_assign_task_to_another_users_category`**:
   Verifica que intentar asignar una tarea del Usuario A a una categoría del Usuario B sea rechazado con `CategoryNotFoundError` o falta de autorización.
8. **`test_task_overdue_when_due_date_past_and_not_completed` (BLOQUEANTE)**:
   Crea una tarea con fecha límite de ayer y estado `pending` o `in_progress`, verificando que `task.is_overdue` sea `True`.
9. **`test_completed_task_never_marked_overdue_even_if_due_date_past` (BLOQUEANTE)**:
   Crea una tarea con fecha límite de ayer pero con estado `completed`, verificando que `task.is_overdue` sea estrictamente `False`.
10. **`test_deleted_task_never_marked_overdue` (BLOQUEANTE)**:
    Crea una tarea con fecha límite pasada pero eliminada lógicamente (`is_deleted=True`), verificando que `task.is_overdue` sea `False`.
11. **`test_task_without_due_date_never_overdue`**:
    Verifica que tareas sin fecha límite (`due_date=None`) tengan `is_overdue == False`.
12. **`test_same_priority_tasks_sorted_by_due_date_ascending_nulls_last`** (añadida tras `/speckit-clarify`, Q2):
    Crea 3 tareas de prioridad `high` con `due_date` en distinto orden (una sin fecha) y verifica que el orden de retorno sea: fecha más próxima primero, y la sin fecha al final del grupo.
13. **`test_create_category_invalid_color_format_rejected`** (añadida tras `/speckit-clarify`, Q3):
    Intenta crear una categoría con `color="azul"` y verifica que se rechace con `InvalidCategoryColorError` (`400 Bad Request`), y que `color="#1A2B3C"` sí se acepte.
