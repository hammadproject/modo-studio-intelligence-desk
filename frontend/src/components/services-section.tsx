import { ArrowDownRight } from 'lucide-react'
import { services } from '../data/content'

export function ServicesSection({ onExpert }: { onExpert: () => void }) {
  return (
    <section id="services" className="services-section" aria-labelledby="services-title">
      <div className="services-heading">
        <p className="eyebrow">What we do / 01 — 03</p>
        <h2 id="services-title">Built for clarity.<br /><em>Designed to last.</em></h2>
      </div>
      <div className="services-list">
        {services.map((service) => (
          <article key={service.id} id={`service-${service.id}`} className="service-row">
            <span className="service-index">{service.index}</span>
            <div>
              <h3>{service.title}</h3>
              <p>{service.summary}</p>
            </div>
            <div className="service-detail">
              <strong>{service.startingAt}</strong>
              <p>{service.detail}</p>
            </div>
            <ArrowDownRight aria-hidden="true" />
          </article>
        ))}
      </div>
      <button type="button" className="text-link" onClick={onExpert}>
        Discuss your project <ArrowDownRight aria-hidden="true" />
      </button>
    </section>
  )
}
