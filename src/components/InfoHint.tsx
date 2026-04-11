type InfoHintProps = {
  label: string
  content: string
}

export function InfoHint({ label, content }: InfoHintProps) {
  return (
    <span className="info-hint">
      <button
        type="button"
        className="info-hint__button"
        aria-label={label}
        tabIndex={0}
      >
        i
      </button>
      <span className="info-hint__bubble" role="tooltip">
        {content}
      </span>
    </span>
  )
}
