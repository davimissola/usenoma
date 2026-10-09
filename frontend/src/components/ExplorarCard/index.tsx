import './explorar-card.css'
import fotoTeste02 from '../../assets/svg/illustrations/fotoTeste02.png'



export function ExplorarCard() {
	return (
		<div className='div-card-explorar'>
			<div className='barra-tempo-explorar' aria-hidden="true" />

			<div className='conteudo-card-explorar'>
				<h2>Streetwear</h2>
				<a href="#">Explore</a>
			</div>

			<img className='imagem-background-explorar' src={fotoTeste02} alt="" />
		</div>
	)
}