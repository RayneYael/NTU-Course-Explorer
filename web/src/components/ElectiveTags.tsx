import type { ProgrammeCourse } from "@/types"

const TAGS: [keyof ProgrammeCourse, string, string][] = [
  ["is_bde", "BDE", "Available as a Broadening and Deepening Elective"],
  ["is_ue", "UE", "Available as an Unrestricted Elective"],
  ["is_ge_pe", "GE-PE", "Available as a General Education Prescribed Elective"],
  ["is_self_paced", "Self-paced", "Self-paced course"],
]

/** Elective flags only mean something relative to a programme, so they need its entry. */
export function ElectiveTags({ entry }: { entry?: ProgrammeCourse }) {
  if (!entry) return null
  const on = TAGS.filter(([k]) => entry[k])
  if (!on.length) return null
  return (
    <span className="inline-flex flex-wrap gap-1">
      {on.map(([k, label, title]) => (
        <span
          key={k}
          title={title}
          className="rounded-sm bg-elective-soft px-1.5 py-px text-[11px] font-semibold uppercase tracking-wide text-elective"
        >
          {label}
        </span>
      ))}
    </span>
  )
}
