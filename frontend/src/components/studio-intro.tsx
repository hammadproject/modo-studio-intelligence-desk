import { ArrowUpRight, Circle, Diamond, Square } from 'lucide-react'
import { services } from '../data/content'

const marks = [Circle, Square, Diamond]

export function StudioIntro() {
  return (
    <section id="studio" className="studio-section" aria-labelledby="studio-title">
      <p className="section-kicker"><span /> The studio <span /></p>
      <h2 id="studio-title">
        Design that moves<br />
        <em>your business forward.</em>
      </h2>
      <p className="studio-copy">
        An independent New York studio shaping brands and digital experiences with clarity and purpose.
      </p>
      <div className="service-tiles">
        {services.map((service, index) => {
          const Mark = marks[index]
          return (
            <a key={service.id} href={`#service-${service.id}`} className="service-tile">
              <span className="service-index">{service.index}</span>
              <span className="service-tile-main">
                <Mark aria-hidden="true" />
                <strong>{service.title}</strong>
              </span>
              <ArrowUpRight aria-hidden="true" />
            </a>
          )
        })}
      </div>
    </section>
  )
}
