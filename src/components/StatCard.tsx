type StatCardProps = {
  label: string
  value: string
  note: string
}

export function StatCard({ label, value, note }: StatCardProps) {
  return (
    <article className="stat-card">
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
      <p className="stat-card__note">{note}</p>
    </article>
  )
}
