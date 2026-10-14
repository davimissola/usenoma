// @vitest-environment jsdom
import { StrictMode, act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App'
import { auth } from '../src/stores/auth'
import type { ProdutoResponse } from '../src/types/produtos'


vi.mock('../src/config', () => ({ apiUrl: 'https://api.noma.test' }))

const fetchMock = vi.fn<typeof fetch>()
let container: HTMLDivElement
let root: Root
let produto: ProdutoResponse


beforeEach(() => {
	auth.accessToken = ''
	auth.sessaoVerificada = false
	fetchMock.mockReset()
	vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
	vi.stubGlobal('fetch', fetchMock)
	produto = {
		id: 'produto-01', store_id: 'loja-01', name: 'Camiseta NOMA', price: '199.90', description: 'Descrição do produto.\nSegunda linha.',
		sizes: [{ size: 'PP', available: true }, { size: 'M', available: true }],
		images: [1, 2, 3].map(position => ({ id: `imagem-${position}`, position, variants: { card: { url: `https://storage.noma.test/${position}/card.webp` }, large: { url: `https://storage.noma.test/${position}/large.webp` } } })),
	}
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		return Response.json(produto)
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


async function abrirPagina(path = '/produto/produto-01') {
	window.history.replaceState({}, '', path)
	await act(async () => {
		root.render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>)
	})
}


it('carrega detalhe público, imagens grandes em ordem e preço, sem iniciar compra', async () => {
	await abrirPagina()
	expect(container.querySelector('.conteudo-produto h1')?.textContent).toBe(produto.name)
	expect(container.querySelector('.descricao-produto')?.textContent).toBe(produto.description)
	expect(container.querySelector('.preco-produto')?.textContent).toContain('199,90')
	expect(Array.from(container.querySelectorAll('.foto-galeria-produto img')).map(img => img.getAttribute('src'))).toEqual(produto.images.map(img => img.variants.large.url))
	expect(container.querySelectorAll('.indicador-imagem-produto')).toHaveLength(3)
	expect(container.querySelectorAll('.imagem-selecionada-produto')).toHaveLength(1)
	expect(container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')?.disabled).toBe(true)

	const consultas = fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/products/produto-01'))
	expect(consultas.length).toBeGreaterThan(0)
	for (const [, options] of consultas) {
		expect(new Headers(options?.headers).has('Authorization')).toBe(false)
		expect(options?.credentials).not.toBe('include')
	}
})


it('seleciona um único tamanho e permite trocar a seleção', async () => {
	await abrirPagina()
	const tamanhos = container.querySelectorAll<HTMLInputElement>('.tamanho-produto input')
	expect(Array.from(tamanhos).map(input => input.value)).toEqual(['PP', 'M'])
	expect(Array.from(tamanhos).every(input => !input.checked)).toBe(true)
	await act(async () => { tamanhos[0].click() })
	expect(tamanhos[0].checked).toBe(true)
	await act(async () => { tamanhos[1].click() })
	expect(tamanhos[0].checked).toBe(false)
	expect(tamanhos[1].checked).toBe(true)
})


it('navega pelos pontos e teclado e atualiza o indicador após rolagem lateral', async () => {
	await abrirPagina()
	const lista = container.querySelector<HTMLDivElement>('.lista-imagens-produto')!
	Object.defineProperty(lista, 'clientWidth', { configurable: true, value: 366 })
	lista.scrollTo = vi.fn((options?: ScrollToOptions | number) => {
		if (typeof options === 'object') {
			lista.scrollLeft = options.left ?? 0
			lista.dispatchEvent(new Event('scroll'))
		}
	})
	await act(async () => { container.querySelector<HTMLButtonElement>('[aria-label="Ver imagem 3"]')!.click() })
	expect(lista.scrollTo).toHaveBeenCalledWith({ left: 732, behavior: 'smooth' })
	expect(container.querySelector('[aria-label="Ver imagem 3"]')?.getAttribute('aria-pressed')).toBe('true')
	await act(async () => { lista.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true, cancelable: true })) })
	expect(lista.scrollLeft).toBe(732)
	await act(async () => { lista.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true, cancelable: true })) })
	expect(lista.scrollLeft).toBe(366)
	expect(container.querySelector('[aria-label="Ver imagem 2"]')?.getAttribute('aria-pressed')).toBe('true')
	await act(async () => {
		lista.scrollLeft = 0
		lista.dispatchEvent(new Event('scroll'))
	})
	expect(container.querySelector('[aria-label="Ver imagem 1"]')?.getAttribute('aria-pressed')).toBe('true')
})


it('produto com uma imagem tem somente um indicador no mobile', async () => {
	produto.images = [produto.images[0]]
	await abrirPagina()
	expect(container.querySelectorAll('.foto-galeria-produto img')).toHaveLength(1)
	expect(container.querySelectorAll('.indicador-imagem-produto')).toHaveLength(1)
})


it.each([1, 2, 3, 4])('preenche os quatro slots desktop com %s imagens sem duplicar as fotos do mobile', async quantidade => {
	produto.images = Array.from({ length: quantidade }, (_, indice) => ({ id: `imagem-${indice + 1}`, position: indice + 1, variants: { card: { url: `https://storage.noma.test/${indice + 1}/card.webp` }, large: { url: `https://storage.noma.test/${indice + 1}/large.webp` } } }))
	await abrirPagina()

	const fotosDesktop = Array.from(container.querySelectorAll('.foto-grade-produto img')).map(img => img.getAttribute('src'))
	const esperadas = Array.from({ length: 4 }, (_, indice) => produto.images[indice % quantidade].variants.large.url)
	expect(fotosDesktop).toEqual(esperadas)
	expect(container.querySelectorAll('.foto-grade-produto')).toHaveLength(4)
	expect(container.querySelectorAll('.foto-galeria-produto')).toHaveLength(quantidade)
	expect(container.querySelectorAll('.indicador-imagem-produto')).toHaveLength(quantidade)
	expect(produto.images).toHaveLength(quantidade)
})


it('produto sem fotos, descrição e tamanhos continua exibindo seus dados reais', async () => {
	produto.images = []
	produto.sizes = []
	produto.description = null
	produto.price = '0.00'
	await abrirPagina()
	expect(container.querySelector('.imagem-ausente-produto')?.textContent).toBe('Produto sem imagem.')
	expect(container.querySelector('.descricao-produto')).toBeNull()
	expect(container.querySelector('.tamanhos-ausentes-produto')?.textContent).toBe('Nenhum tamanho disponível.')
	expect(container.querySelector('.preco-produto')?.textContent).toContain('0,00')
	expect(container.querySelector('.indicadores-imagens-produto')).toBeNull()
	expect(container.querySelectorAll('.foto-grade-produto')).toHaveLength(4)
	expect(container.querySelector('.grade-imagens-produto img')).toBeNull()
})


it('imagem quebrada não impede navegar para as demais ou ler o produto', async () => {
	await abrirPagina()
	await act(async () => { container.querySelector('.foto-galeria-produto img')!.dispatchEvent(new Event('error')) })
	expect(container.querySelector('.imagem-ausente-produto')?.textContent).toBe('Imagem indisponível.')
	expect(container.querySelectorAll('.foto-galeria-produto img')).toHaveLength(2)
	expect(container.querySelector('.conteudo-produto h1')?.textContent).toBe(produto.name)
	expect(container.querySelectorAll('.indicador-imagem-produto')).toHaveLength(3)
})


it.each([404, 422])('produto inexistente ou id inválido (%s) exibe estado próprio sem redirecionar', async status => {
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		return new Response(null, { status })
	})
	await abrirPagina()
	expect(window.location.pathname).toBe('/produto/produto-01')
	expect(container.querySelector('.mensagem-produto h1')?.textContent).toBe('Produto não encontrado.')
	expect(container.querySelector('.mensagem-produto a')?.getAttribute('href')).toBe('/')
	expect(container.querySelector('.botao-carrinho-produto')).toBeNull()
})


it.each([500, 503, 'conexao', 'json', 'formato'])('falha %s permite tentar novamente sem renovar autenticação', async falha => {
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		if (falha === 'conexao') {
			throw new TypeError('Failed to fetch')
		}
		if (falha === 'json') {
			return new Response('JSON inválido')
		}
		if (falha === 'formato') {
			return Response.json({ detail: 'Resposta inesperada' })
		}
		return new Response(null, { status: Number(falha) })
	})
	await abrirPagina()
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('Não foi possível carregar o produto.')
	fetchMock.mockResolvedValue(Response.json(produto))
	await act(async () => { container.querySelector<HTMLButtonElement>('.mensagem-produto button')!.click() })
	expect(container.querySelector('[role="alert"]')).toBeNull()
	expect(container.querySelector('.conteudo-produto h1')?.textContent).toBe(produto.name)
	expect(fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/auth/refresh'))).toHaveLength(1)
})


it('mostra loading e carrega o produto enquanto a sessão ainda está pendente', async () => {
	let concluirProduto!: (response: Response) => void
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Promise(resolve => { concluirRefresh = resolve })
		}
		return new Promise(resolve => { concluirProduto = resolve })
	})
	await abrirPagina()
	expect(container.querySelector('[role="status"]')?.textContent).toBe('Carregando produto...')
	await act(async () => { concluirProduto(Response.json(produto)) })
	expect(container.querySelector('.conteudo-produto h1')?.textContent).toBe(produto.name)
	expect(auth.sessaoVerificada).toBe(false)
	await act(async () => { concluirRefresh(new Response(null, { status: 401 })) })
})


it.each(['sucesso', 'erro', '404'])('trocar produto cancela a consulta anterior e ignora resultado atrasado: %s', async resultado => {
	const pendentes: Array<{ resolve: (response: Response) => void; reject: (error: Error) => void; signal: AbortSignal }> = []
	fetchMock.mockImplementation(async (input, options) => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		if (String(input).endsWith('/products/produto-01')) {
			return new Promise((resolve, reject) => { pendentes.push({ resolve, reject, signal: options!.signal! }) })
		}
		return Response.json({ ...produto, id: 'produto-02', name: 'Outro produto', images: [], sizes: [] })
	})
	await abrirPagina()
	await act(async () => {
		window.history.pushState({}, '', '/produto/produto-02')
		window.dispatchEvent(new PopStateEvent('popstate'))
	})
	expect(pendentes.every(item => item.signal.aborted)).toBe(true)
	await act(async () => {
		for (const item of pendentes) {
			if (resultado === 'erro') {
				item.reject(new TypeError('Falha atrasada'))
			} else if (resultado === '404') {
				item.resolve(new Response(null, { status: 404 }))
			} else {
				item.resolve(Response.json(produto))
			}
		}
	})
	expect(container.querySelector('.conteudo-produto h1')?.textContent).toBe('Outro produto')
	expect(container.querySelector('[role="alert"]')).toBeNull()
	expect(container.querySelector('.mensagem-produto')).toBeNull()
})
