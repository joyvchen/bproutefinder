interface BadgeTopPickProps {
  label?: string | null
  href?: string | null
  size?: 'sm' | 'md'
}

export default function BadgeTopPick({ label, href, size = 'md' }: BadgeTopPickProps) {
  const text = label || 'Top Pick'
  const base = 'inline-flex items-center gap-1 font-semibold rounded-full text-amber-800 bg-amber-100 border border-amber-200'
  const sizeClass = size === 'sm'
    ? 'text-[10px] px-1.5 py-0.5'
    : 'text-xs px-2 py-0.5'

  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className={`${base} ${sizeClass} hover:bg-amber-200`}
      >
        ⭐ {text}
      </a>
    )
  }

  return (
    <span className={`${base} ${sizeClass}`}>
      ⭐ {text}
    </span>
  )
}
