import DOMPurify from 'dompurify'

export interface TocEntry {
  level: number
  title: string
}

export interface PreviewBlock {
  block_id: string
  kind: string
  state: string
  html: string
  citations: string[]
}

export interface PreviewSection {
  level: number
  title: string
  blocks: PreviewBlock[]
}

export interface PreviewAuditEntry {
  chunk_id: string
  source_url: string | null
  source_filename: string | null
  page: number | null
  model_used: string | null
  prompt_version: string | null
  approvals: string[]
}

export interface PreviewPayload {
  workspace_id: string
  template_version_id: string
  cover: PreviewSection
  toc: TocEntry[]
  body: PreviewSection[]
  audit_annex: PreviewAuditEntry[]
  manifest_id: string
  generated_at: string
}

interface Props {
  payload: PreviewPayload
}

export function PreviewRenderer({ payload }: Props) {
  const citationIndex = _buildCitationIndex(payload)

  return (
    <article className="preview-root">
      <section data-preview-section="cover" className="preview-cover">
        <h1>{payload.cover.title}</h1>
        <p className="preview-meta">{new Date(payload.generated_at).toLocaleDateString()}</p>
      </section>

      <section data-preview-section="toc" className="preview-toc">
        <h2>Índice</h2>
        <ol>
          {payload.toc.map((entry, i) => (
            <li key={i} style={{ marginLeft: `${(entry.level - 1) * 1.5}rem` }}>
              {entry.title}
            </li>
          ))}
        </ol>
      </section>

      <section data-preview-section="body" className="preview-body">
        {payload.body.map((section, si) => (
          <div key={si} className="preview-section">
            <h2>{section.title}</h2>
            {section.blocks.map((block) => (
              <div key={block.block_id} className="preview-block">
                {_renderBlock(block, citationIndex)}
              </div>
            ))}
          </div>
        ))}
      </section>

      <section data-preview-section="audit-annex" className="preview-audit">
        <h2>Anexo de auditoría</h2>
        {payload.audit_annex.length === 0 ? (
          <p>Sin citas registradas.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Fuente</th>
                <th>Página</th>
                <th>Modelo</th>
                <th>Versión prompt</th>
              </tr>
            </thead>
            <tbody>
              {payload.audit_annex.map((entry, i) => (
                <tr key={entry.chunk_id} id={`audit-${entry.chunk_id}`}>
                  <td>{i + 1}</td>
                  <td>{entry.source_filename ?? entry.source_url ?? '—'}</td>
                  <td>{entry.page ?? '—'}</td>
                  <td>{entry.model_used ?? '—'}</td>
                  <td>{entry.prompt_version ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </article>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function _buildCitationIndex(payload: PreviewPayload): Map<string, number> {
  const index = new Map<string, number>()
  payload.audit_annex.forEach((entry, i) => {
    index.set(entry.chunk_id, i + 1)
  })
  return index
}

function _renderBlock(block: PreviewBlock, citationIndex: Map<string, number>) {
  const cleanHtml = DOMPurify.sanitize(block.html)

  return (
    <>
      <div dangerouslySetInnerHTML={{ __html: cleanHtml }} />
      {block.citations.length > 0 && (
        <span className="preview-citations">
          {block.citations.map((chunkId) => {
            const num = citationIndex.get(chunkId) ?? '?'
            return (
              <sup key={chunkId}>
                <a href={`#audit-${chunkId}`}>[{num}]</a>
              </sup>
            )
          })}
        </span>
      )}
    </>
  )
}
