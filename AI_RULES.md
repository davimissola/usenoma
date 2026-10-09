# AI_RULES.md

# NOMA — AI Development Rules

Este arquivo define como qualquer IA deve trabalhar dentro do projeto **NOMA**.

Ele existe para manter o projeto consistente ao longo do tempo, evitar código desnecessariamente complexo e preservar a essência do produto.

As regras deste arquivo devem ser consideradas antes de qualquer alteração relevante no projeto.

> Este documento é vivo.  
> Ele pode e deve ser atualizado conforme a arquitetura, o produto e as decisões da NOMA evoluírem.

---

# 1. O que é a NOMA

A **NOMA** é uma plataforma digital de moda.

Ela nasce como um **marketplace especializado em marcas e lojas de roupa**, mas não deve ser tratada como um marketplace genérico.

A essência da NOMA é:

> **Moda como identidade, cultura e descoberta.**

A NOMA não quer ser apenas um lugar onde usuários pesquisam produtos pelo menor preço.

Ela deve ser um lugar onde pessoas:

- descobrem novas marcas;
- descobrem novos estilos;
- acompanham lojas;
- conhecem novas coleções;
- encontram produtos alinhados ao próprio gosto;
- exploram moda de maneira visual e editorial;
- eventualmente acompanham creators, influenciadores e conteúdo de moda.

Ao mesmo tempo, a NOMA deve permitir que pequenas, médias e grandes lojas tenham presença digital dentro da plataforma sem perder sua identidade.

---

# 2. Princípio central do produto

Marketplaces tradicionais normalmente colocam o **produto** no centro.

Na NOMA, devemos colocar:

1. **marca**
2. **identidade**
3. **estilo**
4. **coleção**
5. **produto**
6. **compra**

A NOMA deve evitar transformar lojas em vendedores anônimos dentro de uma grade de produtos.

Cada loja deve parecer uma **marca real dentro de uma plataforma maior**.

---

# 3. Filosofia visual da NOMA

A identidade global da NOMA deve ser:

- minimalista;
- editorial;
- contemporânea;
- fashion-first;
- visual;
- limpa;
- sofisticada;
- predominantemente preto e branco;
- com forte uso de fotografia;
- com pouco ruído visual.

A interface da plataforma deve funcionar como uma moldura.

> **A NOMA é a moldura. As marcas são a arte.**

A identidade visual global da plataforma não deve competir com a identidade visual das lojas.

Cada loja poderá ter personalidade própria através de:

- imagens;
- campanhas;
- coleções;
- cores;
- tipografia;
- layout;
- organização das seções;
- banners;
- lookbooks;
- conteúdo.

Mas a usabilidade principal deve continuar consistente.

---

# 4. Experiência de usuário

A UX deve sempre priorizar:

- descoberta;
- clareza;
- simplicidade;
- velocidade;
- navegação intuitiva;
- identidade visual;
- baixa fricção;
- mobile-first.

A NOMA não deve parecer:

- Shopee;
- AliExpress;
- marketplace de desconto;
- catálogo visualmente poluído;
- painel SaaS genérico.

Evitar:

- excesso de badges;
- excesso de cores;
- excesso de CTAs;
- excesso de informações no mesmo card;
- promoções visuais agressivas;
- banners piscando;
- interfaces visualmente barulhentas.

---

# 5. Estrutura conceitual da experiência

Cada tipo de página tem um papel.

## Home

Objetivo:

- apresentar universos de moda;
- permitir descoberta;
- direcionar para estilos;
- mostrar marcas;
- mostrar coleções;
- eventualmente mostrar produtos personalizados.

A Home não deve ser apenas uma grade de produtos.

## Página de estilo

Exemplos:

- Streetwear
- Minimal
- Elegante
- Casual

Objetivo:

- funcionar como um feed editorial;
- misturar marcas;
- coleções;
- produtos;
- lançamentos;
- campanhas;
- conteúdo relevante.

Pode conter conteúdos patrocinados no futuro.

Conteúdo pago nunca deve destruir a experiência do usuário.

## Página de loja

Objetivo:

> fazer o usuário sentir que entrou no universo daquela marca.

A loja deve poder combinar blocos como:

- hero;
- campanha;
- produtos;
- coleção;
- lookbook;
- vídeo;
- texto editorial;
- lançamento;
- destaque;
- feed da marca.

As lojas devem ter alto nível de personalização sem comprometer a usabilidade.

## Página de produto

Objetivo:

- reduzir fricção;
- mostrar produto com clareza;
- converter.

Deve priorizar:

- imagens;
- variações;
- tamanhos;
- preço;
- estoque;
- frete;
- informações essenciais;
- marca.

---

# 6. Futuro social da NOMA

A arquitetura deve permitir evolução futura para recursos sociais.

Possíveis recursos:

- seguir lojas;
- seguir creators;
- favoritos;
- salvar produtos;
- feed;
- posts;
- produtos marcados em posts;
- collections;
- recomendações;
- comentários;
- curtidas;
- compartilhamentos;
- notificações.

Não implementar tudo antecipadamente.

> Preparar a arquitetura para evolução não significa desenvolver funcionalidades que ainda não são necessárias.

---

# 7. Filosofia de engenharia

O código da NOMA deve ser:

- simples;
- legível;
- previsível;
- organizado;
- testável;
- modular;
- fácil de manter;
- fácil de alterar;
- fácil de entender por outro desenvolvedor.

A regra principal é:

> **Não complicar o que pode ser simples.**

Evitar engenharia excessiva.

Não utilizar padrões complexos apenas porque são considerados "enterprise".

Não criar abstrações antes de existir um problema real que elas resolvam.

---

# 8. Regra contra overengineering

Antes de criar:

- interface;
- classe abstrata;
- factory;
- adapter;
- mediator;
- event bus;
- repository genérico;
- provider;
- strategy;
- command bus;
- microserviço;

perguntar:

> isso resolve um problema real existente agora?

Se a resposta for "não", não criar.

Preferir:

```text
código simples
>
abstração prematura
```

---

# 9. Stack principal

A stack inicial da NOMA é:

## Frontend

- React
- TypeScript

## Backend

- Python
- FastAPI

## Banco

Preferencialmente:

- PostgreSQL

## Arquitetura

- monolito modular

Outras tecnologias podem ser adicionadas conforme necessidade real.

Exemplos futuros:

- Redis;
- storage de imagens;
- CDN;
- filas;
- workers;
- mecanismos de busca;
- serviços de recomendação.

Não adicionar infraestrutura sem necessidade.

---

# 10. Arquitetura backend

O backend deve começar como um **monolito modular**.

Não criar microserviços prematuramente.

Os domínios devem ser separados de maneira clara.

Exemplo:

```text
app/

  auth/
  users/
  stores/
  products/
  categories/
  collections/
  follows/
  favorites/
  feed/
  orders/
  payments/

  core/

  main.py
```

Um módulo pode conter:

```text
router.py
service.py
repository.py
schemas.py
models.py
```

A estrutura deve ser adaptada conforme necessidade.

Não criar arquivos vazios ou camadas sem função real apenas para "seguir arquitetura".

---

# 11. Separação de responsabilidades

Preferencialmente:

## Router

Responsável por:

- receber HTTP request;
- validar parâmetros básicos;
- chamar service;
- retornar resposta HTTP.

Router NÃO deve conter regra complexa de negócio.

## Service

Responsável por:

- regra de negócio;
- coordenação das operações;
- validações de domínio;
- decisões da aplicação.

## Repository

Responsável por:

- consultas ao banco;
- persistência;
- operações específicas de dados.

Não criar repository genérico gigantesco.

## Schema

Responsável por:

- entrada de dados;
- saída de dados;
- validação;
- contrato da API.

---

# 12. Regras de banco de dados

Sempre pensar em:

- integridade;
- constraints;
- índices;
- relacionamentos;
- consistência;
- concorrência.

Não confiar apenas em validações da aplicação.

Utilizar constraints do banco quando fizer sentido.

Exemplos:

- UNIQUE;
- FOREIGN KEY;
- NOT NULL;
- CHECK.

Evitar salvar dados redundantes sem motivo.

---

# 13. Queries

Evitar:

- N+1 queries;
- carregar dados desnecessários;
- buscar tabelas inteiras;
- consultas dentro de loops quando poderiam ser agrupadas.

Antes de otimizar, medir.

Não criar otimizações complexas sem necessidade real.

---

# 14. Migrações

Mudanças estruturais de banco devem utilizar migrations.

Nunca alterar banco de produção manualmente sem controle.

Toda migration deve ser:

- clara;
- reversível quando possível;
- pequena;
- relacionada a uma mudança específica.

---

# 15. API

A API deve ser:

- previsível;
- consistente;
- simples;
- semanticamente clara.

Preferir endpoints REST compreensíveis.

Exemplo:

```text
GET    /stores
GET    /stores/{id}
POST   /stores
PATCH  /stores/{id}
DELETE /stores/{id}
```

Evitar endpoints como:

```text
POST /doSomethingWithStore
```

---

# 16. Status HTTP

Utilizar status HTTP corretos.

Exemplos:

```text
200 OK
201 Created
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
```

Não retornar sempre `200`.

---

# 17. Tratamento de erros

Erros devem ser:

- consistentes;
- previsíveis;
- úteis para o frontend;
- seguros.

Nunca retornar detalhes internos sensíveis.

Evitar mensagens genéricas como:

```text
Something went wrong
```

quando for possível informar o problema corretamente.

---

# 18. Segurança

Segurança deve ser considerada desde o início.

Nunca:

- salvar senha em texto puro;
- colocar secrets no código;
- confiar em dados enviados pelo frontend;
- concatenar SQL manualmente;
- expor stack traces em produção;
- retornar dados privados desnecessários.

Utilizar:

- hashing seguro;
- variáveis de ambiente;
- validação;
- autenticação;
- autorização;
- proteção de rotas.

---

# 19. Autorização

Sempre verificar propriedade de recursos.

Exemplo:

Uma loja não pode:

- editar produtos de outra loja;
- editar perfil de outra loja;
- visualizar informações privadas de outra loja;
- gerenciar pedidos de outra loja.

Nunca confiar apenas no ID enviado pelo frontend.

---

# 20. Frontend

O frontend deve ser:

- componentizado;
- simples;
- responsivo;
- mobile-first;
- consistente;
- semanticamente organizado.

Evitar componentes gigantes.

Quando um componente crescer demais, avaliar separação.

Não separar componentes extremamente pequenos sem ganho real.

---

# 21. TypeScript

Evitar:

```ts
any
```

Sempre que possível utilizar tipos explícitos.

Exemplo:

```ts
type Product = {
  id: number
  name: string
  price: number
}
```

Reutilizar tipos quando fizer sentido.

Não criar tipos excessivamente genéricos.

---

# 22. Estado no frontend

Não transformar tudo em estado global.

Preferir:

- estado local para dados locais;
- contexto apenas quando necessário;
- biblioteca global apenas quando existir necessidade clara.

Evitar complexidade antecipada.

---

# 23. Componentes React

Componentes devem ter responsabilidade clara.

Evitar:

```text
HomePage.tsx com 1500 linhas
```

Separar partes conceitualmente independentes.

Exemplo:

```text
HomePage
  StyleCard
  BrandSection
  CollectionSection
  ProductGrid
```

---

# 24. CSS

O CSS deve ser:

- organizado;
- previsível;
- consistente.

Evitar:

- números mágicos repetidos;
- `!important` sem necessidade;
- estilos duplicados;
- excesso de nesting;
- hacks sem explicação.

Preferir tokens/variáveis para:

- cores;
- spacing;
- border radius;
- typography;
- breakpoints.

---

# 25. Design system

A NOMA deve possuir consistência visual.

Idealmente centralizar:

- cores;
- tipografia;
- spacing;
- radius;
- sombras;
- tamanhos;
- breakpoints;
- componentes básicos.

Não criar designs completamente diferentes para elementos equivalentes sem motivo.

---

# 26. Mobile-first

A experiência principal da NOMA deve ser pensada primeiro para mobile.

Sempre testar:

- celulares pequenos;
- celulares grandes;
- tablets;
- desktop.

Não assumir que algo que funciona no desktop funcionará no celular.

---

# 27. Acessibilidade

Não ignorar acessibilidade.

Utilizar:

- HTML semântico;
- `alt`;
- labels;
- foco;
- contraste;
- áreas clicáveis adequadas;
- navegação por teclado quando aplicável.

---

# 28. Performance frontend

Evitar:

- imagens gigantes sem otimização;
- re-renders desnecessários;
- carregar conteúdo que não aparece;
- bundles desnecessariamente grandes.

Utilizar quando fizer sentido:

- lazy loading;
- paginação;
- infinite scroll;
- image optimization;
- code splitting.

---

# 29. Imagens

Moda depende fortemente de imagem.

Portanto imagens devem ser tratadas como parte crítica da arquitetura.

Pensar em:

- compressão;
- múltiplos tamanhos;
- thumbnails;
- CDN;
- formatos modernos;
- lazy loading;
- qualidade visual.

Nunca enviar uma imagem de vários MB quando uma versão otimizada resolve.

---

# 30. Feed

O feed inicial deve ser simples.

Não tentar criar um algoritmo semelhante ao Instagram no MVP.

Inicialmente pode considerar:

- data;
- estilo;
- relevância;
- popularidade;
- preferências;
- lojas seguidas;
- conteúdo patrocinado.

A complexidade deve crescer conforme dados reais existirem.

---

# 31. Conteúdo patrocinado

A NOMA poderá monetizar através de destaque de:

- lojas;
- produtos;
- coleções;
- posts;
- campanhas.

Publicidade não pode destruir a confiança do usuário.

Conteúdo patrocinado deve ser:

- relevante;
- limitado;
- contextual;
- claramente identificável quando necessário.

Não transformar o ranking inteiro em "quem paga mais".

---

# 32. Recomendações

Recomendação futura pode considerar:

- cliques;
- favoritos;
- follows;
- compras;
- tempo de visualização;
- estilos;
- marcas;
- preço;
- categorias.

Nunca implementar machine learning complexo sem dados suficientes.

Começar simples.

---

# 33. Código legível

Prioridade absoluta.

Código deve ser escrito para humanos.

Preferir:

```python
if store.is_active:
    publish_products(store)
```

ao invés de código condensado ou excessivamente inteligente.

Não escrever código "clever".

---

# 34. Identação e formatação

Sempre manter formatação correta.

Python:

- seguir PEP 8;
- usar formatter;
- usar imports organizados.

TypeScript:

- utilizar formatter;
- manter padrão consistente;
- evitar linhas enormes.

Nunca entregar código mal identado.

---

# 35. Nomes

Nomes devem revelar intenção.

Ruim:

```python
x
data2
temp
obj
doThing()
```

Bom:

```python
store
products
selected_category
create_order()
```

Nomes curtos são permitidos apenas quando óbvios.

---

# 36. Idioma no código

Prioridade:

> consistência do projeto.

Se o projeto já possui uma convenção, seguir a convenção existente.

Para novos módulos sem padrão definido, preferir nomes técnicos em inglês.

Comentários e documentação podem ser em português quando isso facilitar manutenção.

Nunca misturar idiomas aleatoriamente dentro do mesmo contexto.

---

# 37. Funções

Funções devem:

- fazer uma coisa principal;
- possuir nome claro;
- evitar efeitos colaterais escondidos;
- ser pequenas quando isso melhora entendimento.

Não quebrar uma função simples em dez funções de três linhas apenas para parecer "clean code".

---

# 38. Comentários

Comentários devem explicar:

- POR QUE algo existe;
- comportamento não óbvio;
- decisões importantes;
- limitações.

Não escrever comentários redundantes.

Ruim:

```python
# adiciona 1
count += 1
```

Bom:

```python
# Stock is reserved before payment to prevent overselling
reserve_stock(product)
```

---

# 39. Docstrings

Utilizar quando ajudam a explicar:

- funções públicas importantes;
- services;
- regras de negócio;
- integrações.

Não adicionar docstring enorme em função trivial.

---

# 40. Duplicação

Não duplicar lógica importante.

Mas também não criar abstração prematuramente apenas para eliminar duas linhas parecidas.

Usar bom senso.

---

# 41. Dependências

Antes de instalar nova biblioteca, verificar:

1. realmente precisamos dela?
2. não existe solução simples com o que já temos?
3. a biblioteca é mantida?
4. adiciona risco?
5. adiciona muito peso?

Evitar dependências desnecessárias.

---

# 42. Testes

Funcionalidades críticas devem possuir testes.

Prioridades:

- autenticação;
- autorização;
- criação de loja;
- produtos;
- estoque;
- pedidos;
- pagamentos;
- regras financeiras.

Testar:

- happy path;
- erros;
- edge cases;
- permissões.

---

# 43. Testes úteis

Não escrever testes que apenas repetem a implementação.

Testes devem validar comportamento.

Exemplo:

```text
usuário de uma loja não consegue editar produto de outra loja
```

é mais importante que testar uma função trivial de getter.

---

# 44. Logs

Logs devem ajudar a entender o sistema.

Não logar:

- senhas;
- tokens;
- dados sensíveis;
- informações privadas desnecessárias.

Utilizar níveis adequados:

- debug;
- info;
- warning;
- error.

---

# 45. Configuração

Configurações devem ficar fora do código quando apropriado.

Exemplos:

```text
DATABASE_URL
SECRET_KEY
FRONTEND_URL
STORAGE_BUCKET
PAYMENT_API_KEY
```

Nunca commitar credenciais.

---

# 46. Performance

Não fazer otimização prematura.

Primeiro:

1. implementar corretamente;
2. medir;
3. encontrar gargalo;
4. otimizar.

Não reescrever algo em Go apenas por imaginar que Python será lento.

---

# 47. Escalabilidade

A NOMA deve ser construída para crescer, mas sem fingir que já possui milhões de usuários.

Começar simples.

Possíveis evoluções futuras:

```text
FastAPI monolith
        ↓
workers
        ↓
Redis/cache
        ↓
search engine
        ↓
serviços específicos
```

Extrair microserviços apenas quando existir motivo real.

---

# 48. Microserviços

Não criar microserviços apenas por tendência.

Considerar extração quando existir:

- necessidade de escalar isoladamente;
- domínio claramente separado;
- equipe separada;
- gargalo real;
- necessidade operacional concreta.

Até lá:

> monolito modular.

---

# 49. Git

Toda alteração relevante deve ser pequena e rastreável.

Preferir commits como:

```text
feat: create store registration
feat: add product variants
fix: validate store ownership
test: add order service tests
refactor: simplify feed query
```

Evitar commits gigantes com dezenas de mudanças sem relação.

---

# 50. Antes de alterar código existente

A IA deve primeiro entender:

- o que já existe;
- qual é o padrão;
- quem depende daquele código;
- o impacto da alteração.

Não reescrever arquivos inteiros quando uma alteração pequena resolve.

---

# 51. Regra de mudanças mínimas

Quando corrigir um bug ou adicionar feature:

> modificar apenas o necessário.

Não aproveitar a tarefa para "melhorar" partes não relacionadas sem autorização.

---

# 52. Mudanças arquiteturais

Antes de:

- alterar arquitetura;
- trocar biblioteca;
- mudar ORM;
- mudar banco;
- criar microserviço;
- alterar estrutura global de pastas;
- introduzir novo padrão importante;

A IA deve explicar:

1. problema atual;
2. solução proposta;
3. vantagens;
4. desvantagens;
5. impacto.

Não executar mudança estrutural silenciosamente.

---

# 53. Quando houver dúvida

Não inventar regra de negócio.

Se uma decisão relevante não estiver clara:

> perguntar.

Exemplos:

- comissão;
- política de cancelamento;
- devolução;
- estoque;
- frete;
- regras de seller;
- moderação;
- monetização.

---

# 54. Não inventar features

A IA não deve adicionar funcionalidades que não foram solicitadas apenas porque parecem interessantes.

Pode sugerir.

Não implementar sem aprovação quando houver impacto relevante.

---

# 55. Respeitar código existente

A IA deve:

- preservar nomes quando possível;
- preservar lógica quando possível;
- manter padrões existentes;
- evitar refactors desnecessários.

Se o código existente estiver problemático, explicar antes de alterar profundamente.

---

# 56. Processo recomendado para cada feature

Seguir preferencialmente:

```text
1. entender requisito
2. analisar código existente
3. definir pequena solução
4. implementar
5. testar
6. revisar
7. simplificar se necessário
```

---

# 57. Antes de gerar muito código

Para tarefas grandes, primeiro informar:

- arquivos que serão criados;
- arquivos que serão modificados;
- fluxo da solução;
- decisões principais.

Evitar gerar centenas de linhas antes de confirmar direção quando houver ambiguidade.

---

# 58. Code review interno

Antes de considerar a tarefa concluída, revisar:

- legibilidade;
- duplicação;
- bugs óbvios;
- segurança;
- typing;
- edge cases;
- tratamento de erro;
- consistência;
- complexidade desnecessária.

---

# 59. Regra do desenvolvedor seguinte

Antes de finalizar qualquer código, perguntar mentalmente:

> "Outro desenvolvedor conseguiria entender isso rapidamente daqui a 6 meses?"

Se não:

> simplificar.

---

# 60. Regra de produto

Toda decisão técnica deve lembrar:

A NOMA não existe para demonstrar tecnologia.

A NOMA existe para:

> conectar pessoas, marcas, produtos, identidade e cultura de moda.

Tecnologia é meio.

Produto é prioridade.

---

# 61. Regra final

Quando houver duas soluções tecnicamente corretas, preferir nesta ordem:

1. mais simples;
2. mais legível;
3. mais fácil de manter;
4. mais consistente com o projeto;
5. mais fácil de testar;
6. mais fácil de evoluir.

Complexidade só é aceita quando resolve um problema real.

---

# Resumo rápido para a IA

Ao trabalhar na NOMA:

- entenda antes de alterar;
- escreva código simples;
- preserve a arquitetura;
- não faça overengineering;
- não invente regra de negócio;
- mantenha frontend e backend organizados;
- mantenha código legível e formatado;
- faça mudanças pequenas;
- pense em mobile-first;
- preserve o caráter editorial da NOMA;
- preserve a identidade das marcas;
- trate moda como descoberta, identidade e cultura;
- use tecnologia para servir o produto;
- explique mudanças arquiteturais antes de executá-las.

> **Simple first. Scale when needed. Brand always.**
