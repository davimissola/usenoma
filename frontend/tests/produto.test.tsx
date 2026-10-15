// @vitest-environment jsdom
import { StrictMode, act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App'
import { auth, definirSessao } from '../src/stores/auth'
import type { CarrinhoResponse } from '../src/types/carrinho'
import type { ProdutoResponse } from '../src/types/produtos'


vi.mock('../src/config', () => ({ apiUrl: 'https://api.noma.test' }))

const fetchMock = vi.fn<typeof fetch>()
let container: HTMLDivElement
let root: Root
let produto: ProdutoResponse
let carrinho: CarrinhoResponse


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
	carrinho = {
		id: 'carrinho-01', updated_at: '2026-10-14T12:00:00Z',
		items: [{ id: 'item-01', product_id: produto.id, product: { id: produto.id, name: produto.name, description: produto.description, sizes: ['PP', 'M'] }, image: produto.images[0], size: 'M', quantity: 1, unit_price: produto.price, subtotal: produto.price, store: { id: produto.store_id, name: 'Saint', slug: 'saint', description: null, logo_url: null }, available: true, unavailable_reason: null }]
	}
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		if (String(input).endsWith('/cart') || String(input).endsWith('/cart/items')) {
			return Response.json(carrinho)
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


it('carrega detalhe público, imagens em ordem e preço, aguardando selecionar tamanho para adicionar', async () => {
	await abrirPagina()
	expect(container.querySelector('.conteudo-produto h1')?.textContent).toBe(produto.name)
	expect(container.querySelector('.descricao-produto')?.textContent).toBe(produto.description)
	expect(container.querySelector('.preco-produto')?.textContent).toContain('199,90')
	expect(Array.from(container.querySelectorAll('.foto-galeria-produto img')).map(img => img.getAttribute('src'))).toEqual(produto.images.map(img => img.variants.large.url))
	expect(container.querySelectorAll('.indicador-imagem-produto')).toHaveLength(3)
	expect(container.querySelectorAll('.imagem-selecionada-produto')).toHaveLength(1)
	expect(container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')?.disabled).toBe(false)

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
	expect(container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')?.disabled).toBe(false)
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
	expect(container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')?.disabled).toBe(true)
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


async function selecionarTamanho(tamanho = 'M') {
	await act(async () => { container.querySelector<HTMLInputElement>(`.tamanho-produto input[value="${tamanho}"]`)!.click() })
}


async function adicionarAoCarrinho() {
	await act(async () => { container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')!.click() })
}


it('envia produto, tamanho e uma unidade com Bearer e abre o carrinho real após confirmar', async () => {
	definirSessao('token-valido')
	await abrirPagina()
	await selecionarTamanho()
	await adicionarAoCarrinho()

	const [input, options] = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')!
	expect(String(input)).toBe('https://api.noma.test/cart/items')
	expect(new Headers(options?.headers).get('Authorization')).toBe('Bearer token-valido')
	expect(new Headers(options?.headers).get('Content-Type')).toBe('application/json')
	expect(JSON.parse(String(options?.body))).toEqual({ product_id: produto.id, size: 'M', quantity: 1 })
	expect(window.location.pathname).toBe('/carrinho')
	expect(container.querySelector('.item-carrinho h2')?.textContent).toBe(produto.name)
	expect(container.querySelector('select')?.value).toBe('M')
	expect(container.querySelector('.titulo-carrinho sup')?.textContent).toBe('01')
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(0)
})


it.each(['logado', 'visitante'])('sem selecionar tamanho, usuário %s recebe aviso e não envia nenhum item', async sessao => {
	if (sessao === 'logado') {
		definirSessao('token-valido')
	}
	await abrirPagina()
	expect(container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')?.disabled).toBe(false)
	const mensagem = container.querySelector('.validacao-tamanho-produto')!
	const botao = container.querySelector('.botao-carrinho-produto')!
	expect(mensagem.textContent).toBe('')
	expect(mensagem.getAttribute('role')).toBeNull()
	expect(mensagem.nextElementSibling).toBe(botao)
	await adicionarAoCarrinho()
	expect(window.location.pathname).toBe('/produto/produto-01')
	expect(mensagem.textContent).toBe('Selecione um tamanho')
	expect(mensagem.getAttribute('role')).toBe('alert')
	expect(container.querySelector('.validacao-tamanho-produto')).toBe(mensagem)
	expect(container.querySelector('.botao-carrinho-produto')).toBe(botao)
	expect(container.querySelector('.tamanhos-produto-erro')?.getAttribute('aria-invalid')).toBe('true')
	expect(container.querySelector('.erro-carrinho-produto')).toBeNull()
	expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/cart/items'))).toBe(false)
	await selecionarTamanho()
	expect(mensagem.textContent).toBe('')
	expect(mensagem.getAttribute('role')).toBeNull()
	expect(container.querySelector('.validacao-tamanho-produto')).toBe(mensagem)
	expect(container.querySelector('.tamanhos-produto-erro')).toBeNull()
	expect(container.querySelector('.tamanhos-produto')?.getAttribute('aria-invalid')).toBe('false')
	expect(container.querySelector('.erro-carrinho-produto')).toBeNull()
})


it('visitante vai para Acesso sem enviar POST de carrinho', async () => {
	await abrirPagina()
	await selecionarTamanho()
	await adicionarAoCarrinho()
	expect(window.location.pathname).toBe('/acesso')
	expect(container.querySelector('.conteudo-acesso-buttons')).not.toBeNull()
	expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/cart/items'))).toBe(false)
})


it('aguarda refresh do F5 antes de adicionar, mantendo a página pública carregada', async () => {
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Promise(resolve => { concluirRefresh = resolve })
		}
		if (String(input).endsWith('/cart/items') || String(input).endsWith('/cart')) {
			return Response.json(carrinho)
		}
		return Response.json(produto)
	})
	await abrirPagina()
	await selecionarTamanho()
	await adicionarAoCarrinho()
	expect(container.querySelector('.conteudo-produto h1')?.textContent).toBe(produto.name)
	expect(container.querySelector('.botao-carrinho-produto')?.textContent).toBe('Adicionando...')
	expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/cart/items'))).toBe(false)
	await act(async () => { concluirRefresh(Response.json({ access_token: 'token-recuperado', token_type: 'bearer' })) })
	expect(window.location.pathname).toBe('/carrinho')
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(1)
})


it('bloqueia cliques repetidos e troca de tamanho enquanto o POST está pendente', async () => {
	definirSessao('token-valido')
	await abrirPagina()
	await selecionarTamanho()
	let concluir!: (response: Response) => void
	fetchMock.mockImplementation(async (input, options) => {
		if (options?.method === 'POST') {
			return new Promise(resolve => { concluir = resolve })
		}
		expect(String(input)).toBe('https://api.noma.test/cart')
		return Response.json(carrinho)
	})
	await act(async () => {
		const botao = container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')!
		botao.click()
		botao.click()
	})
	expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
	expect(container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')?.disabled).toBe(true)
	expect(Array.from(container.querySelectorAll<HTMLInputElement>('.tamanho-produto input')).every(input => input.disabled)).toBe(true)
	expect(window.location.pathname).toBe('/produto/produto-01')
	await act(async () => { concluir(Response.json(carrinho)) })
	expect(window.location.pathname).toBe('/carrinho')
})


it.each([404, 409, 422, 503])('erro %s ao adicionar mantém produto e seleção, mostrando a mensagem da API', async status => {
	definirSessao('token-valido')
	await abrirPagina()
	await selecionarTamanho()
	fetchMock.mockResolvedValue(Response.json({ detail: 'Não foi possível adicionar este tamanho.' }, { status }))
	await adicionarAoCarrinho()
	expect(window.location.pathname).toBe('/produto/produto-01')
	expect(container.querySelector('.erro-carrinho-produto')?.textContent).toBe('Não foi possível adicionar este tamanho.')
	expect(container.querySelector<HTMLInputElement>('input[value="M"]')?.checked).toBe(true)
	expect(container.querySelector<HTMLButtonElement>('.botao-carrinho-produto')?.disabled).toBe(false)
	expect(auth.accessToken).toBe('token-valido')
})


it.each(['conexao', 'json', 'validacao'])('falha %s mostra mensagem simples sem repetir a adição automaticamente', async falha => {
	definirSessao('token-valido')
	await abrirPagina()
	await selecionarTamanho()
	fetchMock.mockImplementation(async () => {
		if (falha === 'conexao') {
			throw new TypeError('Failed to fetch')
		}
		if (falha === 'json') {
			return new Response('Erro interno privado', { status: 503 })
		}
		return Response.json({ detail: [{ msg: 'invalid' }] }, { status: 422 })
	})
	await adicionarAoCarrinho()
	expect(container.querySelector('.erro-carrinho-produto')?.textContent).toBe('Não foi possível adicionar o produto ao carrinho. Tente novamente.')
	expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
	expect(window.location.pathname).toBe('/produto/produto-01')
})


it('trocar tamanho limpa o erro e permite tentar adicionar novamente', async () => {
	definirSessao('token-valido')
	await abrirPagina()
	await selecionarTamanho('PP')
	fetchMock.mockResolvedValueOnce(Response.json({ detail: 'Tamanho indisponível.' }, { status: 409 }))
	await adicionarAoCarrinho()
	expect(container.querySelector('.erro-carrinho-produto')).not.toBeNull()
	await selecionarTamanho('M')
	expect(container.querySelector('.erro-carrinho-produto')).toBeNull()
	await adicionarAoCarrinho()
	expect(window.location.pathname).toBe('/carrinho')
	expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(2)
})


it.each(['valido', 'expirado', 'segundo-401'])('access expirado trata refresh %s sem loop na adição', async resultado => {
	definirSessao('token-expirado')
	let adicoes = 0
	fetchMock.mockImplementation(async (input, options) => {
		if (String(input).endsWith('/auth/refresh')) {
			if (resultado === 'expirado') {
				return new Response(null, { status: 401 })
			}
			return Response.json({ access_token: 'token-renovado', token_type: 'bearer' })
		}
		if (String(input).endsWith('/cart/items')) {
			adicoes++
			expect(JSON.parse(String(options?.body))).toEqual({ product_id: produto.id, size: 'M', quantity: 1 })
			if (new Headers(options?.headers).get('Authorization') === 'Bearer token-expirado' || resultado === 'segundo-401') {
				return new Response(null, { status: 401 })
			}
			return Response.json(carrinho)
		}
		if (String(input).endsWith('/cart')) {
			return Response.json(carrinho)
		}
		return Response.json(produto)
	})
	await abrirPagina()
	await selecionarTamanho()
	await adicionarAoCarrinho()
	expect(window.location.pathname).toBe(resultado === 'valido' ? '/carrinho' : '/acesso')
	expect(adicoes).toBe(resultado === 'expirado' ? 1 : 2)
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(1)
})


it.each(['sucesso', '401', 'erro'])('sair da página cancela adição e ignora resposta atrasada: %s', async resultado => {
	definirSessao('token-valido')
	await abrirPagina()
	await selecionarTamanho()
	let concluir!: (response: Response) => void
	let falhar!: (error: Error) => void
	let signal!: AbortSignal
	fetchMock.mockImplementation(async (input, options) => {
		if (String(input).endsWith('/auth/refresh')) {
			return Response.json({ access_token: 'token-renovado', token_type: 'bearer' })
		}
		return new Promise((resolve, reject) => {
			concluir = resolve
			falhar = reject
			signal = options!.signal!
		})
	})
	await adicionarAoCarrinho()
	await act(async () => {
		window.history.pushState({}, '', '/')
		window.dispatchEvent(new PopStateEvent('popstate'))
	})
	expect(signal.aborted).toBe(true)
	await act(async () => {
		if (resultado === 'erro') {
			falhar(new TypeError('Failed to fetch'))
		} else {
			concluir(resultado === '401' ? new Response(null, { status: 401 }) : Response.json(carrinho))
		}
	})
	expect(window.location.pathname).toBe('/')
	expect(container.querySelector('.erro-carrinho-produto')).toBeNull()
})
