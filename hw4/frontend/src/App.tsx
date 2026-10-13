import { Link, Route, Routes, useLocation } from 'react-router-dom'
import BrandMark from './components/BrandMark'
import { useChatSearch } from './chatSearch'
import NavBar from './components/NavBar'
import ChatWidget from './components/ChatWidget'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import CreateAccount from './pages/CreateAccount'
import NotFound from './pages/NotFound'

export default function App() {
  const location = useLocation()
  const { clearResults } = useChatSearch()
  return (
    <>
      <NavBar />
      {/* Keyed by path so each page fades in when you navigate. */}
      <main className="page page-enter" key={location.pathname}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <BrandMark size={40} />
            <div>
              <strong>Campus Customs</strong>
              <p>Yale apparel from 57 Broadway, New Haven, CT.</p>
            </div>
          </div>
          {/* Footer links open the catalogue, so they clear any chat results. */}
          <nav className="footer-links" aria-label="Footer" onClick={clearResults}>
            <Link to="/products">Shop all</Link>
            <Link to="/products?cat=Hoodies">Hoodies</Link>
            <Link to="/products?cat=Crewnecks%20%26%20sweatshirts">Crewnecks</Link>
            <Link to="/products?cat=T-shirts">T-shirts</Link>
            <Link to="/about">About us</Link>
          </nav>
          <p className="footer-tag">Boola boola.</p>
        </div>
      </footer>
      <ChatWidget />
    </>
  )
}
