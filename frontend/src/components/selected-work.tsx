import { ArrowUpRight } from 'lucide-react'
import { projects } from '../data/content'
import { ProjectVisual } from './project-visual'

export function SelectedWork({ onExpert }: { onExpert: () => void }) {
  return (
    <section id="selected-work" className="work-section" aria-labelledby="work-title">
      <div className="work-heading">
        <div>
          <p className="eyebrow">Modo Studio / Selected work</p>
          <h2 id="work-title">Ideas made tangible.</h2>
          <p>A selection of brand and digital projects.</p>
        </div>
        <span className="work-counter">01 — 06</span>
      </div>

      <div className="project-grid">
        {projects.map((project) => (
          <figure key={project.id} className="project-card">
            <ProjectVisual project={project} className="project-card-visual" />
            <figcaption>
              <strong>{project.title}</strong>
              <span>{project.category}</span>
            </figcaption>
          </figure>
        ))}
      </div>

      <div className="work-footer">
        <span>Selected work by Modo Studio</span>
        <button type="button" onClick={onExpert}>Start a project <ArrowUpRight aria-hidden="true" /></button>
      </div>
    </section>
  )
}
