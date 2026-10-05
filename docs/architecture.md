# Arquitetura do Sistema: Laboratório de Autenticação Multi-Agent

## 1. Visão Geral da Arquitetura

O sistema adota uma arquitetura em camadas orientada a serviços desacoplados (Frontend Single-Page Application + Backend RESTful API + Banco de Dados Relacional), orquestrada em contêineres Docker independentes.

### Stack Tecnológica
- **Frontend**: React 18+ com TypeScript, empacotado via Vite, estilizado com CSS moderno/Tailwind tokens, consumindo a API via Axios com interceptores configurados para controle de sessão.
- **Backend**: Python 3.12+ com FastAPI, utilizando SQLAlchemy 2.0 (modo assíncrono com `asyncpg`), migrações automáticas de banco via Alembic, e validação/serialização estrita com Pydantic v2.
- **Banco de Dados**: PostgreSQL 16 para persistência transacional ACID de usuários, credenciais e sessões de refresh tokens rotativos.
- **Orquestração e Infraestrutura**: Docker e Docker Compose, provendo isolamento de rede, injeção segura de variáveis de ambiente e inicialização facilitada para desenvolvimento e testes.

---

## 2. Diagrama de Contêineres e Topologia

```mermaid
flowchart TD
    subgraph Browser ["Navegador do Usuário (Client)"]
        SPA["React 18 + TypeScript SPA\n(Vite Dev / Nginx)"]
        MemoryState["AuthContext (In-Memory Access Token)"]
        CookieStorage["HttpOnly, Secure Cookie (Refresh Token)"]
    end

    subgraph GoogleIdP ["Google Identity Provider"]
        GoogleGIS["Google Identity Services (OAuth 2.0 / OIDC)"]
    end

    subgraph DockerHost ["Ambiente Docker Compose"]
        subgraph FrontendContainer ["Frontend Container (Porta 5173 / 80)"]
            SPAApp["Vite Dev Server / Static Assets"]
        end

        subgraph BackendContainer ["Backend Container (Porta 8000)"]
            FastAPIServer["FastAPI Application (Uvicorn Async)"]
            AuthRouter["Routers: /auth, /protected, /users"]
            AuthService["AuthService & GoogleOAuthService"]
            TokenService["TokenService (JWT & Refresh Token Rotation)"]
            SecurityLayer["Security Layer: Argon2id, CORS, RateLimit"]
            SQLAlchemyAsync["SQLAlchemy 2.0 Async Engine"]
        end

        subgraph DatabaseContainer ["Database Container (Porta 5432)"]
            PostgresDB[("PostgreSQL 16 DB\n(Tabelas: users, refresh_tokens, audit_logs)")]
        end
    end

    Browser -->|HTTP/HTTPS :5173| FrontendContainer
    SPA -->|SDK Sign-In| GoogleGIS
    GoogleGIS -.->|Retorna ID Token / Credential| SPA
    SPA -->|Chamadas REST API :8000 com Bearer Token e Cookies| FastAPIServer
    FastAPIServer -->|Validação de ID Token do Google via JWKS/Certs| GoogleIdP
    FastAPIServer -->|Queries Assíncronas via asyncpg| PostgresDB
```

---

## 3. Diagramas de Sequência e Fluxos de Autenticação

### 3.1. Fluxo de Cadastro e Login com E-mail e Senha

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário
    participant React as React Frontend (SPA)
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB

    %% Cadastro
    Note over User, DB: Fluxo de Cadastro (Sign-up)
    User->>React: Preenche Nome, E-mail, Senha
    React->>API: POST /api/v1/auth/register (payload JSON)
    API->>API: Valida formato de e-mail e força da senha
    API->>DB: Verifica existência de e-mail
    alt E-mail já cadastrado
        DB-->>API: Usuário encontrado
        API-->>React: 409 Conflict ("E-mail já registrado")
        React-->>User: Exibe mensagem de erro amigável
    else E-mail livre
        API->>API: Gera Hash da senha com Argon2id
        API->>DB: Salva novo registro na tabela `users`
        DB-->>API: Usuário criado (id, email, created_at)
        API-->>React: 201 Created (UserResponse sem dados sensíveis)
        React-->>User: Redireciona para tela de login ou autentica
    end

    %% Login
    Note over User, DB: Fluxo de Login (Sign-in)
    User->>React: Informa E-mail e Senha
    React->>API: POST /api/v1/auth/login {email, password}
    API->>DB: Busca usuário ativo pelo e-mail
    alt Usuário não encontrado ou senha inválida
        API->>API: Executa dummy hash verification (mitigar timing attack)
        API-->>React: 401 Unauthorized ("Credenciais inválidas")
        React-->>User: Exibe erro genérico
    else Credenciais válidas
        API->>API: Gera Access Token (JWT, exp: 15m)
        API->>API: Gera Refresh Token aleatório (64 bytes) e Family ID
        API->>DB: Salva hash SHA-256 do Refresh Token com exp: 7d
        API-->>React: 200 OK + Set-Cookie (Refresh Token; HttpOnly; SameSite=Lax; Secure) + JSON {access_token, token_type, expires_in, user}
        React->>React: Salva Access Token em memória (AuthContext)
        React-->>User: Redireciona para o Dashboard protegido
    end
```

---

### 3.2. Fluxo de Autenticação Federada com Google (OIDC / OAuth 2.0)

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário
    participant React as React Frontend
    participant Google as Google Identity Services
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB

    User->>React: Clica no botão "Continuar com o Google"
    React->>Google: Abre prompt oficial do Google Sign-In
    User->>Google: Seleciona conta Google e concede permissão
    Google-->>React: Retorna Google ID Token (`credential` JWT assinado)
    React->>API: POST /api/v1/auth/google {id_token: credential}
    API->>Google: Valida assinatura do ID Token contra chaves públicas (JWKS do Google)
    API->>API: Valida audience (Client ID), issuer e expiration
    API->>DB: Busca usuário pelo `google_sub` ou `email`
    alt Usuário não existe
        API->>DB: Cria novo usuário (email, name, avatar, google_sub, is_oauth_only=True)
    else Usuário já existe
        API->>DB: Atualiza google_sub e avatar se necessário
    end
    API->>API: Emite par de tokens do sistema (Access Token + Refresh Token)
    API->>DB: Persiste Refresh Token na família de tokens
    API-->>React: 200 OK + Set-Cookie (Refresh Token) + JSON {access_token, user}
    React->>React: Armazena Access Token no AuthContext
    React-->>User: Acesso liberado ao Dashboard
```

---

### 3.3. Rotação de Refresh Token e Silent Refresh

```mermaid
sequenceDiagram
    autonumber
    participant React as React Frontend
    participant Axios as Interceptor Axios (Client)
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB

    Note over React, DB: Acesso normal com Access Token expirado
    React->>Axios: Requisição para GET /api/v1/protected/dashboard-data
    Axios->>API: GET /api/v1/protected/dashboard-data (Header: Authorization: Bearer <expirado>)
    API->>API: Valida assinatura do JWT -> Detecta 'token expired'
    API-->>Axios: 401 Unauthorized {detail: "Token has expired", code: "TOKEN_EXPIRED"}

    Note over Axios, API: Interceptor captura o 401 e enfileira requisições
    Axios->>API: POST /api/v1/auth/refresh (Cookie: refresh_token=<Token_A>)
    API->>DB: Localiza Token_A pelo hash SHA-256
    alt Token válido e não revogado
        API->>DB: Marca Token_A como 'revoked = true' e 'used_at = now()'
        API->>API: Cria Token_B (novo Refresh Token) associado à mesma Family_ID
        API->>API: Cria novo Access Token (JWT, 15m)
        API->>DB: Insere Token_B no banco
        API-->>Axios: 200 OK + Set-Cookie (refresh_token=<Token_B>) + JSON {access_token}
        Axios->>Axios: Atualiza Access Token no AuthContext
        Axios->>API: Repete GET /api/v1/protected/dashboard-data com novo Bearer
        API-->>Axios: 200 OK (Dados do Dashboard)
        Axios-->>React: Entrega resposta sem intervenção do usuário
    end
```

---

### 3.4. Detecção de Roubo de Token (Reuso de Refresh Token)

```mermaid
sequenceDiagram
    autonumber
    actor Attacker as Atacante
    actor LegitimateUser as Usuário Legítimo
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB

    Note over Attacker, DB: Cenário de Ataque: Atacante obteve cópia do Token_A antigo
    Attacker->>API: POST /api/v1/auth/refresh (Cookie: refresh_token=<Token_A>)
    API->>DB: Consulta hash do Token_A
    DB-->>API: Retorna Token_A com status 'revoked = true' (já consumido anteriormente!)
    Note over API, DB: ALERTA DE SEGURANÇA: Tentativa de Replay/Reuso detectada!
    API->>DB: REVOGA TODA A FAMÍLIA DE TOKENS (family_id) deste usuário imediatamente!
    API->>DB: Registra evento em `audit_logs` (Security Incident: Token Reuse Attempt)
    API-->>Attacker: 401 Unauthorized ("Sessão comprometida. Faça login novamente.")

    Note over LegitimateUser, DB: O usuário legítimo também é protegido
    LegitimateUser->>API: Tenta requisição com seu token atual
    API-->>LegitimateUser: 401 Unauthorized (todos os tokens da família foram desautorizados)
    LegitimateUser->>LegitimateUser: Forçado a realizar novo login com credenciais
```

---

### 3.5. Fluxo de Logout Seguro

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário
    participant React as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB

    User->>React: Clica em "Sair" (Logout)
    React->>API: POST /api/v1/auth/logout (Cookie: refresh_token)
    API->>DB: Marca o Refresh Token como 'revoked = true'
    API-->>React: 200 OK + Set-Cookie (refresh_token=""; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT)
    React->>React: Limpa Access Token em memória (AuthContext = null)
    React-->>User: Redireciona para /login
```

---

## 4. Modelo de Dados (DER)

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : has
    USERS ||--o{ AUDIT_LOGS : generates

    USERS {
        uuid id PK "Identificador único do usuário"
        string email UK "E-mail único normalizado"
        string hashed_password "Hash Argon2id (null se for apenas OAuth)"
        string full_name "Nome completo do usuário"
        string avatar_url "URL do avatar do usuário"
        string google_sub UK "Subject ID único do Google OIDC"
        boolean is_active "Status da conta (ativo/inativo)"
        boolean is_oauth_only "Indica se a conta só usa login social"
        datetime created_at "Data e hora de criação"
        datetime updated_at "Data e hora da última alteração"
    }

    REFRESH_TOKENS {
        uuid id PK "Identificador único da sessão/token"
        uuid user_id FK "Referência ao usuário proprietário"
        string token_hash UK "Hash SHA-256 do refresh token emitido"
        uuid family_id "Identificador da cadeia/família de rotação"
        boolean revoked "Indica se o token foi revogado/consumido"
        datetime expires_at "Data de expiração do refresh token (ex: 7 dias)"
        datetime created_at "Data de emissão"
        datetime used_at "Data e hora em que foi consumido na rotação"
        string user_agent "Identificação do navegador/dispositivo"
        string ip_address "IP de origem da emissão"
    }

    AUDIT_LOGS {
        uuid id PK "ID do log"
        uuid user_id FK "Usuário associado (opcional)"
        string event_type "LOGIN_SUCCESS, LOGIN_FAILED, TOKEN_REUSE_DETECTED, LOGOUT"
        string ip_address "Endereço IP do cliente"
        string user_agent "Dispositivo do cliente"
        json metadata "Detalhes contextuais do evento"
        datetime created_at "Data e hora do evento"
    }
```

---

## 5. Estrutura de Diretórios Recomendada

```
agents-test-auth/
├── .agents/                    # Definições de Agentes e Skills Antigravity
│   ├── agents/
│   │   ├── backend/agent.md
│   │   ├── frontend/agent.md
│   │   ├── lead/agent.md
│   │   └── security/agent.md
│   └── skills/
│       ├── backend-engineering/SKILL.MD
│       ├── frontend-design/SKILL.md
│       └── security-review/SKILL.md
├── docs/                       # Especificações e Fonte da Verdade do Sistema
│   ├── requirements.md
│   ├── architecture.md
│   ├── api-contract.md
│   └── decisions.md
├── backend/                    # Aplicação FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── auth.py
│   │   │       │   └── protected.py
│   │   │       └── router.py
│   │   ├── core/
│   │   │   ├── config.py       # Configurações com Pydantic Settings
│   │   │   ├── database.py     # Engine assíncrono SQLAlchemy e sessionmaker
│   │   │   ├── security.py     # Argon2id, JWT creation, claims
│   │   │   └── exceptions.py   # Handlers de exceção RFC 7807
│   │   ├── models/             # Modelos SQLAlchemy ORM
│   │   │   ├── user.py
│   │   │   ├── token.py
│   │   │   └── audit.py
│   │   ├── schemas/            # Schemas Pydantic v2 (DTOs)
│   │   │   ├── user.py
│   │   │   ├── token.py
│   │   │   └── auth.py
│   │   ├── services/           # Lógica de negócio pura
│   │   │   ├── auth_service.py
│   │   │   ├── token_service.py
│   │   │   └── google_oauth.py
│   │   └── main.py             # Instância do FastAPI, CORS, middlewares
│   ├── alembic/                # Migrações de banco
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/                  # Suíte de testes Pytest
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_tokens.py
│   │   └── test_protected.py
│   ├── Dockerfile
│   ├── pyproject.toml / requirements.txt
│   └── alembic.ini
├── frontend/                   # Aplicação React + TypeScript (Vite)
│   ├── src/
│   │   ├── assets/
│   │   ├── components/         # Componentes UI reutilizáveis (Card, Button, Input, Navbar)
│   │   ├── context/            # AuthContext e Provider
│   │   ├── hooks/              # useAuth, useProtectedApi
│   │   ├── pages/              # Login, Register, Dashboard, NotFound
│   │   ├── services/           # Axios instance, interceptors, chamadas de API
│   │   ├── types/              # Definições TypeScript dos contratos da API
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── docker-compose.yml          # Orquestração do Backend, Frontend e Postgres
├── .env.example                # Template de variáveis de ambiente do projeto
└── AGENTS.md                   # Diretrizes e governança de agentes
```

---

## 6. Governança de Rede e Contêineres Docker

- **Rede `auth-network`**: Rede bridge interna isolando o banco de dados das portas externas.
- **Portas Expostas no Host**:
  - `5173`: Frontend (SPA React).
  - `8000`: Backend (FastAPI).
  - `5432`: PostgreSQL (apenas para debug local, se necessário).
- **Healthchecks**: O backend depende do banco saudável (`condition: service_healthy`) antes de executar as migrações do Alembic e iniciar o Uvicorn.
