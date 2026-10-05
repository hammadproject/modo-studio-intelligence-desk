export interface ProjectItem {
  id: string
  title: string
  category: string
  imageSrc?: string
  imageWidth?: number
  imageHeight?: number
  alt: string
  tone: 'stone' | 'sand' | 'graphite' | 'clay' | 'sage' | 'mist'
}

export interface ServiceItem {
  id: string
  index: string
  title: string
  summary: string
  startingAt: string
  detail: string
}

export const projects: ProjectItem[] = [
  { id: 'forma', title: 'Forma', category: 'Brand identity', imageSrc: '/selected-work/forma.jpg', imageWidth: 1520, imageHeight: 1600, alt: 'Forma blue geometric brand identity artwork', tone: 'stone' },
  { id: 'velin', title: 'Velin', category: 'Packaging', imageSrc: '/selected-work/velin.jpg', imageWidth: 1344, imageHeight: 1840, alt: 'Velin cosmetic packaging and brand application', tone: 'clay' },
  { id: 'atelier-n', title: 'Atelier N', category: 'Web design', imageSrc: '/selected-work/atelier.jpg', imageWidth: 2064, imageHeight: 1232, alt: 'Atelier N architecture website displayed on a laptop', tone: 'graphite' },
  { id: 'common-ground', title: 'Common Ground', category: 'Brand system', imageSrc: '/selected-work/common-ground.jpg', imageWidth: 1296, imageHeight: 1616, alt: 'Common Ground specialty coffee packaging', tone: 'sage' },
  { id: 'still', title: 'Still', category: 'Art direction', imageSrc: '/selected-work/still.png', imageWidth: 978, imageHeight: 1024, alt: 'Sculptural silver object on flowing neutral fabric', tone: 'sand' },
  { id: 'luma', title: 'Luma', category: 'Product UI', imageSrc: '/selected-work/luma.jpg', imageWidth: 1920, imageHeight: 1200, alt: 'Luma wellness product interface displayed on a tablet', tone: 'mist' },
]

export const heroProjects: ProjectItem[] = [
  { id: 'hero-left', title: 'Featured project', category: '', imageSrc: '/hero/image1.jpg', imageWidth: 1344, imageHeight: 1792, alt: 'Editorial portrait illuminated by orange light', tone: 'stone' },
  { id: 'hero-center', title: 'Featured project', category: '', imageSrc: '/hero/image-mid.jpg', imageWidth: 1390, imageHeight: 1544, alt: 'Portrait framed by a sculptural orange arch', tone: 'clay' },
  { id: 'hero-right', title: 'Featured project', category: '', imageSrc: '/hero/image3.jpg', imageWidth: 1408, imageHeight: 1744, alt: 'Orange Kinetic bottle on deep blue fabric', tone: 'mist' },
]

export const services: ServiceItem[] = [
  {
    id: 'branding',
    index: '01',
    title: 'Branding',
    summary: 'Strategy and identity systems that make a business easier to understand.',
    startingAt: 'Strategy from $2,500 · Identity from $4,500',
    detail: 'Audience priorities, positioning, messaging direction, visual identity, typography, color, and practical brand guidelines.',
  },
  {
    id: 'websites',
    index: '02',
    title: 'Websites',
    summary: 'Clear, responsive marketing sites designed around real content and goals.',
    startingAt: 'Landing pages from $3,000 · Websites from $7,500',
    detail: 'Content planning, sitemaps, wireframes, responsive design, Webflow or WordPress development, basic SEO setup, and handoff.',
  },
  {
    id: 'digital-products',
    index: '03',
    title: 'Digital Products',
    summary: 'Focused product experiences that move from user flow to developer handoff.',
    startingAt: 'UI/UX starter from $5,000',
    detail: 'Up to two core user flows, wireframes, ten high-fidelity screens, a starter component library, and a clickable Figma prototype.',
  },
]

export const suggestedQuestions = [
  'What services does Modo Studio offer?',
  'What does a marketing website start at?',
  'How long does a visual identity project take?',
]
