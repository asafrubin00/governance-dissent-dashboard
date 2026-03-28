import { Link, NavLink, Outlet } from 'react-router-dom'

type LayoutProps = {
  generatedAt: string
}

export function Layout({ generatedAt }: LayoutProps) {
  return (
    <div className="site-shell">
      <header className="site-header">
        <div className="site-header__inner">
          <Link className="brand" to="/">
            <span className="brand__eyebrow">Governance portfolio project</span>
            <span className="brand__title">FTSE 100 Shareholder Dissent Tracker</span>
          </Link>
          <nav className="site-nav" aria-label="Primary">
            <NavLink to="/">Overview</NavLink>
            <NavLink to="/dashboard">Dashboard</NavLink>
          </nav>
        </div>
      </header>

      <main className="main-content">
        <Outlet />
      </main>

      <footer className="site-footer">
        <p>Built as a tightly scoped governance research MVP using free public AGM voting data.</p>
        <p>Dataset generated locally on {new Date(generatedAt).toLocaleDateString('en-GB')}.</p>
      </footer>
    </div>
  )
}
