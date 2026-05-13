// KST / relative time utilities. Uses Intl in 'Asia/Seoul' tz; no external deps.

const KST_FMT_TIME = new Intl.DateTimeFormat('ko-KR', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: 'Asia/Seoul',
})

export function kstTime(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  return KST_FMT_TIME.format(d)
}

export function relativeFromNow(iso: string, now: Date = new Date()): string {
  const d = new Date(iso)
  const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (diffSec < 60) return '방금 전'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}분 전`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}시간 전`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 30) return `${diffDay}일 전`
  return d.toISOString().slice(0, 10)
}
