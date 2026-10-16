// @vitest-environment jsdom
import { StrictMode, act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App'
import { auth, definirSessao } from '../src/stores/auth'


vi.mock('../src/config', () => ({ apiUrl: 'https://api.noma.test' }))

const fetchMock = vi.fn<typeof fetch>()
let container: HTMLDivElement
let root: Root


beforeEach(() => {
	auth.accessToken = ''
	auth.sessaoVerificada = false
	fetchMock.mockReset()
	vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true)
	vi.stubGlobal('fetch', fetchMock)

	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return new Response(null, { status: 401 })
		}

		if (String(input).endsWith('/auth/register') || String(input).endsWith('/auth/login')) {
			return Response.json({ access_token: 'token-valido', token_type: 'bearer' })
		}

		if (String(input).includes('/stores/slug/')) {
			return Response.json({ id: 'loja-saint', name: 'Saint', slug: 'saint', description: null, logo: null, cover: null })
		}

		if (String(input).endsWith('/products')) {
			return Response.json([])
		}
		if (String(input).includes('/users/me/addresses')) {
			return Response.json([])
		}

		return Response.json({ id: '937a54e0-9c4e-40f7-9c3d-5b32994d0318', username: 'davi', email: 'davi@example.com', stores: [] })
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


async function abrirPagina(path: string) {
	window.history.replaceState({}, '', path)

	await act(async () => {
		root.render(<StrictMode><BrowserRouter><App /></BrowserRouter></StrictMode>)
	})
}


async function enviarFormulario(values: Record<string, string>) {
	for (const [name, value] of Object.entries(values)) {
		container.querySelector<HTMLInputElement>(`input[name="${name}"]`)!.value = value
	}

	await act(async () => {
		container.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
	})
}


it('não mostra o formulário enquanto verifica a sessão, mesmo com StrictMode', async () => {
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockReturnValue(new Promise(resolve => { concluirRefresh = resolve }))

	await abrirPagina('/login')
	expect(container.querySelector('form')).toBeNull()
	expect(window.location.pathname).toBe('/login')
	expect(fetchMock).toHaveBeenCalledTimes(1)

	await act(async () => {
		concluirRefresh(new Response(null, { status: 401 }))
	})

	expect(container.querySelector('.pages-login form')).not.toBeNull()
})


it('recupera a sessão após F5 em Usuario sem passar por Acesso', async () => {
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockReturnValueOnce(new Promise(resolve => { concluirRefresh = resolve }))

	await abrirPagina('/usuario')
	expect(window.location.pathname).toBe('/usuario')
	expect(container.querySelector('.pages-acesso')).toBeNull()

	await act(async () => {
		concluirRefresh(Response.json({ access_token: 'token-recuperado', token_type: 'bearer' }))
	})

	expect(window.location.pathname).toBe('/usuario')
	expect(container.querySelector('.pages-usuario h2')?.textContent).toBe('davi')
	expect(container.querySelector('.card-loja-usuario')).toBeNull()
	expect(auth.accessToken).toBe('token-recuperado')
})


it('mostra os cards do usuário e abre a loja pelo slug', async () => {
	definirSessao('token-valido')
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/products')) {
			return Response.json([])
		}
		if (String(input).endsWith('/stores/slug/adora-brasil')) {
			return Response.json({ id: 'loja-adora', name: 'Adora', slug: 'adora-brasil', description: null, logo: null, cover: null })
		}

		return Response.json({ id: '937a54e0-9c4e-40f7-9c3d-5b32994d0318', username: 'davi', email: 'davi@example.com', stores: [{ id: 'loja-adora', name: 'Adora', slug: 'adora-brasil' }, { id: 'loja-saint', name: 'Saint', slug: 'saint' }] })
	})

	await abrirPagina('/usuario')
	const lojas = Array.from(container.querySelectorAll('.card-loja-usuario'))

	expect(lojas.map(loja => loja.querySelector('h3')?.textContent)).toEqual(['Adora', 'Saint'])
	expect(container.querySelectorAll('.titulo-lojas-usuario')).toHaveLength(1)
	expect(lojas[0].querySelector('a')?.getAttribute('href')).toBe('/adora-brasil')

	await act(async () => {
		lojas[0].querySelector('a')!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }))
	})

	expect(window.location.pathname).toBe('/adora-brasil')
	expect(container.querySelector('.hero-loja-capa')).not.toBeNull()
	expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/stores/slug/adora-brasil'))).toBe(true)
})


it('busca a loja pelo slug e abre a hero mesmo sem sessão', async () => {
	await abrirPagina('/saint')

	expect(window.location.pathname).toBe('/saint')
	expect(container.querySelector('.pages-loja .hero-loja-capa')).not.toBeNull()
	expect(container.querySelector('.header')).not.toBeNull()
	expect(fetchMock.mock.calls.filter(call => !String(call[0]).endsWith('/auth/refresh')).every(call => String(call[0]).endsWith('/stores/slug/saint') || String(call[0]).endsWith('/stores/loja-saint/products'))).toBe(true)
})


it.each(['/usuario', '/checkout'])('manda visitantes de %s para Acesso após concluir a verificação', async path => {
	await abrirPagina(path)

	expect(window.location.pathname).toBe('/acesso')
	expect(container.querySelector('.conteudo-acesso-buttons')).not.toBeNull()
	expect(fetchMock).toHaveBeenCalledTimes(1)
})


it('checkout aguarda o refresh após F5 e abre sem passar pelo Acesso', async () => {
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockReturnValueOnce(new Promise(resolve => { concluirRefresh = resolve }))

	await abrirPagina('/checkout')
	expect(window.location.pathname).toBe('/checkout')
	expect(container.querySelector('form')).toBeNull()
	expect(container.querySelector('.pages-acesso')).toBeNull()

	await act(async () => {
		concluirRefresh(Response.json({ access_token: 'token-recuperado', token_type: 'bearer' }))
	})

	expect(window.location.pathname).toBe('/checkout')
	expect(container.querySelector('.formulario-checkout')).not.toBeNull()
	expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/auth/refresh'))).toHaveLength(1)
	expect(fetchMock.mock.calls.some(([input, options]) => String(input).includes('/users/me/addresses') && new Headers(options?.headers).get('Authorization') === 'Bearer token-recuperado')).toBe(true)
})


it.each([['/acesso', '/usuario'], ['/login', '/usuario'], ['/criar-conta', '/explorar']])('recupera a sessão em %s e abre %s sem mostrar formulários', async (path, destination) => {
	fetchMock.mockImplementation(async input => {
		if (String(input).endsWith('/auth/refresh')) {
			return Response.json({ access_token: 'token-recuperado', token_type: 'bearer' })
		}

		return Response.json({ id: '937a54e0-9c4e-40f7-9c3d-5b32994d0318', username: 'davi', email: 'davi@example.com', stores: [] })
	})

	await abrirPagina(path)
	expect(window.location.pathname).toBe(destination)
	expect(container.querySelector('form')).toBeNull()
	expect(fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/auth/refresh'))).toHaveLength(1)
})


it.each([['/login', '/usuario'], ['/criar-conta', '/explorar']])('autentica em %s, abre %s e mantém a sessão na navegação', async (path, destination) => {
	await abrirPagina(path)
	const values: Record<string, string> = { username: 'davi', password: 'UmaSenhaSegura123!' }

	if (path === '/criar-conta') {
		values.email = 'davi@example.com'
		values.confirmPassword = values.password
	}

	await enviarFormulario(values)
	expect(window.location.pathname).toBe(destination)
	expect(auth).toEqual({ accessToken: 'token-valido', sessaoVerificada: true })

	const authCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/auth/register') || String(call[0]).endsWith('/auth/login'))!
	expect(authCall[1]?.credentials).toBe('include')

	if (path === '/criar-conta') {
		expect(JSON.parse(String(authCall[1]?.body))).toEqual({ username: 'davi', email: 'davi@example.com', password: values.password })
	} else {
		expect(String(authCall[1]?.body)).toBe(new URLSearchParams({ username: 'davi', password: values.password }).toString())
	}

	if (path === '/criar-conta') {
		await act(async () => {
			container.querySelector<HTMLAnchorElement>('.conteudo-card-explorar a')!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }))
		})
	} else {
		await act(async () => {
			container.querySelector<HTMLAnchorElement>('.voltar-usuario')!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }))
		})
	}

	expect(window.location.pathname).toBe('/')

	await act(async () => {
		container.querySelector<HTMLAnchorElement>('.header a[href="/acesso"]')!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }))
	})

	expect(window.location.pathname).toBe('/usuario')
	expect(container.querySelector('.pages-usuario h2')?.textContent).toBe('davi')
	expect(fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/auth/refresh'))).toHaveLength(1)
})


it('JWT expirado e refresh válido mantêm a página Usuario aberta', async () => {
	definirSessao('token-expirado')
	fetchMock.mockImplementation(async (input, init) => {
		if (String(input).endsWith('/auth/refresh')) {
			return Response.json({ access_token: 'token-renovado', token_type: 'bearer' })
		}

		if (new Headers(init?.headers).get('Authorization') === 'Bearer token-expirado') {
			return new Response(null, { status: 401 })
		}

		return Response.json({ id: '937a54e0-9c4e-40f7-9c3d-5b32994d0318', username: 'davi', email: 'davi@example.com', stores: [] })
	})

	await abrirPagina('/usuario')
	expect(window.location.pathname).toBe('/usuario')
	expect(container.querySelector('.pages-usuario h2')?.textContent).toBe('davi')
	expect(fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/auth/refresh'))).toHaveLength(1)
})


it('refresh expirado manda para Acesso e não entra em um ciclo de redirecionamento', async () => {
	definirSessao('token-expirado')
	fetchMock.mockResolvedValue(new Response(null, { status: 401 }))

	await abrirPagina('/usuario')
	expect(window.location.pathname).toBe('/acesso')
	expect(container.querySelector('.conteudo-acesso-buttons')).not.toBeNull()
	expect(auth.accessToken).toBe('')
	expect(fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/auth/refresh'))).toHaveLength(1)
})


it('login com senha incorreta mostra o erro e não tenta renovar a sessão', async () => {
	await abrirPagina('/login')
	fetchMock.mockResolvedValue(Response.json({ detail: 'Nome de usuário ou senha incorretos.' }, { status: 401 }))

	await enviarFormulario({ username: 'davi', password: 'senha-incorreta' })
	expect(window.location.pathname).toBe('/login')
	expect(container.querySelector('[role="alert"]')?.textContent).toBe('Nome de usuário ou senha incorretos.')
	expect(auth.accessToken).toBe('')
	expect(fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/auth/refresh'))).toHaveLength(1)
})
