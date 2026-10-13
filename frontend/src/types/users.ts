export type UserStoreResponse = {
	id: string
	name: string
	slug: string
}

export type UserResponse = {
	id: string
	username: string
	email: string
	stores: UserStoreResponse[]
}

export type UsuarioInicioProps = {
	usuario: UserResponse
}

export type EstiloPreferidoProps = {
	image: string
	styleName: string
}
