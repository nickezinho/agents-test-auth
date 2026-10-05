---
name: security-review
description: Metodologias de auditoria de segurança, verificação de conformidade OWASP, testes de reuso de token e checagem de transporte de cookies.
---

# Skill: Security Review

## Checklist de Auditoria de Segurança
1. **Cookies**:
   - `HttpOnly`: Ativo em todos os cookies contendo tokens de sessão?
   - `SameSite`: Configurado como `Lax` ou `Strict`?
   - `Secure`: Ativado para conexões HTTPS e tratado de forma segura em ambiente de desenvolvimento local?
   - `Path`: Restrito exclusivamente a `/api/v1/auth`?
2. **Criptografia e Hashes**:
   - Senhas locais são protegidas com Argon2id ou Bcrypt com salt único e custo adequado?
   - Refresh tokens são persistidos como hash SHA-256 no banco, impedindo vazamento em caso de dump?
3. **Mecanismo de Rotação (Token Rotation)**:
   - Um refresh token consumido é imediatamente invalidado?
   - A detecção de reuso revoga toda a árvore de tokens (`family_id`) do usuário?
4. **Google Identity (OIDC)**:
   - O backend valida a assinatura RSA/JWKS oficial do Google, audience (Client ID) e data de expiração?