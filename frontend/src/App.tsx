import { lazy, Suspense, useState } from 'react'
import { ChatWidget } from './components/chat/chat-widget'
import { ContactSection } from './components/contact-section'
import { ExpertRequestDialog } from './components/expert-request-dialog'
import { Footer } from './components/footer'
import { Header } from './components/header'
import { Hero } from './components/hero'
import { SelectedWork } from './components/selected-work'
import { ServicesSection } from './components/services-section'
import { SiteEffects } from './components/site-effects'
import { StudioIntro } from './components/studio-intro'
import { ChatProvider } from './hooks/use-chat'

const AdminDashboard = lazy(() => import('./components/admin/admin-dashboard').then(
  (module) => ({ default: module.AdminDashboard }),
))

function App() {
  const [expertOpen, setExpertOpen] = useState(false)
  if (window.location.pathname.startsWith('/admin')) return (
    <Suspense fallback={<div className="admin-loading">Opening operator inbox…</div>}>
      <AdminDashboard />
    </Suspense>
  )

  return (
    <ChatProvider>
      <SiteEffects />
      <div id="top" className="site-shell">
        <Header onExpert={() => setExpertOpen(true)} />
        <main>
          <Hero />
          <StudioIntro />
          <SelectedWork onExpert={() => setExpertOpen(true)} />
          <ServicesSection onExpert={() => setExpertOpen(true)} />
          <ContactSection onExpert={() => setExpertOpen(true)} />
        </main>
        <Footer />
        <ExpertRequestDialog open={expertOpen} onOpenChange={setExpertOpen} />
        <ChatWidget onExpert={() => setExpertOpen(true)} />
      </div>
    </ChatProvider>
  )
}

export default App
