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
});
