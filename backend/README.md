# Backend Noma

Monolito modular com FastAPI, SQLAlchemy, Psycopg e PostgreSQL no Supabase. Alterações estruturais usam migrations com Alembic.

## Organização

- `app/main.py`: registra os módulos e configura CORS.
- `app/core/config.py`: carrega o `.env` e valida as configurações.
- `app/core/database.py`: conexão, sessão do banco e `DbSession`, compartilhadas pelos módulos. Nas rotas, use `db: DbSession`; a injeção já está definida no alias com `Annotated`.
- `app/modules/auth/`: `models.py` representa as sessões; `schemas.py` define os contratos; `security.py` cuida de hashes e tokens; `service.py` contém os fluxos; `dependencies.py` valida JWT e origem e fornece `CurrentUserId`; `routes.py` expõe cadastro, login, refresh e logout.
- `app/modules/users/`: modelo do usuário, resposta pública e consulta da própria conta.
- `migrations/`: histórico versionado da estrutura do banco.
- `tests/`: testes de autenticação com PostgreSQL local exclusivo de testes.

Usuários guardam somente `id`, `username`, `email` e `password_hash`. Gostos de moda e relações sociais serão implementados em suas próprias tabelas e módulos.

## Preparar o ambiente

A partir da raiz do projeto, no PowerShell:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Coloque a chave gerada em `SECRET_KEY` no `.env`. Preencha `DATABASE_URL` com a URL PostgreSQL obtida em **Connect** no Supabase. URLs `postgresql://` também são aceitas; o backend usa o driver Psycopg.

Se a conexão direta por IPv6 não estiver acessível, consulte o pooler em modo **session**. [Conexões do Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

Defina `FRONTEND_URL` como a origem do frontend, sem caminho. Em produção, use HTTPS e `COOKIE_SECURE=true`. O `.env.example` usa HTTP e `COOKIE_SECURE=false` para desenvolvimento local.

As tabelas ficam no schema `app`. Mantenha esse schema fora dos schemas expostos pela Data API do Supabase; as consultas passam pelo backend. O Alembic considera apenas `app` ao gerar alterações, preservando os schemas internos do Supabase.

## Migrations e execução

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

A API usa a porta `8000`. Para encerrar, pressione `Ctrl+C`.

Para futuras alterações, gere uma revisão, confira o código e aplique a migration:

```powershell
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "descricao_da_alteracao"
.\venv\Scripts\python.exe -m alembic upgrade head
```

## Contratos da API

| Método e rota | Entrada | Resposta |
| --- | --- | --- |
| `POST /auth/register` | JSON com `username`, `email` e `password` | `201`, access token e refresh cookie |
| `POST /auth/login` | Formulário `application/x-www-form-urlencoded` com `username` e `password` | `200`, access token e refresh cookie |
| `POST /auth/refresh` | Refresh cookie; não exige access token | `200`, access token e refresh cookie substituído |
| `POST /auth/logout` | Refresh cookie | `204`, sessão revogada e cookie removido |
| `GET /users/me` | `Authorization: Bearer <access_token>` | `id`, `username` e `email` |

Cadastro, login e refresh retornam somente:

```json
{
	"access_token": "...",
	"token_type": "bearer"
}
```

Username aceita de 3 a 30 letras sem acentos, números, ponto e underscore. Username e email são únicos sem diferenciar maiúsculas e minúsculas. A senha aceita de 8 a 128 caracteres e é armazenada como hash Argon2id.

A conta é criada na primeira etapa do cadastro. Confirmar senha é uma validação do frontend e não é enviado como campo do cadastro. Não há confirmação de email nem conclusão de onboarding nesta versão.

## Sessão no frontend

Guarde o access token somente em memória. Use `credentials: 'include'` nas chamadas de Auth para receber e enviar o refresh cookie. Nas rotas protegidas, envie o access token em `Authorization: Bearer ...`.

Ao recarregar a página, chame `/auth/refresh` para recuperar o access token. Quando o access expirar, renove a sessão e repita a requisição uma vez. Mantenha uma única renovação em andamento, inclusive coordenando abas quando implementarmos o cliente.

O cookie usa `HttpOnly`, `SameSite=Lax`, `Path=/` e `Secure` conforme o ambiente. Sem atributo `Domain`, ele pertence ao host da API. CORS permite somente `FRONTEND_URL` com credenciais.

As rotas POST de Auth verificam `Origin`, com fallback para `Referer`. Aceitam a origem configurada do frontend ou a própria origem da API. Requisições sem origem confiável são rejeitadas. O Swagger funciona no próprio backend; clientes como curl precisam informar `Origin`.

O access token usa HS256, expira em 30 minutos por padrão e contém apenas `sub` com o UUID do usuário e `exp`. Sua validação não consulta usuários no banco. `/users/me` consulta o usuário para retornar seus dados.

Cada login cria uma sessão de refresh de 30 dias. Apenas o hash do token é persistido em `auth_sessions`. A renovação troca esse hash em uma transação, mantendo a expiração original. Tokens antigos são rejeitados; esta versão não guarda histórico para identificar sua reutilização.

O logout revoga somente a sessão atual de refresh. Um access token já emitido continua válido até expirar, mesmo após logout ou exclusão da conta. Rotas que dependam de dados de uma conta excluída precisam tratar sua ausência.

## Testes

Use um PostgreSQL local exclusivo de testes, com nome terminado em `_test`. A suíte rejeita hosts remotos, aplica as migrations e limpa as duas tabelas antes de cada teste.

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:TEST_DATABASE_URL = 'postgresql+psycopg://postgres:SENHA@127.0.0.1:5432/noma_auth_test'
.\venv\Scripts\python.exe -m pytest -q
```

A suíte verifica cadastro, unicidade, credenciais, JWT inválido ou expirado, cookies, expiração e rotação do refresh, concorrência, logout e isolamento entre sessões.
