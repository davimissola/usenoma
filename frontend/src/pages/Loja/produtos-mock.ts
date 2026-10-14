import produtoTeste01 from '../../assets/svg/illustrations/produtoTeste01.webp'
import produtoTeste02 from '../../assets/svg/illustrations/produtoTeste02.webp'
import type { ProdutoLoja } from '../../types/lojas'


// Dados temporários da página; o componente só recebe e exibe a lista.
export const produtosMock: ProdutoLoja[] = [
	{ id: 'produto-01', name: 'Camiseta Oversized', price: 149.9, image: produtoTeste01 },
	{ id: 'produto-02', name: 'Camiseta Boxy', price: 129.9, image: produtoTeste02 },
	{ id: 'produto-03', name: 'Camiseta Classic', price: 99.9, image: produtoTeste01 },
	{ id: 'produto-04', name: 'Camiseta Boxy', price: 119.9, image: produtoTeste02 },
]
