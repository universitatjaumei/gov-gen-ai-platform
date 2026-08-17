import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  useListActivityPrompts,
  useUpdateActivityPrompt,
  useResetActivityPrompt,
  getListActivityPromptsQueryKey,
} from '@/shared/api/generated/hub-activity-prompts/hub-activity-prompts'
import type { ActivityPromptOut } from '@/shared/api/generated/model'

/**
 * Biblioteca de prompts de las **actividades de plataforma** — PRO.2.1.
 *
 * La biblioteca que ya existía (`/hub/prompts`, `/hub/brain`) sólo veía prompts de chatbot,
 * porque su tabla cuelga de uno. Los de las actividades del módulo de Informes —escribir un
 * script, auditarlo— vivían en Python: no se podían afinar sin desplegar ni se podía elegir
 * con qué nivel de modelo corre cada una.
 *
 * Dos cosas que esta pantalla hace a propósito, copiadas del editor del legacy:
 *
 * - El selector de nivel tiene **cuatro** opciones, y la primera **dice cuál es el defecto**
 *   («Por defecto: nivel 2»). Un hueco vacío no se puede interpretar.
 * - El texto por defecto se muestra como marcador, **no se copia** a la caja. Copiarlo
 *   congelaría el prompt: a partir de ahí, mejorarlo en el código no llegaría aquí.
 */
const TIER_STYLES: Record<number, string> = {
  1: 'bg-green-100 text-green-800',
  2: 'bg-yellow-100 text-yellow-800',
  3: 'bg-red-100 text-red-800',
}

function VariablesDetectadas({ texto }: { texto: string }) {
  const { t } = useTranslation('admin')
  const encontradas = Array.from(new Set(texto.match(/\{\w+\}/g) ?? []))
  return (
    <p className="text-xs text-muted-foreground" data-testid="detected-vars">
      {t('hub.activity_prompts.detected_vars')}: {encontradas.length ? encontradas.join(', ') : '—'}
    </p>
  )
}

function ActividadCard({ actividad }: { actividad: ActivityPromptOut }) {
  const { t } = useTranslation('admin')
  const qc = useQueryClient()
  const guardar = useUpdateActivityPrompt()
  const restablecer = useResetActivityPrompt()

  const [tier, setTier] = useState<string>(
    actividad.override_tier != null ? String(actividad.override_tier) : '',
  )
  const [texto, setTexto] = useState<string>(actividad.template_text ?? '')

  function invalidar() {
    qc.invalidateQueries({ queryKey: getListActivityPromptsQueryKey() })
  }

  return (
    <div className="border rounded p-4 space-y-3 bg-card" data-testid={`activity-${actividad.activity}`}>
      <div className="flex items-center gap-2">
        <span className="font-medium text-sm">{actividad.activity}</span>
        <span className="text-xs text-muted-foreground">{actividad.purpose}</span>
        <span
          data-testid={`effective-tier-${actividad.activity}`}
          className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium ${
            TIER_STYLES[actividad.effective_tier] ?? 'bg-gray-100 text-gray-700'
          }`}
        >
          {t('hub.activity_prompts.tier')} {actividad.effective_tier}
          {' · '}
          {actividad.tier_source === 'override'
            ? t('hub.activity_prompts.source_override')
            : t('hub.activity_prompts.source_code')}
        </span>
      </div>

      <div className="space-y-1">
        <label className="text-xs text-muted-foreground" htmlFor={`tier-${actividad.activity}`}>
          {t('hub.activity_prompts.tier_label')}
        </label>
        <select
          id={`tier-${actividad.activity}`}
          data-testid={`tier-select-${actividad.activity}`}
          value={tier}
          onChange={e => setTier(e.target.value)}
          className="w-full text-sm border rounded px-2 py-1 bg-background"
        >
          <option value="">
            {t('hub.activity_prompts.tier_default', { tier: actividad.default_tier })}
          </option>
          <option value="1">{t('hub.activity_prompts.tier')} 1</option>
          <option value="2">{t('hub.activity_prompts.tier')} 2</option>
          <option value="3">{t('hub.activity_prompts.tier')} 3</option>
        </select>
      </div>

      <div className="space-y-1">
        <label className="text-xs text-muted-foreground" htmlFor={`text-${actividad.activity}`}>
          {t('hub.activity_prompts.text_label')}
        </label>
        <textarea
          id={`text-${actividad.activity}`}
          data-testid={`text-${actividad.activity}`}
          value={texto}
          onChange={e => setTexto(e.target.value)}
          rows={8}
          placeholder={actividad.default_template}
          className="w-full text-xs font-mono border rounded p-2"
        />
        <p className="text-xs text-muted-foreground">
          {t('hub.activity_prompts.empty_means_code')}
        </p>
        <VariablesDetectadas texto={texto || actividad.default_template} />
        <p className="text-xs text-muted-foreground">
          {t('hub.activity_prompts.available_vars')}:{' '}
          {actividad.variables.length ? actividad.variables.join(', ') : '—'}
        </p>
      </div>

      {guardar.isError && (
        <p className="text-xs text-red-700" data-testid={`error-${actividad.activity}`}>
          {t('hub.activity_prompts.save_failed')}
        </p>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          data-testid={`save-${actividad.activity}`}
          disabled={guardar.isPending}
          onClick={() =>
            guardar.mutate(
              {
                activity: actividad.activity,
                data: {
                  override_tier: tier ? Number(tier) : null,
                  template_text: texto.trim() ? texto : null,
                },
              },
              { onSuccess: invalidar },
            )
          }
          className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded disabled:opacity-50"
        >
          {t('hub.activity_prompts.save')}
        </button>
        <button
          type="button"
          data-testid={`reset-${actividad.activity}`}
          onClick={() =>
            restablecer.mutate(
              { activity: actividad.activity },
              {
                onSuccess: () => {
                  setTier('')
                  setTexto('')
                  invalidar()
                },
              },
            )
          }
          className="px-3 py-1 text-sm border rounded"
        >
          {t('hub.activity_prompts.reset')}
        </button>
      </div>
    </div>
  )
}

export function ActivityPromptsPage() {
  const { t } = useTranslation('admin')
  const { data: actividades, isPending } = useListActivityPrompts()

  return (
    <div className="space-y-4" data-testid="activity-prompts-page">
      <div>
        <h1 className="text-lg font-semibold">{t('hub.activity_prompts.title')}</h1>
        <p className="text-sm text-muted-foreground">{t('hub.activity_prompts.intro')}</p>
      </div>

      {isPending && <p className="text-sm text-muted-foreground">…</p>}

      {(actividades ?? []).map(actividad => (
        <ActividadCard key={actividad.activity} actividad={actividad} />
      ))}
    </div>
  )
}
