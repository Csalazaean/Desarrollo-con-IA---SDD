# Technical Research: 003-task-organization-priority

**Feature**: `003-task-organization-priority`  
**Date**: 2026-10-01  
**Status**: Completed  

---

## 1. Prioridad de Tareas y Estrategia de Ordenamiento SQL

### Contexto y Problema
La historia `HU-07` requiere que toda tarea tenga una prioridad (`high`, `medium`, `low`) con valor por defecto `medium`, y que el listado pueda ordenarse de forma jerárquica preservando los filtros por estado existentes.

### Decisiones de Diseño
- **Valores Normalizados**:
  - `high` (Alta)
  - `medium` (Media - valor por defecto)
  - `low` (Baja)
- **Estrategia de Ordenamiento Jerárquico en SQLAlchemy**:
  En bases de datos relacionales, el orden lexicográfico de las cadenas (`high`, `low`, `medium`) no coincide con el orden semántico de prioridad. Para ordenar en la capa de datos de forma eficiente mediante índices:
  ```python
  from sqlalchemy import case

  priority_order = case(
      (Task.priority == 'high', 1),
      (Task.priority == 'medium', 2),
      (Task.priority == 'low', 3),
      else_=4
  )
  ```
  Al solicitar orden descendente (`sort=priority_desc`), la consulta SQL aplica `.order_by(priority_order.asc(), Task.due_date.is_(None), Task.due_date.asc())` para mostrar primero las tareas de prioridad alta, luego media y finalmente baja; dentro de cada nivel, desempata por `due_date` ascendente dejando al final las tareas sin fecha límite (actualizado tras `/speckit-clarify`, Session 2026-10-06, Q2 — la versión previa de esta investigación usaba `created_at.desc()`).
- **Compatibilidad con Filtros Preexistentes**:
  El ordenamiento por prioridad se concatena en `TaskService.get_user_tasks` después de aplicar los filtros `user_id`, `is_deleted == False` y `status == requested_status`, sin romper el comportamiento de los Incrementos 1 y 2.

---

## 2. Entidad `Category` y Política de Desvinculación sin Cascada

### Contexto y Problema
La historia `HU-08` exige que eliminar una categoría desvincule sus tareas asociadas, dejando `category_id = NULL`, sin eliminar jamás las tareas pertenecientes a ella (prohibición estricta de borrado en cascada).

### Decisiones de Diseño
- **Definición de Clave Foránea**:
  - `tasks.category_id`: `db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)`.
- **Garantía a Nivel de Base de Datos y Servicio**:
  1. A nivel DDL en el motor relacional: `ON DELETE SET NULL`.
  2. A nivel de servicio (`CategoryService.delete_category`): Antes de eliminar la fila de la categoría, se ejecuta de forma defensiva la actualización atómica:
     ```python
     Task.query.filter_by(category_id=category_id).update({Task.category_id: None})
     ```
     Esto asegura que tanto en SQLite (donde el soporte de claves foráneas con `ON DELETE` requiere `PRAGMA foreign_keys = ON`) como en PostgreSQL o MySQL, las tareas queden 100% preservadas y desvinculadas sin riesgo de cascada.

---

## 3. Indicador de Tareas Vencidas (`is_overdue`) en Backend

### Contexto y Problema
La historia `HU-09` y el Principio III de la constitución exigen que el cálculo de vencimiento se resuelva exclusivamente en el backend y bajo una referencia horaria homogénea (UTC), sin delegar la decisión a JavaScript para evitar discrepancias por la zona horaria del cliente.

### Decisiones de Diseño
- **No Persistencia en Base de Datos**:
  El vencimiento es una condición dependiente del paso del tiempo continuo. Persistir una columna `is_overdue` en la base de datos requeriría procesos en segundo plano (cron jobs/workers periódicos) para actualizarla diariamente, lo cual violaría el Principio I (monolito autónomo sin dependencias complejas de orquestación externa) y generaría desincronizaciones de datos.
- **Cálculo Derivado en Tiempo de Lectura**:
  Se define como propiedad de dominio en la entidad `Task` y se serializa en el payload expuesto al frontend:
  ```python
  @property
  def is_overdue(self) -> bool:
      if not self.due_date or self.status == 'completed' or self.is_deleted:
          return False
      current_date = datetime.now(timezone.utc).date()
      return self.due_date < current_date
  ```
- **Regla Estricta de Negocio**:
  Una tarea completada (`status == 'completed'`) o eliminada (`is_deleted == True`) **nunca** se considera vencida, protegiendo la coherencia visual y operativa.
