export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'Not disclosed'
  }
  return `${value.toFixed(2)}%`
}

export function formatShortPercent(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'n/a'
  }
  return `${value.toFixed(1)}%`
}

export function formatDate(value: string) {
  return new Date(value).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function formatMonth(value: string) {
  return new Date(value).toLocaleDateString('en-GB', {
    month: 'short',
    year: 'numeric',
  })
}

export function formatCount(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'Not disclosed'
  }
  return value.toLocaleString('en-GB')
}
