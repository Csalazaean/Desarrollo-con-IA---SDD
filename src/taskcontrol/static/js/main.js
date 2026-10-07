// TaskControl Vanilla JS (Principio de Restricciones Técnicas - sin framework SPA)
document.addEventListener("DOMContentLoaded", () => {
    // 1. Auto-desvanecer mensajes flash después de 5 segundos
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // 2. Validación preventiva en el cliente para el formulario de registro
    const registerForm = document.querySelector("form[action*='register']");
    if (registerForm) {
        registerForm.addEventListener("submit", (e) => {
            const passwordInput = registerForm.querySelector("input[name='password']");
            if (passwordInput && passwordInput.value.length < 8) {
                e.preventDefault();
                alert("La contraseña debe tener al menos 8 caracteres.");
                passwordInput.focus();
            }
        });
    }

    // 3. Validación preventiva en el cliente para tareas
    const taskForms = document.querySelectorAll("form[action*='tasks']");
    taskForms.forEach(form => {
        form.addEventListener("submit", (e) => {
            const titleInput = form.querySelector("input[name='title']");
            if (titleInput && titleInput.value.trim() === "") {
                e.preventDefault();
                alert("El título de la tarea no puede estar vacío.");
                titleInput.focus();
            }
        });
    });

    // 4. Confirmación antes de acciones destructivas o de cambio de estado (HU-05, HU-06).
    // La confirmación vive aquí y no en un atributo onsubmit para mantener el JavaScript
    // separado de la plantilla (Principio II). El backend valida igual: esto solo evita
    // el clic accidental, nunca sustituye la autorización del servidor (Principio VII).
    const confirmaciones = [
        {
            selector: "form[action*='/delete']",
            mensaje: "¿Estás seguro de que deseas eliminar esta tarea? Podrás consultarla en el historial de auditoría."
        },
        {
            selector: "form[action*='/reopen']",
            mensaje: "¿Deseas reabrir esta tarea completada? Volverá al estado pendiente."
        }
    ];

    confirmaciones.forEach(({ selector, mensaje }) => {
        document.querySelectorAll(selector).forEach(form => {
            form.addEventListener("submit", (e) => {
                if (!window.confirm(mensaje)) {
                    e.preventDefault();
                }
            });
        });
    });

    // ----------------------------------------------------------------------
    // 5. Aviso transitorio para los errores de las operaciones sin recarga.
    // ----------------------------------------------------------------------
    function mostrarError(texto) {
        const aviso = document.createElement("div");
        aviso.className = "alert alert-error js-alert";
        aviso.setAttribute("role", "alert");
        aviso.textContent = texto;

        const contenedor = document.querySelector(".tasks-page") || document.body;
        contenedor.prepend(aviso);

        setTimeout(() => {
            aviso.style.transition = "opacity 0.5s ease";
            aviso.style.opacity = "0";
            setTimeout(() => aviso.remove(), 500);
        }, 5000);
    }

    const ETIQUETAS_ESTADO = {
        pending: "Pendiente",
        in_progress: "En Progreso",
        completed: "Completada"
    };

    // ----------------------------------------------------------------------
    // 6. HU-15: completar una tarea sin recargar la página.
    //
    // Mejora progresiva: los formularios siguen siendo formularios normales. Aquí
    // se intercepta su envío; si este script no carga o JavaScript está apagado,
    // el formulario se envía como siempre y la operación funciona con recarga.
    //
    // Reutiliza el endpoint de cambio de estado del Incremento 1: esta historia
    // no introduce ningún endpoint nuevo.
    // ----------------------------------------------------------------------
    const formulariosEstado = document.querySelectorAll("form[action*='/status']");

    formulariosEstado.forEach(form => {
        form.addEventListener("submit", async (e) => {
            const tarjeta = form.closest("[data-task-id]");
            const distintivo = tarjeta ? tarjeta.querySelector("[data-status-badge]") : null;
            const nuevoEstado = form.querySelector("input[name='status']");

            // Sin los puntos de anclaje no se intercepta: el formulario se envía
            // de la forma tradicional, que siempre funciona.
            if (!tarjeta || !distintivo || !nuevoEstado) {
                return;
            }

            e.preventDefault();

            // Se guarda el estado visual exacto antes de tocarlo, para poder
            // devolverlo tal cual si el backend no confirma el cambio.
            const textoAnterior = distintivo.textContent;
            const clasesAnteriores = distintivo.className;
            const estado = nuevoEstado.value;

            // Cambio optimista: la interfaz responde de inmediato.
            distintivo.textContent = ETIQUETAS_ESTADO[estado] || estado;
            distintivo.className = "badge badge-" + estado;

            try {
                const respuesta = await fetch(form.action, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({ status: estado }),
                    credentials: "same-origin"
                });

                if (!respuesta.ok) {
                    const cuerpo = await respuesta.json().catch(() => ({}));
                    throw new Error(cuerpo.message || "No se pudo actualizar la tarea.");
                }

                // El backend confirmó: el cambio optimista ya era correcto. Se
                // recarga para que los filtros y contadores reflejen el nuevo estado.
                window.location.reload();
            } catch (error) {
                // El backend NO confirmó: se revierte exactamente lo que había.
                // La interfaz nunca debe afirmar algo que el servidor no aceptó.
                distintivo.textContent = textoAnterior;
                distintivo.className = clasesAnteriores;
                mostrarError(error.message || "No se pudo actualizar la tarea.");
            }
        });
    });

    // ----------------------------------------------------------------------
    // 7. HU-16: reordenar tareas arrastrándolas.
    //
    // Usa la API de arrastrar y soltar nativa del navegador, sin librerías: la
    // interacción es una lista vertical y no justifica añadir dependencias.
    //
    // Solo se activa cuando el listado no tiene un ordenamiento explícito; con uno
    // aplicado, el orden arrastrado se desharía en la siguiente recarga.
    // ----------------------------------------------------------------------
    const listado = document.querySelector(".tasks-list[data-reorderable='true']");

    if (listado) {
        const tarjetas = Array.from(listado.querySelectorAll("[data-task-id]"));
        let arrastrada = null;
        let ordenAntesDelArrastre = null;

        function ordenActual() {
            return Array.from(listado.querySelectorAll("[data-task-id]"))
                .map(el => Number(el.dataset.taskId));
        }

        async function persistirOrden() {
            const nuevoOrden = ordenActual();

            // Soltar donde ya estaba no cambia nada: no se molesta al backend.
            if (JSON.stringify(nuevoOrden) === JSON.stringify(ordenAntesDelArrastre)) {
                return;
            }

            try {
                const respuesta = await fetch("/tasks/reorder", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({ task_ids: nuevoOrden }),
                    credentials: "same-origin"
                });

                if (!respuesta.ok) {
                    throw new Error("No se pudo guardar el nuevo orden.");
                }
            } catch (error) {
                // Se devuelve el listado al orden anterior: no puede quedar un orden
                // visible que el backend no haya guardado.
                ordenAntesDelArrastre.forEach(id => {
                    const el = listado.querySelector('[data-task-id="' + id + '"]');
                    if (el) listado.appendChild(el);
                });
                mostrarError(error.message || "No se pudo guardar el nuevo orden.");
            }
        }

        tarjetas.forEach(tarjeta => {
            tarjeta.setAttribute("draggable", "true");

            tarjeta.addEventListener("dragstart", () => {
                arrastrada = tarjeta;
                ordenAntesDelArrastre = ordenActual();
                tarjeta.classList.add("dragging");
            });

            tarjeta.addEventListener("dragend", async () => {
                tarjeta.classList.remove("dragging");
                listado.querySelectorAll(".drag-over").forEach(el => el.classList.remove("drag-over"));
                arrastrada = null;
                await persistirOrden();
            });

            tarjeta.addEventListener("dragover", (e) => {
                e.preventDefault();
                if (!arrastrada || arrastrada === tarjeta) return;

                tarjeta.classList.add("drag-over");

                // Se inserta antes o después según por dónde se cruce la tarjeta.
                const limites = tarjeta.getBoundingClientRect();
                const mitad = limites.top + limites.height / 2;
                if (e.clientY < mitad) {
                    listado.insertBefore(arrastrada, tarjeta);
                } else {
                    listado.insertBefore(arrastrada, tarjeta.nextSibling);
                }
            });

            tarjeta.addEventListener("dragleave", () => {
                tarjeta.classList.remove("drag-over");
            });

            tarjeta.addEventListener("drop", (e) => {
                e.preventDefault();
                tarjeta.classList.remove("drag-over");
            });
        });
    }
});
