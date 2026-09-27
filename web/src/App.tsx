import { useEffect, useMemo, useRef, useState } from "react"
import { Search, X } from "lucide-react"

import { CourseDetail } from "@/components/CourseDetail"
import { CourseList } from "@/components/CourseList"
import { ElectiveHelp } from "@/components/ElectiveHelp"
import { ProgrammePicker } from "@/components/ProgrammePicker"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet"
import { fetchVisitCount } from "@/lib/analytics"
import { fetchSemester, fetchSemesters, formatFetched, listingsFor, search, visibleIndexes } from "@/lib/data"
import { cn } from "@/lib/utils"
import type { SemesterData, SemesterInfo } from "@/types"

type Filter = "classes" | "bde" | "ue"

export default function App() {
  const [semesters, setSemesters] = useState<SemesterInfo[] | null>(null)
  const [semKey, setSemKey] = useState<string | null>(() => remember.get("semester"))
  const [loaded, setLoaded] = useState<SemesterData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [programme, setProgramme] = useState<string | null>(() => remember.get("programme"))
  const [query, setQuery] = useState("")
  const [filters, setFilters] = useState<Set<Filter>>(new Set())
  const [selected, setSelected] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const wide = useMediaQuery("(min-width: 1024px)")
  const searchRef = useRef<HTMLInputElement>(null)
  const [visits, setVisits] = useState<string | null>(null)

  useEffect(() => {
    fetchVisitCount().then(setVisits)
  }, [])

  // semesters index
  useEffect(() => {
    fetchSemesters()
      .then((list) => {
        setSemesters(list)
        setSemKey((k) => (k && list.some((s) => s.key === k) ? k : list[0]?.key ?? null))
      })
      .catch((e) => setError(String(e)))
  }, [])

  const semester = semesters?.find((s) => s.key === semKey) ?? null
  const data = loaded && loaded.semester.key === semester?.key ? loaded : null

  // semester data
  useEffect(() => {
    if (!semester) return
    let live = true
    fetchSemester(semester)
      .then((d) => live && setLoaded(d))
      .catch((e) => live && setError(String(e)))
    remember.set("semester", semester.key)
    return () => {
      live = false
    }
  }, [semester])

  // a programme that doesn't exist in this semester falls back to "all courses"
  const prog = data?.programmes.find((p) => p.value === programme) ?? null
  useEffect(() => remember.set("programme", programme), [programme])

  const results = useMemo(() => {
    if (!data) return []
    let list = search(listingsFor(data, prog), query)
    if (filters.has("classes")) list = list.filter((l) => visibleIndexes(l.course, l.entry).length > 0)
    if (prog && filters.has("bde")) list = list.filter((l) => l.entry?.is_bde)
    if (prog && filters.has("ue")) list = list.filter((l) => l.entry?.is_ue)
    return list
  }, [data, prog, query, filters])

  // keep a course open on wide screens so the page is never an empty shell
  const current = results.find((l) => l.course.code === selected) ?? (wide ? results[0] : undefined)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT") {
        e.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  const toggle = (f: Filter) =>
    setFilters((prev) => {
      const next = new Set(prev)
      if (next.has(f)) next.delete(f)
      else next.add(f)
      return next
    })

  const open = (code: string) => {
    setSelected(code)
    if (!wide) setSheetOpen(true)
  }

  const detail = current && semester && (
    <CourseDetail
      key={`${semester.key}|${prog?.value}|${current.course.code}`}
      course={current.course}
      entry={current.entry}
      semesterLabel={semester.label}
      programmeLabel={prog?.label}
    />
  )

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-20 border-b bg-background/95 pt-[env(safe-area-inset-top,0px)] backdrop-blur">
        <div className="flex flex-col gap-3 px-4 py-3 sm:px-6">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h1 className="text-[17px] font-bold tracking-tight">
              NTU Course Explorer
              <span className="ml-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">unofficial</span>
            </h1>
            {semester && (
              <p className="text-xs text-muted-foreground">
                Data fetched {formatFetched(semester.fetched_at)} from NTU's public class schedule
                {visits && <span className="tabular"> · {visits} visits</span>}
              </p>
            )}
          </div>
          <div className="grid gap-2 md:grid-cols-[minmax(12rem,15rem)_minmax(14rem,22rem)_1fr]">
            <Select value={semKey ?? undefined} onValueChange={(v) => { setSemKey(v); setSelected(null) }}>
              <SelectTrigger id="semester" aria-label="Semester" className="h-9 bg-card">
                <SelectValue placeholder="Loading semesters…" />
              </SelectTrigger>
              <SelectContent>
                {semesters?.map((s) => (
                  <SelectItem key={s.key} value={s.key}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <ProgrammePicker
              programmes={data?.programmes ?? []}
              value={prog ? prog.value : null}
              onChange={(v) => { setProgramme(v); setSelected(null) }}
            />
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="search"
                ref={searchRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search code, title or description   ( / )"
                aria-label="Search courses"
                className="h-9 bg-card pl-9 pr-9"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  aria-label="Clear search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="flex min-h-0 flex-1">
        <aside className="flex w-full min-w-0 flex-col border-r lg:w-[26rem] lg:flex-none">
          <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2 text-xs">
            <span className="mr-auto text-muted-foreground tabular">
              {data ? `${results.length.toLocaleString()} ${results.length === 1 ? "course" : "courses"}` : ""}
            </span>
            <FilterChip on={filters.has("classes")} onClick={() => toggle("classes")}>
              Has classes
            </FilterChip>
            {prog && (
              <>
                <FilterChip on={filters.has("bde")} onClick={() => toggle("bde")}>BDE</FilterChip>
                <FilterChip on={filters.has("ue")} onClick={() => toggle("ue")}>UE</FilterChip>
              </>
            )}
            <ElectiveHelp />
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {error ? (
              <Notice title="Course data couldn't be loaded">
                {error}. When running locally, create the data with{" "}
                <code className="font-mono">python -m ntu_courses export-web</code> and reload.
              </Notice>
            ) : !data ? (
              <Notice title={semester ? `Loading ${semester.label}…` : "Loading…"}>
                The semester file is a few megabytes; it loads once and is then cached.
              </Notice>
            ) : prog && prog.status !== "ok" ? (
              <Notice title={prog.label}>
                {prog.status === "empty"
                  ? `NTU lists no classes for this programme in ${semester?.label}.`
                  : "This programme couldn't be fetched during the last update. It will be retried on the next crawl."}
              </Notice>
            ) : results.length === 0 ? (
              <Notice title="No courses match">Try fewer words, or clear the filters.</Notice>
            ) : (
              <CourseList listings={results} selected={current?.course.code ?? null} onSelect={open} />
            )}
          </div>
        </aside>

        <section className="hidden min-w-0 flex-1 overflow-y-auto lg:block" aria-label="Course details">
          {detail}
        </section>
      </main>

      {!wide && (
        <Sheet open={sheetOpen && !!current} onOpenChange={setSheetOpen}>
          <SheetContent side="bottom" className="h-[92%] overflow-y-auto p-0">
            <SheetTitle className="sr-only">{current?.course.code}</SheetTitle>
            <SheetDescription className="sr-only">{current?.course.title}</SheetDescription>
            {detail}
          </SheetContent>
        </Sheet>
      )}
    </div>
  )
}

function FilterChip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={cn(
        "rounded-full border px-2.5 py-0.5 font-medium transition-colors",
        on ? "border-primary bg-primary text-primary-foreground" : "bg-card text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  )
}

function Notice({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1 px-4 py-8">
      <p className="font-semibold">{title}</p>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  )
}

function useMediaQuery(query: string): boolean {
  const [match, setMatch] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const on = () => setMatch(mq.matches)
    mq.addEventListener("change", on)
    return () => mq.removeEventListener("change", on)
  }, [query])
  return match
}

/** Per-viewer convenience only; storage can be missing or blocked. */
const remember = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(`nce:${key}`)
    } catch {
      return null
    }
  },
  set(key: string, value: string | null) {
    try {
      if (value === null) localStorage.removeItem(`nce:${key}`)
      else localStorage.setItem(`nce:${key}`, value)
    } catch {
      /* ignore */
    }
  },
}
