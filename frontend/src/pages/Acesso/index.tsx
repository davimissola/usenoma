import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { auth, recuperarSessao } from '../../stores/auth'
import videoTeste01 from '../../assets/videos/videoTeste01.mp4'
import caretLeft from '../../assets/svg/icons/caret-left-thin.svg'
import './acesso.css'


export function Acesso() {
	const [verificandoSessao, setVerificandoSessao] = useState(!auth.accessToken)

	useEffect(() => {
		let ativo = true

		async function verificarSessao() {
			// Após F5, recupera a sessão usando o refresh token do cookie.
			await recuperarSessao()

			if (ativo) {
				setVerificandoSessao(false)
			}
		}

		verificarSessao()

		return () => {
			// Evita atualizar o estado depois que o usuário sair desta página.
			ativo = false
		}
	}, [])

	if (auth.accessToken) {
		// O Header aponta para /acesso. Quem já tem sessão segue para /usuario.
		return <Navigate to='/usuario' replace />
	}

	if (verificandoSessao) {
		return <main className='pages-acesso' />
	}

	return (
		<main className='pages-acesso'>
			<div className='conteudo-acesso'>
				<Link to='/' className='voltar-acesso'>
					<img src={caretLeft} alt="Voltar" />
				</Link>
				<div className='conteudo-acesso-bottom'>
					<h2>Onde estilo vira identidade.</h2>
					<div className='conteudo-acesso-buttons'>
						<Link to='/login'>Entrar</Link>
						<Link to='/criar-conta'>Criar</Link>
					</div>
				</div>
			</div>

			<video className='video-acesso' src={videoTeste01} autoPlay loop muted playsInline aria-hidden="true" />
		</main>
	)
}
