import heartSvg from '../../assets/svg/icons/heart-thin.svg'
import bookmarkSvg from '../../assets/svg/icons/bookmark-simple-thin.svg'
import arrowUpRight from '../../assets/svg/icons/arrow-up-right-thin.svg'
import type { FeedCardProps } from '../../types/feed'
import './feed-card.css'


export function FeedCard({ image, title, imageAlt = title }: FeedCardProps) {

	return (
		<figure className='bloco-feed feed-card'>
			<img className='imagem-feed imagem-feed-card' src={image} alt={imageAlt} loading="lazy" />

			<figcaption className='legenda-feed-card'>
				<span className='texto-feed-card'>
					{title} <img src={arrowUpRight} alt="Clique aqui" />
				</span>

				<div className='icones-feed-card'>
					<img src={heartSvg} alt="Curtir" />
					<img src={bookmarkSvg} alt="Salvar" />
				</div>
			</figcaption>
		</figure>
	)
}
