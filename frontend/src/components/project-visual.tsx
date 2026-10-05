import { cn } from '../lib/utils'
import type { ProjectItem } from '../data/content'

export function ProjectVisual({
  project,
  className,
  eager = false,
}: {
  project: ProjectItem
  className?: string
  eager?: boolean
}) {
  return (
    <div className={cn('project-visual', `project-tone-${project.tone}`, className)}>
      {project.imageSrc ? (
        <img
          src={project.imageSrc}
          alt={project.alt}
          width={project.imageWidth}
          height={project.imageHeight}
          loading={eager ? 'eager' : 'lazy'}
          decoding="async"
          className="size-full object-cover"
        />
      ) : (
        <div className="project-fallback" aria-label={`${project.title} project`} />
      )}
    </div>
  )
}
