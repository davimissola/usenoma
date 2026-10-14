import type { ProdutoResponse } from './produtos'


export type VarianteImagemLojaResponse = {
	url: string
	mime_type: 'image/jpeg' | 'image/png' | 'image/webp'
	width: number
	height: number
	size_bytes: number
}

export type VariantesImagemLoja = {
	small?: VarianteImagemLojaResponse
	medium?: VarianteImagemLojaResponse
	large?: VarianteImagemLojaResponse
}

export type LojaPublicaResponse = {
	id: string
	name: string
	slug: string
	description: string | null
	logo: VariantesImagemLoja | null
	cover: VariantesImagemLoja | null
}

export type HeroLojaCapaProps = {
	image?: string
	largeImage?: string
	logo?: string
	nomeLoja: string
}

export type FaixaProdutosLojaProps = {
	titulo: string
	produtos: ProdutoResponse[]
}

export type ImagemEditorialLojaProps = {
	imagens: [string, string, string]
}
