# Modo Studio — Frontend Implementation Plan

## Instructions to Codex

Read this plan, inspect the repository and any AGENTS.md instructions, and inspect both user-supplied design images before coding. Implement the frontend and validate it rather than stopping at a proposal. Preserve the existing backend and Phase 2 integrations. Make routine implementation decisions autonomously. Do not deploy or change production infrastructure.

The user supplies two images:
1. Modo Studio homepage: huge MODO wordmark, New York subtitle, three central editorial cards, selected-work link, service pills, studio introduction, three service tiles, and Intelligence Desk chat launcher.
2. Selected-work section: asymmetric six-project mosaic under “Ideas made tangible.”

Use these as visual references, not whole-page image backgrounds. Build actual responsive HTML/CSS components with selectable text, accessible controls, and working navigation. Inspect the actual images; do not infer their dimensions from this description. If the reference files are missing, implement the described structure and state the visual verification limitation.

## Business and project context

Modo Studio is a premium New York design agency integrating its own AI-assisted client experience, Modo Studio Intelligence Desk. The initial project is the official business website.

The backend foundation and agency knowledge base were handled in earlier phases. Inspect what actually exists; do not assume implementation matches an earlier plan. Read the current business knowledge files, API schemas/OpenAPI, authentication, message responses, history endpoints, and handoff workflow. Use current agency documents as the authority for business copy and pricing. The supplied images guide appearance, not policy facts.

Ensure the site accurately reflects Modo Studio's clients, awards, testimonials, results, and actual appointments as outlined in the provided business knowledge files.

## Critical image requirement

Do NOT generate, download, scrape, purchase, crop, or extract the selected-work pictures. The user will generate and provide those final assets later. Do not reuse the imagery embedded in the selected-work reference screenshot as portfolio assets.

Implement all six selected-work cards with premium neutral placeholders that preserve their exact aspect ratios, dimensions, rounded corners, captions, hover behavior, and responsiveness. Use subtle neutral background tones and an unobtrusive “Project visual coming soon” label. Avoid loud broken-image icons, stock photography, or colorful fake illustrations.

For the three hero cards, use existing standalone project image assets only if the user has already supplied them separately. Do not crop them from the homepage reference. If standalone assets are unavailable, use tasteful placeholder cards with reference-inspired background tones. The layout must remain complete without images.

Define every image through project data with an optional image source and alt text so replacing a placeholder later requires editing data/assets rather than rebuilding components. Reserve geometry to avoid layout shifts. No generated imagery in this phase.

## Technology and organization

Use the existing frontend stack if suitable. If no frontend exists, use React, TypeScript, and Vite. Use ordinary CSS or the repository's established styling approach. Avoid adding a UI kit that imposes a conflicting design language. Use a small icon library if needed and CSS transitions; add an animation dependency only when justified.

Organize the app into components such as Header, Hero, StudioIntro, ServiceTiles, SelectedWork, ProjectCard, ContactSection, Footer, ChatLauncher, ChatWidget, MessageList, MessageBubble, ChatComposer, and ExpertRequestForm. Keep API clients, types, chat state, and project/service content separate from presentation. Naming is flexible; separation matters.

Use FRONTEND environment configuration such as VITE_API_BASE_URL. Browser environment variables are public: do not place LLM keys, database credentials, admin API keys, or vector-store secrets in them. Provide an example environment file and README instructions. Configure backend CORS only for documented development origins if necessary; no universal production wildcard.

## Visual system

Match the reference's premium editorial character:
- Warm off-white/light-gray outer background, white surfaces, nearly black type, restrained gray secondary text.
- Very large, heavy grotesk typography for MODO; clean sans-serif for other text.
- Generous whitespace with deliberate compact spacing within the project mosaic.
- Consistent page gutters, shared alignment guides, subtle rounded panels, thin rules, and no excessive shadows.
- Concentrated color in future artwork; keep the interface restrained.
- Use an available local or openly licensed font with a fallback. Document font licensing. Never use an unlicensed commercial font.

Create shared CSS tokens for colors, typography, spacing, radius, container widths, and animation timing. Scale typography with clamp and verify line breaks at realistic screen sizes. Do not scale a fixed desktop canvas to fit mobile.

## Page structure and behavior

### 1. Header
Small custom Modo typographic/geometric mark at left, compact black Menu pill centered, and “Talk to an expert ↗” at right. Avoid copying the Monero reference logo. The Menu control opens an accessible navigation panel with links to Studio, Services, Selected Work, and Contact. Handle Escape, focus management, and closure after navigation. The expert button opens the real expert-request workflow described below.

### 2. Hero
White rounded panel with giant MODO wordmark spanning its interior width. Small “STUDIO — NEW YORK” beneath it. Add the subtle vertical “INDEPENDENT DESIGN STUDIO” detail on wide screens; remove or reposition it on mobile.

Three central project cards: equal widths, middle card taller/elevated, side cards equal height and aligned, consistent gaps and corner radii. Use placeholders as specified when no independent image assets exist.

Bottom-left: “SELECTED WORK”, thin horizontal rule, and “Explore our projects ↗” link that scrolls to the selected-work section. Do not restore the wireframe globe or the earlier “Clear brands…” block.

Bottom-right: understated service pills for Brand Strategy, Visual Identity, Web Design, and Product UI/UX. Make these useful links to relevant service information or chatbot prompts, not inert button-shaped elements.

### 3. Studio introduction
Small “THE STUDIO” label followed by “Design that moves your business forward.” and concise approved supporting copy. Maintain deliberate headline line breaks on desktop and natural wrapping on smaller screens.

Three service tiles labeled Branding, Websites, and Digital Products with indices 01–03, simple original geometric marks, and arrows. Make them reveal concise service detail or scroll to a services area. Use knowledge-base descriptions and accurate starting rates.

### 4. Selected work
Treat this as the next main showcase section after the homepage composition. Header: “MODO STUDIO / SELECTED WORK”, “Ideas made tangible.”, supporting copy “A selection of brand and digital projects.”, and “01 — 06”.

Desktop: six cards in three rows with alternating approximate column proportions 38/62, 62/38, 38/62. Each row has matching card heights and consistent gutters. Captions are visible and readable rather than available only on hover. In the placeholder state, adapt text contrast to neutral surfaces.

Project data:
| Project | Category |
| --- | --- |
| Forma | Brand identity |
| Velin | Packaging |
| Atelier N | Web design |
| Common Ground | Brand system |
| Still | Art direction |
| Luma | Product UI |

Label the section/footer “Selected projects by Modo Studio.” Incorporate accurate metrics, dates, and case-study narratives as provided in the business knowledge files. If detail images/content are pending, cards may open a restrained modal with title, category, and a truthful preview placeholder, or remain noninteractive. Do not add misleading clickable arrows with no behavior. The section's “Start a project ↗” link opens the contact/expert workflow.

### 5. Contact and footer
Provide a compact contact area so navigation has a real destination. Include a short project-inquiry invitation and “Talk to an expert” action. Integrate the agency's authentic address, telephone number, working email, and live booking calendar as provided. Use the configured handoff mechanism. Footer: Modo Studio, New York, and simple section links. Ensure all necessary legal pages and authentic social links are properly routed.

## Responsive behavior

Validate at desktop 1440px, laptop/tablet around 1024px and 768px, and mobile 390px and 320px. Use breakpoints based on layout needs.

- Header actions must remain readable and tappable; compact the menu without overlapping the brand or expert action.
- Hero wordmark must fit without horizontal scrolling. Keep the staggered three-card composition on widths that support it; simplify to an aligned compact strip or another deliberate mobile treatment when needed.
- Move hero lower annotations into a stacked layout on mobile.
- Service tiles stack when necessary.
- Portfolio mosaic becomes a single-column gallery on narrow screens; preserve project order and meaningful card ratios.
- Chat widget fits the viewport and virtual keyboard, respects safe-area insets, and never covers its own input.
- Contact/footer wrap gracefully. No clipped text or sideways page scrolling.

## Modo Studio Intelligence Desk integration

Use the actual backend API contract. If it differs from earlier expected routes, adapt the client to it rather than replacing working backend behavior. Keep backend calls in a typed client module. Never implement chatbot answers locally as if they came from the backend.

### Widget UI
Floating bottom-right black chat launcher with the Modo Studio mark. Open a polished chat panel consistent with the website. Header identifies the assistant as Ren, the Modo Studio assistant. Include close, new-chat, status/error feedback, scrollable messages, composer, and expert-request action.

A greeting may be static UI copy: “Hi! I can help with Modo Studio’s services, starting prices, and project process. What are you working on?” Suggested questions can include services, website starting prices, and project timelines. Sending them uses the same backend flow as typed messages.

Do not add an upstream cosmetic microphone or voice screen. Include a true online/staff availability indicator based on the actual backend status. Explain an actual backend outage with a useful retry action.

### Sessions and memory
Create a backend conversation when needed and retain the returned conversation ID/access credential according to the backend contract. Prefer the existing secure session approach. If the API uses bearer tokens and no cookie flow, use sessionStorage for the application, never URLs, logs, analytics, or source code; document that refresh resumes the tab's chat but closing the tab may not.

Load authorized persisted history when reopening or refreshing. New chat starts a new conversation; it must not silently delete old server data. Handle expired or missing credentials cleanly. Do not send full history if the backend owns memory; send the current message and required request identifiers.

Use stable request IDs and reuse them for retries after ambiguous failures. Prevent overlapping turns if the backend requires serialization. Keep unsent text when sending fails. Distinguish pending, successful, and failed messages without creating duplicate bubbles on retry.

Render returned answers safely: plain text or sanitized Markdown without raw HTML. Support paragraph breaks and lists. Render source citations only when provided by the backend. Validate external link schemes; do not expose internal file paths or invalid URLs. Retrieval scores are not answer-accuracy percentages and should not be shown as such.

Maintain readable scroll behavior: follow new responses when the user is near the bottom, but do not yank users away from older messages. Add an accessible new-message indication where appropriate.

### Expert request
Both website and widget expert actions must use the same real backend handoff process. Collect only supported fields such as name, email/preferred contact, service interest, brief project summary, budget range, and target date, with minimal required fields. Reuse confirmed conversation context where helpful without silently submitting it.

Ask consent to store contact details for follow-up. Validate fields and show submission/error states. A successful stored request is reported as recorded; do not state an expert is joining, an email was sent, or a meeting was booked unless that exact backend integration confirms it. If the endpoint is missing or unavailable, finish the UI and explain the unavailable submission state. Do not fake success or add a disconnected form that loses inquiries.

## Accessibility and motion

Use semantic landmarks, ordered heading hierarchy, real buttons/links, clear focus indicators, sufficient contrast, and explicit form labels. Modal/menu focus should return to the trigger when closed. Chat updates should use restrained aria-live announcements; do not repeatedly announce the entire history. Keyboard users must be able to navigate and send messages.

Use small opacity/translation transitions and subtle project hover states. Respect prefers-reduced-motion. Avoid excessive scroll effects, custom cursor interference, autoplay media, and elaborate loading screens. Images supplied later need meaningful alt text or empty alt when decorative. No text embedded in full-page raster images.

## Performance and maintainability

Use optimized image loading when images are added: responsive sizing, explicit dimensions/aspect ratios, eager loading only for necessary above-fold visuals, lazy loading for selected-work cards. Keep placeholder and final-asset paths equivalent. Avoid loading huge animation packages or fetching all history repeatedly.

Keep reusable content in structured data. Explain where the user should place the future artwork and how to update image sources. Leave no broken imports, dead template assets, hardcoded upstream URLs, or unneeded branding. Preserve upstream license attribution in project documentation where required.

## Validation

Run the available type check, production build, and relevant lint checks. Test meaningful integration flows with deterministic backend fixtures or an existing test environment.

Verify:
- Navigation, service links, project behavior, contact actions, and mobile menu.
- Placeholder cards render with no image requests or layout shift.
- Chat creation, sending, returned answer display, history restoration, new chat, and access failures.
- Retry with same request ID without duplicate messages.
- Backend outage and expert-form failure handling without false success.
- Successful handoff displays the actual recorded status.
- Keyboard behavior, reduced motion, and responsive viewport fitting.

Where browser tooling is available, capture local screenshots at desktop and mobile sizes and compare hierarchy, spacing, and proportions against the two supplied reference images. Fix material layout problems before delivery. Report any verification that could not be completed rather than claiming it passed.

## Completion criteria and report

Deliver a runnable premium Modo Studio frontend with both reference-inspired sections, neutral selected-work placeholders, a working Intelligence Desk widget against the existing API where available, and truthful expert-request behavior. Include README startup commands and environment configuration. Do not generate portfolio images or deploy.

Report changed components, successful checks, remaining backend dependencies, and the exact project-data/assets locations for the six selected-work images and three hero images. Future artwork replacement should be a straightforward data update.
