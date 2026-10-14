export type ImagemProdutoResponse = {
	id: string
	position: number
	variants: {
		card: { url: string }
		large: { url: string }
	}
}

export type ProdutoResponse = {
	id: string
	store_id: string
	name: string
	price: string
	description: string | null
	sizes: { size: string; available: boolean }[]
	images: ImagemProdutoResponse[]
}
