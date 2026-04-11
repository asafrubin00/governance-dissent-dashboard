type StatCardProps = {
  label: string
  value: string
  note: string
  compact?: boolean
}

export function StatCard({ label, value, note, compact = false }: StatCardProps) {
  return (
    <article className={`stat-card ${compact ? 'stat-card--compact' : ''}`}>
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
      <p className="stat-card__note">{note}</p>
    </article>
  )
}
