import { Link } from 'react-router-dom'

export function LegalLine() {
  return (
    <span className="legal-line">
      © 2026{' '}
      <a href="https://asafrubin00.github.io/asaf-rubin-website/" target="_blank" rel="noreferrer">
        Asaf Rubin
      </a>
      . All rights reserved. <i>·</i> <Link to="/terms">Terms of Use</Link>
    </span>
  )
}
