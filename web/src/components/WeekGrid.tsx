import { DAYS, formatTime, formatWeeks, parseTime } from "@/lib/data"
import type { Session } from "@/types"

const HOUR_PX = 44

interface Block {
  day: string
  start: number
  end: number
  time: string
  type: string
  group: string
  venues: string[]
  weeks: string[]
  lane: number
  lanes: number
}

/**
 * Mon–Sat timetable for one index. Sessions that share day, time, type and group (e.g. the
 * same lecture in a different hall for one week) are merged into one block; genuinely
 * overlapping blocks are placed side by side.
 */
export function WeekGrid({ sessions }: { sessions: Session[] }) {
  const merged = new Map<string, Block>()
  const untimed: Session[] = []
  for (const s of sessions) {
    const t = parseTime(s.time)
    if (!t || !DAYS.includes(s.day as (typeof DAYS)[number])) {
      untimed.push(s)
      continue
    }
    const key = `${s.day}|${s.time}|${s.type}|${s.group}`
    const b = merged.get(key) ?? {
      day: s.day, start: t[0], end: t[1], time: s.time, type: s.type, group: s.group,
      venues: [], weeks: [], lane: 0, lanes: 1,
    }
    if (s.venue && !b.venues.includes(s.venue)) b.venues.push(s.venue)
    if (s.remark && !b.weeks.includes(s.remark)) b.weeks.push(s.remark)
    merged.set(key, b)
  }
  const blocks = [...merged.values()]
  for (const day of DAYS) assignLanes(blocks.filter((b) => b.day === day))

  const days = blocks.some((b) => b.day === "SAT") ? DAYS : DAYS.slice(0, 5)
  const first = Math.min(8, ...blocks.map((b) => Math.floor(b.start / 60)))
  const last = Math.max(18, ...blocks.map((b) => Math.ceil(b.end / 60)))
  const hours = Array.from({ length: last - first }, (_, i) => first + i)
  const height = hours.length * HOUR_PX

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-md border bg-card">
        <div
          className="grid min-w-[34rem]"
          style={{ gridTemplateColumns: `3rem repeat(${days.length}, minmax(0, 1fr))` }}
          role="table"
          aria-label="Weekly timetable"
        >
          <div className="border-b" />
          {days.map((d) => (
            <div key={d} className="border-b border-l px-2 py-1.5 text-[11px] font-semibold tracking-wider text-muted-foreground">
              {d}
            </div>
          ))}
          <div className="relative" style={{ height }}>
            {hours.map((h, i) => (
              <div
                key={h}
                className="absolute right-1.5 -translate-y-1/2 font-mono text-[10.5px] text-muted-foreground tabular"
                style={{ top: i * HOUR_PX }}
              >
                {i > 0 ? `${String(h).padStart(2, "0")}:00` : ""}
              </div>
            ))}
          </div>
          {days.map((d) => (
            <div key={d} className="relative border-l" style={{ height }}>
              {hours.slice(1).map((_, i) => (
                <div key={i} className="absolute inset-x-0 border-t border-dashed border-border/70" style={{ top: (i + 1) * HOUR_PX }} />
              ))}
              {blocks
                .filter((b) => b.day === d)
                .map((b) => (
                  <div
                    key={`${b.time}|${b.type}|${b.group}`}
                    className="absolute overflow-hidden rounded-sm border-l-2 border-primary bg-[hsl(var(--block))] px-1.5 py-1 text-[11px] leading-tight"
                    style={{
                      top: ((b.start - first * 60) / 60) * HOUR_PX + 1,
                      height: Math.max(((b.end - b.start) / 60) * HOUR_PX - 2, 18),
                      left: `calc(${(b.lane / b.lanes) * 100}% + 2px)`,
                      width: `calc(${100 / b.lanes}% - 4px)`,
                    }}
                    title={`${b.type} ${b.group} · ${formatTime(b.time)} · ${b.venues.join(", ")} · ${b.weeks.map(formatWeeks).join("; ")}`}
                  >
                    <div className="font-semibold">{b.type}</div>
                    <div className="truncate text-muted-foreground">{b.venues.join(" / ")}</div>
                  </div>
                ))}
            </div>
          ))}
        </div>
      </div>
      {untimed.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Not on the grid:{" "}
          {untimed.map((s) => [s.type, s.day, s.time, s.venue].filter(Boolean).join(" ")).join("; ")}
        </p>
      )}
    </div>
  )
}

function assignLanes(blocks: Block[]) {
  blocks.sort((a, b) => a.start - b.start || a.end - b.end)
  // cluster overlapping blocks, then give each a lane within its cluster
  let cluster: Block[] = []
  let clusterEnd = -1
  const flush = () => {
    const laneEnds: number[] = []
    for (const b of cluster) {
      let lane = laneEnds.findIndex((end) => end <= b.start)
      if (lane === -1) lane = laneEnds.push(0) - 1
      laneEnds[lane] = b.end
      b.lane = lane
    }
    for (const b of cluster) b.lanes = laneEnds.length
    cluster = []
  }
  for (const b of blocks) {
    if (b.start >= clusterEnd && cluster.length) flush()
    cluster.push(b)
    clusterEnd = Math.max(clusterEnd, b.end)
  }
  if (cluster.length) flush()
}
