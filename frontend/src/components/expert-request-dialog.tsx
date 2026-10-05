import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from './ui/dialog'
import { ExpertRequestForm } from './expert-request-form'

export function ExpertRequestDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="expert-dialog">
        <div className="expert-dialog-heading">
          <p className="eyebrow">Start a project / Modo Studio</p>
          <DialogTitle>Tell us what you’re building.</DialogTitle>
          <DialogDescription>
            Share only what is needed for an initial project inquiry. Please do not include passwords,
            payment information, identity documents, or confidential customer records.
          </DialogDescription>
        </div>
        <ExpertRequestForm />
      </DialogContent>
    </Dialog>
  )
}
