import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Header } from '../../components/Header'
import { GaleriaProduto } from '../../components/Produto/GaleriaProduto'
import { apiUrl } from '../../config'
import { recuperarSessao, requisicaoAutenticada } from '../../stores/auth'
import type { ProdutoResponse } from '../../types/produtos'
import './produto.css'


const formatoPreco = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })


export function Produto() {
	const [produto, setProduto] = useState<ProdutoResponse | null>(null)
	const [erro, setErro] = useState('')
	const [naoEncontrado, setNaoEncontrado] = useState(false)
	const [tentativa, setTentativa] = useState(0)
	const [tamanhoSelecionado, setTamanhoSelecionado] = useState('')
	const [erroTamanho, setErroTamanho] = useState(false)
	const [erroCarrinho, setErroCarrinho] = useState('')
	const [enviando, setEnviando] = useState(false)
	const envioCarrinho = useRef<AbortController | null>(null)
	const { id } = useParams()
	const navigate = useNavigate()

	useEffect(() => {
		const controller = new AbortController()

		async function buscarProduto() {
			setProduto(null)
			setErro('')
			setNaoEncontrado(false)
			setTamanhoSelecionado('')
			setErroTamanho(false)
			setErroCarrinho('')
			setEnviando(false)

			try {
				// Detalhe público: não depende da sessão nem envia token de autenticação.
				const response = await fetch(`${apiUrl}/products/${encodeURIComponent(id ?? '')}`, {
					signal: controller.signal
				})

				if (controller.signal.aborted) {
					return
				}

				if (response.status === 404 || response.status === 422) {
					setNaoEncontrado(true)
					return
				}

				if (!response.ok) {
					throw new Error('Falha ao carregar o produto.')
				}

				const data: ProdutoResponse = await response.json()

				if (!data || !Array.isArray(data.images) || !Array.isArray(data.sizes)) {
					throw new Error('Resposta de produto inválida.')
				}

				if (!controller.signal.aborted) {
					setProduto(data)
				}
			} catch {
				if (!controller.signal.aborted) {
					setErro('Não foi possível carregar o produto. Tente novamente.')
				}
			}
		}

		buscarProduto()

		return () => {
			controller.abort()
			envioCarrinho.current?.abort()
			envioCarrinho.current = null
		}
	}, [id, tentativa])

	async function adicionarAoCarrinho() {
		if (!produto || envioCarrinho.current) {
			return
		}

		if (!tamanhoSelecionado) {
			setErroTamanho(true)
			return
		}

		// A referência bloqueia cliques repetidos antes mesmo de o botão atualizar na tela.
		const controller = new AbortController()
		envioCarrinho.current = controller
		setErroCarrinho('')
		setEnviando(true)

		try {
			// Aguarda também o refresh inicial se o usuário acabou de atualizar a página.
			const sessaoRecuperada = await recuperarSessao()
			if (controller.signal.aborted) {
				return
			}
			if (!sessaoRecuperada) {
				navigate('/acesso')
				return
			}

			const response = await requisicaoAutenticada('/cart/items', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ product_id: produto.id, size: tamanhoSelecionado, quantity: 1 }),
				signal: controller.signal
			})

			if (controller.signal.aborted) {
				return
			}
			if (response.status === 401) {
				navigate('/acesso')
				return
			}
			if (!response.ok) {
				const data: { detail?: unknown } = await response.json()
				if (!controller.signal.aborted) {
					if (typeof data?.detail === 'string') {
						setErroCarrinho(data.detail)
					} else {
						setErroCarrinho('Não foi possível adicionar o produto ao carrinho. Tente novamente.')
					}
				}
				return
			}

			navigate('/carrinho')
		} catch {
			if (!controller.signal.aborted) {
				setErroCarrinho('Não foi possível adicionar o produto ao carrinho. Tente novamente.')
			}
		} finally {
			if (envioCarrinho.current === controller) {
				envioCarrinho.current = null
				if (!controller.signal.aborted) {
					setEnviando(false)
				}
			}
		}
	}

	return (
		<div className='pagina-produto'>
			<Header />

			<main className='pages-produto'>
				{!produto && !erro && !naoEncontrado && <p className='mensagem-produto' role="status">Carregando produto...</p>}

				{erro && (
					<div className='mensagem-produto'>
						<p role="alert">{erro}</p>
						<button type="button" onClick={() => setTentativa(tentativa => tentativa + 1)}>Tentar novamente</button>
					</div>
				)}

				{naoEncontrado && (
					<div className='mensagem-produto'>
						<h1>Produto não encontrado.</h1>
						<Link to='/'>Voltar para o início</Link>
					</div>
				)}

				{produto && (
					<>
						<GaleriaProduto key={produto.id} imagens={produto.images} nomeProduto={produto.name} />

						<div className='conteudo-produto'>
							<h1>{produto.name}</h1>
							{produto.description && <p className='descricao-produto'>{produto.description}</p>}
							<p className='preco-produto'>{formatoPreco.format(Number(produto.price))}</p>

							{produto.sizes.length > 0 ? (
								<>
									<div className={`tamanhos-produto ${erroTamanho ? 'tamanhos-produto-erro' : ''}`} role="group" aria-label="Escolher tamanho" aria-invalid={erroTamanho} aria-describedby='validacao-tamanho-produto'>
										{produto.sizes.map(tamanho => (
											<label className='tamanho-produto' key={tamanho.size}>
												<input type="radio" name="tamanho-produto" value={tamanho.size} checked={tamanhoSelecionado === tamanho.size} disabled={enviando} onChange={() => { setTamanhoSelecionado(tamanho.size); setErroTamanho(false); setErroCarrinho('') }} />
												<span>{tamanho.size.toUpperCase()}</span>
											</label>
										))}
									</div>

									{/* A área permanece no layout para o botão não deslocar ao validar. */}
									<p id='validacao-tamanho-produto' className='validacao-tamanho-produto' role={erroTamanho ? 'alert' : undefined}>{erroTamanho ? 'Selecione um tamanho' : ''}</p>
								</>
							) : (
								<p className='tamanhos-ausentes-produto'>Nenhum tamanho disponível.</p>
							)}

							<button className='botao-carrinho-produto' type="button" disabled={enviando || produto.sizes.length === 0} onClick={adicionarAoCarrinho}>{enviando ? 'Adicionando...' : 'Carrinho'}</button>
							{erroCarrinho && <p className='erro-carrinho-produto' role="alert">{erroCarrinho}</p>}
						</div>
					</>
				)}
			</main>
		</div>
	)
}
