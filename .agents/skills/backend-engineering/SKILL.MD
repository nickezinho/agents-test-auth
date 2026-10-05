---
name: backend-engineering
description: Práticas, convenções e runbooks para desenvolvimento backend com FastAPI, SQLAlchemy 2.0 Async, PostgreSQL e Pydantic v2.
---

# Skill: Backend Engineering

## Diretrizes de Implementação
1. **Estrutura Assíncrona**: Todas as rotas que acessam banco de dados ou serviços externos devem ser `async def` e utilizar `await` nas operações de I/O.
2. **Separação em Camadas**:
   - `routers/`: Apenas parsing HTTP, documentação OpenAPI, injeção de dependências e chamada a services.
   - `services/`: Regras de negócio, manipulação de tokens, hashing e orquestração.
   - `models/`: Definições ORM SQLAlchemy com anotações `Mapped[...]` e constraints explícitas.
   - `schemas/`: DTOs Pydantic v2 com validações rigorosas (`EmailStr`, `Field(min_length=...)`).
3. **Tratamento de Exceções**: Lançar exceções HTTP padronizadas baseadas em `docs/api-contract.md` com status codes semânticos.
4. **Testes com Pytest**: Utilizar fixtures com banco de dados isolado (transações revertidas ou banco de teste em memória/container) e `httpx.AsyncClient`.
