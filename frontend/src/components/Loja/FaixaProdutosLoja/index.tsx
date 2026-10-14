import type { FaixaProdutosLojaProps } from '../../../types/lojas'
import './faixa-produtos-loja.css'


const formatoPreco = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })


export function FaixaProdutosLoja({ titulo, produtos }: FaixaProdutosLojaProps) {
	if (produtos.length === 0) {
		return null
	}

	return (
		<section className='faixa-produtos-loja' aria-label="Produtos da loja">
			<h3 className='titulo-faixa-produtos-loja'>{titulo}</h3>
			<div className='lista-produtos-loja' tabIndex={0} aria-label="Lista de produtos da loja">
				{produtos.map((produto) => (
					<div className='produto-loja' key={produto.id}>
						<figure className='imagem-produto'>
							<img className='imagem-produto-loja' src={produto.image} alt={produto.name} loading="lazy" />

							<figcaption className='legenda-produto-loja'>
								<h3>{produto.name}</h3>
								<p>{formatoPreco.format(produto.price)}</p>
							</figcaption>
						</figure>
					</div>
				))}
			</div>
		</section>
	)
}
