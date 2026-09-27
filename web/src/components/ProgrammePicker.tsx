import { useEffect, useMemo, useRef, useState } from "react"
import { Check, ChevronsUpDown } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { groupProgrammes } from "@/lib/data"
import { cn } from "@/lib/utils"
import type { Programme } from "@/types"

interface Props {
  programmes: Programme[]
  value: string | null // programme value, null = all courses
  onChange: (value: string | null) => void
}

export function ProgrammePicker({ programmes, value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const groups = useMemo(() => groupProgrammes(programmes), [programmes])
  const selected = programmes.find((p) => p.value === value) ?? null
  const listRef = useRef<HTMLDivElement>(null)
  const selectedRef = useRef<HTMLDivElement>(null)

  // Reopen at the current choice: centre it in the list (without scrolling the page).
  useEffect(() => {
    if (!open) return
    const frame = requestAnimationFrame(() => {
      const list = listRef.current
      const item = selectedRef.current
      if (!list || !item) return
      const offset = item.getBoundingClientRect().top - list.getBoundingClientRect().top
      list.scrollTop += offset - (list.clientHeight - item.offsetHeight) / 2
    })
    return () => cancelAnimationFrame(frame)
  }, [open])

  const choose = (v: string | null) => {
    onChange(v)
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id="programme"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label="Programme"
          className="h-9 w-full justify-between bg-card px-3 font-normal"
        >
          <span className="truncate">{selected ? selected.label : "All courses this semester"}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 text-muted-foreground" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[min(28rem,calc(100vw-2rem))] p-0" align="start">
        {/* defaultValue: keyboard highlight starts on the current choice */}
        <Command defaultValue={selected ? itemValue(selected) : ALL}>
          <CommandInput placeholder="Find a programme, minor or year…" />
          <CommandList ref={listRef} className="max-h-[min(24rem,60vh)]">
            <CommandEmpty>No programme matches.</CommandEmpty>
            <CommandGroup>
              <CommandItem value={ALL} onSelect={() => choose(null)}>
                <Check className={cn("h-4 w-4", value === null ? "opacity-100" : "opacity-0")} />
                All courses this semester
              </CommandItem>
            </CommandGroup>
            {groups.map(([group, list]) => (
              <CommandGroup key={group} heading={group}>
                {list.map((p) => (
                  <CommandItem
                    key={p.value}
                    ref={p.value === value ? selectedRef : undefined}
                    value={itemValue(p)}
                    onSelect={() => choose(p.value)}
                    className="gap-2"
                  >
                    <Check className={cn("h-4 w-4 shrink-0", value === p.value ? "opacity-100" : "opacity-0")} />
                    <span className="flex-1 truncate">{p.label}</span>
                    {p.status !== "ok" && (
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {p.status === "empty" ? "no classes" : "not loaded"}
                      </span>
                    )}
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

const ALL = "All courses this semester"

/** cmdk matches the search text against this value, so include the label and the code. */
function itemValue(p: Programme): string {
  return `${p.label} ${p.value}`
}
