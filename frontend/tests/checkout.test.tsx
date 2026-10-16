// @vitest-environment jsdom
import { StrictMode, act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App'
import { definirSessao } from '../src/stores/auth'
import type { EnderecoUsuarioResponse } from '../src/types/enderecos'


vi.mock('../src/config', () => ({ apiUrl: 'https://api.noma.test' }))

const fetchMock = vi.fn<typeof fetch>()
let container: HTMLDivElement
let root: Root
let enderecos: EnderecoUsuarioResponse[]


beforeEach(() => {
	definirSessao('token-valido')
	fetchMock.mockReset()
	vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
	vi.stubGlobal('fetch', fetchMock)
	enderecos = [
		{ id: 'endereco-01', recipient_name: 'Maria da Silva', postal_code: '01001000', street: 'Praça da Sé', number: '10 A', complement: 'Apto 2', neighborhood: 'Sé', city: 'São Paulo', state: 'SP', phone: '11999998888', is_default: true },
		{ id: 'endereco-02', recipient_name: 'João Santos', postal_code: '20040020', street: 'Rua da Assembleia', number: '20', complement: null, neighborhood: 'Centro', city: 'Rio de Janeiro', state: 'RJ', phone: '21999994444', is_default: false }
	]
	fetchMock.mockImplementation(async input => {
		const url = new URL(String(input))
		if (url.pathname === '/auth/refresh') {
			return new Response(null, { status: 401 })
		}
		const offset = Number(url.searchParams.get('offset') ?? 0)
		return Response.json(enderecos.slice(offset, offset + 100))
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


async function abrirPagina() {
	window.history.replaceState({}, '', '/checkout')
	await act(async () => { root.render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>) })
}


async function clicar(texto: string) {
	const button = Array.from(container.querySelectorAll<HTMLButtonElement>('button')).find(button => button.textContent === texto)!
	expect(button).not.toBeUndefined()
	await act(async () => { button.click() })
}


async function selecionar(id: string) {
	await act(async () => {
		const select = container.querySelector<HTMLSelectElement>('#endereco-salvo-checkout')!
		select.value = id
		select.dispatchEvent(new Event('change', { bubbles: true }))
	})
}


function campo(name: string): HTMLInputElement | HTMLSelectElement {
	return container.querySelector<HTMLInputElement | HTMLSelectElement>(`[name="${name}"]`)!
}


async function salvar(values: Record<string, string> = {}) {
	for (const [name, value] of Object.entries(values)) {
		campo(name).value = value
	}
	await act(async () => { container.querySelector('.formulario-endereco-checkout')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) })
}


it('carrega endereços com Bearer e seleciona o padrão, mesmo fora da primeira posição', async () => {
	enderecos.reverse()
	await abrirPagina()
	expect(container.querySelector<HTMLSelectElement>('#endereco-salvo-checkout')!.value).toBe('endereco-01')
	expect(campo('firstName').value).toBe('Maria')
	expect(campo('lastName').value).toBe('da Silva')
	expect(campo('number').value).toBe('10 A')
	expect(campo('state').value).toBe('SP')
	expect(container.querySelector('option[value="endereco-01"]')?.textContent).toContain('(Padrão)')
	expect(fetchMock.mock.calls.every(([input, options]) => new URL(String(input)).pathname === '/users/me/addresses' && new Headers(options?.headers).get('Authorization') === 'Bearer token-valido' && !options?.method)).toBe(true)
})


it('seleciona outro endereço sem alterar o padrão e sem consultar o detalhe novamente', async () => {
	await abrirPagina()
	const consultas = fetchMock.mock.calls.length
	await selecionar('endereco-02')
	expect(campo('firstName').value).toBe('João')
	expect(campo('lastName').value).toBe('Santos')
	expect(campo('postalCode').value).toBe('20040020')
	expect(campo('state').value).toBe('RJ')
	expect(campo('complement').value).toBe('')
	expect(container.querySelector('option[value="endereco-01"]')?.textContent).toContain('(Padrão)')
	expect(fetchMock.mock.calls).toHaveLength(consultas)
})


it('sem endereços salvos mostra formulário vazio e permite criar o primeiro', async () => {
	enderecos = []
	await abrirPagina()
	expect(container.textContent).toContain('Você ainda não tem endereço salvo.')
	expect(container.querySelector('#endereco-salvo-checkout')).toBeNull()
	expect(campo('firstName').value).toBe('')
	expect(campo('country').value).toBe('BR')
	expect(container.querySelector('button[type="submit"]')?.textContent).toBe('Salvar endereço')
})


it('cadastra endereço, envia somente os campos permitidos e exibe os valores normalizados', async () => {
	await abrirPagina()
	await selecionar('')
	expect(campo('firstName').value).toBe('')
	campo('cardNumber').value = 'numero-nao-enviar'
	campo('securityCode').value = '123'
	campo('email').value = 'contato@example.com'
	fetchMock.mockImplementation(async (input, options) => {
		if (options?.method === 'POST') {
			expect(String(input)).toBe('https://api.noma.test/users/me/addresses')
			expect(new Headers(options.headers).get('Content-Type')).toBe('application/json')
			const body = JSON.parse(String(options.body))
			expect(body).toEqual({ recipient_name: 'Ana Maria dos Santos', postal_code: '01001-000', street: 'Praça da Sé', number: 'S/N', complement: null, neighborhood: 'Sé', city: 'São Paulo', state: 'SP', phone: '(11) 99999-7777' })
			const novo = { ...body, id: 'endereco-03', postal_code: '01001000', phone: '11999997777', is_default: false }
			enderecos.push(novo)
			return Response.json(novo, { status: 201 })
		}
		return Response.json(enderecos)
	})
	await salvar({ firstName: ' Ana ', lastName: ' Maria dos Santos ', postalCode: '01001-000', address: ' Praça da Sé ', number: 'S/N', complement: ' ', neighborhood: 'Sé', city: 'São Paulo', state: 'SP', phone: '(11) 99999-7777' })
	expect(container.querySelector<HTMLSelectElement>('#endereco-salvo-checkout')!.value).toBe('endereco-03')
	expect(campo('firstName').value).toBe('Ana')
	expect(campo('lastName').value).toBe('Maria dos Santos')
	expect(campo('postalCode').value).toBe('01001000')
	expect(campo('phone').value).toBe('11999997777')
	expect(container.textContent).toContain('Endereço salvo.')
	expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
})


it('edita endereço existente, aceita destinatário de um nome e limpa complemento com null', async () => {
	await abrirPagina()
	fetchMock.mockImplementation(async (input, options) => {
		if (options?.method === 'PATCH') {
			expect(String(input)).toBe('https://api.noma.test/users/me/addresses/endereco-01')
			const body = JSON.parse(String(options.body))
			expect(body.recipient_name).toBe('Ana')
			expect(body.complement).toBeNull()
			expect(body).not.toHaveProperty('is_default')
			enderecos[0] = { ...enderecos[0], ...body }
			return Response.json(enderecos[0])
		}
		return Response.json(enderecos)
	})
	await salvar({ firstName: 'Ana', lastName: '', complement: '', number: '30 B' })
	expect(campo('firstName').value).toBe('Ana')
	expect(campo('lastName').value).toBe('')
	expect(campo('number').value).toBe('30 B')
	expect(campo('complement').value).toBe('')
})


it('define padrão com PATCH explícito e reflete os marcadores da resposta atualizada', async () => {
	await abrirPagina()
	await selecionar('endereco-02')
	fetchMock.mockImplementation(async (input, options) => {
		if (options?.method === 'PATCH') {
			expect(String(input)).toBe('https://api.noma.test/users/me/addresses/endereco-02')
			expect(JSON.parse(String(options.body))).toEqual({ is_default: true })
			enderecos = enderecos.map(endereco => ({ ...endereco, is_default: endereco.id === 'endereco-02' }))
			return Response.json(enderecos[1])
		}
		return Response.json(enderecos)
	})
	await clicar('Definir como padrão')
	expect(container.querySelector('option[value="endereco-02"]')?.textContent).toContain('(Padrão)')
	expect(container.querySelector('option[value="endereco-01"]')?.textContent).not.toContain('(Padrão)')
	expect(container.textContent).not.toContain('Definir como padrão')
	expect(campo('firstName').value).toBe('João')
})


it.each(['padrão', 'outro', 'último'])('exclui o endereço %s e usa o padrão escolhido pelo backend', async caso => {
	if (caso === 'último') {
		enderecos = [enderecos[0]]
	}
	await abrirPagina()
	let id = 'endereco-01'
	if (caso === 'outro') {
		await selecionar('endereco-02')
		id = 'endereco-02'
	}
	fetchMock.mockImplementation(async (input, options) => {
		if (options?.method === 'DELETE') {
			expect(String(input)).toBe(`https://api.noma.test/users/me/addresses/${id}`)
			expect(options.body).toBeUndefined()
			enderecos = enderecos.filter(endereco => endereco.id !== id)
			if (enderecos.length > 0) {
				enderecos[0].is_default = true
			}
			return new Response(null, { status: 204 })
		}
		return Response.json(enderecos)
	})
	await clicar('Excluir endereço')
	expect(container.querySelector(`option[value="${id}"]`)).toBeNull()
	if (caso === 'último') {
		expect(campo('firstName').value).toBe('')
		expect(campo('state').value).toBe('')
		expect(container.textContent).toContain('Você ainda não tem endereço salvo.')
	} else {
		expect(container.querySelector<HTMLSelectElement>('#endereco-salvo-checkout')!.value).toBe(enderecos[0].id)
		expect(container.querySelector(`option[value="${enderecos[0].id}"]`)?.textContent).toContain('(Padrão)')
	}
})


it('loading bloqueia cadastro até conhecer os endereços e permite tentar novamente após erro', async () => {
	let concluir!: (response: Response) => void
	fetchMock.mockImplementation(async () => new Promise(resolve => { concluir = resolve }))
	await abrirPagina()
	expect(container.textContent).toContain('Carregando endereços...')
	expect(container.querySelector('.formulario-endereco-checkout')).toBeNull()
	await act(async () => { concluir(new Response(null, { status: 503 })) })
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('Não foi possível carregar')
	fetchMock.mockResolvedValue(Response.json(enderecos))
	await clicar('Tentar novamente')
	expect(campo('firstName').value).toBe('Maria')
})


it.each(['json', 'formato', 'campos'])('resposta inválida (%s) mostra erro sem quebrar a página', async caso => {
	if (caso === 'json') {
		fetchMock.mockImplementation(async () => new Response('json inválido'))
	} else if (caso === 'formato') {
		fetchMock.mockResolvedValue(Response.json({ items: [] }))
	} else {
		fetchMock.mockResolvedValue(Response.json([{ id: 'incompleto' }]))
	}
	await abrirPagina()
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('Não foi possível carregar')
	expect(container.querySelector('.formulario-endereco-checkout')).toBeNull()
	expect(container.querySelector('#titulo-pagamento-checkout')).not.toBeNull()
})


it.each(['422', '503', 'html', 'conexão'])('falha %s na edição mantém o preenchimento e libera a correção', async caso => {
	await abrirPagina()
	fetchMock.mockImplementation(async () => {
		if (caso === 'conexão') {
			throw new TypeError('Falha de conexão')
		}
		if (caso === '422') {
			return Response.json({ detail: [{ loc: ['body', 'phone'], msg: 'Inválido', type: 'value_error' }] }, { status: 422 })
		}
		if (caso === 'html') {
			return new Response('erro interno privado', { status: 503 })
		}
		return Response.json({ detail: 'Serviço indisponível.' }, { status: 503 })
	})
	await salvar({ number: '45 A', phone: 'invalido' })
	expect(container.querySelector('[role="alert"]')).not.toBeNull()
	expect(container.textContent).not.toContain('erro interno privado')
	expect(campo('number').value).toBe('45 A')
	expect(campo('phone').value).toBe('invalido')
	expect(container.querySelector<HTMLFieldSetElement>('.edicao-endereco-checkout')!.disabled).toBe(false)
})


it('evita envio duplicado e bloqueia seleção e demais alterações até a recarga terminar', async () => {
	await abrirPagina()
	let concluir!: (response: Response) => void
	fetchMock.mockImplementation(async (_input, options) => {
		if (options?.method === 'PATCH') {
			return new Promise(resolve => { concluir = resolve })
		}
		return Response.json(enderecos)
	})
	await act(async () => {
		const form = container.querySelector('.formulario-endereco-checkout')!
		form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
		form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
	})
	expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'PATCH')).toHaveLength(1)
	expect(container.querySelector<HTMLSelectElement>('#endereco-salvo-checkout')!.disabled).toBe(true)
	expect(container.querySelector<HTMLFieldSetElement>('.edicao-endereco-checkout')!.disabled).toBe(true)
	await act(async () => { concluir(Response.json(enderecos[0])) })
	expect(container.querySelector<HTMLFieldSetElement>('.edicao-endereco-checkout')!.disabled).toBe(false)
})


it('criação confirmada seguida de falha no GET recupera a lista sem cadastrar novamente', async () => {
	await abrirPagina()
	await selecionar('')
	let falharConsulta = true
	fetchMock.mockImplementation(async (_input, options) => {
		if (options?.method === 'POST') {
			const novo = { ...enderecos[0], ...JSON.parse(String(options.body)), id: 'endereco-03', is_default: false }
			enderecos.push(novo)
			return Response.json(novo, { status: 201 })
		}
		if (falharConsulta) {
			return new Response(null, { status: 503 })
		}
		return Response.json(enderecos)
	})
	await salvar({ firstName: 'Ana', lastName: 'Silva', postalCode: '01001000', address: 'Rua Nova', number: '10', neighborhood: 'Centro', city: 'São Paulo', state: 'SP', phone: '11999998888' })
	expect(container.textContent).toContain('Endereço salvo.')
	expect(container.querySelector('[role="alert"]')).not.toBeNull()
	expect(container.querySelector('.formulario-endereco-checkout')).toBeNull()
	falharConsulta = false
	await clicar('Tentar novamente')
	expect(campo('firstName').value).toBe('Ana')
	expect(container.querySelector<HTMLSelectElement>('#endereco-salvo-checkout')!.value).toBe('endereco-03')
	expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST')).toHaveLength(1)
})


it('404 durante edição atualiza a lista quando o endereço foi excluído em outra aba', async () => {
	await abrirPagina()
	fetchMock.mockImplementation(async (_input, options) => {
		if (options?.method === 'PATCH') {
			enderecos = [{ ...enderecos[1], is_default: true }]
			return Response.json({ detail: 'Endereço não encontrado.' }, { status: 404 })
		}
		return Response.json(enderecos)
	})
	await salvar()
	expect(container.querySelector('option[value="endereco-01"]')).toBeNull()
	expect(campo('firstName').value).toBe('João')
	expect(container.querySelector('[role="alert"]')?.textContent).toContain('não está mais disponível')
})


it('exclusão recusada mantém o endereço e permite tentar novamente', async () => {
	await abrirPagina()
	fetchMock.mockResolvedValue(Response.json({ detail: 'Não foi possível excluir o endereço.' }, { status: 503 }))
	await clicar('Excluir endereço')
	expect(container.querySelector<HTMLSelectElement>('#endereco-salvo-checkout')!.value).toBe('endereco-01')
	expect(campo('firstName').value).toBe('Maria')
	expect(container.querySelector('[role="alert"]')?.textContent).toBe('Não foi possível excluir o endereço.')
	expect(container.querySelector<HTMLFieldSetElement>('.edicao-endereco-checkout')!.disabled).toBe(false)
})


it('exclusão confirmada seguida de falha na recarga não mantém dados antigos nem repete DELETE', async () => {
	await abrirPagina()
	let falharConsulta = true
	fetchMock.mockImplementation(async (_input, options) => {
		if (options?.method === 'DELETE') {
			enderecos = [{ ...enderecos[1], is_default: true }]
			return new Response(null, { status: 204 })
		}
		if (falharConsulta) {
			return new Response(null, { status: 503 })
		}
		return Response.json(enderecos)
	})
	await clicar('Excluir endereço')
	expect(container.textContent).toContain('Endereço excluído.')
	expect(container.querySelector('.formulario-endereco-checkout')).toBeNull()
	expect(container.querySelector('[role="alert"]')).not.toBeNull()
	falharConsulta = false
	await clicar('Tentar novamente')
	expect(container.querySelector('option[value="endereco-01"]')).toBeNull()
	expect(container.querySelector<HTMLSelectElement>('#endereco-salvo-checkout')!.value).toBe('endereco-02')
	expect(campo('firstName').value).toBe('João')
	expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'DELETE')).toHaveLength(1)
})


it('carrega todas as páginas de endereços e evita um GET para cada opção', async () => {
	const base = enderecos[0]
	enderecos = Array.from({ length: 101 }, (_, i) => ({ ...base, id: `endereco-${i}`, is_default: i === 0 }))
	await abrirPagina()
	expect(container.querySelectorAll('#endereco-salvo-checkout option')).toHaveLength(102)
	expect(fetchMock.mock.calls.some(([input]) => new URL(String(input)).searchParams.get('offset') === '100')).toBe(true)
	expect(fetchMock.mock.calls.every(([input]) => new URL(String(input)).pathname === '/users/me/addresses')).toBe(true)
})


it('JWT expirado renova uma vez e continua carregando os endereços', async () => {
	definirSessao('token-expirado')
	fetchMock.mockImplementation(async (input, options) => {
		if (String(input).endsWith('/auth/refresh')) {
			return Response.json({ access_token: 'token-renovado', token_type: 'bearer' })
		}
		if (new Headers(options?.headers).get('Authorization') === 'Bearer token-expirado') {
			return new Response(null, { status: 401 })
		}
		return Response.json(enderecos)
	})
	await abrirPagina()
	expect(window.location.pathname).toBe('/checkout')
	expect(campo('firstName').value).toBe('Maria')
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(1)
})


it.each(['consulta', 'alteração'])('sessão expirada durante %s encaminha ao Acesso sem loop', async caso => {
	if (caso === 'alteração') {
		await abrirPagina()
	}
	fetchMock.mockImplementation(async () => new Response(null, { status: 401 }))
	if (caso === 'alteração') {
		await salvar()
	} else {
		await abrirPagina()
	}
	expect(window.location.pathname).toBe('/acesso')
	expect(container.querySelector('.conteudo-acesso-buttons')).not.toBeNull()
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(1)
})


it('sair durante a consulta cancela a requisição e ignora um 401 atrasado', async () => {
	const pendentes: { signal: AbortSignal; resolve: (response: Response) => void }[] = []
	fetchMock.mockImplementation(async (_input, options) => new Promise(resolve => { pendentes.push({ signal: options!.signal!, resolve }) }))
	await abrirPagina()
	await act(async () => {
		window.history.pushState({}, '', '/')
		window.dispatchEvent(new PopStateEvent('popstate'))
	})
	expect(pendentes.every(item => item.signal.aborted)).toBe(true)
	await act(async () => { pendentes.forEach(item => item.resolve(new Response(null, { status: 401 }))) })
	expect(window.location.pathname).toBe('/')
	expect(container.querySelector('.formulario-endereco-checkout')).toBeNull()
})
