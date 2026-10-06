<!--
Sync Impact Report:
- Version change: 0.0.0 → 1.0.0 (Adopción inicial de la constitución de TaskControl)
- Modified principles: N/A (Definición inicial de principios)
- Added sections:
  * Core Principles:
    - I. Monolito por diseño
    - II. Separación de responsabilidades dentro del monolito
    - III. Contrato explícito entre backend y JavaScript
    - IV. Test-first para toda la lógica de negocio
    - V. Simplicidad sobre generalidad prematura
    - VI. Integridad de datos y migraciones
    - VII. Seguridad por defecto
    - VIII. Observabilidad mínima viable
  * Restricciones Técnicas del Stack
  * Alineación con el Backlog y Flujo de Desarrollo
  * Governance
- Removed sections: N/A
- Follow-up TODOs: Ninguno
-->

# TaskControl Constitution

## Core Principles

### I. Monolito por diseño
El sistema se implementa y mantiene estrictamente como una arquitectura monolítica: un único repositorio de código fuente, un único proceso desplegable en ejecución y una única base de datos relacional.
- **Regla no negociable (MUST)**: Queda terminantemente prohibido introducir microservicios, funciones serverless independientes o colas de mensajería asíncronas externas (como RabbitMQ, Kafka o Celery), salvo que una especificación técnica futura demuestre con evidencia empírica medible que el monolito no puede sostener un requisito concreto.
- **Razón de ser**: Reduce la complejidad operativa, simplifica la consistencia transaccional ACID, elimina latencias de red en llamadas internas y optimiza la velocidad de desarrollo del equipo.

### II. Separación de responsabilidades dentro del monolito
La arquitectura monolítica debe estructurarse en capas internas con fronteras estrictas y unidireccionales:
1. **Presentación**: Plantillas Jinja2 renderizadas en servidor y JavaScript modular en cliente para interactividad.
2. **Rutas HTTP (Controladores)**: Blueprints de Flask responsables exclusivamente de la negociación HTTP, deserialización de entradas, llamada al servicio correspondiente y serialización de respuestas.
3. **Lógica de Negocio (Servicios)**: Módulos de servicios que encapsulan las reglas de negocio de dominio sin depender del contexto HTTP.
4. **Modelos y Persistencia**: Modelos de datos y operaciones respaldadas por SQLAlchemy como ORM.
- **Regla no negociable (MUST)**: Ninguna capa puede comunicarse con otra saltándose la capa inmediatamente inferior (por ejemplo, los blueprints de Flask tienen prohibido ejecutar consultas ORM/SQL directas o manipular la base de datos sin pasar por la capa de servicios).
- **Razón de ser**: Garantiza el desacoplamiento, permite probar la lógica de dominio de forma aislada sin levantar el servidor HTTP y mantiene la base de código ordenada y mantenible.

### III. Contrato explícito entre backend y JavaScript
Toda interacción cliente-servidor para funcionalidades dinámicas pasa obligatoriamente por endpoints HTTP con contrato formalmente definido y documentado antes de implementarse.
- **Regla no negociable (MUST)**: Cada contrato debe documentar ruta, método HTTP, payload de entrada, payload de salida y códigos de estado HTTP de éxito y error. La interfaz cliente no debe depender de comportamientos implícitos no especificados en el contrato.
- **Razón de ser**: Previene desajustes de integración entre la interfaz de usuario y los servicios del backend, asegurando respuestas consistentes y pruebas de contrato reproducibles.

### IV. Test-first para toda la lógica de negocio
Toda regla de dominio —incluyendo creación de tareas, transiciones de estado del ciclo de vida, eliminación lógica, asignación de usuarios y validaciones— debe especificarse primero como prueba automatizada.
- **Regla no negociable (MUST)**: El ciclo Red-Green-Refactor es obligatorio y bloqueante para la capa de servicios y dominio. La prueba automatizada debe escribirse y fallar antes de implementar el código de producción que la haga pasar. Ninguna historia de usuario (HU-XX) se considera completada sin su suite de pruebas correspondiente.
- **Razón de ser**: Asegura la cobertura total del dominio, previene regresiones tempranas y convierte las pruebas en especificaciones ejecutables vivas del sistema.

### V. Simplicidad sobre generalidad prematura
Se aplica con rigor el principio YAGNI (You Aren't Gonna Need It).
- **Regla no negociable (MUST)**: Queda prohibida la introducción de abstracciones especulativas, capas de configuración dinámicas, metaprogramación compleja o sistemas de plugins sin la existencia de un requisito funcional documentado en el backlog que lo justifique de forma inmediata.
- **Razón de ser**: Previene la sobreingeniería, reduce la deuda técnica temprana y mantiene el código entendible y directo.

### VI. Integridad de datos y migraciones
La integridad del modelo relacional es prioritaria y debe preservarse en cada fase del ciclo de vida del software.
- **Regla no negociable (MUST)**: Todo cambio estructural en el esquema de la base de datos (tablas, columnas, restricciones, claves foráneas e índices) debe realizarse exclusivamente mediante migraciones versionadas y reproducibles utilizando Flask-Migrate (Alembic). Se prohíbe terminantemente ejecutar modificaciones manuales directas en cualquier entorno.
- **Razón de ser**: Garantiza la reproducibilidad y sincronización exacta de la base de datos entre entornos de desarrollo, pruebas y producción, impidiendo la deriva de esquemas.

### VII. Seguridad por defecto
La seguridad debe integrarse de forma nativa en cada flujo y endpoint del sistema.
- **Regla no negociable (MUST)**:
  - Toda entrada de usuario debe validarse y sanitizarse en el backend, sin confiar en validaciones realizadas en JavaScript.
  - La autenticación y autorización deben verificarse obligatoriamente en cada endpoint que consulte o modifique datos protegidos.
  - No se almacenan contraseñas en texto plano (uso de hash seguro); queda prohibido commitear credenciales o secretos en el repositorio; la configuración sensible se gestiona exclusivamente mediante variables de entorno (`.env` no versionado).
- **Razón de ser**: Minimiza la superficie de ataque, protege la privacidad del usuario y evita vulnerabilidades críticas de inyección y exposición de credenciales.

### VIII. Observabilidad mínima viable
Toda operación que modifique el estado de una tarea o recurso principal debe ser auditable y trazable.
- **Regla no negociable (MUST)**: Desde el primer incremento funcional, cada mutación de estado genera un registro en log estructurado que incluye obligatoriamente:
  - `actor_id`: Identificador del usuario o sistema que ejecuta la acción.
  - `action`: Acción ejecutada (ej. `TASK_CREATED`, `STATUS_CHANGED`, `TASK_ASSIGNED`).
  - `entity_id`: Identificador de la tarea o recurso modificado.
  - `timestamp`: Marca de tiempo en formato ISO-8601 UTC.
- **Razón de ser**: Facilita la auditoría forense, la depuración rápida de incidencias operativas y la trazabilidad del ciclo de vida de los datos.

## Restricciones Técnicas del Stack

- **Lenguaje Backend**: Python 3.11+.
- **Framework Web**: Flask como único framework web. Queda prohibida la introducción de Django, FastAPI u otros frameworks sin una enmienda formal previa de esta constitución.
- **Persistencia**: Base de datos relacional gestionada a través de SQLAlchemy como ORM oficial.
- **Migraciones de Esquema**: Flask-Migrate / Alembic.
- **Capa de Presentación**: Plantillas Jinja2 renderizadas en servidor combinadas con JavaScript vanilla (ES6+) para interactividad asíncrona (Fetch API). No se permite el uso de frameworks SPA pesados (React, Angular, Vue) salvo justificación explícita documentada y aprobada por enmienda.
- **Entorno Unificado**: El entorno de desarrollo y ejecución debe poder levantarse con un único comando (`docker compose up` o script `run.sh` / `run.ps1` equivalente).

## Alineación con el Backlog y Flujo de Desarrollo

- **Trazabilidad de Historias (HU-XX)**: Toda especificación (`spec.md`), plan (`plan.md`) y tarea técnica (`tasks.md`) debe vincularse directamente a la numeración de historias de usuario del backlog oficial (`.specify/memory/backlog.md`) manteniendo consistencia de alcance y nomenclatura.
- **Priorización del Roadmap (MoSCoW)**:
  - **Must**: Base del primer incremento funcional (HU-01 a HU-04 para gestión básica de tareas, HU-12 y HU-13 para cuentas y acceso).
  - **Should**: Siguientes incrementos funcionales (HU-05, HU-06, HU-07, HU-10, HU-14, HU-15).
  - **Could**: Mejoras secundarias y optimizaciones de interacción (HU-08, HU-09, HU-11, HU-16).
- **Puertas de Calidad (Quality Gates)**: Ningún cambio se integrará sin pruebas automatizadas en verde, cumplimiento de contratos HTTP documentados y generación de logs de auditoría estructurados en mutaciones.

## Governance

- **Supremacía de la Constitución**: Esta constitución rige todas las decisiones arquitectónicas y técnicas del proyecto TaskControl, prevaleciendo sobre decisiones de implementación puntuales o desacuerdos temporales.
- **Procedimiento de Enmienda**: Cualquier cambio a los principios o restricciones técnicas requiere:
  1. Propuesta documentada con justificación técnica y evidencia empírica.
  2. Actualización del informe de sincronización (`Sync Impact Report`).
  3. Incremento del número de versión según las reglas de versionado semántico.
- **Política de Versionado Semántico**:
  - **MAYOR (X.0.0)**: Cambios incompatibles con la arquitectura o eliminación/redefinición de principios fundamentales (ej. migrar de monolito a microservicios, sustitución de Flask, eliminación de la exigencia test-first).
  - **MENOR (1.X.0)**: Adición de nuevos principios, incorporación de nuevas directrices de calidad o expansión material de reglas existentes sin revocar las anteriores.
  - **PARCHE (1.0.X)**: Clarificaciones de redacción, corrección de erratas o refinamientos no semánticos.
- **Revisión de Cumplimiento**: En cada ciclo de especificación (`/speckit-specify`), planificación (`/speckit-plan`) e implementación (`/speckit-implement`), se verificará de manera obligatoria la adherencia a estos principios.

**Version**: 1.0.0 | **Ratified**: 2026-09-29 | **Last Amended**: 2026-09-29
