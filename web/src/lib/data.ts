import type { ClassIndex, Course, Programme, ProgrammeCourse, SemesterData, SemesterInfo, Session } from "@/types"

const DATA_DIR = "./data"

export async function fetchSemesters(): Promise<SemesterInfo[]> {
  const res = await fetch(`${DATA_DIR}/semesters.json`)
  if (!res.ok) throw new Error(`semesters.json: HTTP ${res.status}`)
  return res.json()
}

const semesterCache = new Map<string, Promise<SemesterData>>()

export function fetchSemester(info: SemesterInfo): Promise<SemesterData> {
  let p = semesterCache.get(info.key)
  if (!p) {
    p = fetch(`${DATA_DIR}/${info.file}`).then((res) => {
      if (!res.ok) throw new Error(`${info.file}: HTTP ${res.status}`)
      return res.json()
    })
    p.catch(() => semesterCache.delete(info.key))
    semesterCache.set(info.key, p)
  }
  return p
}

// ------------------------------------------------------------------ programmes

export const PROGRAMME_GROUPS = [
  "Degree programmes",
  "Part-time degrees",
  "Minors",
  "Broadening & Deepening / Unrestricted Electives",
  "General Education",
  "Scholars & special programmes",
] as const
export type ProgrammeGroup = (typeof PROGRAMME_GROUPS)[number]

const SPECIAL = new Set(["USP", "CNY", "TAIS", "NGLP", "EP"])

export function programmeGroup(p: Programme): ProgrammeGroup {
  const [category, , , mode] = p.value.split(";")
  if (category === "MLOAD") return "Minors"
  if (category === "GLOAD") return "Broadening & Deepening / Unrestricted Electives"
  if (category === "GERP") return "General Education"
  if (SPECIAL.has(category)) return "Scholars & special programmes"
  if (mode === "P") return "Part-time degrees"
  return "Degree programmes"
}

export function groupProgrammes(programmes: Programme[]): [ProgrammeGroup, Programme[]][] {
  const groups = new Map<ProgrammeGroup, Programme[]>(PROGRAMME_GROUPS.map((g) => [g, []]))
  for (const p of programmes) groups.get(programmeGroup(p))!.push(p)
  return [...groups].filter(([, list]) => list.length > 0)
}

// ------------------------------------------------------------------ listing + search

/** One row in the course list: the course plus, in a programme view, how that programme sees it. */
export interface Listing {
  course: Course
  entry?: ProgrammeCourse
}

export function listingsFor(data: SemesterData, programme: Programme | null): Listing[] {
  if (!programme) {
    return Object.values(data.courses).map((course) => ({ course }))
  }
  return programme.courses
    .filter((e) => data.courses[e.code])
    .map((entry) => ({ course: data.courses[entry.code], entry }))
}

const haystacks = new WeakMap<Course, { code: string; title: string; rest: string }>()

function hay(c: Course) {
  let h = haystacks.get(c)
  if (!h) {
    h = {
      code: c.code.toLowerCase(),
      title: c.title.toLowerCase(),
      rest: (c.description + " " + Object.values(c.attributes).join(" ")).toLowerCase(),
    }
    haystacks.set(c, h)
  }
  return h
}

/**
 * Every whitespace-separated term must appear in the code, title, description or attributes.
 * Ranking: exact code > code prefix > all terms in title > anywhere.
 */
export function search(listings: Listing[], query: string): Listing[] {
  const q = query.trim().toLowerCase()
  if (!q) return [...listings].sort((a, b) => a.course.code.localeCompare(b.course.code))
  const terms = q.split(/\s+/)
  const scored: [number, Listing][] = []
  for (const l of listings) {
    const h = hay(l.course)
    const all = `${h.code} ${h.title} ${h.rest}`
    if (!terms.every((t) => all.includes(t))) continue
    let score = 1
    if (h.code === q) score = 100
    else if (h.code.startsWith(q)) score = 60
    else if (terms.every((t) => h.title.includes(t) || h.code.includes(t))) score = 30
    scored.push([score, l])
  }
  return scored
    .sort((a, b) => b[0] - a[0] || a[1].course.code.localeCompare(b[1].course.code))
    .map(([, l]) => l)
}

// ------------------------------------------------------------------ indexes + time

/** Indexes a programme sees for a course (all when the programme view shows every index). */
export function visibleIndexes(course: Course, entry?: ProgrammeCourse): ClassIndex[] {
  if (!entry?.indexes) return course.indexes
  const wanted = new Set(entry.indexes)
  return course.indexes.filter((i) => wanted.has(i.index))
}

export const DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"] as const

/** "0830-0920" -> [510, 560] minutes after midnight, or null when there is no time. */
export function parseTime(time: string): [number, number] | null {
  const m = /^(\d{2})(\d{2})-(\d{2})(\d{2})$/.exec(time.trim())
  if (!m) return null
  return [+m[1] * 60 + +m[2], +m[3] * 60 + +m[4]]
}

export function formatTime(time: string): string {
  const m = /^(\d{2})(\d{2})-(\d{2})(\d{2})$/.exec(time.trim())
  return m ? `${m[1]}:${m[2]}–${m[3]}:${m[4]}` : time || "—"
}

/** "Teaching Wk2-13" -> "Wk 2–13" */
export function formatWeeks(remark: string): string {
  return remark.replace(/^Teaching\s+/i, "").replace(/^Wk\s*/i, "Wk ").replace(/(\d)-(\d)/g, "$1–$2")
}

export function sessionKey(s: Session): string {
  return `${s.type}|${s.group}|${s.day}|${s.time}|${s.venue}|${s.remark}`
}

export function formatFetched(iso: string): string {
  const d = new Date(iso)
  return isNaN(+d) ? iso : d.toLocaleDateString("en-SG", { day: "numeric", month: "short", year: "numeric" })
}
