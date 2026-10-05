# Registro de Decisões de Arquitetura (ADRs): Laboratório de Autenticação

Este documento registra as decisões técnicas, arquiteturais e de segurança adotadas para o projeto, explicitando o contexto, as ambiguidades identificadas, as alternativas avaliadas e as justificativas técnicas.

---

## Índice das Decisões

- [ADR-001: Estratégia de Armazenamento de Tokens no Cliente](#adr-001-estratégia-de-armazenamento-de-tokens-no-cliente)
- [ADR-002: Rotação de Refresh Tokens e Mitigação de Reuso](#adr-002-rotação-de-refresh-tokens-e-mitigação-de-reuso)
- [ADR-003: Algoritmo Criptográfico para Hashing de Senhas](#adr-003-algoritmo-criptográfico-para-hashing-de-senhas)
- [ADR-004: Fluxo de Integração com Google Identity (OAuth 2.0 / OIDC)](#adr-004-fluxo-de-integração-com-google-identity-oauth-20--oidc)
- [ADR-005: Gestão de Concorrência no Refresh Silencioso (Axios Queue)](#adr-005-gestão-de-concorrência-no-refresh-silencioso-axios-queue)
- [ADR-006: Stack de Persistência Assíncrona no Backend](#adr-006-stack-de-persistência-assíncrona-no-backend)
- [ADR-007: Gestão do Esquema de Banco de Dados com Alembic](#adr-007-gestão-do-esquema-de-banco-de-dados-com-alembic)
- [ADR-008: Política de CORS e Cookies Cross-Origin em Desenvolvimento](#adr-008-política-de-cors-e-cookies-cross-origin-em-desenvolvimento)

---

### ADR-001: Estratégia de Armazenamento de Tokens no Cliente

- **Status**: Aceito
- **Contexto**:
  Aplicações Single-Page (SPA) necessitam reter o estado de autenticação entre requisições. O armazenamento de tokens no navegador envolve trade-offs críticos de segurança:
  - Armazenar ambos os tokens no `localStorage` expõe a sessão a roubo irrecuperável em caso de qualquer brecha de XSS (Cross-Site Scripting).
  - Armazenar ambos em cookies automáticos pode aumentar a superfície de ataque CSRF se não houver proteção adequada.
- **Decisão**:
  1. **Access Token (JWT)**: Mantido estritamente **em memória JavaScript** (estado React dentro do `AuthContext`). Não é gravado em `localStorage` ou `sessionStorage`.
  2. **Refresh Token**: Gravado em **Cookie HTTP-Only**, emitido pelo backend com atributos:
     - `HttpOnly`: Impede acesso por scripts JavaScript (`document.cookie`), anulando exfiltração direta via XSS.
     - `SameSite=Lax`: Previne o envio do cookie em requisições de origem cruzada arbitrárias (mitigação essencial contra CSRF).
     - `Path=/api/v1/auth`: O cookie é enviado apenas aos endpoints de autenticação (`/refresh`, `/logout`), não trafegando desnecessariamente em outras rotas da API.
     - `Secure`: Ativado obrigatoriamente em produção (HTTPS) e condicional em desenvolvimento local (`http://localhost`).
- **Consequências**:
  - *Positivas*: Máxima segurança contra roubo persistente de credenciais; o risco de XSS limita-se à janela de vida de 15 minutos do token em memória.
  - *Atenuadas*: Ao recarregar a página (F5), o estado do React é reiniciado; o cliente executa um *silent refresh* inicial imediato através do endpoint `/api/v1/auth/refresh` aproveitando o cookie HttpOnly existente para recuperar a sessão transparentemente.

---

### ADR-002: Rotação de Refresh Tokens e Mitigação de Reuso

- **Status**: Aceito
- **Contexto**:
  Refresh Tokens possuem validade estendida (ex: 7 a 30 dias). Se um token for estático e interceptado, o atacante mantém acesso contínuo.
- **Decisão**:
  Adotar **Refresh Token Rotation (RTR)** conforme as recomendações da RFC 6749 e OAuth 2.0 Security BCP:
  1. Cada chamada ao `/api/v1/auth/refresh` invalida o token apresentado e emite um par novinho (novo Access Token + novo Refresh Token).
  2. Cada refresh token pertence a uma `family_id` (UUID).
  3. No banco de dados, o token nunca é salvo em texto claro; armazena-se seu hash criptográfico **SHA-256**.
  4. **Detecção de Reuso**: Se o backend receber um refresh token cujo hash já conste como consumido/revogado, interpreta-se que uma cópia do token foi utilizada por dois atores (vítima e atacante). O backend imediatamente **revoga todos os tokens daquela `family_id`**, invalidando a sessão em todos os dispositivos e registrando um incidente de segurança.
- **Consequências**:
  - *Positivas*: Reduz drasticamente a utilidade de um token vazado e alerta ativamente o sistema sobre comprometimento de sessão.
  - *Atenuadas*: Exige sincronismo apurado no frontend para não disparar refreshes concorrentes legítimos que acionem falso positivo de reuso (ver ADR-005).

---

### ADR-003: Algoritmo Criptográfico para Hashing de Senhas

- **Status**: Aceito
- **Contexto**:
  Algoritmos tradicionais como MD5 e SHA-256 são inadequados para senhas devido à facilidade de ataques em GPU/ASIC. Bcrypt e Argon2id são os dois padrões modernos aceitos.
- **Decisão**:
  Utilizar **Argon2id** (variante híbrida recomendada pelo Password Hashing Competition e OWASP).
  - Parâmetros padrão: memória de 64MB (`m=65536`), 3 iterações no tempo (`t=3`), paralelismo de 4 threads (`p=4`).
  - Implementação via biblioteca Python `pwdlib[argon2]` ou `passlib[argon2]`.
- **Consequências**:
  - *Positivas*: Resistência contra ataques de canal lateral (side-channel) e ataques por força bruta massivamente paralelos (GPUs/FPGAs).
  - *Atenuadas*: Custo computacional controlado para o servidor (tempo de cálculo ~50ms por verificação, adequado para fluxo de login).

---

### ADR-004: Fluxo de Integração com Google Identity (OAuth 2.0 / OIDC)

- **Status**: Aceito
- **Contexto**:
  Existem duas abordagens comuns para autenticação Google em SPAs:
  1. *Authorization Code Flow tradicional com redirect*: Redireciona a página inteira para o Google, recebe `code` via callback e troca por tokens. Requer gerenciamento complexo de `state` e pode interromper o fluxo na UI.
  2. *Google Identity Services (GIS) com ID Token (OIDC)*: O frontend utiliza o SDK moderno do Google (botão estilizado ou One-Tap popup), recebendo um ID Token (JWT) assinado pelo Google.
- **Decisão**:
  Adotar o **Google Identity Services (GIS) com validação de ID Token**:
  1. Frontend exibe o botão do Google ou popup One-Tap e recebe a `credential` (ID Token JWT).
  2. Frontend envia a `credential` via POST para `/api/v1/auth/google`.
  3. Backend valida a assinatura do token usando as chaves públicas oficiais do Google (JWKS) via biblioteca oficial `google-auth` (`id_token.verify_oauth2_token`).
  4. Backend valida o `audience` (Client ID do projeto Google), `issuer` (`accounts.google.com`) e expiração.
  5. Se válido, busca ou cria o usuário na base PostgreSQL e emite os tokens do próprio sistema.
- **Consequências**:
  - *Positivas*: Experiência de usuário fluida, sem redirects pesados; segurança robusta garantida por assinatura de chaves públicas assimétricas; compatibilidade total com o modelo de tokens do nosso sistema.

---

### ADR-005: Gestão de Concorrência no Refresh Silencioso (Axios Queue)

- **Status**: Aceito
- **Contexto**:
  Em uma SPA, quando um usuário navega para uma tela rica, múltiplos componentes podem disparar requisições de API simultaneamente. Se o Access Token estiver expirado, todas as requisições falharão com 401 quase no mesmo milissegundo. Sem coordenação, múltiplos refreshes seriam disparados para o backend, o que violaria o Token Rotation e causaria falso positivo de reuso.
- **Decisão**:
  Implementar um mecanismo de **Fila com Lock (Mutex)** no Interceptor de resposta do Axios:
  1. Declarar variáveis de controle de fluxo: `isRefreshing = false` e `failedQueue = []`.
  2. Ao receber o primeiro erro 401:
     - Se `!isRefreshing`: Define `isRefreshing = true`, despacha a chamada para `POST /api/v1/auth/refresh`.
     - Se `isRefreshing == true`: Enfileira a requisição na `failedQueue` como uma Promise pendente.
  3. Quando o refresh responder com sucesso:
     - Atualiza o Access Token em memória.
     - Processa todas as requisições da fila `failedQueue`, injetando o novo cabeçalho `Authorization: Bearer <novo_token>` e reexecutando-as.
     - Reseta `isRefreshing = false`.
  4. Se o refresh falhar (ex: refresh token expirado ou revogado):
     - Rejeita todas as requisições na fila.
     - Dispara o logout do usuário e redireciona para a tela de login.
- **Consequências**:
  - *Positivas*: Zero race conditions; elimina falhas intermitentes de token rotation; transparência completa para os componentes React.

---

### ADR-006: Stack de Persistência Assíncrona no Backend

- **Status**: Aceito
- **Contexto**:
  FastAPI é construído nativamente sobre `asyncio` e Starlette. Operações bloqueantes de I/O em banco de dados podem limitar o throughput da aplicação.
- **Decisão**:
  Utilizar **SQLAlchemy 2.0 com suporte assíncrono** (`AsyncEngine`, `AsyncSession`) utilizando o driver **`asyncpg`** para o PostgreSQL.
- **Consequências**:
  - *Positivas*: Desempenho superior sob alta concorrência; modelos modernos com tipagem estrita `Mapped[...]` do SQLAlchemy 2.0; injeção limpa de dependência de sessão (`get_db`) nos routers.

---

### ADR-007: Gestão do Esquema de Banco de Dados com Alembic

- **Status**: Aceito
- **Contexto**:
  É necessário manter versionamento controlado das tabelas (`users`, `refresh_tokens`, `audit_logs`) sem depender de sincronização manual ou comandos imperativos de criação que não suportam evolução futura.
- **Decisão**:
  Configurar o **Alembic** para gerenciar todas as migrações DDL em modo assíncrono.
  - Os modelos SQLAlchemy são importados em `alembic/env.py`.
  - As migrações são geradas e revisadas formalmente (`alembic revision --autogenerate`).
  - No contêiner Docker do backend, o entrypoint executa automaticamente `alembic upgrade head` antes de iniciar o servidor da aplicação.
- **Consequências**:
  - *Positivas*: Ambiente reproduzível, schema auditável e versionado no Git; deploys seguros.

---

### ADR-008: Política de CORS e Cookies Cross-Origin em Desenvolvimento

- **Status**: Aceito
- **Contexto**:
  No ambiente de desenvolvimento local com Docker ou npm/uvicorn, o frontend roda em `http://localhost:5173` e o backend em `http://localhost:8000`. Essa configuração caracteriza requisição *Cross-Origin*.
- **Decisão**:
  1. **FastAPI CORSMiddleware**:
     - `allow_origins`: `["http://localhost:5173", "http://127.0.0.1:5173"]` (origens explícitas, jamais `*` pois `allow_credentials=True` proíbe wildcard).
     - `allow_credentials`: `True` (essencial para envio e recebimento de cookies HttpOnly).
     - `allow_methods`: `["*"]`.
     - `allow_headers`: `["*"]`.
  2. **Atributo `Secure` do Cookie**:
     - Configurado dinamicamente via variável de ambiente `ENVIRONMENT`:
       - Em `development`: `COOKIE_SECURE = False`, permitindo o tráfego do cookie via HTTP local.
       - Em `production`: `COOKIE_SECURE = True`, forçando HTTPS estrito.
  3. **Axios Client**:
     - `withCredentials = true` ativado globalmente na instância do Axios.
- **Consequências**:
  - *Positivas*: O laboratório funciona perfeitamente tanto em ambiente local de desenvolvimento quanto em produção conteinerizada com HTTPS reverso.
