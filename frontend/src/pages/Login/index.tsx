import { useState, type SubmitEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { auth } from '../../stores/auth'
import type { AuthErrorResponse, AuthTokenResponse } from '../../types/auth'
import caretLeft from '../../assets/svg/icons/caret-left-thin.svg'
import '../conta.css'


export function Login() {
	const [erro, setErro] = useState('')
	const [enviando, setEnviando] = useState(false)
	const navigate = useNavigate()

	async function login(event: SubmitEvent<HTMLFormElement>) {
		event.preventDefault()

		if (enviando) {
			return
		}

		const formData = new FormData(event.currentTarget)
		const body = new URLSearchParams({ username: String(formData.get('username') ?? ''), password: String(formData.get('password') ?? '') })

		setErro('')
		setEnviando(true)

		try {
			const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
			const response = await fetch(`${apiUrl.replace(/\/+$/, '')}/auth/login`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body })

			if (!response.ok) {
				const data: AuthErrorResponse = await response.json()

				if (typeof data.detail === 'string') {
					setErro(data.detail)
				} else {
					setErro('Confira o nome de usuário e a senha informados.')
				}

				return
			}

			const data: AuthTokenResponse = await response.json()
			auth.accessToken = data.access_token
			navigate('/', { replace: true })
		} catch {
			setErro('Não foi possível entrar na conta. Tente novamente.')
		} finally {
			setEnviando(false)
		}
	}

	return (
		<main className='pages-conta pages-login'>
			<Link to='/acesso' className='voltar-conta'>
				<img src={caretLeft} alt="Voltar" />
			</Link>

			<div className='conteudo-conta'>
				<h2>Entrar</h2>
				<p className='frase-conta'>Bom te ver de volta.</p>

				<form className='formulario-conta' onSubmit={login}>
					<div className='campo-conta'>
						<label htmlFor='usuario-login'>Nome de usuário</label>
						<input id='usuario-login' name='username' type="text" placeholder="Seu nome de usuário" autoComplete="username" autoCapitalize="none" spellCheck={false} required />
					</div>

					<div className='campo-conta'>
						<label htmlFor='senha-login'>Senha</label>
						<input id='senha-login' name='password' type="password" placeholder="Sua senha" autoComplete="current-password" required />
					</div>

					<button className='botao-conta' type="submit" disabled={enviando}>Entrar</button>

					{erro && <p className='mensagem-conta' role="alert">{erro}</p>}
				</form>
			</div>
		</main>
	)
}
