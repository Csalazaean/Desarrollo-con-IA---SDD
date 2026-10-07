# Research: 005-frontend-interaction

**Feature**: 005-frontend-interaction
**Date**: 2026-10-07

---

## 1. Fetch Nativo vs. Framework para Interacción sin Recarga (HU-15)

**Decision**: `fetch()` nativo del navegador contra el endpoint `POST /tasks/<id>/status` ya existente, con actualización optimista del DOM y reversión manual en caso de error.

**Rationale**: La interacción se limita a un cambio de estado de un único recurso ya expuesto por contrato. Introducir React/Vue para esto violaría el Principio V (YAGNI) y la restricción técnica explícita del stack ("JavaScript vanilla... salvo justificación explícita documentada y aprobada por enmienda") — no existe tal enmienda ni justificación que lo amerite para una interacción de este tamaño.

**Alternatives considered**:
- Framework SPA ligero (Alpine.js, htmx): descartado — ninguno es parte del stack aprobado por la constitución, y agregarlo para una sola interacción sería una dependencia nueva sin justificación proporcional.

---

## 2. API Nativa de Drag and Drop vs. Librería (SortableJS) para HU-16

**Decision**: API nativa de Drag and Drop HTML5 del navegador (`draggable`, `dragstart`, `dragover`, `drop`).

**Rationale**: El caso de uso (reordenar tarjetas de una lista plana) es exactamente lo que la API nativa resuelve sin configuración adicional. Una librería como SortableJS agrega una dependencia de terceros (y su respectivo mantenimiento, actualizaciones de seguridad, peso de descarga) para resolver algo que el navegador ya soporta — exactamente el tipo de generalización prematura que el Principio V prohíbe sin un requisito que la justifique. No hay requisito en la spec (ej. soporte táctil avanzado, animaciones complejas) que exija las capacidades extra de una librería.

**Alternatives considered**:
- SortableJS u otra librería de arrastre: descartada por Principio V: sin justificación documentada de que la API nativa sea insuficiente.
- Implementación con eventos de mouse/touch manuales (sin la API de Drag and Drop): descartada por reinventar algo que el estándar HTML5 ya resuelve de forma más accesible y con menos código.

---

## 3. Diseño del Endpoint de Reordenamiento: Lote Completo vs. Posición Individual

**Decision**: Un único endpoint `POST /tasks/reorder` que recibe el arreglo completo de `task_id` en el nuevo orden visual, y reasigna `manual_order` secuencialmente según la posición de cada uno en el arreglo.

**Rationale**: Evita la complejidad de "desplazar" los `manual_order` de las tareas intermedias en el backend (lo que requeriría lógica de desplazamiento con posibles condiciones de carrera si se modelara como "mover la tarea X a la posición N"). Enviar el arreglo completo tras cada `drop` es simple, atómico (se reemplaza todo o nada) y evita inconsistencias parciales — alineado con Principio V.

**Alternatives considered**:
- `POST /tasks/<id>/reorder` con `{"new_position": N}` por tarea individual: descartado por requerir lógica de desplazamiento en el backend (recalcular el `manual_order` de todas las tareas entre la posición antigua y la nueva), más compleja y con más superficie para errores de concurrencia, sin beneficio real dado que el cliente ya tiene el arreglo completo disponible tras el `drop`.

---

## 4. Auditoría del Reordenamiento

**Decision**: El reordenamiento manual **no** genera un nuevo evento en `AuditLog`.

**Rationale**: El Principio VIII exige auditar mutaciones del "estado de una tarea o recurso principal". El orden manual es una preferencia de visualización personal (confirmado en Clarifications Q3: "es una preferencia de vista personal, no una edición de la tarea"), no un cambio al contenido ni al ciclo de vida de negocio de la tarea — consistente con que tampoco se audita, por ejemplo, qué filtro o criterio de orden (`priority_desc`, `due_date`) tiene seleccionado un usuario en un momento dado.

**Alternatives considered**:
- Auditar cada reordenamiento con una acción `TASK_REORDERED`: descartado — generaría ruido de auditoría de alta frecuencia (cada arrastre) sin valor forense real, y no hay un requisito funcional (FR) que lo exija.

---

## 5. Backfill del Campo `manual_order` para Tareas Existentes

**Decision**: Migración con backfill determinista: para cada usuario, las tareas existentes reciben `manual_order` secuencial siguiendo el mismo orden en que ya se listaban por defecto (`created_at` descendente).

**Rationale**: La spec (Assumptions) exige que las tareas existentes reciban "un orden inicial razonable (por ejemplo, el mismo orden en que ya se listaban)". Un valor plano (ej. `0` para todas) no cumpliría esto, porque al activar el modo manual por primera vez todas las tareas empatarían en la misma posición, con un orden de desempate no determinista. El backfill por `created_at` evita esa sorpresa.

**Alternatives considered**:
- `manual_order = 0` para todas las tareas existentes: descartado por no preservar ningún orden reconocible al activar el modo manual por primera vez.
