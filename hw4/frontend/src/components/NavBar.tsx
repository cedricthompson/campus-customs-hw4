import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import BrandMark from './BrandMark'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  return (
    <header className="nav">
      <div className="nav-inner">
        <Link to="/" className="brand" aria-label="Campus Customs home">
          <BrandMark size={34} />
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-tag">Yale apparel · New Haven</span>
          </span>
        </Link>
        <nav className="nav-links">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>
              {l.label}
            </NavLink>
          ))}
          <span className="nav-spacer" />
          {user ? (
            <>
              <span className="nav-user">Hi, {user.first_name || user.name}</span>
              <button className="nav-logout" onClick={handleLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/create-account" className="nav-cta">
                Create account
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
