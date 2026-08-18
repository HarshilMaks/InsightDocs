import type { TaskStatus } from '@/types'

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  const units = ['KB', 'MB', 'GB', 'TB']
  let value = bytes / 1024
  let unitIndex = 0

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }

  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatRelativeTime(value: string): string {
  const diff = new Date(value).getTime() - Date.now()
  const abs = Math.abs(diff)

  const steps: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 1000 * 60 * 60 * 24 * 365],
    ['month', 1000 * 60 * 60 * 24 * 30],
    ['day', 1000 * 60 * 60 * 24],
    ['hour', 1000 * 60 * 60],
    ['minute', 1000 * 60],
    ['second', 1000],
  ]

  for (const [unit, size] of steps) {
    if (abs >= size || unit === 'second') {
      const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
      return formatter.format(Math.round(diff / size), unit)
    }
  }

  return 'just now'
}

export function formatStatus(status: TaskStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

export function formatPercentage(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function formatScore(score: number): string {
  return `${Math.max(0, Math.min(100, Math.round(score * 100)))}% match`
}

export function truncateText(value: string, maxLength = 120): string {
  if (value.length <= maxLength) {
    return value
  }

  return `${value.slice(0, maxLength - 1).trimEnd()}…`
}
