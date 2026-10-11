import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { apiUrl } from '../../config'
import { UsuarioInicio } from '../../components/UsuarioInicio'
import { auth } from '../../stores/auth'
import type { UserResponse } from '../../types/users'
import caretLeft from '../../assets/svg/icons/caret-left-thin.svg'
import dotsThree from '../../assets/svg/icons/dots-three-thin.svg'
import './usuario.css'


export function Usuario() {
	const [usuario, setUsuario] = useState<UserResponse | null>(null)
	const [erro, setErro] = useState('')
	const navigate = useNavigate()

	useEffect(() => {
		if (!auth.accessToken) {
			return
		}

		let ativo = true

		async function buscarUsuario() {
			try {
				// O backend identifica o usuário pelo access token enviado no Authorization.
				const response = await fetch(`${apiUrl}/users/me`, {
					headers: {
						Authorization: `Bearer ${auth.accessToken}`
					}
				})

				if (!ativo) {
					return
				}

				if (response.status === 401) {
					// O Acesso tenta recuperar a sessão quando o token é rejeitado.
					auth.accessToken = ''
					navigate('/acesso', { replace: true })
					return
				}

				if (!response.ok) {
					setErro('Não foi possível carregar os dados do usuário.')
					return
				}

				const data: UserResponse = await response.json()

				if (ativo) {
					setUsuario(data)
				}
			} catch {
				if (ativo) {
					setErro('Não foi possível carregar os dados do usuário.')
				}
			}
		}

		buscarUsuario()

		return () => {
			// Evita atualizar o estado depois que o usuário sair desta página.
			ativo = false
		}
	}, [navigate])

	// Sem token na memória, o Acesso tenta recuperar a sessão pelo cookie.
	if (!auth.accessToken) {
		return <Navigate to='/acesso' replace />
	}

	return (
		<main className='pages-usuario'>
			<Link to='/' className='voltar-usuario'>
				<img src={caretLeft} alt="Voltar" />
			</Link>

			<button className='ajustes-usuario' type="button">
				<img src={dotsThree} alt="Ajustes" />
			</button>

			{erro && <p>{erro}</p>}
			{usuario && <UsuarioInicio usuario={usuario} />}
		</main>
	)
}
