import { Link } from 'react-router-dom'
import caretLeft from '../../assets/svg/icons/caret-left-thin.svg'
import caretRight from '../../assets/svg/icons/caret-right-thin.svg'
import '../conta.css'


export function CriarConta() {

	return (
		<main className='pages-conta pages-criar-conta'>
			<Link to='/acesso' className='voltar-conta'>
				<img src={caretLeft} alt="Voltar" />
			</Link>

			<div className='conteudo-conta'>
				<h2>Criar conta</h2>
				<p className='frase-conta'>Seu estilo começa aqui.</p>

				<form className='formulario-conta' onSubmit={(event) => event.preventDefault()}>
					<div className='campo-conta'>
						<label htmlFor='usuario-criar-conta'>Nome de usuário</label>
						<input id='usuario-criar-conta' name='username' type="text" placeholder="Seu nome de usuário" autoComplete="username" autoCapitalize="none" spellCheck={false} />
					</div>

					<div className='campo-conta'>
						<label htmlFor='email-criar-conta'>Email</label>
						<input id='email-criar-conta' name='email' type="email" placeholder="Seu email" autoComplete="email" autoCapitalize="none" spellCheck={false} />
					</div>

					<div className='campo-conta'>
						<label htmlFor='senha-criar-conta'>Senha</label>
						<input id='senha-criar-conta' name='password' type="password" placeholder="Crie sua senha" autoComplete="new-password" />
					</div>

					<div className='campo-conta'>
						<label htmlFor='confirmar-senha-criar-conta'>Confirmar senha</label>
						<input id='confirmar-senha-criar-conta' name='confirmPassword' type="password" placeholder="Confirme sua senha" autoComplete="new-password" />
					</div>

					<button className='botao-conta' type="submit">
						Próximo
						<img src={caretRight} alt="Próximo" />
					</button>
				</form>
			</div>
		</main>
	)
}
