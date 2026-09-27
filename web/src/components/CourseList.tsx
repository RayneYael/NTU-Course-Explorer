import { ElectiveTags } from "@/components/ElectiveTags"
import { visibleIndexes, type Listing } from "@/lib/data"
import { cn } from "@/lib/utils"

interface Props {
  listings: Listing[]
  selected: string | null
  onSelect: (code: string) => void
}

export function CourseList({ listings, selected, onSelect }: Props) {
  return (
    <ul className="divide-y" aria-label="Courses">
      {listings.map(({ course, entry }) => {
        const n = visibleIndexes(course, entry).length
        const active = course.code === selected
        return (
          <li key={course.code}>
            <button
              type="button"
              onClick={() => onSelect(course.code)}
              aria-current={active ? "true" : undefined}
              className={cn(
                "grid w-full grid-cols-[5.5rem_1fr] gap-x-3 gap-y-1 px-4 py-3 text-left transition-colors hover:bg-accent",
                active && "bg-accent shadow-[inset_3px_0_0_hsl(var(--primary))]",
              )}
            >
              <span className="font-mono text-[13px] font-medium text-primary">{course.code}</span>
              <span className="min-w-0 text-[12.5px] font-medium uppercase leading-snug tracking-[0.02em]">{course.title}</span>
              <span className="font-mono text-xs text-muted-foreground tabular">
                {course.au != null ? `${course.au.toFixed(1)} AU` : ""}
              </span>
              <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                <span className="tabular">{n ? `${n} ${n === 1 ? "index" : "indexes"}` : "No classes"}</span>
                <ElectiveTags entry={entry} />
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
