interface BadgeTopPickProps {
  score?: number
  size?: 'sm' | 'md'
}

export default function BadgeTopPick({ score = 0, size = 'md' }: BadgeTopPickProps) {
  const label = score >= 2 ? 'Editor Favorite' : 'Top Pick'
  const base = 'inline-flex items-center gap-1 font-semibold rounded-full text-amber-800 bg-amber-100 border border-amber-200'
  const sizeClass = size === 'sm'
    ? 'text-[10px] px-1.5 py-0.5'
    : 'text-xs px-2 py-0.5'

  return (
    <span className={`${base} ${sizeClass}`}>
      ⭐ {label}
    </span>
  )
}
