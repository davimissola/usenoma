import { Navigate, Route, Routes } from 'react-router-dom'
import { Feed } from './pages/Feed'
import { Acesso } from './pages/Acesso'
import { Login } from './pages/Login'
import { CriarConta } from './pages/CriarConta'
import { Explorar } from './pages/Explorar'
import { Usuario } from './pages/Usuario'


function App() {

	return (
		<Routes>
			<Route path='/' element={<Feed />} />
			<Route path='/acesso' element={<Acesso />} />
			<Route path='/usuario' element={<Usuario />} />
			<Route path='/login' element={<Login />} />
			<Route path='/criar-conta' element={<CriarConta />} />
			<Route path='/explorar' element={<Explorar />} />
			<Route path='*' element={<Navigate to='/' replace />} />
		</Routes>
	)
}

export default App
