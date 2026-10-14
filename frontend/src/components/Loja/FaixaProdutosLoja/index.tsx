import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { FaixaProdutosLojaProps } from '../../../types/lojas'
import './faixa-produtos-loja.css'


// O preço chega como string decimal; Number é usado somente para exibir a moeda.
const formatoPreco = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })


export function FaixaProdutosLoja({ titulo, produtos }: FaixaProdutosLojaProps) {
	const [imagensComErro, setImagensComErro] = useState<string[]>([])

	if (produtos.length === 0) {
		return null
	}

	return (
		<section className='faixa-produtos-loja' aria-label="Produtos da loja">
			<h3 className='titulo-faixa-produtos-loja'>{titulo}</h3>
			<div className='lista-produtos-loja' tabIndex={0} aria-label="Lista de produtos da loja">
				{produtos.map((produto) => {
					const imagem = produto.images[0]?.variants.card.url

					return (
						<Link className='produto-loja' to={`/produto/${produto.id}`} key={produto.id}>
							<figure className='imagem-produto'>
								{imagem && !imagensComErro.includes(imagem) ? (
									<img className='imagem-produto-loja' src={imagem} alt={produto.name} loading="lazy" onError={() => setImagensComErro(imagens => [...imagens, imagem])} />
								) : (
									<div className='imagem-produto-loja imagem-produto-ausente' aria-hidden="true" />
								)}

								<figcaption className='legenda-produto-loja'>
									<h3>{produto.name}</h3>
									<p>{formatoPreco.format(Number(produto.price))}</p>
								</figcaption>
							</figure>
						</Link>
					)
				})}
			</div>
		</section>
	)
}
