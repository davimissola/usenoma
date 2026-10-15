import type { LojaPublicaResponse } from './lojas'
import type { ImagemProdutoResponse } from './produtos'


export type ItemCarrinhoResponse = {
	id: string
	product_id: string | null
	product: {
		id: string
		name: string
		description: string | null
		sizes: string[]
	} | null
	image: ImagemProdutoResponse | null
	size: string
	quantity: number
	unit_price: string | null
	subtotal: string | null
	store: (Pick<LojaPublicaResponse, 'id' | 'name' | 'slug' | 'description'> & { logo_url: string | null }) | null
	available: boolean
	unavailable_reason: 'product_removed' | 'size_removed' | 'size_unavailable' | null
}

export type CarrinhoResponse = {
	id: string | null
	updated_at: string | null
	items: ItemCarrinhoResponse[]
}

export type AlteracaoItemCarrinho = {
	quantity?: number
	size?: string
}

export type ItemCarrinhoProps = {
	item: ItemCarrinhoResponse
	alterando: boolean
	onAlterar: (itemId: string, dados: AlteracaoItemCarrinho) => Promise<void>
	onRemover: (itemId: string) => Promise<void>
}
