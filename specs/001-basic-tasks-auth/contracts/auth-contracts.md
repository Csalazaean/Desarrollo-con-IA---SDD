# Contratos de Endpoints: Autenticación (HU-12, HU-13)

**Blueprint**: `auth_bp` (`/auth`)  
**Cumplimiento**: Principio III (Contrato explícito entre backend y JavaScript/cliente) y Principio VII (Seguridad por defecto).

---

## 1. Registro de Usuario (`HU-12`)

### 1.1. `POST /auth/register`
Registra una nueva cuenta de usuario en el sistema.

- **Método**: `POST`
- **Ruta**: `/auth/register`
- **Autenticación**: Pública (sin sesión requerida).
- **Headers requeridos**:
  - `Content-Type: application/x-www-form-urlencoded` (Formulario HTML) o `application/json` (API)
- **Payload de Entrada**:
  ```json
  {
    "email": "usuario@ejemplo.com",
    "password": "Password123!"
  }
  ```
- **Validaciones en Backend**:
  - `email`: Obligatorio, formato de correo válido, no registrado previamente.
  - `password`: Obligatoria, longitud mínima de 8 caracteres.

#### Respuestas:
- **`201 Created` / `302 Found` (Éxito)**:
  - Si es HTML: Redirección a `/auth/login` con mensaje flash de confirmación.
  - Si es JSON:
    ```json
    {
      "status": "success",
      "message": "Usuario registrado exitosamente",
      "data": {
        "user_id": 1,
        "email": "usuario@ejemplo.com"
      }
    }
    ```
- **`400 Bad Request` (Error de validación)**:
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "Datos de registro inválidos",
    "errors": {
      "password": "La contraseña debe tener al menos 8 caracteres"
    }
  }
  ```
- **`409 Conflict` (Correo ya existente)**:
  ```json
  {
    "status": "error",
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "El correo electrónico ya se encuentra registrado"
  }
  ```

---

## 2. Inicio de Sesión (`HU-13`)

### 2.1. `POST /auth/login`
Autentica al usuario y crea una sesión segura en el backend.

- **Método**: `POST`
- **Ruta**: `/auth/login`
- **Autenticación**: Pública.
- **Headers requeridos**:
  - `Content-Type: application/x-www-form-urlencoded` o `application/json`
- **Payload de Entrada**:
  ```json
  {
    "email": "usuario@ejemplo.com",
    "password": "Password123!"
  }
  ```

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  - Header: `Set-Cookie: session=<signed_session_cookie>; HttpOnly; SameSite=Lax`
  - Si es HTML: Redirección a `/tasks`.
  - Si es JSON:
    ```json
    {
      "status": "success",
      "message": "Inicio de sesión exitoso",
      "data": {
        "user_id": 1,
        "email": "usuario@ejemplo.com"
      }
    }
    ```
- **`401 Unauthorized` (Credenciales inválidas)**:
  ```json
  {
    "status": "error",
    "code": "INVALID_CREDENTIALS",
    "message": "Correo o contraseña incorrectos"
  }
  ```

---

## 3. Cierre de Sesión (`HU-13`)

### 3.1. `POST /auth/logout`
Destruye la sesión activa del usuario.

- **Método**: `POST`
- **Ruta**: `/auth/logout`
- **Autenticación**: Requiere sesión activa (`session['user_id']`).
- **Payload de Entrada**: Vacío `{}`.

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  - Header: Invalida la cookie de sesión (`session=; Max-Age=0`).
  - Si es HTML: Redirección a `/auth/login`.
  - Si es JSON:
    ```json
    {
      "status": "success",
      "message": "Sesión finalizada exitosamente"
    }
    ```
- **`401 Unauthorized`**: Si se invoca sin sesión activa.
