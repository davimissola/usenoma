import { Route, Routes } from 'react-router-dom'
import { Feed } from './pages/Feed'
import { Acesso } from './pages/Acesso'
import { Login } from './pages/Login'
import { CriarConta } from './pages/CriarConta'


function App() {

	return (
		<Routes>
			<Route path='/' element={<Feed />} />
			<Route path='/acesso' element={<Acesso />} />
			<Route path='/login' element={<Login />} />
			<Route path='/criar-conta' element={<CriarConta />} />
		</Routes>
	)
}

export default App
