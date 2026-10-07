# Quickstart: 005-ui-interaction

Procedimiento de verificación del Incremento 5 (HU-15, HU-16).

---

## ⚠️ Alcance de la verificación automática

**Este proyecto no tiene infraestructura de pruebas de frontend.** No hay Jest, Vitest ni Playwright, y `requirements.txt` es exclusivamente Python. Montar una introduciría un ecosistema de Node completo en un proyecto que hasta ahora no lo necesita, lo cual excede el alcance de este incremento.

En consecuencia:

| Comportamiento | Cómo se verifica |
|---|---|
| El endpoint de reordenamiento persiste el orden | ✅ `pytest` |
| Los identificadores ajenos no alteran tareas de otros | ✅ `pytest` |
| Identificadores inexistentes o eliminados se ignoran | ✅ `pytest` |
| El endpoint de estado responde JSON al `fetch` | ✅ `pytest` |
| Las tareas preexistentes conservan su orden | ✅ `pytest` |
| **Que un error del backend revierta el estado visual** | ⚠️ **manual** (§3) |
| **Que el arrastre reordene visualmente** | ⚠️ **manual** (§4) |
| **Que todo funcione sin JavaScript** | ⚠️ **manual** (§5) |

Las pruebas automatizadas cubren todo el contrato de backend, que es donde reside el riesgo de pérdida o corrupción de datos. Lo que queda manual es la capa visual.

---

## 1. Preparación

```
cd C:\Users\marie\Proyectos\Desarrollo-con-IA---SDD
venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
pytest -v
flask run
```

Abre http://127.0.0.1:5000, inicia sesión y crea al menos **tres tareas** con títulos distinguibles ("Primera", "Segunda", "Tercera").

---

## 2. Completar sin recargar (HU-15) — camino feliz

1. Aplica un filtro cualquiera, por ejemplo **Pendientes**.
2. Pulsa **Completar** en una tarea.

**Esperado**: el distintivo de esa tarea cambia a "Completada". El filtro aplicado se conserva.

---

## 3. Reversión ante error (HU-15) — ⚠️ verificación manual de FR-003

Este es el comportamiento crítico de la historia y el que no cubre `pytest`.

1. Con la página de tareas abierta, **detén el servidor** (`Ctrl+C` en la terminal de `flask run`).
2. Sin recargar la página, pulsa **Completar** en una tarea pendiente.

**Esperado**:
- El distintivo cambia un instante a "Completada" (cambio optimista).
- Al fallar la petición, **vuelve exactamente a su estado anterior**.
- Aparece un mensaje de error en la parte superior.

**Fallo**: si el distintivo se queda en "Completada" pese a que el servidor está caído, la interfaz estaría afirmando algo que el backend nunca confirmó. Eso incumple FR-003 y SC-002.

3. Vuelve a levantar el servidor y recarga: la tarea debe seguir **pendiente**, confirmando que nada se guardó.

---

## 4. Reordenar arrastrando (HU-16) — ⚠️ verificación manual de FR-006

1. Asegúrate de **no** tener un ordenamiento explícito activo: pulsa **Más recientes** en la fila de orden.
2. Arrastra la última tarea del listado hasta la primera posición.
3. **Recarga la página** (F5).

**Esperado**: el orden que definiste se mantiene tras la recarga (FR-008, SC-003).

4. Ahora pulsa **Prioridad: alta primero**.

**Esperado**: las tarjetas **ya no se pueden arrastrar**, porque hay un criterio de orden activo que el arrastre contradiría (FR-012).

5. Vuelve a **Más recientes**: el arrastre se habilita de nuevo y el orden personal que guardaste sigue ahí.

---

## 5. Funcionamiento sin JavaScript — ⚠️ verificación manual de FR-005

1. Desactiva JavaScript en el navegador (en Chrome: `F12` → `⋮` → *Settings* → *Debugger* → *Disable JavaScript*).
2. Recarga la página de tareas.
3. Pulsa **Completar** en una tarea.

**Esperado**: la operación funciona igualmente, esta vez **con recarga de página**. El arrastrar y soltar no está disponible, lo cual es correcto: es una mejora, no un requisito funcional.

**Fallo**: si el botón deja de funcionar sin JavaScript, la mejora progresiva estaría rota y se incumpliría SC-006.

---

## 6. Aislamiento entre usuarios (FR-010)

Cubierto por `pytest`, pero puede comprobarse a mano con dos cuentas: reordenar las tareas de una **no** altera el orden de la otra, porque las posiciones solo se comparan entre tareas del mismo propietario.
