import { Link, Navigate } from 'react-router-dom'
import { auth } from '../../stores/auth'
import videoTeste01 from '../../assets/videos/videoTeste01.mp4'
import caretLeft from '../../assets/svg/icons/caret-left-thin.svg'
import './acesso.css'


export function Acesso() {
	if (auth.accessToken) {
		// O Header aponta para /acesso. Quem já tem sessão segue para /usuario.
		return <Navigate to='/usuario' replace />
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
