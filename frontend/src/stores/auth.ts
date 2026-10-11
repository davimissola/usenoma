import { apiUrl } from '../config'
import type { AuthTokenResponse } from '../types/auth'


export const auth = {
	accessToken: '',
	sessaoVerificada: false
}

let refreshPendente: Promise<boolean> | null = null


export function definirSessao(accessToken: string): void {
	// O access token fica somente na memória. O refresh é gerenciado pelo cookie HttpOnly.
	auth.accessToken = accessToken
	auth.sessaoVerificada = true
}


// quando o access_token expira e da 401 chama aq
export async function recuperarSessao(renovar = false): Promise<boolean> {
	// Uma sessão já verificada só precisa de outro refresh quando uma requisição receber 401.
	if (auth.sessaoVerificada && !renovar) {
		return Boolean(auth.accessToken)
	}

	if (!refreshPendente) {
		// O lock evita que abas diferentes renovem o mesmo refresh token ao mesmo tempo.
		if (navigator.locks) {
			refreshPendente = navigator.locks.request('noma-auth', buscarSessao)
		} else {
			refreshPendente = buscarSessao()
		}
	}

	const refresh = refreshPendente

	try {
		// Dentro da mesma aba, todas as chamadas aguardam uma única renovação.
		return await refresh
	} catch {
		definirSessao('')
		return false
	} finally {
		if (refreshPendente === refresh) {
			refreshPendente = null
		}
	}
}


// chama o /auth/refresh -> não é chamado nas pages e componentes
async function buscarSessao(): Promise<boolean> {
	const response = await fetch(`${apiUrl}/auth/refresh`, {
		method: 'POST',
		credentials: 'include',
		// Evita deixar o app esperando indefinidamente se a API não responder.
		signal: AbortSignal.timeout(10000)
	})

	if (!response.ok) {
		definirSessao('')
		return false
	}

	const data: AuthTokenResponse = await response.json()
	definirSessao(data.access_token)

	return Boolean(auth.accessToken)
}


// retorna o /auth/me aq mas com as regras bonitinhas de validaçao de erro pa
export async function requisicaoAutenticada(path: string, options: RequestInit = {}): Promise<Response> {
	await recuperarSessao()

	const token = auth.accessToken
	const headers = new Headers(options.headers)
	headers.set('Authorization', `Bearer ${token}`)

	let response = await fetch(`${apiUrl}${path}`, {
		...options,
		headers
	})

	if (response.status !== 401 || !auth.accessToken) {
		return response
	}

	// Outra requisição pode já ter renovado o token enquanto esta estava em andamento.
	if (auth.accessToken === token) {
		const sessaoRecuperada = await recuperarSessao(true)

		if (!sessaoRecuperada) {
			return response
		}
	}

	headers.set('Authorization', `Bearer ${auth.accessToken}`)
	response = await fetch(`${apiUrl}${path}`, {
		...options,
		headers
	})

	// A repetição acontece uma única vez. Um segundo 401 encerra a sessão, sem outro refresh.
	if (response.status === 401) {
		definirSessao('')
	}

	return response
}


export async function encerrarSessao(): Promise<void> {
	// Espera a renovação terminar para ela não restaurar o token depois do logout.
	if (refreshPendente) {
		await recuperarSessao(true)
	}

	async function logout() {
		const response = await fetch(`${apiUrl}/auth/logout`, {
			method: 'POST',
			credentials: 'include',
			signal: AbortSignal.timeout(10000)
		})

		if (!response.ok) {
			throw new Error('Não foi possível sair da conta. Tente novamente.')
		}

		definirSessao('')
	}

	if (navigator.locks) {
		await navigator.locks.request('noma-auth', logout)
		return
	}

	await logout()
}
