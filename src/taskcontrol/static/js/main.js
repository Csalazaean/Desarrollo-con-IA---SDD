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

    // 4. Validación preventiva en el cliente para el formulario de categorías (HU-08)
    // El campo color usa <input type="color">, por lo que el navegador ya garantiza
    // un valor hexadecimal válido; solo se valida aquí el nombre obligatorio.
    const categoryForms = document.querySelectorAll("form[action*='categories']");
    categoryForms.forEach(form => {
        form.addEventListener("submit", (e) => {
            const nameInput = form.querySelector("input[name='name']");
            if (nameInput && nameInput.value.trim() === "") {
                e.preventDefault();
                alert("El nombre de la categoría no puede estar vacío.");
                nameInput.focus();
            }
        });
    });

    // 5. Confirmación previa para acciones destructivas o irreversibles (eliminar, reabrir)
    function attachConfirmListeners(scope) {
        const confirmForms = scope.querySelectorAll("form[data-confirm]");
        confirmForms.forEach(form => {
            form.addEventListener("submit", (e) => {
                if (!window.confirm(form.dataset.confirm)) {
                    e.preventDefault();
                }
            });
        });
    }
    attachConfirmListeners(document);

    // 6. Completar tareas sin recargar la página (HU-15): fetch optimista con
    // reversión visual si el backend rechaza el cambio (nunca queda en pantalla
    // un estado que el backend no confirmó).
    const completeForms = document.querySelectorAll("form.complete-form");
    completeForms.forEach(form => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const card = form.closest(".task-card");
            const badge = card.querySelector("[data-status-badge]");
            const actionsContainer = card.querySelector("[data-status-actions]");
            const submitButton = form.querySelector("button[type='submit']");

            const previousBadgeClass = badge.className;
            const previousBadgeText = badge.textContent;

            // Actualización optimista
            badge.className = "badge badge-completed";
            badge.textContent = "Completada";
            submitButton.disabled = true;

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: new FormData(form),
                    headers: { "Accept": "application/json" },
                });

                if (!response.ok) {
                    throw new Error("La petición de completar la tarea falló");
                }

                // Éxito confirmado por el backend: las únicas acciones de estado
                // válidas tras completar son reabrir (Iniciar/Pausar/Completar ya no aplican).
                const reopenUrl = actionsContainer.dataset.reopenUrl;
                actionsContainer.innerHTML = `
                    <form action="${reopenUrl}" method="POST" class="inline-form" data-confirm="¿Reabrir esta tarea completada? Volverá al estado 'pendiente'.">
                        <button type="submit" class="btn btn-secondary btn-sm">Reabrir</button>
                    </form>`;
                attachConfirmListeners(actionsContainer);
            } catch (error) {
                // Reversión: nunca dejar visible un estado no confirmado por el backend
                badge.className = previousBadgeClass;
                badge.textContent = previousBadgeText;
                submitButton.disabled = false;
                alert("No se pudo completar la tarea. Verifica tu conexión e intenta de nuevo.");
            }
        });
    });

    // 7. Reordenar tareas arrastrándolas (HU-16): API nativa de Drag and Drop del
    // navegador, habilitada únicamente cuando el listado está en modo de orden manual
    // (las tarjetas solo traen draggable="true" en ese modo — ver tasks/index.html).
    const tasksList = document.querySelector(".tasks-list");
    const draggableCards = document.querySelectorAll(".task-card[draggable='true']");

    if (tasksList && draggableCards.length > 0) {
        let draggedCard = null;
        let reorderInFlight = false;

        draggableCards.forEach(card => {
            card.addEventListener("dragstart", () => {
                if (reorderInFlight) return;
                draggedCard = card;
                card.classList.add("dragging");
            });

            card.addEventListener("dragend", () => {
                card.classList.remove("dragging");
                draggableCards.forEach(c => c.classList.remove("drag-over"));
            });

            card.addEventListener("dragover", (e) => {
                e.preventDefault();
                if (!draggedCard || draggedCard === card) return;
                card.classList.add("drag-over");
            });

            card.addEventListener("dragleave", () => {
                card.classList.remove("drag-over");
            });

            card.addEventListener("drop", async (e) => {
                e.preventDefault();
                card.classList.remove("drag-over");
                if (!draggedCard || draggedCard === card || reorderInFlight) return;

                // Reordena en el DOM antes de persistir, para feedback visual inmediato
                const cardsBeforeMove = Array.from(tasksList.querySelectorAll(".task-card"));
                const draggedIndex = cardsBeforeMove.indexOf(draggedCard);
                const targetIndex = cardsBeforeMove.indexOf(card);
                if (draggedIndex < targetIndex) {
                    card.after(draggedCard);
                } else {
                    card.before(draggedCard);
                }

                // Persiste el arreglo completo del nuevo orden (Principio V: lote atómico,
                // sin lógica de desplazamiento en el backend)
                reorderInFlight = true;
                const taskIds = Array.from(tasksList.querySelectorAll(".task-card")).map(
                    (c) => parseInt(c.dataset.taskId, 10)
                );

                try {
                    const response = await fetch("/tasks/reorder", {
                        method: "POST",
                        headers: { "Content-Type": "application/json", "Accept": "application/json" },
                        body: JSON.stringify({ task_ids: taskIds }),
                    });
                    if (!response.ok) {
                        throw new Error("No se pudo guardar el nuevo orden");
                    }
                } catch (error) {
                    alert("No se pudo guardar el nuevo orden. Recarga la página e intenta de nuevo.");
                } finally {
                    reorderInFlight = false;
                }
            });
        });
    }
});
