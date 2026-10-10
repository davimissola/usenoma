import { useState, type SubmitEvent } from 'react'
import { Link } from 'react-router-dom'
import type { AuthErrorResponse, AuthTokenResponse } from '../../types/auth'
import caretLeft from '../../assets/svg/icons/caret-left-thin.svg'
import caretRight from '../../assets/svg/icons/caret-right-thin.svg'
import '../conta.css'


export function CriarConta() {
	const [accessToken, setAccessToken] = useState('')
	const [erro, setErro] = useState('')
	const [enviando, setEnviando] = useState(false)

	async function criarConta(event: SubmitEvent<HTMLFormElement>) {
		event.preventDefault()

		if (enviando) {
			return
		}

		const formData = new FormData(event.currentTarget)
		const password = String(formData.get('password') ?? '')
		const confirmPassword = String(formData.get('confirmPassword') ?? '')

		setErro('')
		setAccessToken('')

		if (password !== confirmPassword) {
			setErro('As senhas não coincidem.')
			return
		}

		setEnviando(true)

		try {
			const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
			const response = await fetch(`${apiUrl.replace(/\/+$/, '')}/auth/register`, { 
				method: 'POST',
				credentials: 'include',
				
				headers: { 
					'Content-Type': 
					'application/json' 
				}, 

				body: JSON.stringify({ 
					username: formData.get('username'), 
					email: formData.get('email'), 
					password 
				}) 
			})

			if (!response.ok) {
				const data: AuthErrorResponse = await response.json()

				if (typeof data.detail === 'string') {
					setErro(data.detail)
				} else {
					setErro('Confira o nome de usuário, o email e a senha informados.')
				}

				return
			}

			const data: AuthTokenResponse = await response.json()
			setAccessToken(data.access_token)
		} catch {
			setErro('Não foi possível criar a conta. Tente novamente.')
		} finally {
			setEnviando(false)
		}
	}

	return (
		<main className='pages-conta pages-criar-conta'>
			<Link to='/acesso' className='voltar-conta'>
				<img src={caretLeft} alt="Voltar" />
			</Link>

			<div className='conteudo-conta'>
				<h2>Criar conta</h2>
				<p className='frase-conta'>Seu estilo começa aqui.</p>

				<form className='formulario-conta' onSubmit={criarConta}>
					<div className='campo-conta'>
						<label htmlFor='usuario-criar-conta'>Nome de usuário</label>
						<input id='usuario-criar-conta' name='username' type="text" placeholder="Seu nome de usuário" autoComplete="username" autoCapitalize="none" spellCheck={false} required />
					</div>

					<div className='campo-conta'>
						<label htmlFor='email-criar-conta'>Email</label>
						<input id='email-criar-conta' name='email' type="email" placeholder="Seu email" autoComplete="email" autoCapitalize="none" spellCheck={false} required />
					</div>

					<div className='campo-conta'>
						<label htmlFor='senha-criar-conta'>Senha</label>
						<input id='senha-criar-conta' name='password' type="password" placeholder="Crie sua senha" autoComplete="new-password" required />
					</div>

					<div className='campo-conta'>
						<label htmlFor='confirmar-senha-criar-conta'>Confirmar senha</label>
						<input id='confirmar-senha-criar-conta' name='confirmPassword' type="password" placeholder="Confirme sua senha" autoComplete="new-password" required />
					</div>

					<button className='botao-conta' type="submit" disabled={enviando}>
						Próximo
						<img src={caretRight} alt="Próximo" />
					</button>

					{erro && <p className='mensagem-conta' role="alert">{erro}</p>}
					{accessToken && <p className='mensagem-conta' role="status">Conta criada com sucesso.</p>}
				</form>
			</div>
		</main>
	)
}
