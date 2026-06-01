interface Props {
  announcement: string
}

export function BlockStateAnnouncer({ announcement }: Props) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    >
      {announcement}
    </div>
  )
}
