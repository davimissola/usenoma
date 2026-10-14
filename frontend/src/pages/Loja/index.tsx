import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Header } from '../../components/Header'
import { HeroLojaCapa } from '../../components/Loja/HeroLojaCapa'
import { FaixaProdutosLoja } from '../../components/Loja/FaixaProdutosLoja'
import { ImagemEditorialLoja } from '../../components/Loja/ImagemEditorialLoja'
import fotoTeste02 from '../../assets/svg/illustrations/fotoTeste02.png'
import fotoTeste04 from '../../assets/svg/illustrations/fotoTeste04.png'
import fotoTeste06 from '../../assets/svg/illustrations/fotoTeste01.png'
import { apiUrl } from '../../config'
import type { LojaPublicaResponse } from '../../types/lojas'
import type { ProdutoResponse } from '../../types/produtos'
import './loja.css'


export function Loja() {
	const [loja, setLoja] = useState<LojaPublicaResponse | null>(null)
	const [erro, setErro] = useState('')
	const [tentativa, setTentativa] = useState(0)
	const [produtos, setProdutos] = useState<ProdutoResponse[] | null>(null)
	const [erroProdutos, setErroProdutos] = useState('')
	const { slug } = useParams()
	const navigate = useNavigate()

	useEffect(() => {
		const controller = new AbortController()

		async function buscarProdutos(storeId: string) {
			try {
				const response = await fetch(`${apiUrl}/stores/${storeId}/products`, {
					signal: controller.signal
				})

				if (controller.signal.aborted) {
					return
				}

				if (!response.ok) {
					throw new Error('Falha ao carregar produtos.')
				}

				const data: ProdutoResponse[] = await response.json()

				if (!Array.isArray(data)) {
					throw new Error('Resposta de produtos inválida.')
				}

				if (!controller.signal.aborted) {
					setProdutos(data)
				}
			} catch {
				if (!controller.signal.aborted) {
					setErroProdutos('Não foi possível carregar os produtos. Tente novamente.')
				}
			}
		}

		async function buscarLoja() {
			setLoja(null)
			setErro('')
			setProdutos(null)
			setErroProdutos('')

			try {
				// Leitura pública: não envia Bearer nem depende da recuperação da sessão.
				const response = await fetch(`${apiUrl}/stores/slug/${encodeURIComponent(slug ?? '')}`, {
					signal: controller.signal
				})

				if (controller.signal.aborted) {
					return
				}

				if (response.status === 404) {
					navigate('/', { replace: true })
					return
				}

				if (!response.ok) {
					throw new Error('Falha ao carregar a loja.')
				}

				const data: LojaPublicaResponse = await response.json()

				if (!controller.signal.aborted) {
					setLoja(data)
					await buscarProdutos(data.id)
				}
			} catch {
				if (!controller.signal.aborted) {
					setErro('Não foi possível carregar a loja. Tente novamente.')
				}
			}
		}

		buscarLoja()

		return () => {
			// Cancela a consulta anterior ao trocar o slug ou sair da página.
			controller.abort()
		}
	}, [slug, navigate, tentativa])

	// Referências antigas podem ter uma única variante; usa a que estiver disponível.
	const imagemCapa = loja?.cover?.medium ?? loja?.cover?.large ?? loja?.cover?.small
	const imagemLogo = loja?.logo?.medium ?? loja?.logo?.small ?? loja?.logo?.large

	return (
		<>
			<Header />

			<main className='pages-loja'>
				{!loja && !erro && <p className='mensagem-loja'>Carregando loja...</p>}

				{erro && (
					<div className='mensagem-loja'>
						<p role="alert">{erro}</p>
						<button type="button" onClick={() => setTentativa(tentativa => tentativa + 1)}>Tentar novamente</button>
					</div>
				)}

				{loja && (
					<>
						<HeroLojaCapa key={loja.id} image={imagemCapa?.url} largeImage={loja.cover?.large?.url} logo={imagemLogo?.url} nomeLoja={loja.name} />
						{produtos === null && !erroProdutos && <p className='mensagem-produtos-loja'>Carregando produtos...</p>}
						{erroProdutos && (
							<div className='mensagem-loja mensagem-produtos-loja'>
								<p role="alert">{erroProdutos}</p>
								<button type="button" onClick={() => setTentativa(tentativa => tentativa + 1)}>Tentar novamente</button>
							</div>
						)}
						{produtos && <FaixaProdutosLoja titulo='Destaques da semana' produtos={produtos} />}
						<ImagemEditorialLoja imagens={[fotoTeste02, fotoTeste04, fotoTeste06]} />
					</>
				)}
			</main>
		</>
	)
}
