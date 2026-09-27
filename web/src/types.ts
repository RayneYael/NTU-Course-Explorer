// Shapes of the JSON written by `python -m ntu_courses export-web` (see ntu_courses/crawler.py).

export interface SemesterInfo {
  key: string // "2026_1"
  label: string // "Acad Yr 2026 Semester 1"
  fetched_at: string
  programmes: number
  courses: number
  file: string
}

export interface Session {
  type: string // LEC/STUDIO, TUT, LAB, SEM ...
  group: string
  day: string // MON ... SAT
  time: string // "0830-0920"
  venue: string
  remark: string // "Teaching Wk2-13"
}

export interface ClassIndex {
  index: string
  sessions: Session[]
}

export interface Course {
  code: string
  title: string
  au: number | null
  description: string
  attributes: Record<string, string>
  indexes: ClassIndex[]
}

/** A course as listed on one programme's page. */
export interface ProgrammeCourse {
  code: string
  is_ue: boolean
  is_bde: boolean
  is_self_paced: boolean
  is_ge_pe: boolean
  remark?: string
  indexes?: string[] // indexes shown to this programme; absent = all
}

export interface Programme {
  value: string // "CSC;;1;F"
  label: string // "Computer Science Year 1"
  status: "ok" | "empty" | "error"
  courses: ProgrammeCourse[]
}

export interface SemesterData {
  format: number
  semester: { key: string; year: number; sem: string; label: string }
  fetched_at: string
  programmes: Programme[]
  courses: Record<string, Course>
  errors: { programme: string; error: string }[]
}
