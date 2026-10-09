export type FeedCardProps = {
	image: string
	title: string
	imageAlt?: string
}

export type FeedProdutosProps = {
	productImage: string
	brandLogo: string
}

export type FeedProdutosListaProps = {
	products: FeedProdutosProps[]
}

export type FeedInfluenciadorProps = {
	image: string
	influencerName: string
	imageAlt?: string
}

export type FeedMarcasProps = {
	brands: readonly string[]
}
