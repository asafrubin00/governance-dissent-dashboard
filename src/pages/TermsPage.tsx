import { Link } from 'react-router-dom'
import { LegalLine } from '../components/LegalLine'

export function TermsPage() {
  return (
    <div className="page-flow">
      <section className="terms-screen">
        <div className="terms-panel">
          <Link className="terms-panel__back" to="/radar">← Back to Radar</Link>
          <p className="terms-panel__eyebrow">Legal</p>
          <h1>Terms of Use</h1>

          <div className="terms-panel__copy">
            <p>
              Proxy Wars and all original associated content, including the site design,
              analytical frameworks, scoring methodology, governance taxonomy,
              visualisations, and written analysis, are the proprietary work of{' '}
              <a href="https://asafrubin00.github.io/asaf-rubin-website/" target="_blank" rel="noreferrer">
                Asaf Rubin
              </a>{' '}
              (© 2026). All rights reserved.
            </p>
            <p>
              Underlying company announcements, shareholder-voting data, market data,
              company names and marks, and linked third-party materials remain the
              property of their respective owners and are used here for research,
              analysis, and attribution.
            </p>
            <p>
              This website is made available for personal, non-commercial research and
              portfolio demonstration only. No original part of Proxy Wars may be
              reproduced, distributed, licensed, or used for commercial purposes without
              the express prior written permission of the author.
            </p>
            <p>
              The material is general research information, not investment, legal,
              governance, or proxy-voting advice. Coverage is selective, may not be
              complete, and should be checked against the linked primary sources before
              any decision is made.
            </p>
            <p>
              For licensing or partnership enquiries, contact:{' '}
              <a href="mailto:rubin.asaf01@gmail.com">rubin.asaf01@gmail.com</a>
            </p>
          </div>

          <footer className="terms-panel__footer"><LegalLine /></footer>
        </div>
      </section>
    </div>
  )
}
