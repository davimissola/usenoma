export type UserResponse = {
	id: string
	username: string
	email: string
}

export type UsuarioInicioProps = {
	usuario: UserResponse
}

export type EstiloPreferidoProps = {
	image: string
	styleName: string
}
