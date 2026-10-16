import { useEffect, useRef, useState, type SubmitEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { auth, requisicaoAutenticada } from '../../../stores/auth'
import type { DadosEndereco, EnderecoUsuarioResponse } from '../../../types/enderecos'
import './endereco-checkout.css'


const estados = [
	{ sigla: 'AC', nome: 'Acre' },
	{ sigla: 'AL', nome: 'Alagoas' },
	{ sigla: 'AP', nome: 'Amapá' },
	{ sigla: 'AM', nome: 'Amazonas' },
	{ sigla: 'BA', nome: 'Bahia' },
	{ sigla: 'CE', nome: 'Ceará' },
	{ sigla: 'DF', nome: 'Distrito Federal' },
	{ sigla: 'ES', nome: 'Espírito Santo' },
	{ sigla: 'GO', nome: 'Goiás' },
	{ sigla: 'MA', nome: 'Maranhão' },
	{ sigla: 'MT', nome: 'Mato Grosso' },
	{ sigla: 'MS', nome: 'Mato Grosso do Sul' },
	{ sigla: 'MG', nome: 'Minas Gerais' },
	{ sigla: 'PA', nome: 'Pará' },
	{ sigla: 'PB', nome: 'Paraíba' },
	{ sigla: 'PR', nome: 'Paraná' },
	{ sigla: 'PE', nome: 'Pernambuco' },
	{ sigla: 'PI', nome: 'Piauí' },
	{ sigla: 'RJ', nome: 'Rio de Janeiro' },
	{ sigla: 'RN', nome: 'Rio Grande do Norte' },
	{ sigla: 'RS', nome: 'Roraima' },
	{ sigla: 'RR', nome: 'Roraima' },
	{ sigla: 'SC', nome: 'Santa Catarina' },
	{ sigla: 'SP', nome: 'São Paulo' },
	{ sigla: 'SE', nome: 'Sergipe' },
	{ sigla: 'TO', nome: 'Tocantins' }
]


export function EnderecoCheckout() {
	const [enderecos, setEnderecos] = useState<EnderecoUsuarioResponse[] | null>(null)
	const [enderecoId, setEnderecoId] = useState('')
	const [carregando, setCarregando] = useState(true)
	const [alterando, setAlterando] = useState(false)
	const [erro, setErro] = useState('')
	const [erroAcao, setErroAcao] = useState('')
	const [mensagem, setMensagem] = useState('')
	const [tentativa, setTentativa] = useState(0)
	const [versaoFormulario, setVersaoFormulario] = useState(0)
	const requisicaoAtual = useRef<AbortController | null>(null)
	// A ref bloqueia outro envio antes mesmo de o botão receber o estado desabilitado.
	const alteracaoPendente = useRef(false)
	// Preserva o endereço salvo/alterado durante a recarga da lista, inclusive em uma nova tentativa.
	const enderecoAposAtualizacao = useRef<string | null>(null)
	const navigate = useNavigate()

	useEffect(() => {
		if (!auth.accessToken) {
			return
		}

		const controller = new AbortController()
		requisicaoAtual.current = controller

		async function buscarEnderecos() {
			setCarregando(true)
			setErro('')

			try {
				const lista: EnderecoUsuarioResponse[] = []
				let quantidade = 0

				do {
					// A API é paginada; busca as páginas sem consultar cada endereço separadamente.
					const response = await requisicaoAutenticada(`/users/me/addresses?offset=${lista.length}&limit=100`, {
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
						throw new Error('Falha ao carregar endereços.')
					}

					const data: EnderecoUsuarioResponse[] = await response.json()
					const camposTexto = ['id', 'recipient_name', 'postal_code', 'street', 'number', 'neighborhood', 'city', 'state', 'phone'] as const
					if (!Array.isArray(data) || data.some(endereco => !endereco || camposTexto.some(campo => typeof endereco[campo] !== 'string') || typeof endereco.is_default !== 'boolean' || (endereco.complement !== null && typeof endereco.complement !== 'string') || lista.some(atual => atual.id === endereco.id))) {
						throw new Error('Resposta de endereços inválida.')
					}
					lista.push(...data)
					quantidade = data.length
				} while (quantidade === 100)

				if (controller.signal.aborted) {
					return
				}

				const idPreferido = enderecoAposAtualizacao.current
				setEnderecos(lista)
				setEnderecoId(atual => {
					const id = idPreferido ?? atual
					if (lista.some(endereco => endereco.id === id)) {
						return id
					}
					return lista.find(endereco => endereco.is_default)?.id ?? lista[0]?.id ?? ''
				})
				enderecoAposAtualizacao.current = null
				// Reinicia os campos com os valores normalizados e confirmados pelo backend.
				setVersaoFormulario(versao => versao + 1)
			} catch {
				if (!controller.signal.aborted) {
					setEnderecos(null)
					setErro('Não foi possível carregar os endereços. Tente novamente.')
				}
			} finally {
				if (!controller.signal.aborted) {
					setCarregando(false)
					setAlterando(false)
					alteracaoPendente.current = false
				}
			}
		}

		buscarEnderecos()

		return () => {
			controller.abort()
		}
	}, [navigate, tentativa])

	async function alterarEndereco(method: 'POST' | 'PATCH' | 'DELETE', dados?: DadosEndereco | { is_default: true }) {
		const controller = requisicaoAtual.current
		if (carregando || alteracaoPendente.current || !controller || controller.signal.aborted) {
			return
		}

		let path = '/users/me/addresses'
		if (method !== 'POST') {
			path += `/${enderecoId}`
		}

		let confirmado = false
		let recarregar = false
		alteracaoPendente.current = true
		setAlterando(true)
		setErroAcao('')
		setMensagem('')

		try {
			const response = await requisicaoAutenticada(path, {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(dados),
				signal: controller.signal
			})

			if (controller.signal.aborted) {
				return
			}
			if (response.status === 401) {
				navigate('/acesso', { replace: true })
				return
			}
			if (response.status === 404) {
				setErroAcao('Este endereço não está mais disponível. A lista será atualizada.')
				enderecoAposAtualizacao.current = ''
				recarregar = true
				setTentativa(tentativa => tentativa + 1)
				return
			}
			if (!response.ok) {
				let mensagem = 'Não foi possível alterar o endereço. Tente novamente.'
				try {
					const data: { detail?: unknown } | null = await response.json()
					if (typeof data?.detail === 'string') {
						mensagem = data.detail
					} else if (response.status === 422) {
						mensagem = 'Confira os dados do endereço, incluindo nome, CEP, estado e celular.'
					}
				} catch {
					// Respostas sem JSON usam a mensagem padrão.
				}
				setErroAcao(mensagem)
				return
			}

			confirmado = true
			enderecoAposAtualizacao.current = ''
			let mensagem = 'Endereço excluído.'
			if (method !== 'DELETE') {
				const data: EnderecoUsuarioResponse = await response.json()
				if (!data || typeof data.id !== 'string') {
					throw new Error('Resposta de endereço inválida.')
				}
				enderecoAposAtualizacao.current = data.id
				mensagem = 'Endereço salvo.'
				if (dados && 'is_default' in dados) {
					mensagem = 'Endereço padrão atualizado.'
				}
			}

			if (controller.signal.aborted) {
				return
			}
			setMensagem(mensagem)
			// Reconsulta também após DELETE: o backend pode ter promovido outro padrão.
			recarregar = true
			setTentativa(tentativa => tentativa + 1)
		} catch {
			if (!controller.signal.aborted) {
				if (confirmado) {
					// A escrita já deu certo. Recupera a lista sem repetir a alteração.
					setMensagem('Alteração concluída. Atualizando os endereços.')
					recarregar = true
					setTentativa(tentativa => tentativa + 1)
				} else {
					setErroAcao('Não foi possível alterar o endereço. Tente novamente.')
				}
			}
		} finally {
			if (!recarregar && !controller.signal.aborted) {
				setAlterando(false)
				alteracaoPendente.current = false
			}
		}
	}

	function salvarEndereco(event: SubmitEvent<HTMLFormElement>) {
		event.preventDefault()
		const formData = new FormData(event.currentTarget)
		const dados: DadosEndereco = {
			recipient_name: `${String(formData.get('firstName') ?? '').trim()} ${String(formData.get('lastName') ?? '').trim()}`.trim(),
			postal_code: String(formData.get('postalCode') ?? '').trim(),
			street: String(formData.get('address') ?? '').trim(),
			number: String(formData.get('number') ?? '').trim(),
			complement: String(formData.get('complement') ?? '').trim() || null,
			neighborhood: String(formData.get('neighborhood') ?? '').trim(),
			city: String(formData.get('city') ?? '').trim(),
			state: String(formData.get('state') ?? ''),
			phone: String(formData.get('phone') ?? '').trim()
		}

		let method: 'POST' | 'PATCH' = 'POST'
		if (enderecoId) {
			method = 'PATCH'
		}
		alterarEndereco(method, dados)
	}

	const selecionado = enderecos?.find(endereco => endereco.id === enderecoId)
	const nome = selecionado?.recipient_name.trim().split(/\s+/) ?? []
	const ocupado = carregando || alterando

	return (
		<section className='secao-checkout' aria-labelledby="titulo-endereco-checkout" aria-busy={ocupado}>
			<h2 className='titulo-checkout' id='titulo-endereco-checkout'>ENDEREÇO</h2>

			{carregando && <p className='mensagem-endereco-checkout' role="status">Carregando endereços...</p>}
			{mensagem && <p className='mensagem-endereco-checkout' role="status">{mensagem}</p>}
			{erro && (
				<div className='mensagem-endereco-checkout erro-endereco-checkout'>
					<p role="alert">{erro}</p>
					<button className='acao-endereco-checkout' type="button" onClick={() => setTentativa(tentativa => tentativa + 1)}>Tentar novamente</button>
				</div>
			)}
			{erroAcao && <p className='mensagem-endereco-checkout erro-endereco-checkout' role="alert">{erroAcao}</p>}

			{enderecos !== null && (
				<>
					{enderecos.length > 0 ? (
						<div className='seletor-enderecos-checkout'>
							<label htmlFor='endereco-salvo-checkout'>Endereços salvos</label>
							<select className='campo-checkout' id='endereco-salvo-checkout' value={enderecoId} disabled={ocupado} onChange={event => { setEnderecoId(event.currentTarget.value); setErroAcao(''); setMensagem('') }}>
								{enderecos.map(endereco => <option key={endereco.id} value={endereco.id}>{endereco.is_default ? '(Padrão) ' : ''}{endereco.street}, {endereco.number} — {endereco.city}/{endereco.state}</option>)}
								<option value="">Adicionar novo endereço</option>
							</select>
						</div>
					) : (
						<p className='mensagem-endereco-checkout'>Você ainda não tem endereço salvo. Cadastre seu endereço de entrega.</p>
					)}

					<form className='formulario-endereco-checkout' key={`${enderecoId}-${versaoFormulario}`} onSubmit={salvarEndereco}>
						<fieldset className='edicao-endereco-checkout' disabled={ocupado}>
							<div className='campos-checkout campos-endereco-checkout'>
								<select className='campo-checkout campo-largo-checkout' id='pais-checkout' name='country' aria-label="País/região" autoComplete="shipping country" defaultValue="BR">
									<option value="BR">Brasil</option>
								</select>
								<input className='campo-checkout' id='nome-checkout' name='firstName' type="text" placeholder="Nome" aria-label="Nome" autoComplete="shipping given-name" defaultValue={nome[0] ?? ''} maxLength={120} required />
								<input className='campo-checkout' id='sobrenome-checkout' name='lastName' type="text" placeholder="Sobrenome" aria-label="Sobrenome" autoComplete="shipping family-name" defaultValue={nome.slice(1).join(' ')} maxLength={120} />
								<input className='campo-checkout campo-largo-checkout' id='cep-checkout' name='postalCode' type="text" placeholder="CEP" aria-label="CEP" inputMode="numeric" autoComplete="shipping postal-code" defaultValue={selecionado?.postal_code ?? ''} maxLength={9} pattern="[0-9]{5}-?[0-9]{3}" required />

								<div className='linha-endereco-checkout campo-largo-checkout'>
									<input className='campo-checkout' id='endereco-checkout' name='address' type="text" placeholder="Endereço" aria-label="Endereço" autoComplete="shipping address-line1" defaultValue={selecionado?.street ?? ''} maxLength={200} required />
									<input className='campo-checkout' id='numero-checkout' name='number' type="text" placeholder="Número" aria-label="Número" defaultValue={selecionado?.number ?? ''} maxLength={20} required />
								</div>

								<input className='campo-checkout' id='complemento-checkout' name='complement' type="text" placeholder="Complemento" aria-label="Complemento" autoComplete="shipping address-line2" defaultValue={selecionado?.complement ?? ''} maxLength={120} />
								<input className='campo-checkout' id='bairro-checkout' name='neighborhood' type="text" placeholder="Bairro" aria-label="Bairro" autoComplete="shipping address-level3" defaultValue={selecionado?.neighborhood ?? ''} maxLength={120} required />
								<input className='campo-checkout' id='cidade-checkout' name='city' type="text" placeholder="Cidade" aria-label="Cidade" autoComplete="shipping address-level2" defaultValue={selecionado?.city ?? ''} maxLength={120} required />
								<select className='campo-checkout' id='estado-checkout' name='state' aria-label="Estado" autoComplete="shipping address-level1" defaultValue={selecionado?.state ?? ''} required>
									<option value="" disabled>Estado</option>
									{estados.map(estado => <option key={estado.sigla} value={estado.sigla}>{estado.nome}</option>)}
								</select>
								<input className='campo-checkout campo-largo-checkout' id='celular-checkout' name='phone' type="tel" placeholder="Celular" aria-label="Celular" autoComplete="shipping tel" defaultValue={selecionado?.phone ?? ''} maxLength={24} required />
							</div>

							<div className='acoes-endereco-checkout'>
								<button className='salvar-endereco-checkout' type="submit">{alterando ? 'Aguarde...' : selecionado ? 'Salvar alterações' : 'Salvar endereço'}</button>
								{selecionado && !selecionado.is_default && <button className='acao-endereco-checkout' type="button" onClick={() => alterarEndereco('PATCH', { is_default: true })}>Definir como padrão</button>}
								{selecionado && <button className='acao-endereco-checkout' type="button" onClick={() => alterarEndereco('DELETE')}>Excluir endereço</button>}
							</div>
						</fieldset>
					</form>
				</>
			)}
		</section>
	)
}
