import { useEffect, useRef } from 'react'
import { useFocusStore, type CopilotAction, type CopilotActionKind } from '../useFocusStore'

/**
 * Hook que consume `pendingAction` del store cuando coincide con `targetKind`.
 * El wizard activo (chart builder / ETL / script proposal) llama a `useCopilotAction(kind, onApply)`
 * para recibir la configuración que el Copilot ha dispatcheado.
 */
export function useCopilotAction(
  targetKind: CopilotActionKind,
  onApply: (action: CopilotAction) => void,
): void {
  const pendingAction = useFocusStore((s) => s.pendingAction)
  const clearPendingAction = useFocusStore((s) => s.clearPendingAction)
  const onApplyRef = useRef(onApply)
  onApplyRef.current = onApply

  useEffect(() => {
    if (pendingAction && pendingAction.kind === targetKind) {
      onApplyRef.current(pendingAction)
      clearPendingAction()
    }
  }, [pendingAction, targetKind, clearPendingAction])
}
