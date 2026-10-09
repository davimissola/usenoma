import heartSvg from '../../assets/svg/icons/heart-thin.svg'
import bookmarkSvg from '../../assets/svg/icons/bookmark-simple-thin.svg'
import type { FeedProdutosListaProps } from '../../types/feed'
import './feed-produtos.css'


export function FeedProdutos({ products }: FeedProdutosListaProps) {
	if (products.length === 0) return null

	return (
		<section className='bloco-feed feed-produtos' aria-label="Produtos">
			<ul className='lista-feed' tabIndex={0} aria-label="Lista de produtos" >

				{products.map((product, index) => (
					<li className='produto-feed' key={`${product.productImage}-${index}`}>
						<figure className='imagem-produto'>
							<img
								className='imagem-feed-produto'
								src={product.productImage}
								alt={`Produto ${index + 1}`}
								loading="lazy"
							/>

							<figcaption className='legenda-feed-produtos'>
								<img className='logo-marca-produto' src={product.brandLogo} alt="Logo da marca" loading="lazy" />

								<div className='icones-feed-produtos'>
									<img src={heartSvg} alt="Curtir" />
									<img src={bookmarkSvg} alt="Salvar" />
								</div>
							</figcaption>
						</figure>
					</li>
				))}
				
			</ul>
		</section>
	)
}
