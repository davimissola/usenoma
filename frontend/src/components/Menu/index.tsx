import closeSvg from '../../assets/svg/icons/x-thin.svg'
import tiktokSvg from '../../assets/svg/icons/tiktok-logo-thin.svg'
import instagramSvg from '../../assets/svg/icons/instagram-logo-thin.svg'
import logoTeste from '../../assets/svg/logos/logoTeste.png'
import './menu.css'


type MenuProps = {
	menuAberto: boolean
	setMenuAberto: (aberto: boolean) => void
}


export function Menu({ menuAberto, setMenuAberto }: MenuProps) {

	return (
		<div className={menuAberto ? 'menu menu-aberto' : 'menu'} inert={!menuAberto}>
			<button className='fechar-menu' type="button" onClick={() => setMenuAberto(false)}>
				<img src={closeSvg} alt="Fechar menu" width={28} height={28} />
			</button>

			<div className='logo-menu'>
				<img src={logoTeste} alt="" />
			</div>

			<nav className='navegacao-menu' aria-label="Navegação principal">
                    <a href='/' onClick={() => setMenuAberto(false)}>Início</a>
					<a href='/produtos' onClick={() => setMenuAberto(false)}>Produtos</a>
					<a href='/marcas' onClick={() => setMenuAberto(false)}>Marcas</a>
					<a href='/cadastrar' onClick={() => setMenuAberto(false)}>Cadastrar</a>
					<a href='/seja-parceiro' onClick={() => setMenuAberto(false)}>Seja parceiro</a>
			</nav>

			<div className='redes-menu'>
				<a href='https://www.instagram.com/nomabrasil/' target="_blank" rel="noopener noreferrer">
                    <img src={instagramSvg} alt="Instagram nomabrasil" />
					<span>nomabrasil</span>
				</a>

				<a href='https://www.tiktok.com/@nomabrasil' target="_blank" rel="noopener noreferrer">
                    <img src={tiktokSvg} alt="Instagram nomabrasil" />
					<span>nomabrasil</span>
				</a>
			</div>
		</div>
	)
}
