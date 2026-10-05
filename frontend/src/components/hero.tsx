import { ArrowUpRight } from 'lucide-react'
import { heroProjects } from '../data/content'
import { ProjectVisual } from './project-visual'
import { Wordmark } from './wordmark'

const servicePills = [
  ['Brand Strategy', '#service-branding'],
  ['Visual Identity', '#service-branding'],
  ['Web Design', '#service-websites'],
  ['Product UI/UX', '#service-digital-products'],
]

export function Hero() {
  return (
    <section className="hero-panel" aria-labelledby="hero-title">
      <h1 id="hero-title" className="hero-wordmark"><Wordmark /></h1>
      <p className="hero-subtitle">Studio <span /> New York</p>
      <p className="hero-vertical">Independent design studio</p>

      <div className="hero-projects" aria-label="Featured Modo Studio projects">
        {heroProjects.map((project, index) => (
          <ProjectVisual
            key={project.id}
            project={project}
            eager
            className={index === 1 ? 'hero-project hero-project-featured' : 'hero-project'}
          />
        ))}
      </div>

      <div className="hero-footer">
        <div className="hero-work-link">
          <span className="eyebrow">Selected work</span>
          <span className="hero-rule" />
          <a href="#selected-work">Explore our projects <ArrowUpRight aria-hidden="true" /></a>
        </div>
        <nav className="service-pills" aria-label="Explore services">
          {servicePills.map(([label, href]) => <a key={label} href={href}>{label}</a>)}
        </nav>
      </div>
    </section>
  )
}
