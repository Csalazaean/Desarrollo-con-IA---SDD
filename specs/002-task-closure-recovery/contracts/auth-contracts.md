# Contratos de Endpoints: Recuperación de Acceso (HU-14)

**Blueprint**: `auth_bp` (`/auth`)  
**Cumplimiento**: Principio III (Contrato explícito), Principio VII (Seguridad por defecto, no enumeración de cuentas y no almacenamiento de secretos en texto plano) y Principio VIII (Observabilidad).

---

## 1. Solicitud de Restablecimiento de Contraseña

### 1.1. `POST /auth/forgot-password`
Recibe el correo del usuario que solicita recuperar el acceso y genera el token de restablecimiento si el correo existe, respondiendo siempre de forma neutra para prevenir la enumeración de cuentas.

- **Método**: `POST`
- **Ruta**: `/auth/forgot-password`
- **Autenticación**: Pública (no requiere sesión).
- **Headers**:
  - `Content-Type: application/json` o `application/x-www-form-urlencoded`
  - `Accept: application/json` o `text/html`
- **Payload de Entrada**:
  ```json
  {
    "email": "usuario@ejemplo.com"
  }
  ```

#### Respuestas:

- **`200 OK` (Respuesta Neutra Garantizada)**:
  Tanto si el correo existe como si NO existe en la base de datos, el sistema retorna exactamente la misma respuesta:
  ```json
  {
    "status": "success",
    "message": "Si el correo ingresado coincide con una cuenta activa en el sistema, recibirás un correo con las instrucciones para restablecer tu contraseña."
  }
  ```
  *(En caso HTML: renderiza la vista de confirmación con el mensaje neutro).*
- **`400 Bad Request`**: Formato de correo inválido o campo vacío.
  ```json
  {
    "status": "error",
    "code": "INVALID_EMAIL_FORMAT",
    "message": "Debe proporcionar una dirección de correo electrónico válida"
  }
  ```

---

## 2. Confirmación de Restablecimiento de Contraseña

### 2.1. `GET /auth/reset-password/<string:token>`
Verifica la validez y vigencia del token recibido antes de mostrar el formulario de nueva contraseña.

- **Método**: `GET`
- **Ruta**: `/auth/reset-password/<string:token>`
- **Autenticación**: Pública con token temporal en URL.
- **Parámetro de Ruta**: `token` (cadena URL-safe generada criptográficamente).

#### Respuestas:
- **`200 OK`**: El token es válido y no ha expirado. Renderiza `auth/reset_password.html`.
- **`400 Bad Request`**: Token inexistente, alterado, ya utilizado o expirado. Renderiza vista de error o redirige a `/auth/forgot-password` con mensaje de error:
  *"El enlace de restablecimiento es inválido o ha expirado. Por favor, solicita uno nuevo."*

---

### 2.2. `POST /auth/reset-password/<string:token>`
Procesa el cambio efectivo de contraseña, actualiza el hash de la clave del usuario e invalida de forma inmediata e irreversible el token utilizado.

- **Método**: `POST`
- **Ruta**: `/auth/reset-password/<string:token>`
- **Autenticación**: Pública con token temporal en URL.
- **Headers**:
  - `Content-Type: application/json` o `application/x-www-form-urlencoded`
  - `Accept: application/json` o `text/html`
- **Payload de Entrada**:
  ```json
  {
    "new_password": "NuevaPassword123!",
    "confirm_password": "NuevaPassword123!"
  }
  ```

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  Contraseña actualizada correctamente y token marcado como consumido (`used_at = now()`).
  - JSON:
    ```json
    {
      "status": "success",
      "message": "Tu contraseña ha sido restablecida exitosamente. Ya puedes iniciar sesión con tu nueva contraseña."
    }
    ```
  - HTML: Redirección `302` a `/auth/login` con mensaje flash de éxito.
- **`400 Bad Request`**:
  - Token expirado, ya utilizado o inválido.
  - Las contraseñas no coinciden o la contraseña no cumple la longitud mínima (8 caracteres).
  ```json
  {
    "status": "error",
    "code": "PASSWORD_RESET_FAILED",
    "message": "Las contraseñas no coinciden o el enlace ha caducado"
  }
  ```
