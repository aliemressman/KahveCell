import { NavLink, Outlet, useNavigate } from 'react-router-dom'

const links = [
  { to: '/', label: 'Ana sayfa', end: true },
  { to: '/shops', label: 'Dükkânlar' },
  { to: '/subscription', label: 'Abonelik' },
  { to: '/history', label: 'Sipariş geçmişi' },
  { to: '/login', label: 'Giriş' },
  { to: '/register', label: 'Kayıt' },
]

function AppLayout() {
  const navigate = useNavigate()

  function signOut() {
    localStorage.removeItem('kahvecell.accessToken')
    localStorage.removeItem('kahvecell.refreshToken')
    navigate('/', { replace: true })
  }

  return (
    <>
      <header className="site-header">
        <NavLink className="brand" to="/">
          KahveCell
        </NavLink>
        <nav aria-label="Ana gezinme">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {link.label}
            </NavLink>
          ))}
          <button className="link-button" type="button" onClick={signOut}>
            Çıkış
          </button>
        </nav>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </>
  )
}

export default AppLayout
