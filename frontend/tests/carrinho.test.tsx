// @vitest-environment jsdom
import { StrictMode, act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App'
import { auth, definirSessao } from '../src/stores/auth'
import type { CarrinhoResponse, ItemCarrinhoResponse } from '../src/types/carrinho'


vi.mock('../src/config', () => ({ apiUrl: 'https://api.noma.test' }))

const fetchMock = vi.fn<typeof fetch>()
let container: HTMLDivElement
let root: Root
let carrinho: CarrinhoResponse


beforeEach(() => {
	definirSessao('token-valido')
	fetchMock.mockReset()
	vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
	vi.stubGlobal('fetch', fetchMock)
	carrinho = {
		id: 'carrinho-01', updated_at: '2026-10-14T12:00:00Z',
		items: [
			criarItem('item-01', 'Camiseta Saint', 'Saint', 1),
			criarItem('item-02', 'Camiseta Adora', 'Adora', 2),
			criarItem('item-03', 'Calça Saint', 'Saint', 1),
		]
	}
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}
		if (String(input).includes('/users/me/addresses')) {
			return Response.json([])
		}
		return Response.json(carrinho)
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


function criarItem(id: string, nome: string, loja: string, quantity: number): ItemCarrinhoResponse {
	return {
		id, product_id: `produto-${id}`, product: { id: `produto-${id}`, name: nome, description: 'Algodão e corte confortável.', sizes: ['G', 'M'] },
		image: { id: `foto-${id}`, position: 1, variants: { card: { url: `https://storage.noma.test/${id}/card.webp` }, large: { url: `https://storage.noma.test/${id}/large.webp` } } },
		size: 'M', quantity, unit_price: '199.90', subtotal: (199.90 * quantity).toFixed(2),
		store: { id: `loja-${loja}`, name: loja, slug: loja.toLowerCase(), description: null, logo_url: null }, available: true, unavailable_reason: null
	}
}


async function abrirPagina(path = '/carrinho') {
	window.history.replaceState({}, '', path)
	await act(async () => {
		root.render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>)
	})
}


async function clicar(selector: string) {
	await act(async () => { container.querySelector<HTMLButtonElement>(selector)!.click() })
}


async function trocarTamanho(size: string, indice = 0) {
	await act(async () => {
		const select = container.querySelectorAll<HTMLSelectElement>('.tamanho-item-carrinho select')[indice]
		select.value = size
		select.dispatchEvent(new Event('change', { bubbles: true }))
	})
}


it('mostra uma lista contínua na ordem da API, com dados reais e loja em cada item', async () => {
	await abrirPagina()
	const items = container.querySelectorAll('.lista-carrinho > .item-carrinho')
	expect(items).toHaveLength(3)
	expect(Array.from(items).map(item => item.querySelector('h2')?.textContent)).toEqual(carrinho.items.map(item => item.product!.name))
	expect(Array.from(items).map(item => item.querySelector('.loja-item-carrinho > span:last-child')?.textContent)).toEqual(['Saint', 'Adora', 'Saint'])
	expect(items[0].querySelector('.descricao-item-carrinho')?.textContent).toBe('Algodão e corte confortável.')
	expect(items[0].querySelector('.preco-item-carrinho')?.textContent).toContain('199,90')
	expect(items[0].querySelector('img')?.getAttribute('src')).toContain('/item-01/card.webp')
	expect(items[0].querySelector('h2 a')?.getAttribute('href')).toBe('/produto/produto-item-01')
	expect(items[0].querySelector('.loja-item-carrinho')?.getAttribute('href')).toBe('/saint')
	expect(items[0].querySelector('select')?.value).toBe('M')
	expect(container.querySelectorAll('.lista-carrinho')).toHaveLength(1)
	expect(container.querySelector('.titulo-carrinho')?.textContent).toBe('CARRINHO04')
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe('R$ 799,60')
	expect(container.querySelector('.frete-resumo-carrinho')?.textContent).toBe('Frete calculado no final da compra.')
	expect(fetchMock.mock.calls.every(([input, options]) => String(input).endsWith('/cart') && new Headers(options?.headers).get('Authorization') === 'Bearer token-valido')).toBe(true)
})


it('mostra a logo real de cada loja sem buscar a loja separadamente por item', async () => {
	for (const item of carrinho.items) {
		item.store!.logo_url = `https://storage.noma.test/${item.store!.slug}/small.webp`
	}
	await abrirPagina()
	const logos = Array.from(container.querySelectorAll('.icone-loja-carrinho img'))
	expect(logos.map(logo => logo.getAttribute('src'))).toEqual(['https://storage.noma.test/saint/small.webp', 'https://storage.noma.test/adora/small.webp', 'https://storage.noma.test/saint/small.webp'])
	expect(fetchMock.mock.calls.every(([input]) => String(input).endsWith('/cart'))).toBe(true)
})


it('lojas sem logo usam a inicial e continuam com nome e link corretos', async () => {
	await abrirPagina()
	expect(container.querySelector('.icone-loja-carrinho img')).toBeNull()
	expect(Array.from(container.querySelectorAll('.icone-loja-carrinho')).map(icone => icone.textContent)).toEqual(['S', 'A', 'S'])
	expect(container.querySelector('.loja-item-carrinho')?.getAttribute('href')).toBe('/saint')
})


it('logo quebrada usa a inicial e tenta a imagem novamente quando sua URL muda', async () => {
	carrinho.items[0].store!.logo_url = 'https://storage.noma.test/saint/antiga.webp'
	await abrirPagina()
	await act(async () => { container.querySelector('.icone-loja-carrinho img')!.dispatchEvent(new Event('error')) })
	expect(container.querySelector('.icone-loja-carrinho img')).toBeNull()
	expect(container.querySelector('.icone-loja-carrinho')?.textContent).toBe('S')
	expect(container.querySelector('.foto-item-carrinho img')).not.toBeNull()
	fetchMock.mockImplementation(async () => {
		carrinho.items[0].store!.logo_url = 'https://storage.noma.test/saint/nova.webp'
		carrinho.items[0].quantity = 2
		return Response.json(carrinho)
	})
	await clicar('[aria-label="Aumentar quantidade de Camiseta Saint"]')
	expect(container.querySelector('.icone-loja-carrinho img')?.getAttribute('src')).toBe('https://storage.noma.test/saint/nova.webp')
})


it('o ícone do Header navega para o carrinho sem tratar carrinho como slug de loja', async () => {
	await abrirPagina('/')
	const link = container.querySelector<HTMLAnchorElement>('.header a[href="/carrinho"]')!
	expect(link).not.toBeNull()
	await act(async () => { link.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })) })
	expect(window.location.pathname).toBe('/carrinho')
	expect(container.querySelector('.titulo-carrinho')?.textContent).toBe('CARRINHO04')
	expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/stores/slug/carrinho'))).toBe(false)
})


it.each(['aumentar', 'diminuir'])('envia quantidade inteira ao %s e usa o carrinho retornado pelo PATCH', async acao => {
	await abrirPagina()
	const quantidade = acao === 'aumentar' ? 3 : 1
	fetchMock.mockImplementation(async (input, options) => {
		expect(String(input)).toBe('https://api.noma.test/cart/items/item-02')
		expect(options?.method).toBe('PATCH')
		expect(new Headers(options?.headers).get('Content-Type')).toBe('application/json')
		expect(JSON.parse(String(options?.body))).toEqual({ quantity: quantidade })
		carrinho.items[1].quantity = quantidade
		carrinho.items[1].unit_price = '209.90'
		return Response.json(carrinho)
	})
	await clicar(`[aria-label="${acao === 'aumentar' ? 'Aumentar' : 'Diminuir'} quantidade de Camiseta Adora"]`)
	expect(container.querySelectorAll('.valor-quantidade-carrinho')[1].textContent).toBe(String(quantidade).padStart(2, '0'))
	expect(container.querySelectorAll('.preco-item-carrinho')[1].textContent).toContain('209,90')
	expect(container.querySelector('.titulo-carrinho sup')?.textContent).toBe(String(quantidade + 2).padStart(2, '0'))
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe(acao === 'aumentar' ? 'R$ 1.029,50' : 'R$ 609,70')
})


it('não permite diminuir abaixo de um nem exceder o limite inteiro da API', async () => {
	carrinho.items[1].quantity = 2147483647
	await abrirPagina()
	expect(container.querySelector<HTMLButtonElement>('[aria-label="Diminuir quantidade de Camiseta Saint"]')?.disabled).toBe(true)
	expect(container.querySelector<HTMLButtonElement>('[aria-label="Aumentar quantidade de Camiseta Adora"]')?.disabled).toBe(true)
})


it('envia apenas o tamanho escolhido e preserva a quantidade devolvida pela API', async () => {
	await abrirPagina()
	fetchMock.mockImplementation(async (input, options) => {
		expect(String(input)).toBe('https://api.noma.test/cart/items/item-01')
		expect(options?.method).toBe('PATCH')
		expect(JSON.parse(String(options?.body))).toEqual({ size: 'G' })
		carrinho.items[0].size = 'G'
		return Response.json(carrinho)
	})
	await trocarTamanho('G')
	expect(container.querySelector('select')?.value).toBe('G')
	expect(container.querySelector('.valor-quantidade-carrinho')?.textContent).toBe('01')
})


it('reflete a união de itens feita pelo backend ao trocar para um tamanho já presente', async () => {
	carrinho.items[1] = { ...carrinho.items[0], id: 'item-02', size: 'G', quantity: 2 }
	await abrirPagina()
	fetchMock.mockImplementation(async () => {
		carrinho.items[1].quantity = 3
		carrinho.items = [carrinho.items[1], carrinho.items[2]]
		return Response.json(carrinho)
	})
	await trocarTamanho('G')
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(2)
	expect(container.querySelector('.valor-quantidade-carrinho')?.textContent).toBe('03')
	expect(container.querySelector('select')?.value).toBe('G')
	expect(container.querySelector('.titulo-carrinho sup')?.textContent).toBe('04')
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe('R$ 799,60')
})


it('aguarda confirmação para remover, bloqueia ações concorrentes e recarrega após o 204', async () => {
	await abrirPagina()
	let concluir!: (response: Response) => void
	fetchMock.mockImplementation(async (input, options) => {
		if (options?.method === 'DELETE') {
			expect(String(input)).toBe('https://api.noma.test/cart/items/item-01')
			return new Promise(resolve => { concluir = resolve })
		}
		expect(String(input)).toBe('https://api.noma.test/cart')
		return Response.json(carrinho)
	})
	await clicar('[aria-label="Remover Camiseta Saint do carrinho"]')
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(3)
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe('R$ 799,60')
	expect(container.querySelector('.lista-carrinho')?.getAttribute('aria-busy')).toBe('true')
	expect(Array.from(container.querySelectorAll<HTMLButtonElement>('.lista-carrinho button')).every(button => button.disabled)).toBe(true)
	expect(container.querySelector<HTMLButtonElement>('.limpar-carrinho')?.disabled).toBe(true)
	carrinho.items = carrinho.items.slice(1)
	carrinho.items[0].unit_price = '219.90'
	await act(async () => { concluir(new Response(null, { status: 204 })) })
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(2)
	expect(container.querySelector('.preco-item-carrinho')?.textContent).toContain('219,90')
	expect(container.querySelector('.titulo-carrinho sup')?.textContent).toBe('03')
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe('R$ 639,70')
	expect(container.querySelector('.lista-carrinho')?.getAttribute('aria-busy')).toBe('false')
})


it.each(['ultimo', 'todos'])('remover %s mostra carrinho vazio e atualiza o contador', async caso => {
	if (caso === 'ultimo') {
		carrinho.items = [carrinho.items[0]]
	}
	await abrirPagina()
	fetchMock.mockImplementation(async (input, options) => {
		if (options?.method === 'DELETE') {
			expect(String(input)).toBe(`https://api.noma.test/cart${caso === 'ultimo' ? '/items/item-01' : ''}`)
			carrinho.items = []
			return new Response(null, { status: 204 })
		}
		return Response.json(carrinho)
	})
	await clicar(caso === 'ultimo' ? '[aria-label="Remover Camiseta Saint do carrinho"]' : '.limpar-carrinho')
	expect(container.querySelector('.carrinho-vazio p')?.textContent).toBe('Seu carrinho está vazio.')
	expect(container.querySelector('.carrinho-vazio a')?.getAttribute('href')).toBe('/')
	expect(container.querySelector('.titulo-carrinho sup')?.textContent).toBe('00')
	expect(container.querySelector('.lista-carrinho')).toBeNull()
	expect(container.querySelector('.limpar-carrinho')).toBeNull()
	expect(container.querySelector('.resumo-carrinho')).toBeNull()
	expect(container.querySelector('.carrinho-com-resumo')).toBeNull()
})


it('carrinho ainda não criado exibe estado vazio sem fazer POST', async () => {
	carrinho = { id: null, updated_at: null, items: [] }
	await abrirPagina()
	expect(container.querySelector('.carrinho-vazio')).not.toBeNull()
	expect(container.querySelector('.resumo-carrinho')).toBeNull()
	expect(fetchMock.mock.calls.every(([, options]) => !options?.method)).toBe(true)
})


it.each(['sem imagem', 'imagem quebrada'])('produto com %s mantém nome, preço e controles', async caso => {
	if (caso === 'sem imagem') {
		carrinho.items[0].image = null
	}
	await abrirPagina()
	if (caso === 'imagem quebrada') {
		await act(async () => { container.querySelector('.foto-item-carrinho img')!.dispatchEvent(new Event('error')) })
	}
	expect(container.querySelector('.foto-item-carrinho > span')?.textContent).toBe(caso === 'sem imagem' ? 'Sem imagem' : 'Imagem indisponível')
	expect(container.querySelector('.dados-item-carrinho h2')?.textContent).toBe('Camiseta Saint')
	expect(container.querySelector<HTMLButtonElement>('[aria-label="Aumentar quantidade de Camiseta Saint"]')?.disabled).toBe(false)
})


it.each(['size_unavailable', 'size_removed', 'product_removed'] as const)('preserva item inválido (%s), informa o problema e mantém remoção', async motivo => {
	const item = carrinho.items[0]
	item.available = false
	item.unavailable_reason = motivo
	item.product!.sizes = ['G']
	if (motivo === 'product_removed') {
		Object.assign(item, { product_id: null, product: null, image: null, store: null, unit_price: null, subtotal: null })
	}
	await abrirPagina()
	const linha = container.querySelector('.item-indisponivel-carrinho')!
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(3)
	expect(linha.querySelector('.aviso-item-carrinho')?.textContent).toContain(motivo === 'product_removed' ? 'produto não está mais disponível' : 'tamanho M não está mais disponível')
	expect(Array.from(linha.querySelectorAll<HTMLButtonElement>('.quantidade-item-carrinho button')).slice(0, 2).every(button => button.disabled)).toBe(true)
	expect(linha.querySelector<HTMLButtonElement>('.remover-item-carrinho')?.disabled).toBe(false)
	expect(linha.querySelector('select')?.value).toBe('M')
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe(motivo === 'product_removed' ? 'R$ 599,70' : 'R$ 799,60')
	if (motivo === 'product_removed') {
		expect(linha.querySelector('.preco-item-carrinho')).toBeNull()
		expect(linha.querySelector<HTMLSelectElement>('select')?.disabled).toBe(true)
	} else {
		expect(linha.querySelector<HTMLSelectElement>('select')?.disabled).toBe(false)
		expect(linha.querySelector('option')?.disabled).toBe(true)
	}
})


it('permite recuperar item com tamanho indisponível escolhendo outro disponível', async () => {
	carrinho.items[0].available = false
	carrinho.items[0].unavailable_reason = 'size_unavailable'
	carrinho.items[0].product!.sizes = ['G']
	await abrirPagina()
	fetchMock.mockImplementation(async () => {
		Object.assign(carrinho.items[0], { size: 'G', available: true, unavailable_reason: null })
		return Response.json(carrinho)
	})
	await trocarTamanho('G')
	expect(container.querySelector('.item-indisponivel-carrinho')).toBeNull()
	expect(container.querySelector('select')?.value).toBe('G')
})


it('produto sem tamanhos disponíveis desabilita somente quantidade/tamanho e permite remover', async () => {
	carrinho.items[0].product!.sizes = []
	carrinho.items[0].available = false
	carrinho.items[0].unavailable_reason = 'size_unavailable'
	await abrirPagina()
	expect(container.querySelector<HTMLSelectElement>('select')?.disabled).toBe(true)
	expect(container.querySelector<HTMLButtonElement>('.remover-item-carrinho')?.disabled).toBe(false)
})


it.each([409, 404])('PATCH rejeitado com %s recarrega disponibilidade sem apagar o item', async status => {
	await abrirPagina()
	fetchMock.mockImplementation(async (_input, options) => {
		if (options?.method === 'PATCH') {
			carrinho.items[0].available = false
			carrinho.items[0].unavailable_reason = 'size_unavailable'
			carrinho.items[0].product!.sizes = ['G']
			return Response.json({ detail: 'Tamanho indisponível neste produto.' }, { status })
		}
		return Response.json(carrinho)
	})
	await clicar('[aria-label="Aumentar quantidade de Camiseta Saint"]')
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(3)
	expect(container.querySelector('.aviso-item-carrinho')?.textContent).toContain('não está mais disponível')
	expect(container.querySelector('[role="alert"]')?.textContent).toBe('Tamanho indisponível neste produto.')
	expect(container.querySelector<HTMLButtonElement>('.remover-item-carrinho')?.disabled).toBe(false)
	expect(container.querySelector('.lista-carrinho')?.getAttribute('aria-busy')).toBe('false')
})


it.each(['PATCH', 'DELETE', 'limpar'])('falha em %s preserva itens e mostra erro recuperável', async acao => {
	await abrirPagina()
	fetchMock.mockResolvedValue(Response.json({ detail: 'Serviço temporariamente indisponível.' }, { status: 503 }))
	const selector = acao === 'PATCH' ? '[aria-label="Aumentar quantidade de Camiseta Saint"]' : acao === 'DELETE' ? '[aria-label="Remover Camiseta Saint do carrinho"]' : '.limpar-carrinho'
	await clicar(selector)
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(3)
	expect(container.querySelector('[role="alert"]')?.textContent).toBe('Serviço temporariamente indisponível.')
	expect(container.querySelector<HTMLButtonElement>('.limpar-carrinho')?.disabled).toBe(false)
})


it.each(['conexao', 'json', 'formato', '422'])('erro %s durante PATCH mostra mensagem simples sem alterar quantidade', async falha => {
	await abrirPagina()
	fetchMock.mockImplementation(async () => {
		if (falha === 'conexao') {
			throw new TypeError('Failed to fetch')
		}
		if (falha === 'json') {
			return new Response('JSON inválido')
		}
		if (falha === '422') {
			return Response.json({ detail: [{ msg: 'invalid' }] }, { status: 422 })
		}
		return Response.json({ inesperado: true })
	})
	await clicar('[aria-label="Aumentar quantidade de Camiseta Saint"]')
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('Não foi possível atualizar o carrinho.')
	expect(container.querySelector('.valor-quantidade-carrinho')?.textContent).toBe('01')
})


it('DELETE confirmado com falha no GET seguinte mantém a remoção e permite recarregar', async () => {
	await abrirPagina()
	fetchMock.mockImplementation(async (_input, options) => {
		if (options?.method === 'DELETE') {
			carrinho.items = carrinho.items.slice(1)
			return new Response(null, { status: 204 })
		}
		throw new TypeError('Failed to fetch')
	})
	await clicar('[aria-label="Remover Camiseta Saint do carrinho"]')
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(2)
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('Remoção concluída')
	fetchMock.mockResolvedValue(Response.json(carrinho))
	await clicar('.mensagem-carrinho button')
	expect(container.querySelector('[role="alert"]')).toBeNull()
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(2)
})


it.each([500, 'conexao', 'json', 'formato'])('falha %s ao carregar permite tentar novamente', async falha => {
	fetchMock.mockImplementation(async () => {
		if (falha === 'conexao') {
			throw new TypeError('Failed to fetch')
		}
		if (falha === 'json') {
			return new Response('JSON inválido')
		}
		if (falha === 'formato') {
			return Response.json({ detail: 'Formato inesperado' })
		}
		return new Response(null, { status: Number(falha) })
	})
	await abrirPagina()
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('Não foi possível carregar o carrinho.')
	fetchMock.mockResolvedValue(Response.json(carrinho))
	await clicar('.mensagem-carrinho button')
	expect(container.querySelector('[role="alert"]')).toBeNull()
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(3)
})


it('loading aguarda o GET sem mostrar carrinho vazio', async () => {
	let concluir!: (response: Response) => void
	fetchMock.mockReturnValue(new Promise(resolve => { concluir = resolve }))
	await abrirPagina()
	expect(container.querySelector('[role="status"]')?.textContent).toBe('Carregando carrinho...')
	expect(container.querySelector('.carrinho-vazio')).toBeNull()
	expect(container.querySelector('.resumo-carrinho')).toBeNull()
	await act(async () => { concluir(Response.json(carrinho)) })
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(3)
})


it('após F5 aguarda o refresh e abre o carrinho sem passar por Acesso', async () => {
	auth.accessToken = ''
	auth.sessaoVerificada = false
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Promise(resolve => { concluirRefresh = resolve })
		}
		return Response.json(carrinho)
	})
	await abrirPagina()
	expect(window.location.pathname).toBe('/carrinho')
	expect(container.querySelector('[role="status"]')?.textContent).toBe('Verificando sessão...')
	expect(container.querySelector('.pages-acesso')).toBeNull()
	await act(async () => { concluirRefresh(Response.json({ access_token: 'token-recuperado', token_type: 'bearer' })) })
	expect(window.location.pathname).toBe('/carrinho')
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(3)
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(1)
})


it('visitante é direcionado para Acesso depois da verificação, sem consultar o carrinho', async () => {
	auth.accessToken = ''
	auth.sessaoVerificada = false
	await abrirPagina()
	expect(window.location.pathname).toBe('/acesso')
	expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/cart'))).toBe(false)
})


it('JWT expirado renova uma vez e repete a consulta usando o novo token', async () => {
	definirSessao('token-expirado')
	fetchMock.mockImplementation(async (input, options) => {
		if (String(input).endsWith('/auth/refresh')) {
			return Response.json({ access_token: 'token-renovado', token_type: 'bearer' })
		}
		if (new Headers(options?.headers).get('Authorization') === 'Bearer token-expirado') {
			return new Response(null, { status: 401 })
		}
		return Response.json(carrinho)
	})
	await abrirPagina()
	expect(window.location.pathname).toBe('/carrinho')
	expect(container.querySelectorAll('.item-carrinho')).toHaveLength(3)
	expect(auth.accessToken).toBe('token-renovado')
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(1)
})


it.each(['GET', 'PATCH', 'DELETE'])('401 definitivo em %s redireciona sem loop', async method => {
	if (method !== 'GET') {
		await abrirPagina()
	}
	fetchMock.mockResolvedValue(new Response(null, { status: 401 }))
	if (method === 'GET') {
		await abrirPagina()
	} else {
		await clicar(method === 'PATCH' ? '[aria-label="Aumentar quantidade de Camiseta Saint"]' : '[aria-label="Remover Camiseta Saint do carrinho"]')
	}
	expect(window.location.pathname).toBe('/acesso')
	expect(auth.accessToken).toBe('')
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(1)
})


it.each(['GET', 'PATCH', 'DELETE'])('sair da página cancela %s e ignora resposta atrasada', async method => {
	if (method !== 'GET') {
		await abrirPagina()
	}
	const pendentes: Array<{ resolve: (response: Response) => void; signal: AbortSignal }> = []
	fetchMock.mockImplementation(async (_input, options) => new Promise(resolve => { pendentes.push({ resolve, signal: options!.signal! }) }))
	if (method === 'GET') {
		await abrirPagina()
	} else {
		await clicar(method === 'PATCH' ? '[aria-label="Aumentar quantidade de Camiseta Saint"]' : '[aria-label="Remover Camiseta Saint do carrinho"]')
	}
	await act(async () => {
		window.history.pushState({}, '', '/')
		window.dispatchEvent(new PopStateEvent('popstate'))
	})
	expect(pendentes.every(item => item.signal.aborted)).toBe(true)
	await act(async () => { pendentes.forEach(item => item.resolve(new Response(null, { status: 401 }))) })
	expect(window.location.pathname).toBe('/')
	expect(container.querySelector('.pages-carrinho')).toBeNull()
})


it('subtotal usa preço atual e quantidade com centavos exatos, sem somar o campo subtotal da API', async () => {
	carrinho.items = [
		{ ...carrinho.items[0], unit_price: '0.10', quantity: 3, subtotal: '9999.99' },
		{ ...carrinho.items[1], unit_price: '0.20', quantity: 1, subtotal: '9999.99' },
	]
	await abrirPagina()
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe('R$ 0,50')
})


it('subtotal preserva centavos mesmo quando a multiplicação ultrapassa inteiros seguros de Number', async () => {
	carrinho.items = [{ ...carrinho.items[0], unit_price: '99999999.99', quantity: 2147483647 }]
	await abrirPagina()
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe('R$ 214.748.364.678.525.163,53')
})


it('produto gratuito mantém subtotal zero e o resumo visível enquanto houver item', async () => {
	carrinho.items = [{ ...carrinho.items[0], unit_price: '0.00' }]
	await abrirPagina()
	expect(container.querySelector('.resumo-carrinho')).not.toBeNull()
	expect(container.querySelector('.valor-subtotal-carrinho')?.textContent).toBe('R$ 0,00')
})


it('Finalizar Compra abre o checkout e carrega endereços sem iniciar pagamento', async () => {
	await abrirPagina()
	const consultas = fetchMock.mock.calls.length
	expect(container.querySelector<HTMLButtonElement>('.finalizar-compra-carrinho')?.disabled).toBe(false)
	await clicar('.finalizar-compra-carrinho')
	expect(window.location.pathname).toBe('/checkout')
	expect(container.querySelector('.formulario-checkout')).not.toBeNull()
	expect(fetchMock.mock.calls.slice(consultas).every(([input, options]) => String(input).includes('/users/me/addresses') && !options?.method)).toBe(true)
	const consultasCheckout = fetchMock.mock.calls.length
	await clicar('input[value="pix"]')
	expect(container.querySelector('.campos-cartao-checkout')).toBeNull()
	await clicar('input[value="cartao"]')
	expect(container.querySelector('.campos-cartao-checkout')).not.toBeNull()
	expect(fetchMock.mock.calls).toHaveLength(consultasCheckout)
})
