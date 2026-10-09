import { Link } from 'react-router-dom'
import caretLeft from '../../assets/svg/icons/caret-left-thin.svg'
import '../conta.css'


export function Login() {

	return (
		<main className='pages-conta pages-login'>
			<Link to='/acesso' className='voltar-conta'>
				<img src={caretLeft} alt="Voltar" />
			</Link>

			<div className='conteudo-conta'>
				<h2>Entrar</h2>
				<p className='frase-conta'>Bom te ver de volta.</p>

				<form className='formulario-conta' onSubmit={(event) => event.preventDefault()}>
					<div className='campo-conta'>
						<label htmlFor='usuario-login'>Nome de usuário</label>
						<input id='usuario-login' name='username' type="text" placeholder="Seu nome de usuário" autoComplete="username" autoCapitalize="none" spellCheck={false} />
					</div>

					<div className='campo-conta'>
						<label htmlFor='senha-login'>Senha</label>
						<input id='senha-login' name='password' type="password" placeholder="Sua senha" autoComplete="current-password" />
					</div>

					<button className='botao-conta' type="submit">Entrar</button>
				</form>
			</div>
		</main>
	)
}
