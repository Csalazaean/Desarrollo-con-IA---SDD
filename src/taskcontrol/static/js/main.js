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

    // 4. Confirmación previa para acciones destructivas o irreversibles (eliminar, reabrir)
    const confirmForms = document.querySelectorAll("form[data-confirm]");
    confirmForms.forEach(form => {
        form.addEventListener("submit", (e) => {
            if (!window.confirm(form.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });
});
