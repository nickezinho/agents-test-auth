---
name: frontend-design
description: Padrões de design visual, arquitetura de componentes React, TypeScript, Vite e gerenciamento seguro de tokens.
---

# Skill: Frontend Design

## Diretrizes Visuais e de UX
1. **Design Moderno e Polido**:
   - Paleta de cores escura e sofisticada (dark mode nativo ou toggle dinâmico), tipografia limpa (Inter/Roboto), bordas arredondadas sutis, glassmorphism e sombras elegantes.
   - Feedback visual imediato: loaders durante login/refresh, toasts informativos de erro e sucesso, e contagem regressiva para expiração do token no dashboard.
2. **Gerenciamento de Estado**:
   - O estado global de autenticação deve residir no `AuthContext`.
   - O Access Token é guardado exclusivamente em variável de estado do React, nunca persistido em storage local do navegador.
3. **Resiliência do Cliente HTTP (Axios)**:
   - Configurar Axios com `withCredentials: true`.
   - Implementar interceptor de resposta com enfileiramento de requisições durante a execução de refresh token para mitigar race conditions.
