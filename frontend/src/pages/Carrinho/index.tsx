import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Header } from '../../components/Header'
import { ItemCarrinho } from '../../components/Carrinho/ItemCarrinho'
import { auth, requisicaoAutenticada } from '../../stores/auth'
import type { AlteracaoItemCarrinho, CarrinhoResponse } from '../../types/carrinho'
import './carrinho.css'


const formatoNumero = new Intl.NumberFormat('pt-BR')


export function Carrinho() {
	const [carrinho, setCarrinho] = useState<CarrinhoResponse | null>(null)
	const [erro, setErro] = useState('')
	const [erroAcao, setErroAcao] = useState('')
	const [carregando, setCarregando] = useState(true)
	const [alterando, setAlterando] = useState(false)
	const [tentativa, setTentativa] = useState(0)
	const requisicaoAtual = useRef<AbortController | null>(null)
	const navigate = useNavigate()

	useEffect(() => {
		if (!auth.accessToken) {
			return
		}

		const controller = new AbortController()
		requisicaoAtual.current = controller

		async function buscarCarrinho() {
			setErro('')
			setCarregando(true)

			try {
				// O helper já trata JWT expirado com um refresh e uma única repetição.
				const response = await requisicaoAutenticada('/cart', {
					signal: controller.signal
				})

				if (controller.signal.aborted) {
					return
				}

				if (response.status === 401) {
					navigate('/acesso', { replace: true })
					return
				}

				if (!response.ok) {
					throw new Error('Falha ao carregar o carrinho.')
				}

				const data: CarrinhoResponse = await response.json()
				if (!data || !Array.isArray(data.items)) {
					throw new Error('Resposta de carrinho inválida.')
				}

				if (!controller.signal.aborted) {
					setCarrinho(data)
				}
			} catch {
				if (!controller.signal.aborted) {
					setErro('Não foi possível carregar o carrinho. Tente novamente.')
				}
			} finally {
				if (!controller.signal.aborted) {
					setCarregando(false)
				}
			}
		}

		buscarCarrinho()

		return () => {
			// Também cancela alterações em andamento ao sair da página.
			controller.abort()
		}
	}, [navigate, tentativa])

	async function conferirResposta(response: Response): Promise<boolean> {
		if (response.status === 401) {
			navigate('/acesso', { replace: true })
			return false
		}

		if (!response.ok) {
			let mensagem = 'Não foi possível atualizar o carrinho. Tente novamente.'

			try {
				const data = await response.json()
				if (typeof data.detail === 'string') {
					mensagem = data.detail
				}
			} catch {
				// Respostas sem JSON usam a mensagem padrão, sem expor conteúdo interno.
			}

			setErroAcao(mensagem)
			return false
		}

		return true
	}

	async function atualizarItem(itemId: string, dados: AlteracaoItemCarrinho) {
		const controller = requisicaoAtual.current
		if (alterando || carregando || !controller || controller.signal.aborted) {
			return
		}

		let atualizarDisponibilidade = false
		setAlterando(true)
		setErroAcao('')

		try {
			const response = await requisicaoAutenticada(`/cart/items/${itemId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(dados),
				signal: controller.signal
			})

			if (controller.signal.aborted) {
				return
			}

			if (response.status === 404 || response.status === 409) {
				// O catálogo pode ter mudado; recarrega para mostrar a disponibilidade real.
				atualizarDisponibilidade = true
			}

			if (await conferirResposta(response)) {
				const data: CarrinhoResponse = await response.json()
				if (!data || !Array.isArray(data.items)) {
					throw new Error('Não foi possível atualizar o carrinho. Tente novamente.')
				}
				if (!controller.signal.aborted) {
					// O PATCH retorna o carrinho completo, inclusive quando une dois tamanhos.
					setCarrinho(data)
				}
			}
		} catch {
			if (!controller.signal.aborted) {
				setErroAcao('Não foi possível atualizar o carrinho. Tente novamente.')
			}
		} finally {
			if (!controller.signal.aborted) {
				setAlterando(false)
				if (atualizarDisponibilidade) {
					setTentativa(tentativa => tentativa + 1)
				}
			}
		}
	}

	async function removerItens(itemId?: string) {
		const controller = requisicaoAtual.current
		if (alterando || carregando || !controller || controller.signal.aborted) {
			return
		}

		let path = '/cart'
		if (itemId) {
			path = `/cart/items/${itemId}`
		}

		let removido = false
		let atualizarDisponibilidade = false
		setAlterando(true)
		setErroAcao('')

		try {
			const response = await requisicaoAutenticada(path, {
				method: 'DELETE',
				signal: controller.signal
			})

			if (response.status === 404) {
				atualizarDisponibilidade = true
			}

			if (controller.signal.aborted || !await conferirResposta(response)) {
				return
			}

			removido = true
			// Só retira itens da tela depois da confirmação do backend.
			setCarrinho(carrinho => {
				if (!carrinho) {
					return null
				}
				return { ...carrinho, items: carrinho.items.filter(item => itemId && item.id !== itemId) }
			})

			// DELETE retorna 204; o GET seguinte atualiza também os demais itens.
			const responseCarrinho = await requisicaoAutenticada('/cart', {
				signal: controller.signal
			})
			if (controller.signal.aborted || !await conferirResposta(responseCarrinho)) {
				if (!controller.signal.aborted && responseCarrinho.status !== 401) {
					setErroAcao('Remoção concluída, mas não foi possível atualizar o carrinho. Tente novamente.')
				}
				return
			}
			const data: CarrinhoResponse = await responseCarrinho.json()
			if (!data || !Array.isArray(data.items)) {
				throw new Error('Resposta de carrinho inválida.')
			}
			if (!controller.signal.aborted) {
				setCarrinho(data)
			}
		} catch {
			if (!controller.signal.aborted) {
				if (removido) {
					setErroAcao('Remoção concluída, mas não foi possível atualizar o carrinho. Tente novamente.')
				} else {
					setErroAcao('Não foi possível remover os itens. Tente novamente.')
				}
			}
		} finally {
			if (!controller.signal.aborted) {
				setAlterando(false)
				if (atualizarDisponibilidade) {
					setTentativa(tentativa => tentativa + 1)
				}
			}
		}
	}

	if (!auth.accessToken) {
		return <Navigate to='/acesso' replace />
	}

	const quantidadeItens = carrinho?.items.reduce((total, item) => total + item.quantity, 0) ?? 0
	const subtotalCentavos = carrinho?.items.reduce((total, item) => {
		// Produtos removidos permanecem na lista, mas já não têm um preço atual.
		if (item.unit_price === null) {
			return total
		}

		// A API envia duas casas decimais. Somar centavos inteiros evita erros de arredondamento.
		const [reais, centavos] = item.unit_price.split('.')
		const precoCentavos = BigInt(reais) * 100n + BigInt(centavos)
		return total + precoCentavos * BigInt(item.quantity)
	}, 0n) ?? 0n
	const subtotalFormatado = `R$ ${formatoNumero.format(subtotalCentavos / 100n)},${String(subtotalCentavos % 100n).padStart(2, '0')}`

	return (
		<div className='pagina-carrinho'>
			<Header />

			<main className={`pages-carrinho ${carrinho && carrinho.items.length > 0 ? 'carrinho-com-resumo' : ''}`}>
				<div className='conteudo-carrinho'>
					<h1 className='titulo-carrinho'>CARRINHO{carrinho && <sup>{String(quantidadeItens).padStart(2, '0')}</sup>}</h1>

					{!carrinho && !erro && <p className='mensagem-carrinho' role="status">Carregando carrinho...</p>}

					{(erro || erroAcao) && (
						<div className='mensagem-carrinho'>
							<p role="alert">{erro || erroAcao}</p>
							<button type="button" disabled={alterando || carregando} onClick={() => { setErroAcao(''); setTentativa(tentativa => tentativa + 1) }}>Tentar novamente</button>
						</div>
					)}

					{carrinho && carrinho.items.length === 0 && (
						<div className='mensagem-carrinho carrinho-vazio'>
							<p>Seu carrinho está vazio.</p>
							<Link to='/'>Continuar explorando</Link>
						</div>
					)}

					{carrinho && carrinho.items.length > 0 && (
						<>
							<ul className='lista-carrinho' aria-busy={alterando || carregando}>
								{carrinho.items.map(item => <ItemCarrinho key={item.id} item={item} alterando={alterando || carregando} onAlterar={atualizarItem} onRemover={removerItens} />)}
							</ul>
							<button className='limpar-carrinho' type="button" disabled={alterando || carregando} onClick={() => removerItens()}>Limpar carrinho</button>
						</>
					)}
					{(alterando || (carregando && carrinho)) && <p className='atualizando-carrinho' role="status">Atualizando carrinho...</p>}
				</div>

				{carrinho && carrinho.items.length > 0 && (
					<footer className='resumo-carrinho' aria-label="Resumo do carrinho">
						<div className='conteudo-resumo-carrinho'>
							<div className='linha-subtotal-carrinho'>
								<span>SUBTOTAL</span>
								<strong className='valor-subtotal-carrinho' aria-live="polite">{subtotalFormatado}</strong>
							</div>
							<p className='frete-resumo-carrinho'>Frete calculado no final da compra.</p>
							<button className='finalizar-compra-carrinho' type="button" disabled>Finalizar Compra</button>
						</div>
					</footer>
				)}
			</main>
		</div>
	)
}
