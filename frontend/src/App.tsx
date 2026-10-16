import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { auth, recuperarSessao } from './stores/auth'
import { Feed } from './pages/Feed'
import { Acesso } from './pages/Acesso'
import { Login } from './pages/Login'
import { CriarConta } from './pages/CriarConta'
import { Explorar } from './pages/Explorar'
import { Usuario } from './pages/Usuario'
import { Loja } from './pages/Loja'
import { Produto } from './pages/Produto'
import { Carrinho } from './pages/Carrinho'
import { FinalizarCompra } from './pages/FinalizarCompra'


function App() {
	const [verificandoSessao, setVerificandoSessao] = useState(!auth.sessaoVerificada)

	useEffect(() => {
		let ativo = true

		async function verificarSessao() {
			// Após F5, recupera o access pelo cookie antes de decidir quais páginas abrir.
			await recuperarSessao()

			if (ativo) {
				setVerificandoSessao(false)
			}
		}

		verificarSessao()

		return () => {
			ativo = false
		}
	}, [])

	// As telas da conta aguardam a sessão; páginas públicas já podem carregar seus dados.
	const carregandoSessao = <main className='pages-conta' />

	return (
		<Routes>
			<Route path='/' element={<Feed />} />
			<Route path='/acesso' element={verificandoSessao ? carregandoSessao : <Acesso />} />
			<Route path='/usuario' element={verificandoSessao ? carregandoSessao : <Usuario />} />
			<Route path='/login' element={verificandoSessao ? carregandoSessao : <Login />} />
			<Route path='/criar-conta' element={verificandoSessao ? carregandoSessao : <CriarConta />} />
			<Route path='/explorar' element={<Explorar />} />
			<Route path='/produto/:id' element={<Produto />} />
			<Route path='/carrinho' element={verificandoSessao ? <main className='pages-carrinho'><p className='mensagem-carrinho' role="status">Verificando sessão...</p></main> : <Carrinho />} />
			<Route path='/checkout' element={verificandoSessao ? <main className='pages-checkout'><p className='mensagem-checkout' role="status">Verificando sessão...</p></main> : <FinalizarCompra />} />
			<Route path='/:slug' element={<Loja />} />
			<Route path='*' element={<Navigate to='/' replace />} />
		</Routes>
	)
}

export default App
