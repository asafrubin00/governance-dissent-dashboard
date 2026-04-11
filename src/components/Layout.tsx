import { Link, NavLink, Outlet } from 'react-router-dom'

type LayoutProps = {
  generatedAt: string
}

export function Layout({ generatedAt }: LayoutProps) {
  return (
    <div className="site-shell">
      <header className="site-header">
        <div className="site-header__inner">
          <Link className="brand brand--ghost" to="/" aria-label="Overview">
            <span className="brand__title">Proxy Wars</span>
          </Link>
          <nav className="site-nav" aria-label="Primary">
            <NavLink to="/dashboard">Dashboard</NavLink>
            <NavLink to="/">Overview</NavLink>
          </nav>
        </div>
      </header>

      <main className="main-content">
        <Outlet context={{ generatedAt }} />
      </main>
    </div>
  )
}
