// GoatCounter page-view analytics (https://www.goatcounter.com).
//
// Only the public GitHub Pages site is tracked: local dev, bundle.html opened from disk and
// the claude.ai preview load nothing. To stop counting your own visits, open the site once
// per browser with #toggle-goatcounter appended to the URL.

const GOATCOUNTER = "https://rayneyael.goatcounter.com"
const TRACKED_HOST = "rayneyael.github.io"

export const analyticsEnabled = typeof location !== "undefined" && location.hostname === TRACKED_HOST

export function loadAnalytics(): void {
  if (!analyticsEnabled || document.querySelector("script[data-goatcounter]")) return
  const s = document.createElement("script")
  s.async = true
  s.src = "https://gc.zgo.at/count.js"
  s.dataset.goatcounter = `${GOATCOUNTER}/count`
  document.head.appendChild(s)
}

/**
 * Site-wide visit count, formatted by GoatCounter (e.g. "1,234"), or null when unavailable
 * (not the tracked host, the counter setting is off, or the request fails). GoatCounter
 * caches this number for up to four hours.
 */
export async function fetchVisitCount(): Promise<string | null> {
  if (!analyticsEnabled) return null
  try {
    const res = await fetch(`${GOATCOUNTER}/counter/TOTAL.json`)
    if (!res.ok) return null
    const body: { count?: string } = await res.json()
    return body.count?.trim() || null
  } catch {
    return null
  }
}
