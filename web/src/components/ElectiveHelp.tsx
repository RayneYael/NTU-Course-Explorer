import { CircleHelp } from "lucide-react"

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

// Legend from the foot of NTU's class schedule page, plus how this app shows it.
const TAGS = [
  { tag: "BDE", mark: "~", meaning: "Counts as a Broadening and Deepening Elective." },
  { tag: "UE", mark: "*", meaning: "Counts as an Unrestricted Elective." },
  { tag: "GE-PE", mark: "#", meaning: "Counts as a General Education Prescribed Elective." },
  { tag: "Self-paced", mark: "^", meaning: "Self-paced course." },
]

/** Click-to-open legend for the elective tags (a popover, so it also works on touch screens). */
export function ElectiveHelp() {
  return (
    <Popover>
      <PopoverTrigger
        aria-label="What do BDE, UE and the other tags mean?"
        className="inline-flex h-6 w-6 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <CircleHelp className="h-4 w-4" />
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(22rem,calc(100vw-2rem))] space-y-3 p-4 text-[13px]">
        <p className="font-semibold">Elective tags</p>
        <dl className="grid grid-cols-[auto_1fr] items-baseline gap-x-3 gap-y-2">
          {TAGS.map(({ tag, mark, meaning }) => (
            <div key={tag} className="contents">
              <dt>
                <span className="rounded-sm bg-elective-soft px-1.5 py-px text-[11px] font-semibold uppercase tracking-wide text-elective">
                  {tag}
                </span>
              </dt>
              <dd className="leading-snug">
                {meaning}{" "}
                <span className="text-muted-foreground">
                  NTU marks it <code className="font-mono">{mark}</code>.
                </span>
              </dd>
            </div>
          ))}
        </dl>
        <ul className="list-disc space-y-1.5 pl-4 leading-snug text-muted-foreground">
          <li>
            Tags depend on the programme. A course can be a BDE for one programme and not for another, so tags
            appear only after you pick a programme.
          </li>
          <li>
            A tag doesn't guarantee you can take the course. Also check "Not available to Programme" and the
            prerequisites in the course details.
          </li>
          <li>Which elective types apply to you depends on your programme and intake year.</li>
        </ul>
      </PopoverContent>
    </Popover>
  )
}
