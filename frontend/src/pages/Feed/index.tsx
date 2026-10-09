import { FeedCard } from '../../components/FeedCard'
import { FeedMarcas } from '../../components/FeedMarcas'
import { FeedProdutos } from '../../components/FeedProdutos'
import { Header } from '../../components/Header'
import fotoTeste03 from '../../assets/svg/illustrations/fotoTeste03.png'
import fotoTeste04 from '../../assets/svg/illustrations/fotoTeste04.png'
import fotoTeste06 from '../../assets/svg/illustrations/fotoTeste06.png'
import produtoTeste01 from '../../assets/svg/illustrations/produtoTeste01.png'
import produtoTeste02 from '../../assets/svg/illustrations/produtoTeste02.png'
import './feed.css'
import { FeedInfluenciador } from '../../components/FeedInfluenciador'



export function Feed() {
	return (
		<>
			<Header />

			<main className='pages-feed'>
				<FeedCard image={fotoTeste03} title='Explore streetwear na Noma' />

				<FeedInfluenciador image={fotoTeste04} influencerName='davimissola' />

				<FeedMarcas brands={[fotoTeste03, fotoTeste04, fotoTeste03, fotoTeste04, fotoTeste03, fotoTeste04, fotoTeste03]} />

				<FeedProdutos products={[
					{ productImage: produtoTeste01, brandLogo: fotoTeste03 },
					{ productImage: produtoTeste02, brandLogo: fotoTeste04 },
				]} />

                <FeedInfluenciador image={fotoTeste06} influencerName='davimissola' />
			</main>
		</>
	)
}