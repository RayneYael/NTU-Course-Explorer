import { Fragment, useMemo, useState } from "react"

import { ElectiveTags } from "@/components/ElectiveTags"
import { WeekGrid } from "@/components/WeekGrid"
import { Button } from "@/components/ui/button"
import { formatTime, formatWeeks, visibleIndexes } from "@/lib/data"
import { cn } from "@/lib/utils"
import type { Course, ProgrammeCourse } from "@/types"

const ATTRIBUTE_ORDER = [
  "Prerequisite",
  "Mutually exclusive with",
  "Not available to Programme",
  "Not available to all Programme with",
  "Not available as Core to Programme",
  "Not available as BDE/UE to Programme",
  "Grade Type",
  "Department",
  "Notes",
]

interface Props {
  course: Course
  entry?: ProgrammeCourse
  semesterLabel: string
  programmeLabel?: string
}

export function CourseDetail({ course, entry, semesterLabel, programmeLabel }: Props) {
  const [showAll, setShowAll] = useState(false)
  const own = visibleIndexes(course, entry)
  const partial = own.length < course.indexes.length
  const indexes = showAll || !partial ? course.indexes : own
  const [picked, setPicked] = useState<string | null>(null)

  const current = indexes.find((i) => i.index === picked) ?? indexes[0]
  const attributes = useMemo(() => {
    const entries = Object.entries(course.attributes)
    const rank = (k: string) => (ATTRIBUTE_ORDER.indexOf(k) + 1 || 99)
    return entries.sort((a, b) => rank(a[0]) - rank(b[0]))
  }, [course])

  return (
    <article className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-5 sm:px-6">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-mono text-base font-semibold text-primary">{course.code}</span>
          {course.au != null && (
            <span className="font-mono text-sm text-muted-foreground tabular">{course.au.toFixed(1)} AU</span>
          )}
          <ElectiveTags entry={entry} />
        </div>
        <h2 className="text-xl font-semibold uppercase leading-tight tracking-[0.01em] sm:text-2xl">{course.title}</h2>
        {entry?.remark && (
          <p className="text-sm">
            <span className="font-medium">Remark for {programmeLabel}:</span> {entry.remark}
          </p>
        )}
      </header>

      {attributes.length > 0 && (
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[13rem_1fr]">
          {attributes.map(([k, v]) => (
            <Fragment key={k}>
              <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground sm:pt-0.5">{k}</dt>
              <dd className="break-words">{v}</dd>
            </Fragment>
          ))}
        </dl>
      )}

      {course.description && (
        <section className="max-w-[68ch] space-y-3 text-[14.5px] leading-relaxed">
          {course.description.split("\n").map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </section>
      )}

      <section className="flex flex-col gap-3" aria-labelledby="classes-heading">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 id="classes-heading" className="text-sm font-semibold uppercase tracking-wider">
            Classes
            <span className="ml-2 font-normal normal-case tracking-normal text-muted-foreground tabular">
              {course.indexes.length === 0
                ? `none scheduled in ${semesterLabel}`
                : partial && !showAll && own.length === 0
                  ? `none listed for ${programmeLabel}; ${course.indexes.length} ${course.indexes.length === 1 ? "index" : "indexes"} offered to other programmes`
                  : partial && !showAll
                  ? `${own.length} of ${course.indexes.length} indexes listed for ${programmeLabel}`
                  : `${course.indexes.length} ${course.indexes.length === 1 ? "index" : "indexes"}`}
            </span>
          </h3>
          {partial && (
            <Button variant="link" size="sm" className="h-auto p-0" onClick={() => setShowAll((v) => !v)}>
              {showAll ? `Only indexes for ${programmeLabel}` : "Show all indexes"}
            </Button>
          )}
        </div>

        {current && (
          <>
            <p className="text-xs text-muted-foreground">
              Timetable for index <span className="font-mono font-semibold text-foreground">{current.index}</span>.
              Select another index below to compare.
            </p>
            <WeekGrid sessions={current.sessions} />
          </>
        )}

        {indexes.length > 0 && (
          <div className="overflow-x-auto rounded-md border bg-card">
            <table className="w-full min-w-[40rem] border-collapse text-[13px]">
              <thead>
                <tr className="border-b text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                  {["Index", "Type", "Group", "Day", "Time", "Venue", "Weeks"].map((h) => (
                    <th key={h} scope="col" className="px-3 py-2 font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              {indexes.map((idx) => {
                const active = idx.index === current?.index
                return (
                  <tbody
                    key={idx.index}
                    onClick={() => setPicked(idx.index)}
                    className={cn(
                      "cursor-pointer border-b last:border-b-0 hover:bg-accent/60",
                      active && "bg-accent",
                    )}
                  >
                    {idx.sessions.map((s, i) => (
                      <tr key={i} className="align-top">
                        {i === 0 && (
                          <td rowSpan={idx.sessions.length} className="px-3 py-1.5">
                            <button
                              type="button"
                              onClick={() => setPicked(idx.index)}
                              aria-pressed={active}
                              className={cn(
                                "font-mono font-semibold tabular",
                                active ? "text-primary" : "text-foreground",
                              )}
                            >
                              {idx.index}
                            </button>
                          </td>
                        )}
                        <td className="px-3 py-1.5">{s.type}</td>
                        <td className="px-3 py-1.5 font-mono">{s.group}</td>
                        <td className="px-3 py-1.5">{s.day}</td>
                        <td className="whitespace-nowrap px-3 py-1.5 font-mono tabular">{formatTime(s.time)}</td>
                        <td className="px-3 py-1.5">{s.venue}</td>
                        <td className="px-3 py-1.5 text-muted-foreground">{formatWeeks(s.remark)}</td>
                      </tr>
                    ))}
                  </tbody>
                )
              })}
            </table>
          </div>
        )}
      </section>
    </article>
  )
}
