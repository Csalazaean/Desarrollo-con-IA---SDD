# Data Model: 005-frontend-interaction

**Feature**: 005-frontend-interaction
**Date**: 2026-10-07
**ORM**: SQLAlchemy

---

## 1. Entidad `Task` (Extendida para Orden Manual)

Se mantiene la compatibilidad absoluta con los Incrementos 1-4, agregando una única columna:

| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `manual_order` | `Integer` | Not Null, Default `0`, Index | Posición global del usuario en el modo de orden manual (ver spec Clarifications, Session 2026-10-07, Q1) |

**Reglas de negocio (`TaskService`)**:
- `manual_order` es una posición **global por tarea**, no por combinación de filtros (Clarifications Q1) — el mismo valor aplica sin importar qué filtro de estado o categoría esté activo.
- Solo tiene efecto visible cuando el listado se consulta con `sort=manual` (Clarifications Q2); con cualquier otro criterio de orden, la columna existe pero no se usa para ordenar.
- `TaskService.reorder_tasks(user_id, task_ids)` es la única vía de escritura de este campo. Autoriza cada `task_id` como creador **o** asignatario (Clarifications Q3, reutilizando el criterio ya establecido en el Incremento 4), y aplica el lote completo de forma atómica.
- No genera evento de `AuditLog` (ver `research.md` §4).
- Las tareas eliminadas lógicamente (`is_deleted=True`) no participan del reordenamiento manual, consistente con su exclusión general del listado activo desde el Incremento 2.

---

## 2. Sin Nuevas Entidades

Este incremento no introduce ninguna entidad nueva — únicamente extiende `Task` con la columna `manual_order`. No hay cambios en `User`, `Category`, `Notification` ni `AuditLog`.
