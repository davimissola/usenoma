import { useRef, useState, type MouseEvent, type PointerEvent } from 'react'
import { Link } from 'react-router-dom'
import './explorar-card.css'
import type { ExplorarCardListaProps } from '../../types/explorar'


export function ExplorarCard({ styles }: ExplorarCardListaProps) {
	const [indiceAtual, setIndiceAtual] = useState(0)
	const inicioGesto = useRef({ x: 0, y: 0, arrastou: false })

	function avancarEstilo() {
		setIndiceAtual(indice => indice + 1)
	}

	function iniciarGesto(event: PointerEvent<HTMLDivElement>) {
		// Guarda o início do arraste sem renderizar o card novamente.
		inicioGesto.current = { x: event.clientX, y: event.clientY, arrastou: false }
	}

	function finalizarGesto(event: PointerEvent<HTMLDivElement>) {
		const distanciaHorizontal = Math.abs(event.clientX - inicioGesto.current.x)
		const distanciaVertical = Math.abs(event.clientY - inicioGesto.current.y)

		if (distanciaHorizontal >= 50 && distanciaHorizontal > distanciaVertical) {
			inicioGesto.current.arrastou = true
			avancarEstilo()
		}
	}

	function ignorarCliqueAposArraste(event: MouseEvent<HTMLDivElement>) {
		// O arraste já avançou: evita um segundo avanço ou abrir o Link ao soltar.
		if (inicioGesto.current.arrastou && event.detail > 0) {
			event.preventDefault()
			event.stopPropagation()
			inicioGesto.current.arrastou = false
		}
	}

	if (styles.length === 0) {
		return null
	}

	const style = styles[indiceAtual % styles.length]

	return (
		<div className='div-card-explorar' onPointerDown={iniciarGesto} onPointerUp={finalizarGesto} onClickCapture={ignorarCliqueAposArraste}>
			{/* A key reinicia os 10 segundos também quando o usuário avança manualmente. */}
			<div className='barra-tempo-explorar' key={indiceAtual} aria-hidden="true" onAnimationEnd={avancarEstilo} />

			<button className='avancar-card-explorar' type="button" aria-label="Próximo estilo" onClick={avancarEstilo} />

			<div className='conteudo-card-explorar'>
				<h2>{style.styleName}</h2>
				<Link to='/' draggable={false}>Explore</Link>
			</div>

			<img className='imagem-background-explorar' src={style.image} alt="" draggable={false} />
		</div>
	)
}
