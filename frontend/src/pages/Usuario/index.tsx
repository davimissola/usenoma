import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { UsuarioInicio } from '../../components/UsuarioInicio'
import { auth, requisicaoAutenticada } from '../../stores/auth'
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
				// Envia o token e, se necessário, faz um refresh e repete a consulta uma vez.
				const response = await requisicaoAutenticada('/users/me')

				if (!ativo) {
					return
				}

				if (response.status === 401) {
					// Só chega aqui se a recuperação falhou ou o novo token também foi rejeitado.
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

	// O App já terminou a verificação inicial antes de abrir esta página.
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
