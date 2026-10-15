import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { ItemCarrinhoProps } from '../../../types/carrinho'
import trashSvg from '../../../assets/svg/icons/trash-thin.svg'
import './item-carrinho.css'


const formatoPreco = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })


export function ItemCarrinho({ item, alterando, onAlterar, onRemover }: ItemCarrinhoProps) {
	const [imagemComErro, setImagemComErro] = useState('')
	const [logoComErro, setLogoComErro] = useState('')
	const imagem = item.image?.variants.card.url
	const logo = item.store?.logo_url
	const nomeProduto = item.product?.name ?? 'Produto removido'
	const tamanhos = item.product?.sizes ?? []
	let aviso = ''

	if (item.unavailable_reason === 'product_removed') {
		aviso = 'Este produto não está mais disponível.'
	} else if (item.unavailable_reason === 'size_removed' || item.unavailable_reason === 'size_unavailable') {
		aviso = `O tamanho ${item.size} não está mais disponível.`
	}

	return (
		<li className={`item-carrinho ${item.available ? '' : 'item-indisponivel-carrinho'}`}>
			<div className='foto-item-carrinho'>
				{imagem && imagemComErro !== imagem ? (
					<img src={imagem} alt={nomeProduto} loading="lazy" decoding="async" onError={() => setImagemComErro(imagem)} />
				) : (
					<span>{imagem ? 'Imagem indisponível' : 'Sem imagem'}</span>
				)}
			</div>

			<div className='dados-item-carrinho'>
				<h2>{item.product ? <Link to={`/produto/${item.product.id}`}>{nomeProduto}</Link> : nomeProduto}</h2>
				{item.product?.description && <p className='descricao-item-carrinho'>{item.product.description}</p>}
				{aviso && <p className='aviso-item-carrinho'>{aviso}</p>}

				<div className='detalhes-item-carrinho'>
					{item.unit_price !== null && <p className='preco-item-carrinho'>{formatoPreco.format(Number(item.unit_price))}</p>}
					<label className='tamanho-item-carrinho'>
						<span>Tamanho</span>
						<select aria-label={`Tamanho de ${nomeProduto}`} value={item.size} disabled={alterando || tamanhos.length === 0} onChange={event => onAlterar(item.id, { size: event.currentTarget.value })}>
							{/* O tamanho antigo continua visível mesmo quando sai do catálogo. */}
							{!tamanhos.includes(item.size) && <option value={item.size} disabled>{item.size} (indisponível)</option>}
							{tamanhos.map(tamanho => <option key={tamanho} value={tamanho}>{tamanho}</option>)}
						</select>
					</label>
				</div>
			</div>

			<div className='acoes-item-carrinho'>
				{item.store && (
					<Link className='loja-item-carrinho' to={`/${item.store.slug}`}>
						<span className='icone-loja-carrinho' aria-hidden="true">
							{logo && logoComErro !== logo ? (
								<img src={logo} alt="" loading="lazy" decoding="async" onError={() => setLogoComErro(logo)} />
							) : item.store.name.slice(0, 1)}
						</span>
						<span>{item.store.name}</span>
					</Link>
				)}

				<div className='quantidade-item-carrinho'>
					<button type="button" aria-label={`Diminuir quantidade de ${nomeProduto}`} disabled={alterando || !item.available || item.quantity <= 1} onClick={() => onAlterar(item.id, { quantity: item.quantity - 1 })}><span className='simbolo-quantidade-carrinho' aria-hidden="true">−</span></button>
					<span className='valor-quantidade-carrinho' aria-label={`Quantidade: ${item.quantity}`}>{String(item.quantity).padStart(2, '0')}</span>
					<button type="button" aria-label={`Aumentar quantidade de ${nomeProduto}`} disabled={alterando || !item.available || item.quantity >= 2147483647} onClick={() => onAlterar(item.id, { quantity: item.quantity + 1 })}><span className='simbolo-quantidade-carrinho' aria-hidden="true">+</span></button>
					<button className='remover-item-carrinho' type="button" aria-label={`Remover ${nomeProduto} do carrinho`} disabled={alterando} onClick={() => onRemover(item.id)}><img src={trashSvg} alt="" /></button>
				</div>
			</div>
		</li>
	)
}
