import type { Filters } from '../types'

type FilterBarProps = {
  filters: Filters
  options: {
    companies: string[]
    years: string[]
    sectors: string[]
    categories: string[]
  }
  onChange: (name: keyof Filters, value: string) => void
  onReset: () => void
}

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: keyof Filters
  label: string
  value: string
  options: string[]
  onChange: (name: keyof Filters, value: string) => void
}) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(id, event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

export function FilterBar({
  filters,
  options,
  onChange,
  onReset,
}: FilterBarProps) {
  return (
    <section className="filter-bar">
      <div className="filter-grid">
        <SelectField
          id="company"
          label="Company"
          value={filters.company}
          options={options.companies}
          onChange={onChange}
        />
        <SelectField
          id="year"
          label="Year"
          value={filters.year}
          options={options.years}
          onChange={onChange}
        />
        <SelectField
          id="sector"
          label="Sector"
          value={filters.sector}
          options={options.sectors}
          onChange={onChange}
        />
        <SelectField
          id="category"
          label="Resolution category"
          value={filters.category}
          options={options.categories}
          onChange={onChange}
        />
      </div>
      <button className="ghost-button" onClick={onReset} type="button">
        Reset filters
      </button>
    </section>
  )
}
