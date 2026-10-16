import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Header } from '../../components/Header'
import { EnderecoCheckout } from '../../components/Checkout/EnderecoCheckout'
import { auth } from '../../stores/auth'
import './finalizar-compra.css'


export function FinalizarCompra() {
	const [pagamento, setPagamento] = useState<'cartao' | 'pix'>('cartao')

	if (!auth.accessToken) {
		return <Navigate to='/acesso' replace />
	}

	return (
		<div className='pagina-checkout'>
			<Header />

			<main className='pages-checkout'>
				<div className='formulario-checkout'>
					<section className='secao-checkout' aria-labelledby="titulo-contato-checkout">
						<h1 className='titulo-checkout' id='titulo-contato-checkout'>CONTATO</h1>
						<input className='campo-checkout' id='email-checkout' name='email' type="email" placeholder="Insira seu email" aria-label="Email" autoComplete="email" />
					</section>

					<EnderecoCheckout />

					<section className='secao-checkout' aria-labelledby="titulo-envio-checkout">
						<h2 className='titulo-checkout' id='titulo-envio-checkout'>ENVIO</h2>
						<p className='mensagem-envio-checkout'>Insira o endereço de entrega para ver as formas de frete disponíveis.</p>
					</section>

					<section className='secao-checkout' aria-labelledby="titulo-pagamento-checkout">
						<h2 className='titulo-checkout' id='titulo-pagamento-checkout'>PAGAMENTO</h2>

						<fieldset className='opcoes-pagamento-checkout' aria-label="Forma de pagamento">
							<div className='pagamento-cartao-checkout'>
								<label className='opcao-pagamento-checkout'>
									<input name='paymentMethod' type="radio" value="cartao" checked={pagamento === 'cartao'} onChange={() => setPagamento('cartao')} />
									<span>Cartão de crédito</span>
								</label>

								{pagamento === 'cartao' && (
									<div className='campos-cartao-checkout'>
										<div className='campos-checkout dados-cartao-checkout'>
											<input className='campo-checkout campo-largo-checkout' id='cartao-checkout' name='cardNumber' type="text" placeholder="Número do cartão" aria-label="Número do cartão" inputMode="numeric" autoComplete="cc-number" maxLength={23} />
											<input className='campo-checkout' id='vencimento-checkout' name='expiry' type="text" placeholder="MM/AA" aria-label="Vencimento (MM/AA)" inputMode="numeric" autoComplete="cc-exp" maxLength={7} />
											<input className='campo-checkout' id='seguranca-checkout' name='securityCode' type="password" placeholder="CVV" aria-label="Código de segurança" inputMode="numeric" autoComplete="cc-csc" maxLength={4} />
											<input className='campo-checkout campo-largo-checkout' id='nome-cartao-checkout' name='cardholderName' type="text" placeholder="Nome no cartão" aria-label="Nome no cartão" autoComplete="cc-name" />
										</div>

										<select className='campo-checkout' id='parcelas-checkout' name='installments' aria-label="Parcelas" defaultValue="">
											<option value="" disabled>Selecione as parcelas</option>
											<option value="1">1x</option>
										</select>

										<label className='endereco-faturamento-checkout'>
											<input name='sameBillingAddress' type="checkbox" defaultChecked />
											<span>Usar o endereço de entrega como endereço de faturamento</span>
										</label>
									</div>
								)}
							</div>

							<label className='opcao-pagamento-checkout'>
								<input name='paymentMethod' type="radio" value="pix" checked={pagamento === 'pix'} onChange={() => setPagamento('pix')} />
								<span>Pix</span>
							</label>
						</fieldset>
					</section>
				</div>
			</main>
		</div>
	)
}
