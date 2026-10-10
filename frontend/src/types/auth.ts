export type AuthTokenResponse = {
	access_token: string
	token_type: 'bearer'
}

export type AuthErrorResponse = {
	detail: string | { msg: string }[]
}
