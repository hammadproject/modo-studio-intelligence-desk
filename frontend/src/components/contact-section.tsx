import { ArrowUpRight } from 'lucide-react'
import { Button } from './ui/button'

export function ContactSection({ onExpert }: { onExpert: () => void }) {
  return (
    <section id="contact" className="contact-section" aria-labelledby="contact-title">
      <p className="eyebrow">Have a project in mind?</p>
      <h2 id="contact-title">Let’s make it<br /><em>clear and useful.</em></h2>
      <p>
        Modo Studio works remotely from New York with teams in the United States and internationally.
        Start with a concise project request and consented contact details.
      </p>
      <Button size="lg" onClick={onExpert}>
        Talk to an expert <ArrowUpRight aria-hidden="true" />
      </Button>
      <div className="contact-facts">
        <span><strong>Working hours</strong> Mon–Fri, 9:00 a.m.–6:00 p.m. ET</span>
        <span><strong>Meetings</strong> Remote, by confirmed appointment</span>
        <span><strong>Location</strong> New York City / No public walk-in office</span>
      </div>
    </section>
  )
}
