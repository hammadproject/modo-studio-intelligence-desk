import { useState, type FormEvent } from 'react'
import { CheckCircle2, LoaderCircle } from 'lucide-react'
import { useChat } from '../hooks/use-chat'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'

export function ExpertRequestForm() {
  const { submitHandoff } = useChat()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recorded, setRecorded] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    if (form.get('consent') !== 'on') {
      setError('Please consent to storing your contact details before submitting.')
      return
    }
    setIsSubmitting(true)
    setError(null)
    try {
      const contactDetails = {
        name: String(form.get('name') || ''),
        email: String(form.get('email') || ''),
        service_interest: String(form.get('service') || ''),
        budget_range: String(form.get('budget') || ''),
        target_date: String(form.get('targetDate') || ''),
        consent: 'Contact details may be stored for follow-up.',
      }
      const summary = String(form.get('summary') || '')
      await submitHandoff({
        reason: `Project inquiry: ${summary}`,
        contact_details: contactDetails,
      })
      setRecorded(true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The request could not be recorded.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (recorded) {
    return (
      <div className="recorded-state" role="status">
        <CheckCircle2 aria-hidden="true" />
        <h3>Your request is in the team inbox.</h3>
        <p>
          The details are stored for later review. This does not mean a staff member has been
          A Modo Studio team member can now review it. A response time is not guaranteed.
        </p>
      </div>
    )
  }

  return (
    <form className="expert-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <div className="field-group">
          <Label htmlFor="expert-name">Name</Label>
          <Input id="expert-name" name="name" autoComplete="name" required maxLength={120} />
        </div>
        <div className="field-group">
          <Label htmlFor="expert-email">Email</Label>
          <Input id="expert-email" name="email" type="email" autoComplete="email" required maxLength={254} />
        </div>
        <div className="field-group">
          <Label htmlFor="expert-service">Service interest</Label>
          <select id="expert-service" name="service" className="form-select" required defaultValue="">
            <option value="" disabled>Select a service</option>
            <option>Brand strategy</option>
            <option>Visual identity</option>
            <option>Website design and build</option>
            <option>Product UI/UX</option>
            <option>Marketing design</option>
            <option>Ongoing design support</option>
            <option>Not sure yet</option>
          </select>
        </div>
        <div className="field-group">
          <Label htmlFor="expert-budget">Approximate budget</Label>
          <select id="expert-budget" name="budget" className="form-select" required defaultValue="">
            <option value="" disabled>Select a range</option>
            <option>Under $2,500</option>
            <option>$2,500–$5,000</option>
            <option>$5,000–$10,000</option>
            <option>$10,000–$20,000</option>
            <option>$20,000+</option>
            <option>Not determined</option>
          </select>
        </div>
      </div>
      <div className="field-group">
        <Label htmlFor="expert-date">Target date <span className="optional">Optional</span></Label>
        <Input id="expert-date" name="targetDate" type="date" />
      </div>
      <div className="field-group">
        <Label htmlFor="expert-summary">What are you working on?</Label>
        <Textarea id="expert-summary" name="summary" required maxLength={1800} placeholder="A brief project summary, goals, and anything we should know." />
      </div>
      <label className="consent-row">
        <input type="checkbox" name="consent" required />
        <span>I consent to Modo Studio storing these contact details for project follow-up.</span>
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <Button type="submit" size="lg" disabled={isSubmitting} className="w-full">
        {isSubmitting && <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />}
        {isSubmitting ? 'Recording request…' : 'Record project request'}
      </Button>
    </form>
  )
}
