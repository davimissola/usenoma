import { useState } from 'react'
import type { HeroLojaCapaProps } from '../../types/lojas'
import './hero-loja-capa.css'


export function HeroLojaCapa({ image, largeImage, logo, nomeLoja }: HeroLojaCapaProps) {
	const [erroCapa, setErroCapa] = useState(false)
	const [erroLogo, setErroLogo] = useState(false)

	return (
		<section className='hero-loja-capa'>
			{image && !erroCapa && (
				<picture>
					{/* O navegador escolhe a capa maior no desktop, sem estado de tamanho de tela. */}
					{largeImage && <source media="(min-width: 960px)" srcSet={largeImage} />}
					<img className='imagem-hero-loja' src={image} alt="" onError={() => setErroCapa(true)} />
				</picture>
			)}

			<div className='perfil-hero-loja'>
				{logo && !erroLogo ? (
					<div className='logo-hero-loja'>
						<img src={logo} alt={`Logo de ${nomeLoja}`} onError={() => setErroLogo(true)} />
					</div>
				) : (
					<h2>{nomeLoja}</h2>
				)}
				<div className='perfil-hero-loja-conteudo'>
					<p>
						12.5k
						<span>seguidores</span>
					</p>
					<p>
						33
						<span>produtos</span>
					</p>
				</div>
			</div>
		</section>
	)
}
