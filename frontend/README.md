# NOMA — Frontend

React, TypeScript e Vite.

## Desenvolvimento

Instale as dependências com `npm install` e inicie com `npm run dev`.

## Validação

- `npm run lint`: verifica o código com ESLint.
- `npm run build`: verifica o TypeScript e gera a versão de produção.
- `npm run preview`: visualiza a versão de produção localmente.

## Organização de imagens e SVGs

```text
src/assets/
  svg/
    icons/          # Ícones da interface: busca, menu, carrinho etc.
    logos/          # Logos e símbolos em SVG.
    illustrations/  # Ilustrações e outros vetores em SVG.
  images/           # Fotos, banners e imagens raster: WebP, AVIF, PNG, JPG etc.
public/             # Arquivos que precisam de URL e nome fixos, como favicon.svg.
```

Use `src/assets` como local padrão para arquivos visuais que fazem parte da aplicação.
Os arquivos `.gitkeep` apenas permitem versionar as pastas ainda vazias; não devem ser importados.

### Uso em React

Exemplo em `src/App.tsx`, depois de adicionar os arquivos indicados:

```tsx
import logoUrl from './assets/svg/logos/noma.svg'
import searchIconUrl from './assets/svg/icons/search.svg'
import campaignUrl from './assets/images/summer-campaign.webp'

function App() {
  return (
    <main>
      <img src={logoUrl} alt="NOMA" />
      <button type="button" aria-label="Buscar">
        <img src={searchIconUrl} alt="" />
      </button>
      <img src={campaignUrl} alt="Looks da campanha de verão" />
    </main>
  )
}
```

Ajuste o caminho relativo conforme a localização do componente. Por exemplo, em
`src/components/Header/index.tsx`, o logo seria importado de
`../../assets/svg/logos/noma.svg`.

Nesta configuração, importar um SVG retorna sua URL. Use-o com `<img>`;
a sintaxe `<Logo />` exige outra configuração e não está habilitada.

### Uso em CSS

O caminho é relativo ao arquivo CSS. Exemplo em `src/index.css`:

```css
.campaign {
  background-image: url('./assets/images/summer-campaign.webp');
}
```

Use `<img>` para imagens que transmitem conteúdo e CSS para fundos decorativos.

### Quando usar public

Reserve `public` para arquivos que precisam manter o nome ou ser acessados diretamente
por URL. Por exemplo, `public/favicon.svg` é referenciado como `/favicon.svg` no
HTML, sem incluir `public` no caminho. Em componentes, se houver implantação em
uma subpasta, use a base configurada: `${import.meta.env.BASE_URL}favicon.svg`.

Assets importados de `src` entram no processamento do build e podem receber nomes
com hash para cache. Os arquivos de `public` são copiados como estão. O Vite não
comprime automaticamente suas fotos: otimize os arquivos antes de adicioná-los.

### Convenções de manutenção

- Use nomes descritivos em inglês e `kebab-case`: `search.svg`, `noma-wordmark.svg`,
  `summer-campaign.webp`. Evite espaços, acentos e nomes como `img1` ou `final-final`.
- Guarde cada arquivo em um único lugar. Se um logo for PNG, ele vai em `images`;
  se for SVG, vai em `svg/logos`.
- Prefira WebP ou AVIF para fotos quando adequados; use PNG quando necessário.
  Preserve SVG para vetores e exporte imagens nas dimensões necessárias.
- Crie subpastas por finalidade apenas quando houver arquivos suficientes para
  justificar, por exemplo `images/campaigns` ou `images/placeholders`.
- Ao remover um asset, confira seus imports e referências em CSS e HTML.
- Imagens de produtos e lojas enviadas por usuários devem futuramente vir de
  storage/CDN através de URLs da API; essas pastas são para assets da aplicação.

Referência: [documentação oficial de assets do Vite](https://vite.dev/guide/assets.html).

## Componentes do feed

Cada componente tem sua pasta em `src/components`, com `index.tsx` e CSS próprio.
O arquivo `src/components/feed.css` concentra somente estilos compartilhados do feed.
As props ficam em `src/types/feed.ts`, agrupadas por domínio. Novos domínios podem
ter seus próprios arquivos em `src/types`, sem acumular todas as props em um arquivo genérico.

| Componente | Props obrigatórias | Props opcionais |
| --- | --- | --- |
| `FeedCard` | `image: string`, `title: string` | `imageAlt: string` |
| `FeedProdutos` | `products: FeedProdutosProps[]` (cada item tem `productImage` e `brandLogo`) | — |
| `FeedInfluenciador` | `image: string`, `influencerName: string` | `imageAlt: string` |
| `FeedMarcas` | `brands: readonly string[]` | — |

Exemplo em uma página dentro de `src/pages`, usando URLs ou imports reais nos valores:

```tsx
import { FeedCard } from '../components/FeedCard'
import { FeedProdutos } from '../components/FeedProdutos'
import { FeedInfluenciador } from '../components/FeedInfluenciador'
import { FeedMarcas } from '../components/FeedMarcas'

// Dentro do JSX da página:
<FeedCard image={campaignUrl} title="Streetwear na NOMA" />
<FeedProdutos products={[{ productImage: productUrl, brandLogo: brandLogoUrl }, { productImage: anotherProductUrl, brandLogo: anotherBrandLogoUrl }]} />
<FeedInfluenciador image={portraitUrl} influencerName="davimissola" />
<FeedMarcas brands={['SAINT', 'ADORA']} />
```

Os valores de imagem acima são exemplos de variáveis, não assets já incluídos.
Os componentes não foram adicionados ao `App.tsx`, pois ainda não há conteúdo real
para compor o feed. Esta versão contém apenas apresentação básica, sem fontes novas,
logos fictícios, ações de curtir/salvar ou integração com API.

`imageAlt` permite descrever o conteúdo das fotos. A lista de produtos usa uma descrição
básica por posição; quando receber objetos da API, poderá ter descrição e ID por produto.
Listas vazias de produtos ou marcas não renderizam conteúdo.

Na integração futura, IDs podem identificar marcas e produtos e servir como chaves
estáveis das listas. Os componentes de apresentação ainda podem receber nomes e URLs
resolvidos pela página ou camada de dados, sem buscar dados por conta própria.
