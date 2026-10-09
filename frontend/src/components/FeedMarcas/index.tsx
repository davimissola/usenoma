import type { FeedMarcasProps } from '../../types/feed'
import './feed-marcas.css'


export function FeedMarcas({ brands }: FeedMarcasProps) {
	if (brands.length === 0) return null

	return (
		<section className='bloco-feed feed-marcas' aria-label="Marcas">
			<h4>Marcas na Noma</h4>
			<ul className='lista-feed' tabIndex={0} aria-label="Lista de marcas">
				{brands.map((brand, index) => (
					<li className='marca-feed' key={`${brand}-${index}`}>
						<img src={brand} alt={`Marca ${index + 1}`} loading="lazy" />
					</li>
				))}
			</ul>
		</section>
	)
}
