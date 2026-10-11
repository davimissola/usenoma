import type { UsuarioInicioProps } from '../../types/users'
import { EstiloPreferido } from '../EstiloPreferido'
import fotoUsuario from '../../assets/svg/illustrations/fotoUsuario.png'
import fotoTeste03 from '../../assets/svg/illustrations/fotoTeste01.png'
import './usuario-inicio.css'


export function UsuarioInicio({ usuario }: UsuarioInicioProps) {
	return (
		<section className='inicio-usuario'>
			<div className='perfil-usuario'>
				<div className='foto-usuario'>
					<img src={fotoUsuario} alt={`Foto de ${usuario.username}`} />
				</div>

				<div className='dados-usuario'>
					<h2>{usuario.username}</h2>

					{/* Os contadores ficam fixos nesta primeira versão da tela. */}
					<div className='estatisticas-usuario'>
						<span>0 seguindo</span>
						<span>0 salvos</span>
					</div>
				</div>
			</div>

			<div className='card-desconto-usuario'>
				<div className='texto-desconto-usuario'>
					<h3>10% em qualquer loja</h3>
					<p>Faltam 5 compras no mês<br />para resgatar</p>
				</div>

				<span className='numero-desconto-usuario'>5</span>
			</div>

			{/* Imagem e estilo de teste enquanto esses dados não vêm do backend. */}
			<EstiloPreferido image={fotoTeste03} styleName='Streetwear' />
		</section>
	)
}
