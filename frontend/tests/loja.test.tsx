// @vitest-environment jsdom
import { StrictMode, act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App'
import { auth } from '../src/stores/auth'
import type { LojaPublicaResponse } from '../src/types/lojas'
import type { ProdutoResponse } from '../src/types/produtos'


vi.mock('../src/config', () => ({ apiUrl: 'https://api.noma.test' }))

const fetchMock = vi.fn<typeof fetch>()
let container: HTMLDivElement
let root: Root
let loja: LojaPublicaResponse
let produtos: ProdutoResponse[]


beforeEach(() => {
	auth.accessToken = ''
	auth.sessaoVerificada = false
	fetchMock.mockReset()
	vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
	vi.stubGlobal('fetch', fetchMock)
	loja = {
		id: 'loja-saint',
		name: 'Saint',
		slug: 'saint',
		description: 'Streetwear.',
		logo: {
			small: { url: 'https://storage.noma.test/logo-small.webp', mime_type: 'image/webp', width: 256, height: 256, size_bytes: 1000 },
			medium: { url: 'https://storage.noma.test/logo-medium.webp', mime_type: 'image/webp', width: 512, height: 512, size_bytes: 2000 },
		},
		cover: {
			medium: { url: 'https://storage.noma.test/cover-medium.webp', mime_type: 'image/webp', width: 640, height: 960, size_bytes: 10000 },
			large: { url: 'https://storage.noma.test/cover-large.webp', mime_type: 'image/webp', width: 1280, height: 1920, size_bytes: 20000 },
		},
	}

	produtos = [{
		id: 'produto-saint', store_id: 'loja-saint', name: 'Camiseta real', price: '149.90', description: null, sizes: [],
		images: [{ id: 'imagem-01', position: 1, variants: { card: { url: 'https://storage.noma.test/produto-card.webp' }, large: { url: 'https://storage.noma.test/produto-large.webp' } } }],
	}]

	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}

		if (String(input).endsWith('/products')) {
			return Response.json(produtos)
		}

		return Response.json(loja)
	})

	container = document.createElement('div')
	document.body.append(container)
	root = createRoot(container)
})

afterEach(async () => {
	await act(async () => { root.unmount() })
	container.remove()
	vi.unstubAllGlobals()
})


async function abrirPagina(path = '/saint') {
	window.history.replaceState({}, '', path)

	await act(async () => {
		root.render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>)
	})
}


it('exibe as imagens reais com variantes para celular e desktop, sem enviar autenticação', async () => {
	await abrirPagina()

	expect(container.querySelector('.imagem-hero-loja')?.getAttribute('src')).toBe(loja.cover?.medium?.url)
	expect(container.querySelector('picture source')?.getAttribute('srcset')).toBe(loja.cover?.large?.url)
	expect(container.querySelector('picture source')?.getAttribute('media')).toBe('(min-width: 960px)')
	expect(container.querySelector('.logo-hero-loja img')?.getAttribute('src')).toBe(loja.logo?.medium?.url)
	expect(container.querySelector('.logo-hero-loja img')?.getAttribute('alt')).toBe('Logo de Saint')
	expect(container.querySelector('.estatisticas-hero-loja')).toBeNull()

	const consultas = fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/stores/slug/saint'))
	expect(consultas.length).toBeGreaterThan(0)

	for (const [, options] of consultas) {
		expect(new Headers(options?.headers).has('Authorization')).toBe(false)
		expect(options?.credentials).not.toBe('include')
	}
})


it('carrega a loja enquanto a verificação da sessão ainda está pendente', async () => {
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Promise(resolve => { concluirRefresh = resolve })
		}

		if (String(input).endsWith('/products')) {
			return Response.json(produtos)
		}

		return Response.json(loja)
	})

	await abrirPagina()
	expect(auth.sessaoVerificada).toBe(false)
	expect(container.querySelector('.imagem-hero-loja')).not.toBeNull()

	await act(async () => {
		concluirRefresh(new Response(null, { status: 401 }))
	})

	expect(window.location.pathname).toBe('/saint')
	expect(container.querySelector('.hero-loja-capa')).not.toBeNull()
})


it.each(['nenhuma', 'logo', 'cover'])('aceita loja com %s imagem sem usar imagens de teste', async tipo => {
	if (tipo !== 'logo') {
		loja.logo = null
	}

	if (tipo !== 'cover') {
		loja.cover = null
	}

	await abrirPagina()
	expect(window.location.pathname).toBe('/saint')
	expect(container.querySelector('.hero-loja-capa')).not.toBeNull()
	expect(Boolean(container.querySelector('.imagem-hero-loja'))).toBe(tipo === 'cover')
	expect(Boolean(container.querySelector('.logo-hero-loja img'))).toBe(tipo === 'logo')

	if (tipo !== 'logo') {
		expect(container.querySelector('.perfil-hero-loja h2')?.textContent).toBe('Saint')
	}
})


it('usa referências antigas de PNG e JPEG quando há somente uma variante', async () => {
	loja.logo = { medium: { url: 'https://storage.noma.test/logo-antiga.png', mime_type: 'image/png', width: 600, height: 400, size_bytes: 1000 } }
	loja.cover = { large: { url: 'https://storage.noma.test/capa-antiga.jpg', mime_type: 'image/jpeg', width: 2000, height: 1200, size_bytes: 5000 } }

	await abrirPagina()
	expect(container.querySelector('.logo-hero-loja img')?.getAttribute('src')).toBe(loja.logo.medium?.url)
	expect(container.querySelector('.imagem-hero-loja')?.getAttribute('src')).toBe(loja.cover.large?.url)
})


it('redireciona para o Feed quando a API retorna 404', async () => {
	fetchMock.mockResolvedValue(new Response(null, { status: 404 }))
	await abrirPagina('/inexistente')

	expect(window.location.pathname).toBe('/')
	expect(container.querySelector('.pages-feed')).not.toBeNull()
})


it.each([500, 503, 'conexao'])('mantém a página em falha %s e permite tentar novamente', async falha => {
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}

		if (falha === 'conexao') {
			throw new TypeError('Failed to fetch')
		}

		return new Response(null, { status: Number(falha) })
	})

	await abrirPagina()
	expect(window.location.pathname).toBe('/saint')
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('Não foi possível carregar a loja.')

	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/products')) {
			return Response.json(produtos)
		}
		return Response.json(loja)
	})
	await act(async () => {
		container.querySelector('.mensagem-loja button')!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
	})

	expect(container.querySelector('[role="alert"]')).toBeNull()
	expect(container.querySelector('.imagem-hero-loja')?.getAttribute('src')).toBe(loja.cover?.medium?.url)
})


it('uma imagem quebrada mantém a loja aberta e a logo pode cair para o nome', async () => {
	await abrirPagina()

	await act(async () => {
		container.querySelector('.imagem-hero-loja')!.dispatchEvent(new Event('error'))
		container.querySelector('.logo-hero-loja img')!.dispatchEvent(new Event('error'))
	})

	expect(window.location.pathname).toBe('/saint')
	expect(container.querySelector('.hero-loja-capa')).not.toBeNull()
	expect(container.querySelector('.imagem-hero-loja')).toBeNull()
	expect(container.querySelector('.perfil-hero-loja h2')?.textContent).toBe('Saint')
})


it('trocar o slug cancela a consulta anterior e ignora respostas atrasadas', async () => {
	const pendentes: Array<(response: Response) => void> = []
	const sinais: AbortSignal[] = []
	fetchMock.mockImplementation(async (input, options) => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}

		if (String(input).endsWith('/products')) {
			return Response.json([])
		}

		if (String(input).endsWith('/stores/slug/saint')) {
			sinais.push(options!.signal!)
			return new Promise(resolve => { pendentes.push(resolve) })
		}

		return Response.json({ ...loja, id: 'loja-adora', name: 'Adora', slug: 'adora', logo: null, cover: null })
	})

	await abrirPagina()
	expect(container.querySelector('.mensagem-loja')?.textContent).toBe('Carregando loja...')

	await act(async () => {
		window.history.pushState({}, '', '/adora')
		window.dispatchEvent(new PopStateEvent('popstate'))
	})

	expect(container.querySelector('.perfil-hero-loja h2')?.textContent).toBe('Adora')
	expect(sinais.every(signal => signal.aborted)).toBe(true)

	await act(async () => {
		for (const concluir of pendentes) {
			concluir(Response.json(loja))
		}
	})

	expect(window.location.pathname).toBe('/adora')
	expect(container.querySelector('.perfil-hero-loja h2')?.textContent).toBe('Adora')
})


it('exibe produtos reais com preço decimal formatado e primeira imagem ordenada', async () => {
	await abrirPagina()
	expect(container.querySelectorAll('.produto-loja')).toHaveLength(1)
	expect(container.querySelector('.imagem-produto-loja')?.getAttribute('src')).toBe(produtos[0].images[0].variants.card.url)
	expect(container.querySelector('.legenda-produto-loja h3')?.textContent).toBe('Camiseta real')
	expect(container.querySelector('.legenda-produto-loja p')?.textContent).toContain('149,90')
	expect(container.querySelector('.produto-loja')?.getAttribute('href')).toBe('/produto/produto-saint')

	const chamadas = fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/stores/loja-saint/products'))
	expect(chamadas.length).toBeGreaterThan(0)
	for (const [, options] of chamadas) {
		expect(new Headers(options?.headers).has('Authorization')).toBe(false)
		expect(options?.credentials).not.toBe('include')
	}
})


it('clicar no card abre o detalhe público do produto', async () => {
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		if (String(input).endsWith('/products/produto-saint')) {
			return Response.json(produtos[0])
		}
		if (String(input).endsWith('/products')) {
			return Response.json(produtos)
		}
		return Response.json(loja)
	})
	await abrirPagina()
	await act(async () => {
		container.querySelector<HTMLAnchorElement>('.produto-loja')!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }))
	})
	expect(window.location.pathname).toBe('/produto/produto-saint')
	expect(container.querySelector('.conteudo-produto h1')?.textContent).toBe('Camiseta real')
	expect(container.querySelector('.foto-galeria-produto img')?.getAttribute('src')).toBe(produtos[0].images[0].variants.large.url)
})


it('loja sem produtos mantém a hero e não exibe produtos fictícios', async () => {
	produtos = []
	await abrirPagina()
	expect(container.querySelector('.hero-loja-capa')).not.toBeNull()
	expect(container.querySelector('.faixa-produtos-loja')).toBeNull()
})


it('produto sem imagem usa espaço neutro sem foto mockada', async () => {
	produtos[0].images = []
	await abrirPagina()
	expect(container.querySelector('.imagem-produto-ausente')).not.toBeNull()
	expect(container.querySelector('.produto-loja img')).toBeNull()
	expect(container.querySelector('.legenda-produto-loja h3')?.textContent).toBe('Camiseta real')
})


it.each([500, 503, 401, 404, 'conexao', 'json', 'objeto', 'null'])('falha %s nos produtos preserva a loja e permite tentar novamente', async tipoFalha => {
	let falha = true
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		if (String(input).endsWith('/products')) {
			if (!falha) {
				return Response.json(produtos)
			}
			if (tipoFalha === 'conexao') {
				throw new TypeError('Failed to fetch')
			}
			if (tipoFalha === 'json') {
				return new Response('JSON inválido', { status: 200 })
			}
			if (tipoFalha === 'objeto') {
				return Response.json({ detail: 'Resposta inesperada' })
			}
			if (tipoFalha === 'null') {
				return Response.json(null)
			}
			return new Response(null, { status: Number(tipoFalha) })
		}
		return Response.json(loja)
	})
	await abrirPagina()
	expect(container.querySelector('.hero-loja-capa')).not.toBeNull()
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('Não foi possível carregar os produtos')
	expect(window.location.pathname).toBe('/saint')
	falha = false
	await act(async () => {
		container.querySelector('.mensagem-produtos-loja button')!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
	})
	expect(container.querySelector('[role="alert"]')).toBeNull()
	expect(container.querySelector('.legenda-produto-loja h3')?.textContent).toBe('Camiseta real')
	expect(fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/auth/refresh'))).toHaveLength(1)
})


it('trocar de loja ignora uma consulta de produtos atrasada', async () => {
	let concluirProdutos!: (response: Response) => void
	let sinal!: AbortSignal
	fetchMock.mockImplementation(async (input, options) => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		if (String(input).endsWith('/stores/loja-saint/products')) {
			sinal = options!.signal!
			return new Promise(resolve => { concluirProdutos = resolve })
		}
		if (String(input).endsWith('/products')) {
			return Response.json([])
		}
		if (String(input).endsWith('/stores/slug/adora')) {
			return Response.json({ ...loja, id: 'loja-adora', name: 'Adora', slug: 'adora', logo: null, cover: null })
		}
		return Response.json(loja)
	})
	await abrirPagina()
	expect(container.querySelector('.mensagem-produtos-loja')?.textContent).toContain('Carregando produtos')
	await act(async () => {
		window.history.pushState({}, '', '/adora')
		window.dispatchEvent(new PopStateEvent('popstate'))
	})
	expect(sinal.aborted).toBe(true)
	await act(async () => { concluirProdutos(Response.json(produtos)) })
	expect(container.querySelector('.perfil-hero-loja h2')?.textContent).toBe('Adora')
	expect(container.querySelector('.faixa-produtos-loja')).toBeNull()
})


it('imagem de produto quebrada usa espaço neutro e preserva nome, preço e demais produtos', async () => {
	produtos.push({ ...produtos[0], id: 'produto-02', name: 'Outra camiseta', price: '0.00', images: [{ ...produtos[0].images[0], id: 'imagem-02', variants: { card: { url: 'https://storage.noma.test/outra.webp' }, large: { url: 'https://storage.noma.test/outra-large.webp' } } }] })
	await abrirPagina()
	await act(async () => {
		container.querySelector('.produto-loja img')!.dispatchEvent(new Event('error'))
	})

	const cards = container.querySelectorAll('.produto-loja')
	expect(cards).toHaveLength(2)
	expect(cards[0].querySelector('img')).toBeNull()
	expect(cards[0].querySelector('.imagem-produto-ausente')).not.toBeNull()
	expect(cards[0].querySelector('h3')?.textContent).toBe('Camiseta real')
	expect(cards[0].querySelector('p')?.textContent).toContain('149,90')
	expect(cards[1].querySelector('img')?.getAttribute('src')).toBe('https://storage.noma.test/outra.webp')
	expect(cards[1].querySelector('p')?.textContent).toContain('0,00')
})


it('erro de produtos atrasado não aparece na próxima loja', async () => {
	let rejeitar!: (error: Error) => void
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		if (String(input).endsWith('/stores/loja-saint/products')) {
			return new Promise((_resolve, reject) => { rejeitar = reject })
		}
		if (String(input).endsWith('/products')) {
			return Response.json([])
		}
		if (String(input).endsWith('/stores/slug/adora')) {
			return Response.json({ ...loja, id: 'loja-adora', name: 'Adora', slug: 'adora', logo: null, cover: null })
		}
		return Response.json(loja)
	})
	await abrirPagina()
	await act(async () => {
		window.history.pushState({}, '', '/adora')
		window.dispatchEvent(new PopStateEvent('popstate'))
	})
	await act(async () => { rejeitar(new TypeError('Falha atrasada')) })
	expect(container.querySelector('.perfil-hero-loja h2')?.textContent).toBe('Adora')
	expect(container.querySelector('[role="alert"]')).toBeNull()
})
