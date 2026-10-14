import type { ImagemEditorialLojaProps } from '../../../types/lojas'
import './imagem-editorial-loja.css'


export function ImagemEditorialLoja({ imagens }: ImagemEditorialLojaProps) {
	return (
		<div className='imagens-editoriais-loja' tabIndex={0} aria-label="Imagens da loja">
			{imagens.map((imagem, index) => (
				<img className='imagem-editorial-loja' key={index} src={imagem} alt="" loading="lazy" />
			))}
		</div>
	)
}
