import { useEffect, useRef } from 'react'

const interactiveSelector = 'a, button, input, textarea, select, [role="button"]'

export function SiteEffects() {
  const cursorRef = useRef<HTMLDivElement>(null)
  const trailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const finePointer = window.matchMedia?.('(hover: hover) and (pointer: fine)')
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!finePointer?.matches || reducedMotion?.matches) return

    const root = document.documentElement
    const cursor = cursorRef.current
    const trail = trailRef.current
    if (!cursor || !trail) return

    root.classList.add('has-custom-cursor')
    let targetX = -100
    let targetY = -100
    let cursorX = targetX
    let cursorY = targetY
    let trailX = targetX
    let trailY = targetY
    let frame = 0

    const render = () => {
      cursorX += (targetX - cursorX) * 0.34
      cursorY += (targetY - cursorY) * 0.34
      trailX += (cursorX - trailX) * 0.16
      trailY += (cursorY - trailY) * 0.16
      cursor.style.transform = `translate3d(${cursorX}px, ${cursorY}px, 0) translate(-50%, -50%)`
      trail.style.transform = `translate3d(${trailX}px, ${trailY}px, 0) translate(-50%, -50%)`
      frame = window.requestAnimationFrame(render)
    }

    const show = () => {
      cursor.classList.add('is-visible')
      trail.classList.add('is-visible')
    }
    const hide = () => {
      cursor.classList.remove('is-visible')
      trail.classList.remove('is-visible')
    }
    const move = (event: MouseEvent) => {
      targetX = event.clientX
      targetY = event.clientY
      show()
      const target = event.target instanceof Element ? event.target : null
      cursor.classList.toggle('is-active', Boolean(target?.closest(interactiveSelector)))
    }
    const press = () => cursor.classList.add('is-pressed')
    const release = () => cursor.classList.remove('is-pressed')

    frame = window.requestAnimationFrame(render)
    window.addEventListener('mousemove', move, { passive: true })
    document.addEventListener('mouseleave', hide)
    window.addEventListener('blur', hide)
    window.addEventListener('mousedown', press)
    window.addEventListener('mouseup', release)

    return () => {
      root.classList.remove('has-custom-cursor')
      window.cancelAnimationFrame(frame)
      window.removeEventListener('mousemove', move)
      document.removeEventListener('mouseleave', hide)
      window.removeEventListener('blur', hide)
      window.removeEventListener('mousedown', press)
      window.removeEventListener('mouseup', release)
    }
  }, [])

  useEffect(() => {
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    const elements = Array.from(document.querySelectorAll<HTMLElement>([
      '.studio-section .section-kicker',
      '.studio-section h2',
      '.studio-copy',
      '.service-tile',
      '.work-heading',
      '.project-card',
      '.services-heading',
      '.service-row',
      '.contact-section > .eyebrow',
      '.contact-section h2',
      '.contact-section > p:not(.eyebrow)',
      '.contact-section > button',
    ].join(',')))

    if (reducedMotion?.matches || !('IntersectionObserver' in window)) {
      elements.forEach((element) => element.classList.add('is-visible'))
      return
    }

    elements.forEach((element, index) => {
      element.classList.add('reveal-ready')
      element.style.setProperty('--reveal-delay', `${(index % 3) * 55}ms`)
    })
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('is-visible')
        observer.unobserve(entry.target)
      })
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 })
    elements.forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [])

  return (
    <>
      <div ref={trailRef} className="cursor-trail" aria-hidden="true" />
      <div ref={cursorRef} className="custom-cursor" aria-hidden="true" />
    </>
  )
}
