import { afterEach, beforeEach, expect, it, vi } from 'vitest'


vi.mock('../src/config', () => ({ apiUrl: 'https://api.noma.test' }))

const fetchMock = vi.fn<typeof fetch>()
let session: typeof import('../src/stores/auth')


beforeEach(async () => {
	vi.resetModules()
	fetchMock.mockReset()
	vi.stubGlobal('fetch', fetchMock)
	vi.stubGlobal('navigator', {})
	session = await import('../src/stores/auth')
})

afterEach(() => {
	vi.unstubAllGlobals()
})


function tokenResponse(accessToken = 'novo-token') {
	return Response.json({ access_token: accessToken, token_type: 'bearer' })
}


it('recupera a sessão após F5 e compartilha o refresh entre chamadas simultâneas', async () => {
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockReturnValue(new Promise(resolve => { concluirRefresh = resolve }))

	const first = session.recuperarSessao()
	const second = session.recuperarSessao()

	expect(session.auth.sessaoVerificada).toBe(false)
	expect(session.auth.accessToken).toBe('')
	expect(fetchMock).toHaveBeenCalledTimes(1)
	expect(fetchMock.mock.calls[0][1]?.credentials).toBe('include')

	concluirRefresh(tokenResponse())
	expect(await Promise.all([first, second])).toEqual([true, true])
	expect(session.auth).toEqual({ accessToken: 'novo-token', sessaoVerificada: true })
	await session.recuperarSessao()
	expect(fetchMock).toHaveBeenCalledTimes(1)
})


it.each([401, 503])('termina a verificação quando o refresh retorna %s e não o repete ao abrir Acesso', async status => {
	fetchMock.mockResolvedValue(new Response(null, { status }))

	expect(await session.recuperarSessao()).toBe(false)
	expect(session.auth).toEqual({ accessToken: '', sessaoVerificada: true })
	expect(await session.recuperarSessao()).toBe(false)
	expect(fetchMock).toHaveBeenCalledTimes(1)
})


it('termina a verificação mesmo quando a API está sem conexão', async () => {
	fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

	expect(await session.recuperarSessao()).toBe(false)
	expect(session.auth).toEqual({ accessToken: '', sessaoVerificada: true })
})


it('uma falha de conexão na requisição protegida não apaga uma sessão válida', async () => {
	session.definirSessao('token-valido')
	fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

	await expect(session.requisicaoAutenticada('/users/me')).rejects.toThrow('Failed to fetch')
	expect(session.auth.accessToken).toBe('token-valido')
	expect(fetchMock).toHaveBeenCalledTimes(1)
})


it('renova o access após 401 e repete a requisição uma vez, preservando body e headers', async () => {
	session.definirSessao('token-expirado')
	const tokens: string[] = []
	const body = JSON.stringify({ item: 123 })
	const options = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body }

	fetchMock.mockImplementation(async (input, init) => {
		if (String(input).endsWith('/auth/refresh')) {
			return tokenResponse()
		}

		const headers = new Headers(init?.headers)
		tokens.push(headers.get('Authorization')!)
		expect(init?.body).toBe(body)
		expect(init?.method).toBe('POST')
		expect(headers.get('Content-Type')).toBe('application/json')

		if (tokens.length === 1) {
			return new Response(null, { status: 401 })
		}

		return Response.json({ ok: true })
	})

	expect((await session.requisicaoAutenticada('/protegida', options)).status).toBe(200)
	expect(tokens).toEqual(['Bearer token-expirado', 'Bearer novo-token'])
	expect(fetchMock).toHaveBeenCalledTimes(3)
	expect(options.headers).toEqual({ 'Content-Type': 'application/json' })
})


it('não repete a requisição protegida quando o refresh expirou', async () => {
	session.definirSessao('token-expirado')
	fetchMock.mockResolvedValueOnce(new Response(null, { status: 401 })).mockResolvedValueOnce(new Response(null, { status: 401 }))

	expect((await session.requisicaoAutenticada('/users/me')).status).toBe(401)
	expect(session.auth.accessToken).toBe('')
	expect(fetchMock).toHaveBeenCalledTimes(2)
	await session.recuperarSessao()
	expect(fetchMock).toHaveBeenCalledTimes(2)
})


it('um segundo 401 encerra a sessão sem começar outro refresh', async () => {
	session.definirSessao('token-expirado')
	fetchMock.mockResolvedValueOnce(new Response(null, { status: 401 })).mockResolvedValueOnce(tokenResponse()).mockResolvedValueOnce(new Response(null, { status: 401 }))

	expect((await session.requisicaoAutenticada('/users/me')).status).toBe(401)
	expect(session.auth.accessToken).toBe('')
	expect(fetchMock).toHaveBeenCalledTimes(3)
	await session.recuperarSessao()
	expect(fetchMock).toHaveBeenCalledTimes(3)
})


it('requisições protegidas simultâneas usam um único refresh', async () => {
	session.definirSessao('token-expirado')
	let refreshes = 0

	fetchMock.mockImplementation(async (input, init) => {
		if (String(input).endsWith('/auth/refresh')) {
			refreshes++
			return tokenResponse()
		}

		if (new Headers(init?.headers).get('Authorization') === 'Bearer token-expirado') {
			return new Response(null, { status: 401 })
		}

		return Response.json({ ok: true })
	})

	const responses = await Promise.all([session.requisicaoAutenticada('/primeira'), session.requisicaoAutenticada('/segunda')])
	expect(responses.map(response => response.status)).toEqual([200, 200])
	expect(refreshes).toBe(1)
	expect(fetchMock).toHaveBeenCalledTimes(5)
})


it('um 401 atrasado reutiliza o token já renovado por outra requisição', async () => {
	session.definirSessao('token-expirado')
	let responderAtrasada!: (response: Response) => void
	let refreshes = 0

	fetchMock.mockImplementation(async (input, init) => {
		if (String(input).endsWith('/auth/refresh')) {
			refreshes++
			return tokenResponse()
		}

		if (new Headers(init?.headers).get('Authorization') === 'Bearer token-expirado') {
			if (String(input).endsWith('/atrasada')) {
				return new Promise(resolve => { responderAtrasada = resolve })
			}

			return new Response(null, { status: 401 })
		}

		return Response.json({ ok: true })
	})

	const first = session.requisicaoAutenticada('/primeira')
	const delayed = session.requisicaoAutenticada('/atrasada')
	expect((await first).status).toBe(200)
	responderAtrasada(new Response(null, { status: 401 }))
	expect((await delayed).status).toBe(200)
	expect(refreshes).toBe(1)
})


it('coordena duas abas com sessões em memória separadas e um refresh cookie compartilhado', async () => {
	let queue = Promise.resolve()
	const request = vi.fn((_name: string, callback: () => Promise<boolean>) => {
		const result = queue.then(callback)
		queue = result.then(() => undefined, () => undefined)
		return result
	})
	vi.stubGlobal('navigator', { locks: { request } })

	const firstTab = session
	vi.resetModules()
	const secondTab = await import('../src/stores/auth')
	let cookie = 1
	let active = 0
	let maxActive = 0

	// Simula o backend: usar duas vezes a mesma versão do cookie retorna 401.
	fetchMock.mockImplementation(async () => {
		const receivedCookie = cookie
		active++
		maxActive = Math.max(maxActive, active)
		await new Promise(resolve => setTimeout(resolve, 0))
		active--

		if (receivedCookie !== cookie) {
			return new Response(null, { status: 401 })
		}

		cookie++
		return tokenResponse(`token-aba-${cookie}`)
	})

	expect(await Promise.all([firstTab.recuperarSessao(), secondTab.recuperarSessao()])).toEqual([true, true])
	expect(maxActive).toBe(1)
	expect(firstTab.auth.accessToken).toBe('token-aba-2')
	expect(secondTab.auth.accessToken).toBe('token-aba-3')
	expect(request.mock.calls.map(call => call[0])).toEqual(['noma-auth', 'noma-auth'])
})


it('aguarda um refresh em andamento antes do logout, sem restaurar a sessão depois', async () => {
	session.definirSessao('token-expirado')
	let concluirRefresh!: (response: Response) => void
	fetchMock.mockReturnValueOnce(new Promise(resolve => { concluirRefresh = resolve })).mockResolvedValueOnce(new Response(null, { status: 204 }))

	const refresh = session.recuperarSessao(true)
	const logout = session.encerrarSessao()
	expect(fetchMock).toHaveBeenCalledTimes(1)

	concluirRefresh(tokenResponse())
	await Promise.all([refresh, logout])
	expect(fetchMock.mock.calls[1][0]).toBe('https://api.noma.test/auth/logout')
	expect(fetchMock.mock.calls[1][1]?.credentials).toBe('include')
	expect(session.auth.accessToken).toBe('')
})


it('mantém a sessão e informa erro se o backend não conseguir concluir o logout', async () => {
	session.definirSessao('token-valido')
	fetchMock.mockResolvedValue(new Response(null, { status: 503 }))

	await expect(session.encerrarSessao()).rejects.toThrow('Não foi possível sair da conta.')
	expect(session.auth.accessToken).toBe('token-valido')
})
