interface Props {
  section: string
}

export function PlaceholderPage({ section }: Props) {
  return (
    <div className="flex items-center justify-center h-full text-muted-foreground">
      <p>{section}</p>
    </div>
  )
}
