# Backend Noma

Monolito modular com FastAPI, SQLAlchemy, Psycopg e PostgreSQL no Supabase. Alterações estruturais usam migrations com Alembic.

## Organização

- `app/main.py`: registra os módulos, configura CORS e remove os dados enviados das respostas de validação `422`.
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

Coloque a chave gerada em `SECRET_KEY` no `.env`. Preencha `DATABASE_URL` com a URL PostgreSQL obtida em **Connect** no Supabase e mantenha `sslmode=require`. URLs `postgresql://` também são aceitas; o backend usa o driver Psycopg.

Se a conexão direta por IPv6 não estiver acessível, consulte o pooler em modo **session**. [Conexões do Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

Defina `FRONTEND_URL` como a origem do frontend, sem caminho. Em produção, use HTTPS e `COOKIE_SECURE=true`. O `.env.example` usa HTTP e `COOKIE_SECURE=false` para desenvolvimento local.

As tabelas ficam no schema `app`. Mantenha esse schema fora dos schemas expostos pela Data API do Supabase; as consultas passam pelo backend. O Alembic considera apenas `app` ao gerar alterações, preservando os schemas internos do Supabase.

## Migrations e execução

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

A API usa a porta `8000`. Para encerrar, pressione `Ctrl+C`.

Execute `alembic upgrade head` também após atualizar o código quando houver novas migrations. No módulo de produtos, `0005` cria as três tabelas, `0006` permite reordenar imagens e `0007` limita cada produto a 4 imagens. Compare `alembic current` com `alembic heads` para confirmar que o banco está atualizado; se aparecer `relation "app.products" does not exist`, confira as migrations e se a API usa o mesmo `DATABASE_URL`.

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

Use um PostgreSQL local exclusivo de testes, com nome terminado em `_test`. A suíte rejeita hosts remotos, aplica as migrations e limpa as tabelas da aplicação antes de cada teste.

Com as ferramentas do PostgreSQL no PATH, prepare uma instância isolada uma única vez, dentro de `backend`:

```powershell
New-Item -ItemType Directory -Path .local -Force | Out-Null
initdb -D .local/postgres-test -U postgres --encoding=UTF8 --locale=C --auth=trust
pg_ctl -D .local/postgres-test -l .local/postgres-test.log -o "-p 55432 -h 127.0.0.1" -w start
createdb -h 127.0.0.1 -p 55432 -U postgres noma_auth_test
```

Essa instância aceita conexões apenas em `127.0.0.1` e usa autenticação sem senha exclusivamente para os testes locais. `.local` não é versionado. Nas próximas execuções, use somente o comando `pg_ctl ... start`, sem repetir `initdb` ou `createdb`.

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:TEST_DATABASE_URL = 'postgresql+psycopg://postgres@127.0.0.1:55432/noma_auth_test'
.\venv\Scripts\python.exe -m pytest -q
pg_ctl -D .local/postgres-test -m fast -w stop
```

A suíte verifica cadastro, unicidade, credenciais, JWT inválido ou expirado, cookies, expiração e rotação do refresh, concorrência, logout, isolamento entre sessões, validação sem exposição de senhas e correspondência entre models e migrations.

## Criar uma loja administrativamente

Dentro de `backend`, com o `.env` configurado e as migrations aplicadas:

```powershell
.\venv\Scripts\python.exe -m app.modules.stores.create_store --name "Saint" --slug "saint" --owner-username "davi" --description "Loja de streetwear."
```

`--description` é opcional. O usuário responsável precisa existir. A loja e seu primeiro owner são salvos juntos; qualquer falha desfaz a criação. Este comando deve ser executado pela equipe NOMA com acesso ao ambiente do backend.

## Imagens das lojas

Configure `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (chave `sb_secret_...`) e `SUPABASE_STORAGE_BUCKET=store-media` no ambiente do backend. A chave fica somente no servidor. No Supabase Storage, crie `store-media` como bucket público para leitura, sem políticas de escrita para `anon` ou `authenticated`. Pode definir também limite de 5 MiB e tipos permitidos `image/jpeg`, `image/png` e `image/webp` no bucket.

Instale as dependências atualizadas e aplique a migration dentro de `backend`:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m alembic upgrade head
```

Envie `PUT /stores/{store_id}/images/logo` ou `/cover`, com Bearer token e `multipart/form-data` no campo `file`. Owner e manager podem enviar/substituir. A resposta contém `id`, `store_id`, `type` e um objeto `variants`: cada nome aponta para URL pública, MIME, largura, altura e tamanho em bytes. `DELETE` nos mesmos endereços remove a imagem lógica e tenta excluir seus arquivos; repetir a remoção retorna `204`.

JPEG, PNG e WebP estáticos são validados pelos bytes, com até 5 MiB, 6000 pixels por lado e 20 milhões de pixels no total. SVG, animações e arquivos multipágina são rejeitados. Pillow decodifica, corrige orientação EXIF e normaliza para RGB/RGBA, preservando transparência. Perfis ICC válidos e compatíveis são convertidos para sRGB; perfis inválidos são descartados. As saídas são WebP sem EXIF/ICC/XMP, com resize LANCZOS, sem crop nem upscale.

Logo usa `small` até 256 px e `medium` até 512 px, com qualidade 90. Cover usa `medium` até 960 px e `large` até 1920 px, com qualidade 85. O limite é aplicado ao maior lado, mantendo proporção. Variantes que resultam nas mesmas dimensões compartilham um arquivo físico. Não se armazena o original de novos uploads.

Cada envio usa paths `stores/<store_id>/<type>/<uuid>/<variant>.webp`. Todas as variantes são processadas e enviadas antes da transação curta no banco, com nova verificação de autorização. Depois do commit, os arquivos anteriores são excluídos. Falhas parciais de upload ou falhas confirmadas antes do commit tentam excluir todos os novos arquivos; resultado incerto do commit os preserva. Falhas na limpeza geram log com o path pendente, sem chave ou resposta externa. Essa limpeza é best effort e pode deixar arquivos órfãos em falhas ou interrupções.

`store_images` representa logo/cover; `store_image_variants` guarda cada arquivo e seus metadados. A migration `0004` preserva referências do 3A como `medium` para logo e `large` para cover, sem acessar o Storage. Elas continuam válidas até serem substituídas; novos envios passam pelo processamento. O downgrade recupera só a maior variante para o formato antigo e não altera arquivos no Storage.

Os testes usam PostgreSQL local e simulam as operações externas de Storage. Não precisam de Supabase real.

Para revisar o fluxo e as funções principais: [resumo de estudo](ESTUDO_IMAGENS.md).

## Carrinho

O módulo `app/modules/cart/` usa Bearer token em todas as rotas: `GET /cart`, `POST /cart/items`, `PATCH /cart/items/{item_id}`, `DELETE /cart/items/{item_id}` e `DELETE /cart`. A migration `0008` cria um carrinho por usuário e itens únicos por produto/tamanho. Aplique com `alembic upgrade head`.

POST recebe `product_id`, `size` e `quantity`; PATCH recebe tamanho e/ou quantidade. POST e PATCH retornam o carrinho atualizado (`200`), e exclusões retornam `204`. Ao trocar para um tamanho já presente, a quantidade final do item de origem é somada à do destino. Quantidade deve ser um inteiro positivo; não há controle de estoque.

GET não cria registros e não altera `updated_at`. Antes da primeira adição, retorna `id: null`, `updated_at: null` e `items: []`. Os itens incluem produto, imagem principal, loja, tamanho, quantidade, preço atual e subtotal como strings decimais. `available` e `unavailable_reason` identificam tamanho indisponível/removido ou produto removido. Ao excluir um produto, sua FK fica nula e o item permanece; não se mantém cópia de nome, loja ou preço antigo. Limpar um carrinho vazio ou fazer PATCH sem mudança não altera seu timestamp.
