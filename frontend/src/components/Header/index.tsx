import { useState } from 'react'
import menuSvg from '../../assets/svg/icons/list-thin.svg'
import closeSvg from '../../assets/svg/icons/x-thin.svg'
import './header.css'
import { Menu } from '../Menu'
import userSvg from '../../assets/svg/icons/user-thin.svg'
import shoppingCart from '../../assets/svg/icons/shopping-cart-simple-thin.svg'
import { Link } from 'react-router-dom'


export function Header() {
	const [menuAberto, setMenuAberto] = useState(false)

	return (
		<header className='header'>
			<div className='coluna-header'>
				<button className='botao-menu' type="button" onClick={() => setMenuAberto(!menuAberto)}>
					<img src={menuAberto ? closeSvg : menuSvg} alt={menuAberto ? 'Fechar menu' : 'Abrir menu'} />
				</button>
			</div>

			<div className='coluna-header'>
				<Link to='/acesso'>
					<img src={userSvg} alt="User" />
				</Link>
				<a href="#">
					<img src={shoppingCart} alt="Cart" />
				</a>
			</div>

			<Menu menuAberto={menuAberto} setMenuAberto={setMenuAberto} />
		</header>
	)
}