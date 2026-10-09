import { useState } from 'react'
import './explorar-card.css'
import type { ExplorarCardListaProps } from '../../types/explorar'


export function ExplorarCard({ styles }: ExplorarCardListaProps) {
	const [indiceAtual, setIndiceAtual] = useState(0)

	if (styles.length === 0) return null

	const style = styles[indiceAtual % styles.length]

	return (
		<div className='div-card-explorar'>
			<div className='barra-tempo-explorar' key={indiceAtual} aria-hidden="true" onAnimationEnd={() => setIndiceAtual(indiceAtual + 1)} />

			<div className='conteudo-card-explorar'>
				<h2>{style.styleName}</h2>
				<a href="#">Explore</a>
			</div>

			<img className='imagem-background-explorar' src={style.image} alt="" />
		</div>
	)
}
