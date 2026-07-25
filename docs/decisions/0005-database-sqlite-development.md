# ADR-005: Banco de Dados de Desenvolvimento (SQLite Assíncrono com SQLAlchemy & Alembic)

## Status
Aceito

## Contexto
O assistente armazena o histórico de conversas e mensagens para manter o contexto ativo do Llama 3. No ambiente de desenvolvimento local, precisamos de um banco de dados leve que não exija instalação de serviços adicionais (como contêineres Docker de PostgreSQL).

## Decisão
Decidimos utilizar o **SQLite** no modo assíncrono via `aiosqlite` no ambiente de desenvolvimento, mapeado pelo **SQLAlchemy 2.0 (Async)** e gerenciado por migrações do **Alembic**.

### Principais Motivos:
1. **Zero Setup**: O arquivo `.sqlite3` é criado localmente na pasta da aplicação, sem necessidade de servidores externos.
2. **Abstração ORM**: O SQLAlchemy 2.0 permite chavear facilmente para **PostgreSQL** (`asyncpg`) em ambientes de produção mudando apenas a string de conexão no `.env`.
3. **Migrações via Alembic**: Padrão de mercado no ecossistema Python para controle de versão do schema relacional.

## Consequências
* **Positivas**:
  * Execução imediata no `uvicorn` sem pré-requisitos de infraestrutura de banco de dados.
  * Transição suave e transparente para PostgreSQL quando necessário.
