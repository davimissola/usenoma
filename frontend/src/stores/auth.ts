import type { AuthTokenResponse } from '../types/auth'


export const auth = {
	accessToken: ''
}

let refreshPendente: Promise<void> | null = null


export async function recuperarSessao(): Promise<void> {
	if (auth.accessToken) {
		return
	}

	if (!refreshPendente) {
		refreshPendente = renovarSessao()
	}

	// Espera o refresh terminar. Chamadas simultâneas aguardam a mesma requisição.
	await refreshPendente
	refreshPendente = null
}


async function renovarSessao(): Promise<void> {
	try {
		const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
		const response = await fetch(`${apiUrl}/auth/refresh`, {
			method: 'POST',
			credentials: 'include'
		})

		if (!response.ok) {
			return
		}

		const data: AuthTokenResponse = await response.json()
		auth.accessToken = data.access_token
	} catch {
		return
	}
}
