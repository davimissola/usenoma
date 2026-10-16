export type DadosEndereco = {
	recipient_name: string
	postal_code: string
	street: string
	number: string
	complement: string | null
	neighborhood: string
	city: string
	state: string
	phone: string
}

export type EnderecoUsuarioResponse = DadosEndereco & {
	id: string
	is_default: boolean
}
