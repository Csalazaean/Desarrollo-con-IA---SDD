# Research: 004-user-collaboration

**Feature**: 004-user-collaboration
**Date**: 2026-10-06

---

## 1. Resolución del Destinatario de Asignación por Correo Electrónico

**Decision**: El endpoint de asignación recibe `assigned_to_email` (string); el backend resuelve `User.query.filter_by(email=assigned_to_email.strip().lower())` y obtiene el `user_id` internamente. Nunca se expone ni se acepta un `user_id` crudo desde el cliente para este flujo.

**Rationale**: Resuelto en `/speckit-clarify` (Session 2026-10-06, Q1) — el correo es el único dato que un usuario conoce de un compañero de equipo; aceptar un ID numérico expondría detalles de implementación (autoincrementales de base de datos) sin aportar valor de UX, y aceptar ambos formatos duplicaría la lógica de validación sin un requisito que lo justifique (Principio V, YAGNI).

**Alternatives considered**:
- Aceptar `user_id` numérico vía selector/dropdown ya resuelto en frontend: descartado porque requeriría exponer un listado completo de usuarios del sistema a cualquier usuario autenticado (fuga de información, Principio VII).
- Aceptar ambos formatos con detección automática: descartado por complejidad innecesaria sin caso de uso que lo requiera.

---

## 2. Notificación al Desasignar

**Decision**: La operación de desasignar (`unassign_task`) **nunca** genera una notificación interna. Solo queda auditada (`TASK_UNASSIGNED`).

**Rationale**: Resuelto en `/speckit-clarify` (Session 2026-10-06, Q2) — HU-11 del backlog únicamente pide notificar "cuando se me asigna una tarea"; expandir el alcance a la desasignación sería agregar una funcionalidad no solicitada (Principio V). Además, el efecto ya es inmediatamente visible: la tarea desaparece de la pestaña "Asignadas a mí" del usuario afectado en su siguiente consulta.

**Alternatives considered**:
- Notificar también al desasignar: descartado por exceder el alcance de HU-11 sin un criterio de aceptación que lo pida.

---

## 3. Umbral de Latencia de SC-003 (<100ms)

**Decision**: Se documenta como cumplido por diseño (la notificación se persiste en la misma transacción síncrona que la asignación, sobre SQLite local). No se construye infraestructura de medición de rendimiento ni prueba de carga dedicada.

**Rationale**: Resuelto en `/speckit-clarify` (Session 2026-10-06, Q3) — una escritura síncrona local cumple el umbral de sobra sin esfuerzo adicional; instrumentar una prueba de rendimiento real sería sobreingeniería para el alcance académico de este proyecto (Principio V, YAGNI), y no existe infraestructura de carga en el proyecto para hacerlo de forma significativa.

**Alternatives considered**:
- Prueba automatizada que mida tiempo de ejecución: descartada por desproporcionada frente al riesgo real (SQLite local nunca se acerca a 100ms para un `INSERT` simple).

---

## 4. Relación Dual de `Task` con `User` (Creador y Asignatario)

**Decision**: `Task.assigned_to_id` se define como una segunda FK independiente a `users.id`, con `db.relationship('User', foreign_keys=[assigned_to_id])` explícito para evitar la ambigüedad que SQLAlchemy reporta cuando detecta dos FKs desde la misma tabla hacia `users` sin que se indique cuál usa cada relación.

**Rationale**: `Task.user_id` (creador) ya tiene su propia relación implícita vía el backref `User.tasks` definido en el Incremento 1. Agregar `assigned_to_id` sin `foreign_keys` explícito causaría un error de configuración del mapeador ORM al arrancar la aplicación.

**Alternatives considered**:
- Tabla de asignación separada (`task_assignments`) para permitir múltiples asignatarios: descartada explícitamente por la spec ("Asignación múltiple... fuera de alcance") y por Principio V.

---

## 5. Mensaje de Notificación Denormalizado vs. Calculado

**Decision**: El texto de la notificación (`message`) se construye y persiste como cadena fija en el momento de la creación, nunca se recalcula a partir de un join con `Task`/`User` en cada lectura.

**Rationale**: El Edge Case "Eliminación lógica de tarea asignada" exige que "las notificaciones históricas previas preservan el texto del evento sin romper enlaces" — si el mensaje se recalculara dinámicamente y la tarea referenciada cambiara de título (o se eliminara lógicamente), el historial de notificaciones mostraría un texto distinto al que realmente ocurrió, violando la trazabilidad esperada de un log de eventos.

**Alternatives considered**:
- Calcular el mensaje dinámicamente uniendo `task.title` en cada consulta: descartado porque no preserva el estado histórico del evento.
