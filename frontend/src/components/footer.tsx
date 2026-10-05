import { ArrowUp } from 'lucide-react'
import { Wordmark } from './wordmark'

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-wordmark"><Wordmark /></div>
      <div className="footer-grid">
        <div>
          <span className="footer-logo" aria-hidden="true">
            <img src="/modo-studio-logo.png" alt="" />
          </span>
          <strong>Modo Studio</strong>
          <span>New York / Working worldwide</span>
        </div>
        <nav aria-label="Footer navigation">
          <a href="#studio">Studio</a>
          <a href="#services">Services</a>
          <a href="#selected-work">Selected work</a>
          <a href="#contact">Contact</a>
        </nav>
        <a href="#top" className="back-to-top" aria-label="Back to top"><ArrowUp /></a>
      </div>
    </footer>
  )
}
