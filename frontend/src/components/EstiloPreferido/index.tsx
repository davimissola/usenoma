import type { EstiloPreferidoProps } from '../../types/users'
import './estilo-preferido.css'
import arrowUpRight from '../../assets/svg/icons/arrow-up-right-thin.svg'


export function EstiloPreferido({ image, styleName }: EstiloPreferidoProps) {
	return (
		<figure className='card-estilo-preferido'>
			<img className='imagem-estilo-preferido' src={image} alt={`Estilo ${styleName}`} />

			<figcaption className='legenda-estilo-preferido'>
				<h2>
					{styleName} na noma
					<img src={arrowUpRight} alt="Explore" />
				</h2>
				<p>Onde estilo vira identidade.</p>
			</figcaption>
		</figure>
	)
}
