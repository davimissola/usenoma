import { useRef, useState, type KeyboardEvent, type UIEvent } from 'react'
import type { GaleriaProdutoProps } from '../../../types/produtos'
import './galeria-produto.css'


export function GaleriaProduto({ imagens, nomeProduto }: GaleriaProdutoProps) {
	const [indiceAtual, setIndiceAtual] = useState(0)
	const [imagensComErro, setImagensComErro] = useState<string[]>([])
	const listaImagens = useRef<HTMLDivElement>(null)

	function trocarImagem(indice: number) {
		if (!listaImagens.current) {
			return
		}

		listaImagens.current.scrollTo({ left: indice * listaImagens.current.clientWidth, behavior: 'smooth' })
	}

	function atualizarIndice(event: UIEvent<HTMLDivElement>) {
		const { scrollLeft, clientWidth } = event.currentTarget

		if (clientWidth > 0) {
			setIndiceAtual(Math.max(0, Math.min(imagens.length - 1, Math.round(scrollLeft / clientWidth))))
		}
	}

	function navegarImagens(event: KeyboardEvent<HTMLDivElement>) {
		if (event.key === 'ArrowRight') {
			event.preventDefault()
			trocarImagem(Math.min(indiceAtual + 1, imagens.length - 1))
		} else if (event.key === 'ArrowLeft') {
			event.preventDefault()
			trocarImagem(Math.max(indiceAtual - 1, 0))
		}
	}

	// A repetição preenche somente os quatro slots do desktop, sem alterar a lista recebida.
	const imagensDesktop = Array.from({ length: 4 }, (_, indice) => {
		if (imagens.length === 0) {
			return null
		}

		return imagens[indice % imagens.length]
	})

	return (
		<div className='galeria-produto'>
			<div className='grade-imagens-produto' aria-label="Imagens do produto">
				{imagensDesktop.map((imagem, indice) => (
					<div className='foto-grade-produto' key={indice}>
						{imagem && !imagensComErro.includes(imagem.id) ? (
							<img src={imagem.variants.large.url} alt={`${nomeProduto} — imagem ${imagem.position}`} loading="lazy" decoding="async" onError={() => setImagensComErro(imagens => [...imagens, imagem.id])} />
						) : (
							<p className='imagem-ausente-produto'>{imagem ? 'Imagem indisponível.' : 'Produto sem imagem.'}</p>
						)}
					</div>
				))}
			</div>

			<div className='carousel-produto'>
				{imagens.length === 0 ? (
					<p className='imagem-ausente-produto'>Produto sem imagem.</p>
				) : (
					<>
						{/* O scroll nativo funciona com toque; o CSS encaixa uma foto por vez. */}
						<div className='lista-imagens-produto' ref={listaImagens} onScroll={atualizarIndice} onKeyDown={navegarImagens} tabIndex={imagens.length > 1 ? 0 : undefined} aria-label="Imagens do produto">
							{imagens.map((imagem, indice) => (
								<div className='foto-galeria-produto' key={imagem.id}>
									{imagensComErro.includes(imagem.id) ? (
										<p className='imagem-ausente-produto'>Imagem indisponível.</p>
									) : (
										<img src={imagem.variants.large.url} alt={`${nomeProduto} — imagem ${indice + 1}`} loading={indice === 0 ? 'eager' : 'lazy'} decoding="async" draggable={false} onError={() => setImagensComErro(imagens => [...imagens, imagem.id])} />
									)}
								</div>
							))}
						</div>

						{imagens.length > 0 && (
							<div className='indicadores-imagens-produto' aria-label="Escolher imagem">
								{imagens.map((imagem, indice) => (
									<button className={`indicador-imagem-produto ${indiceAtual === indice ? 'imagem-selecionada-produto' : ''}`} type="button" key={imagem.id} aria-label={`Ver imagem ${indice + 1}`} aria-pressed={indiceAtual === indice} onClick={() => trocarImagem(indice)} />
								))}
							</div>
						)}
					</>
				)}
			</div>
		</div>
	)
}
