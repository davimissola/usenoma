import { ExplorarCard } from '../../components/ExplorarCard'
import fotoTeste02 from '../../assets/svg/illustrations/fotoTeste02.png'
import fotoTeste07 from '../../assets/svg/illustrations/fotoTeste07.png'
import './explorar.css'



export function Explorar() {
	return (
		<main>
			<ExplorarCard styles={[
				{ image: fotoTeste02, styleName: 'Streetwear' },
				{ image: fotoTeste07, styleName: 'Minimalista' },
			]} />
		</main>
	)
}