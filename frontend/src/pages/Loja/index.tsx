import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Header } from '../../components/Header'
import { HeroLojaCapa } from '../../components/HeroLojaCapa'
import { apiUrl } from '../../config'
import type { LojaPublicaResponse } from '../../types/lojas'
import './loja.css'


export function Loja() {
	const [loja, setLoja] = useState<LojaPublicaResponse | null>(null)
	const [erro, setErro] = useState('')
	const [tentativa, setTentativa] = useState(0)
	const { slug } = useParams()
	const navigate = useNavigate()

	useEffect(() => {
		const controller = new AbortController()

		async function buscarLoja() {
			setLoja(null)
			setErro('')

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

				{loja && <HeroLojaCapa key={loja.id} image={imagemCapa?.url} largeImage={loja.cover?.large?.url} logo={imagemLogo?.url} nomeLoja={loja.name} />}
			</main>
		</>
	)
}
