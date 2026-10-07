# Quickstart & Verification Guide: 005-frontend-interaction

**Feature**: `005-frontend-interaction`
**Date**: 2026-10-07

---

## 1. Prerrequisitos y Configuración de Entorno

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 2. Aplicación de Migraciones de Base de Datos (Principio VI)

```powershell
flask db upgrade
```

---

## 3. Ejecución de Pruebas Automatizadas (Principio IV)

```powershell
# 1. Pruebas de dominio y servicios (Test-First) — único alcance con pruebas automatizadas de este incremento
pytest tests/services/test_task_service.py -v

# 2. Suite completa (cero regresión sobre los Incrementos 1-4)
pytest -v
```

> No existen pruebas automatizadas de JavaScript en este proyecto. La verificación de HU-15 y HU-16 a nivel de interfaz es **manual**, siguiendo los escenarios E2E de abajo (ver `plan.md` §6).

---

## 4. Verificación Manual de Escenarios E2E

Inicia la aplicación:
```powershell
flask run
```

### Escenario A: Completar sin Recargar (HU-15)
1. Inicia sesión y abre el listado de tareas con una tarea pendiente.
2. Abre las herramientas de desarrollador del navegador (pestaña Red/Network).
3. Haz clic en "Completar". **Verificación**: el badge de estado cambia a "Completada" inmediatamente, sin que la página recargue (no hay una navegación completa en la pestaña Red).
4. Simula un fallo: desconecta la red (modo "Offline" en DevTools) y repite la acción sobre otra tarea. **Verificación**: el badge revierte a su estado anterior y aparece un mensaje de error — la tarea nunca queda mostrando "Completada" si el backend no lo confirmó.
5. Reconecta la red y recarga la página: el estado real coincide exactamente con lo que el backend tiene persistido.

### Escenario B: Reordenar con Arrastrar y Soltar (HU-16)
1. Con varias tareas en el listado, selecciona el control de orden **"Manual"** (`sort=manual`).
2. **Verificación**: las tarjetas de tarea ahora son arrastrables (cursor de arrastre al pasar sobre ellas); al cambiar a ordenar por "Prioridad" o "Más reciente", deja de ser posible arrastrarlas.
3. Vuelve a "Manual" y arrastra una tarea a una nueva posición. **Verificación**: el listado refleja el nuevo orden inmediatamente.
4. Recarga la página completa (F5). **Verificación**: el orden manual se mantiene exactamente como quedó.
5. Cambia a la pestaña "Asignadas a mí" (Incremento 4) con el modo manual activo, y arrastra una tarea que otro usuario te asignó. **Verificación**: el reordenamiento se guarda sin error — reordenar una tarea asignada (no propia) está permitido (Clarifications Q3).
6. Intenta (vía API, no por la interfaz) enviar un `task_id` que no te pertenece en el payload de `/tasks/reorder`. **Verificación**: la petición se rechaza con `404` y ninguna tarea del lote cambia de orden, ni siquiera las que sí eran válidas.
