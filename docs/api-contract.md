# Contrato da API REST: Laboratório de Autenticação

## 1. Padrões Globais da API

- **Base URL**: `http://localhost:8000/api/v1`
- **Content-Type**: `application/json; charset=utf-8` para requisições e respostas com corpo.
- **Autenticação de Rotas Protegidas**:
  - Header HTTP: `Authorization: Bearer <access_token>`
- **Transporte de Refresh Token**:
  - Cookie HTTP: `refresh_token`
  - Atributos obrigatórios do cookie: `HttpOnly; Path=/api/v1/auth; SameSite=Lax; Secure` (em produção).
- **Formato Padrão de Resposta de Erro**:
  Todas as respostas de erro (4xx e 5xx) seguem a estrutura padronizada:
  ```json
  {
    "code": "ERROR_CODE_STRING",
    "detail": "Mensagem explicativa para o usuário ou desenvolvedor.",
    "errors": [
      {
        "field": "nome_do_campo",
        "message": "Descrição específica da validação"
      }
    ],
    "timestamp": "2026-10-05T16:30:00Z"
  }
  ```

---

## 2. Tabela Resumo dos Endpoints

| Método | Rota | Autenticação Requerida | Descrição |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Nenhuma (Pública) | Cadastro de novo usuário local com e-mail e senha |
| `POST` | `/api/v1/auth/login` | Nenhuma (Pública) | Autenticação por e-mail e senha; emite tokens |
| `POST` | `/api/v1/auth/google` | Nenhuma (Pública) | Autenticação federada via Google ID Token |
| `POST` | `/api/v1/auth/refresh` | Cookie `refresh_token` | Rotação e emissão de novo Access e Refresh token |
| `POST` | `/api/v1/auth/logout` | Opcional Bearer + Cookie | Revogação de sessão ativa e limpeza de cookies |
| `GET`  | `/api/v1/auth/me` | Bearer Token | Obtém dados do perfil do usuário autenticado |
| `GET`  | `/api/v1/protected/dashboard` | Bearer Token | Retorna métricas e dados de teste de rota protegida |
| `GET`  | `/api/v1/health` | Nenhuma (Pública) | Liveness e readiness probe da aplicação e banco |

---

## 3. Especificação Detalhada dos Endpoints

### 3.1. `POST /api/v1/auth/register`
Cria uma nova conta de usuário com e-mail e senha.

#### Request Body
```json
{
  "email": "user@exemplo.com",
  "password": "SenhaForte@2026",
  "full_name": "João da Silva"
}
```
- `email`: string, formato de e-mail RFC 5322 válido, obrigatório.
- `password`: string, mín. 8 caracteres, obrigatório, deve conter ao menos: 1 maiúscula, 1 minúscula, 1 número e 1 caractere especial.
- `full_name`: string, mín. 2 e máx. 100 caracteres, obrigatório.

#### Respostas
- **`201 Created`**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "user@exemplo.com",
    "full_name": "João da Silva",
    "avatar_url": null,
    "is_active": true,
    "created_at": "2026-10-05T16:30:00Z"
  }
  ```
- **`400 Bad Request`**: Dados de entrada mal formatados.
- **`409 Conflict`**: E-mail já registrado.
  ```json
  {
    "code": "EMAIL_ALREADY_EXISTS",
    "detail": "Já existe uma conta associada a este endereço de e-mail.",
    "timestamp": "2026-10-05T16:30:00Z"
  }
  ```
- **`422 Unprocessable Entity`**: Validação de senha ou campos violada.

---

### 3.2. `POST /api/v1/auth/login`
Autentica o usuário com credenciais locais e inicializa a sessão.

#### Request Body
```json
{
  "email": "user@exemplo.com",
  "password": "SenhaForte@2026"
}
```

#### Respostas
- **`200 OK`**:
  - **Headers**:
    `Set-Cookie: refresh_token=rt_9f8d7c6b5a4...; Path=/api/v1/auth; HttpOnly; SameSite=Lax; Max-Age=604800`
  - **Body**:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "token_type": "Bearer",
      "expires_in": 900,
      "user": {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "email": "user@exemplo.com",
        "full_name": "João da Silva",
        "avatar_url": null,
        "is_active": true
      }
    }
    ```
- **`401 Unauthorized`**: Credenciais incorretas ou conta inativa.
  ```json
  {
    "code": "INVALID_CREDENTIALS",
    "detail": "E-mail ou senha inválidos.",
    "timestamp": "2026-10-05T16:30:00Z"
  }
  ```
- **`429 Too Many Requests`**: Bloqueio temporário por excesso de tentativas incorretas.

---

### 3.3. `POST /api/v1/auth/google`
Autentica ou cadastra o usuário através de um Google ID Token (OIDC).

#### Request Body
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
}
```
- `id_token`: string JWT assinado pelo Google Identity Services, obrigatório.

#### Respostas
- **`200 OK`**:
  - **Headers**:
    `Set-Cookie: refresh_token=rt_9f8d7c6b5a4...; Path=/api/v1/auth; HttpOnly; SameSite=Lax; Max-Age=604800`
  - **Body**: Idêntico ao retorno do login local (`access_token`, `token_type`, `expires_in`, `user`).
- **`400 Bad Request`**: Token ausente ou token formatado incorretamente.
- **`401 Unauthorized`**: Token do Google com assinatura inválida, expirado ou audience incorreta.
  ```json
  {
    "code": "GOOGLE_AUTH_FAILED",
    "detail": "Token de autenticação do Google inválido ou expirado.",
    "timestamp": "2026-10-05T16:30:00Z"
  }
  ```

---

### 3.4. `POST /api/v1/auth/refresh`
Efetua a rotação do Refresh Token e emite um novo Access Token.

#### Request Headers / Cookies
- **Cookie**: `refresh_token=rt_9f8d7c6b5a4...` (enviado automaticamente pelo navegador se `credentials: 'include'`).

#### Respostas
- **`200 OK`**:
  - **Headers**:
    `Set-Cookie: refresh_token=rt_novo_hash_rotacionado...; Path=/api/v1/auth; HttpOnly; SameSite=Lax; Max-Age=604800`
  - **Body**:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIs...",
      "token_type": "Bearer",
      "expires_in": 900
    }
    ```
- **`401 Unauthorized`**: Cookie ausente, token revogado, expirado ou detecção de reuso.
  ```json
  {
    "code": "REFRESH_TOKEN_INVALID",
    "detail": "Sessão inválida ou expirada. Efetue login novamente.",
    "timestamp": "2026-10-05T16:30:00Z"
  }
  ```

---

### 3.5. `POST /api/v1/auth/logout`
Revoga o refresh token no banco de dados e limpa os cookies de sessão.

#### Request Headers / Cookies
- **Cookie**: `refresh_token=rt_...`
- **Header**: `Authorization: Bearer <access_token>` (opcional, se presente valida o contexto do usuário).

#### Respostas
- **`200 OK`**:
  - **Headers**:
    `Set-Cookie: refresh_token=; Path=/api/v1/auth; HttpOnly; SameSite=Lax; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT`
  - **Body**:
    ```json
    {
      "message": "Sessão encerrada com sucesso."
    }
    ```

---

### 3.6. `GET /api/v1/auth/me`
Retorna os dados detalhados do usuário autenticado no token atual.

#### Request Headers
- `Authorization: Bearer <access_token>` (obrigatório).

#### Respostas
- **`200 OK`**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "user@exemplo.com",
    "full_name": "João da Silva",
    "avatar_url": "https://lh3.googleusercontent.com/...",
    "is_active": true,
    "is_oauth_only": false,
    "created_at": "2026-10-05T16:30:00Z",
    "updated_at": "2026-10-05T16:30:00Z"
  }
  ```
- **`401 Unauthorized`**: Token expirado, malformado ou ausente.

---

### 3.7. `GET /api/v1/protected/dashboard`
Endpoint de teste de rota protegida que simula dados sensíveis do painel do usuário.

#### Request Headers
- `Authorization: Bearer <access_token>` (obrigatório).

#### Respostas
- **`200 OK`**:
  ```json
  {
    "status": "success",
    "message": "Acesso concedido à área restrita.",
    "session_info": {
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "email": "user@exemplo.com",
      "token_issued_at": "2026-10-05T16:30:00Z",
      "token_expires_at": "2026-10-05T16:45:00Z",
      "seconds_until_expiry": 845
    },
    "metrics": {
      "total_logins": 12,
      "last_login_ip": "192.168.1.100",
      "active_sessions_count": 2
    }
  }
  ```
- **`401 Unauthorized`**: Token ausente ou inválido.

---

### 3.8. `GET /api/v1/health`
Health check para monitoramento de liveness e readiness de contêineres.

#### Respostas
- **`200 OK`**:
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "timestamp": "2026-10-05T16:30:00Z"
  }
  ```
- **`503 Service Unavailable`**: Caso a conexão com o PostgreSQL falhe.

---

## 4. Tipos TypeScript Compartilhados (Frontend & Backend Contract)

Para assegurar total coerência entre as equipes e agentes, os seguintes tipos TypeScript são a referência contratual:

```typescript
export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  is_active: boolean;
  is_oauth_only?: boolean;
  created_at?: string;
}

export interface AuthSuccessResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface TokenRefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiErrorResponse {
  code: string;
  detail: string;
  errors?: Array<{ field: string; message: string }>;
  timestamp: string;
}

export interface DashboardDataResponse {
  status: string;
  message: string;
  session_info: {
    user_id: string;
    email: string;
    token_issued_at: string;
    token_expires_at: string;
    seconds_until_expiry: number;
  };
  metrics: {
    total_logins: number;
    last_login_ip: string;
    active_sessions_count: number;
  };
}
```
