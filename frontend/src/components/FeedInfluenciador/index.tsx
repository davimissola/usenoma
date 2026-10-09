import type { FeedInfluenciadorProps } from '../../types/feed'
import fotoPerfilTeste from '../../assets/svg/illustrations/fotoPerfilTeste.png'
import './feed-influenciador.css'
import heartSvg from '../../assets/svg/icons/heart-thin.svg'
import bookmarkSvg from '../../assets/svg/icons/bookmark-simple-thin.svg'



export function FeedInfluenciador({image, influencerName, imageAlt = `Foto de ${influencerName}`, }: FeedInfluenciadorProps) {

	return (
		<figure className='bloco-feed feed-influenciador'>
			<img className='imagem-feed imagem-feed-influenciador' src={image} alt={imageAlt} loading="lazy" />

			<figcaption className='legenda-feed-influenciador'>
				<div>
					<img className='foto-perfil-influenciador' src={fotoPerfilTeste} alt={`Foto perfil ${influencerName}`} />
					<img src={heartSvg} alt="Curtir" />
					<img src={bookmarkSvg} alt="Salvar" />
				</div>
				<span>{influencerName}</span>
			</figcaption>
		</figure>
	)
}
