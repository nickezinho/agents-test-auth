# Requisitos do Sistema: Laboratório de Autenticação Multi-Agent

## 1. Visão Geral e Objetivos

O **Laboratório de Autenticação** é uma aplicação completa de autenticação e autorização moderna, desenvolvida para demonstrar e validar boas práticas de segurança, engenharia de software e um fluxo colaborativo de desenvolvimento multi-agente.

O sistema provê controle de identidade completo, abrangendo:
1. Autenticação tradicional baseada em credenciais (E-mail e Senha) com hashing moderno.
2. Autenticação federada com Google Identity Services (OAuth 2.0 / OpenID Connect).
3. Sessões com JSON Web Tokens (JWT) adotando o padrão Access Token de curta duração e Refresh Token rotativo persistido.
4. Encerramento seguro de sessão (Logout) com revogação ativa no banco de dados.
5. Proteção de rotas ponta a ponta (Backend via dependências FastAPI e Frontend via rotas protegidas em React).
6. Totalmente containerizado via Docker e Docker Compose, com banco relacional PostgreSQL e suíte automatizada de testes.

---

## 2. Personas e Atores

- **Usuário Visitante (Anônimo)**: Pode visualizar telas públicas de login, registro e documentação de API; pode se cadastrar ou autenticar com credenciais locais ou Google.
- **Usuário Autenticado**: Possui conta ativa; pode acessar rotas protegidas, consultar seu perfil, renovar tokens e encerrar sua sessão.
- **Administrador / Auditing**: Perfil opcional previsto para visualizar métricas e histórico de sessões/dispositivos conectados.

---

## 3. Requisitos Funcionais (RF)

### RF-01: Cadastro de Usuário Local (Sign-up)
- **Descrição**: O sistema deve permitir que novos usuários criem uma conta informando nome completo, endereço de e-mail válido e senha segura.
- **Critérios de Aceite**:
  - O e-mail deve ser normalizado (lowercase, trim) e único na base de dados.
  - A senha deve cumprir a política mínima: mínimo de 8 caracteres, contendo pelo menos uma letra maiúscula, uma minúscula, um número e um caractere especial.
  - A senha em texto plano **nunca** deve ser persistida ou logada; o hash deve ser gerado utilizando Argon2id.
  - Em caso de e-mail duplicado, a API deve retornar `409 Conflict` com mensagem descritiva sem vazar detalhes sensíveis.
  - Após o cadastro com sucesso, o usuário é salvo com status ativo e pode realizar login imediatamente.

### RF-02: Autenticação Local (Sign-in)
- **Descrição**: O usuário deve poder se autenticar enviando e-mail e senha.
- **Critérios de Aceite**:
  - Validação de formato de e-mail e presença de senha antes de consultar o banco.
  - Comparação de senha com algoritmo time-constant (Argon2id) para prevenir ataques de timing.
  - Retorno em caso de credenciais inválidas: `401 Unauthorized` genérico ("Credenciais inválidas") para evitar enumeração de usuários.
  - Em caso de sucesso: emissão de Access Token (JWT retornado no payload JSON) e Refresh Token (token opaco criptográfico armazenado em Cookie `HttpOnly`, `Secure`, `SameSite=Lax`).
  - Registro de timestamp do último login e IP/User-Agent do cliente.

### RF-03: Autenticação Federada Google (OAuth 2.0 / OIDC)
- **Descrição**: O usuário deve poder se autenticar ou cadastrar utilizando sua conta Google.
- **Critérios de Aceite**:
  - O frontend utiliza o Google Identity Services (GIS / Google Sign-In) para obter o `credential` (ID Token JWT assinado pelo Google).
  - O backend recebe o ID Token no endpoint `/api/v1/auth/google`, valida a assinatura criptográfica, emissor (`accounts.google.com` ou `https://accounts.google.com`), `audience` (Client ID) e data de expiração via biblioteca oficial do Google (`google-auth`).
  - Se o usuário já existir por `google_sub` ou e-mail correspondente: vincula o `google_sub` e atualiza nome/avatar caso necessário.
  - Se for o primeiro acesso: cria o usuário automaticamente com senha desabilitada (`hashed_password = null`) e flag `is_oauth_only = true`.
  - Gera os tokens da aplicação (Access e Refresh tokens proprietários do sistema) exatamente como no login local.

### RF-04: Gestão do Ciclo de Vida de Tokens (Access & Refresh)
- **Descrição**: O sistema deve gerenciar dois tipos de tokens com propósitos distintos.
- **Critérios de Aceite**:
  - **Access Token**: JWT assinado com algoritmo assimétrico ou HMAC-SHA256 (HS256 com chave >= 256 bits), contendo claims padrão: `sub` (User ID), `exp` (15 minutos), `iat`, `jti` (JWT ID único) e `token_type: "access"`.
  - **Refresh Token**: Token criptograficamente seguro (UUIDv4 ou hash aleatório de 64 bytes), com validade de 7 dias. O hash do token (SHA-256) é salvo na tabela `refresh_tokens` associado ao `user_id`, data de expiração, status de revogação e família de tokens (`family_id`).
  - O cliente envia o Access Token no header `Authorization: Bearer <token>` para rotas protegidas.

### RF-05: Rotação Automática de Refresh Token (Token Rotation) e Detecção de Reuso
- **Descrição**: Ao solicitar renovação de token, o refresh token utilizado deve ser invalidado e substituído por um novo.
- **Critérios de Aceite**:
  - Cada refresh gera um novo par (novo Access Token + novo Refresh Token).
  - O refresh token anterior é marcado como consumido/revogado.
  - **Detecção de Reuso (Roubo de Sessão)**: Se um refresh token já consumido ou revogado for enviado novamente, o sistema detecta violação de segurança e **revoga imediatamente toda a família de tokens (`family_id`) do usuário**, forçando reautenticação em todos os dispositivos relacionados.

### RF-06: Renovação Silenciosa de Sessão (Silent Refresh)
- **Descrição**: O frontend deve renovar o Access Token antes de sua expiração sem interromper a navegação do usuário.
- **Critérios de Aceite**:
  - Endpoint `POST /api/v1/auth/refresh` lê o Refresh Token diretamente do Cookie `HttpOnly`.
  - Interceptor HTTP no frontend identifica respostas `401 Unauthorized` de tokens expirados e enfileira requisições simultâneas enquanto executa o refresh (prevenindo *race conditions* de múltiplos refreshes concorrentes).
  - Atualiza o Access Token em memória e repete as requisições pendentes.

### RF-07: Encerramento de Sessão (Logout)
- **Descrição**: O usuário deve poder encerrar sua sessão ativa a qualquer momento.
- **Critérios de Aceite**:
  - Endpoint `POST /api/v1/auth/logout`.
  - O backend invalida o refresh token atual no banco de dados (marcando `revoked = true`).
  - O backend instrui o navegador a limpar o cookie de refresh token emitindo header `Set-Cookie` com `Max-Age=0` e data de expiração no passado.
  - O frontend descarta o Access Token mantido em memória e redireciona o usuário para a tela de login.

### RF-08: Autorização e Proteção de Rotas
- **Descrição**: Endpoints e páginas privadas devem ser inacessíveis a usuários não autenticados.
- **Critérios de Aceite**:
  - No Backend: dependência FastAPI (`get_current_user`) extrai e valida o Access Token, rejeitando requisições sem token, com token expirado ou com assinatura inválida com `401 Unauthorized`.
  - No Frontend: componente `ProtectedRoute` do React Router verifica o estado de autenticação; se não autenticado, redireciona para `/login` preservando a rota de origem (`returnUrl`).

### RF-09: Perfil do Usuário Autenticado (`/api/v1/auth/me`)
- **Descrição**: O usuário autenticado deve poder obter os dados de seu perfil e da sessão atual.
- **Critérios de Aceite**:
  - Retorna `id`, `email`, `full_name`, `avatar_url`, `is_active`, `created_at` e método de autenticação utilizado (`local` ou `google`).
  - Dados sensíveis como senhas ou hashes jamais são expostos.

### RF-10: Painel de Demonstração (Dashboard Protegido)
- **Descrição**: Interface que evidencia o estado da autenticação, o payload decodificado do Access Token, o tempo restante de vida do token (countdown) e permite testar chamadas protegidas e forçar refresh/logout.

---

## 4. Requisitos Não-Funcionais (RNF)

| Identificador | Categoria | Descrição | Métrica / Critério de Sucesso |
| :--- | :--- | :--- | :--- |
| **RNF-01** | **Segurança** | Armazenamento de credenciais locais com função de derivação de chave resistente a GPU/ASIC. | Uso obrigatório de **Argon2id** (m=65536, t=3, p=4) ou Bcrypt (fator de custo >= 12). |
| **RNF-02** | **Segurança** | Mitigação de vulnerabilidades XSS e CSRF para tokens. | Refresh token confinado em cookie `HttpOnly`, `SameSite=Lax/Strict`, `Secure` (em prod) e `Path=/api/v1/auth`. Access token em memória JavaScript. |
| **RNF-03** | **Performance** | Latência de resposta nas validações de rota protegida. | Tempo médio de processamento do middleware de validação JWT < 5ms (validação in-memory sem roundtrip ao banco). |
| **RNF-04** | **Concorrência** | Suporte a chamadas assíncronas concorrentes de refresh no cliente. | Implementação de Mutex / Fila no interceptor HTTP do frontend para que apenas uma requisição de refresh seja despachada por vez. |
| **RNF-05** | **Portabilidade** | Empacotamento e execução padronizados em qualquer ambiente. | Containers Docker para Backend, Frontend e PostgreSQL orquestrados via `docker-compose up` com um único comando. |
| **RNF-06** | **Qualidade de Código** | Cobertura de testes automatizados unitários e de integração. | Cobertura mínima de 85% no backend (Pytest) com banco real de testes e testes de componentes/hooks no frontend (Vitest). |
| **RNF-07** | **Segurança de Rede** | Controle de Origem Cruzada (CORS). | Backend configurado com CORS estrito via `CORSMiddleware`, permitindo apenas origens autorizadas com `allow_credentials=True`. |
| **RNF-08** | **Proteção contra Brute Force** | Rate Limiting em rotas críticas de autenticação. | Limite de tentativas no `/login`, `/register` e `/refresh` (ex: máx. 5 requisições por minuto por IP via SlowAPI / Redis ou in-memory). |

---

## 5. Regras de Negócio (RN)

- **RN-01 (Unicidade de Identidade)**: O endereço de e-mail é o identificador único universal de um usuário. Se um usuário registrar-se localmente com `user@empresa.com` e posteriormente fizer login com Google com o mesmo e-mail, as contas devem ser vinculadas de forma segura.
- **RN-02 (Contas OAuth Estritas)**: Usuários criados exclusivamente via Google não possuem senha local cadastrada. Se tentarem login por senha, o sistema deve orientá-los a entrar via Google ou solicitar definição de senha através de fluxo próprio.
- **RN-03 (Expiração Rígida de Tokens)**: Tokens expirados são rejeitados sumariamente. Não há tolerância de tempo (*clock skew* máximo de 30 segundos aceitável apenas para sincronismo de relógio).
- **RN-04 (Invalidação Imediata de Sessão)**: O logout invalida explicitamente o refresh token no banco de dados. Um refresh token revogado não pode ser reutilizado sob hipótese alguma.
- **RN-05 (Detecção de Anomalia de Reuso)**: Quando um refresh token já revogado for apresentado para novo refresh, a aplicação deve assumir comprometimento do token e revogar todas as sessões filhas e pai pertencentes àquela `family_id`.

---

## 6. Matriz de Rastreabilidade

| Requisito | Componente Backend | Componente Frontend | Testes Automatizados |
| :--- | :--- | :--- | :--- |
| **RF-01** (Cadastro) | `POST /api/v1/auth/register`, `UserService`, `User` model | `RegisterPage`, `RegisterForm` | `test_register_success`, `test_register_duplicate_email`, `test_password_policy` |
| **RF-02** (Login Local) | `POST /api/v1/auth/login`, `AuthService`, Argon2id | `LoginPage`, `LoginForm` | `test_login_success`, `test_login_invalid_password`, `test_login_user_not_found` |
| **RF-03** (Google OAuth) | `POST /api/v1/auth/google`, `GoogleOAuthService` | `GoogleLoginButton`, Google GIS SDK | `test_google_auth_new_user`, `test_google_auth_existing_user`, `test_google_invalid_token` |
| **RF-04/05/06** (Refresh/Rotation) | `POST /api/v1/auth/refresh`, `TokenService`, `RefreshToken` model | `useAuth`, Axios Interceptor de refresh | `test_refresh_token_rotation`, `test_refresh_token_reuse_detection`, `test_concurrent_refreshes` |
| **RF-07** (Logout) | `POST /api/v1/auth/logout`, `TokenService` | `LogoutButton`, `useAuth.logout()` | `test_logout_revokes_token`, `test_logout_clears_cookie` |
| **RF-08** (Rotas Protegidas) | `get_current_user` dependency, `/api/v1/protected/*` | `ProtectedRoute`, React Router | `test_protected_route_authenticated`, `test_protected_route_unauthenticated` |
| **RF-09** (Perfil /me) | `GET /api/v1/auth/me` | `ProfileCard`, `useAuth.user` | `test_get_current_user_profile` |
