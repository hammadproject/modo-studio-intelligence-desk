import { ArrowUpRight, Menu as MenuIcon } from 'lucide-react'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog'
import { Button } from './ui/button'

const links = [
  ['Studio', '#studio'],
  ['Services', '#services'],
  ['Selected work', '#selected-work'],
  ['Contact', '#contact'],
]

export function Header({ onExpert }: { onExpert: () => void }) {
  return (
    <header className="site-header" aria-label="Primary navigation">
      <a href="#top" className="modo-mark" aria-label="Modo Studio home">
        <img src="/modo-studio-logo.png" alt="" />
      </a>

      <Dialog>
        <DialogTrigger asChild>
          <Button className="menu-pill" aria-label="Open navigation menu">
            <MenuIcon className="size-5" aria-hidden="true" />
            Menu
          </Button>
        </DialogTrigger>
        <DialogContent className="nav-dialog" showClose>
          <DialogTitle className="eyebrow">Modo Studio / Navigation</DialogTitle>
          <DialogDescription className="sr-only">
            Navigate to a section of the Modo Studio website.
          </DialogDescription>
          <nav className="nav-dialog-links" aria-label="Site sections">
            {links.map(([label, href], index) => (
              <DialogClose key={href} asChild>
                <a href={href}>
                  <span>0{index + 1}</span>
                  {label}
                  <ArrowUpRight aria-hidden="true" />
                </a>
              </DialogClose>
            ))}
          </nav>
          <div className="nav-dialog-footer">
            Independent design studio<br />New York / Working worldwide
          </div>
        </DialogContent>
      </Dialog>

      <button className="expert-link" type="button" onClick={onExpert}>
        Talk to an expert <ArrowUpRight className="size-4" aria-hidden="true" />
      </button>
    </header>
  )
}
