from typing import List, Dict, Any, Optional
import pandas as pd
from client_app.app.modules.privacy.anonymizer import AnonymizationContext, Entity
from dataclasses import dataclass
from client_app.app.services.enterprise_audit_service import enterprise_audit_service

@dataclass
class AnonymizationRule:
    method: str
    params: Dict[str, Any]
    entity_type_raw: str = "UNKNOWN"

class AnonymizationService:
    def __init__(self):
        self.ctx = AnonymizationContext()
        # In a real app we might inject encryption service here
        
    async def load_dataframe(self, file_path: str) -> pd.DataFrame:
        """Load DF from path (async wrapper if needed)."""
        # Simple loader, enhance with extensions check
        if file_path.endswith('.csv'):
             return pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
             return pd.read_excel(file_path)
        elif file_path.endswith('.json'):
             return pd.read_json(file_path)
        elif file_path.endswith('.parquet'):
             return pd.read_parquet(file_path)
        else:
             raise ValueError("Unsupported format")

    async def analyze_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze DF columns for PII."""
        # Use existing logic from AnonymizationContext.analyze_fields
        # It returns list of dicts with {'field', 'type', 'is_sensitive', 'confidence', 'recommended_strategy'}
        
        # We need to map it to what UI expects.
        # UI expects: 'column', 'entity_type', 'confidence_score', 'suggested_method'
        
        analysis = self.ctx.analyze_fields(df)
        results = []
        for item in analysis:
            results.append({
                'column': item['field'],
                'entity_type': item['type'],
                'confidence_score': item['confidence'],
                'suggested_method': self._map_strategy_to_method(item['recommended_strategy'], item['type']),
                'entity_type_raw': item['type'] # Preserve raw type for UI logic
            })
        return results

    def _map_strategy_to_method(self, strategy: str, entity_type: str) -> str:
        if strategy == 'none': return 'none'
        if entity_type == 'PERSON': return 'initials'
        if entity_type == 'ID': return 'aepd'
        if strategy == 'masking': return 'redact'
        if strategy == 'synthetic': return 'faker'
        return 'none'

    async def apply_anonymization(self, df: pd.DataFrame, config: Dict[str, AnonymizationRule]) -> pd.DataFrame:
        """Apply rules to DF."""
        # The underlying Anonymizer.anonymize_dataframe expects config as Dict[str, Dict]
        # Our config is Dict[str, AnonymizationRule]
        
        # Map config
        mapped_config = {}
        for col, rule in config.items():
            if rule.method == 'none': continue
             
            # Map method to what anonymize_dataframe expects
            # anonymize_dataframe checks 'type' and 'mode'
            
            # Note: The underlying anonymizer logic relies heavily on KNOWN types (DNI, PERSON, etc)
            # If we just say method='mask', we need to tell it WHAT it is to mask correctly?
            # Or does generic mask work? Yes _mask_generic handles types.
            
            # Ideally we should preserve the DETECTED type in the rule or config.
            # But the UI rule only has method/params.
            # We might need to re-detect or store the type in the rule?
            # Let's assume for now we don't have the type stored in rule, so we might lose specific masking
            # unless we re-infer or pass it.
            
            # Better approach: The UI should store the 'entity_type' in the rule or explicitly pass it.
            # For this fix, let's try to trust the column logic or use a default type if unknown.
            
            # Wait, AnonymizationContext.anonymize_dataframe iterates columns_config.
            # It expects config[col] to have 'type' and 'mode'.
            
            # We need to look up the type for this column.
            # Since we don't have it easily here without re-analyzing, 
            # we might default to "UNKNOWN" which triggers generic masking if mode is mask.
            
            mapped_config[col] = {
                "mode": self._map_method_to_mode(rule.method),
                "type": getattr(rule, 'entity_type_raw', "UNKNOWN") 
            }
            
            # If method is faker/synthetic, we want 'PERSON' or similar.
            # Let's try to infer efficiently or just use generic?
            # Anonymizer._mask_generic works on type.
            
            # Refinement: Let's assume we can re-infer type from header for better masking.
            inferred_type = self.ctx._analyze_header(col)
            if inferred_type:
                 mapped_config[col]["type"] = inferred_type

        result_df = self.ctx.anonymize_dataframe(df, mapped_config)

        # Registrar en auditoría RGPD (asíncrono, usar create_task para no bloquear)
        stats = self.ctx.get_stats()
        if stats.get('total_anonymized', 0) > 0 or len(config) > 0:
            try:
                # Contar tipos de PII procesados
                pii_types = {}
                for col, rule in config.items():
                    if rule.method != 'none':
                        entity_type = getattr(rule, 'entity_type_raw', 'UNKNOWN')
                        pii_types[entity_type] = pii_types.get(entity_type, 0) + 1

                import asyncio
                asyncio.create_task(enterprise_audit_service.log_pii_operation(
                    operation="ANONYMIZE",
                    pii_types=pii_types,
                    method="mixed",
                    module="anonymization_service",
                    source_description=f"DataFrame con {len(df)} filas, {len(config)} columnas procesadas"
                ))
            except Exception as e:
                print(f"[AnonymizationService] Error registrando auditoría: {e}")

        return result_df

    def _map_method_to_mode(self, method: str) -> str:
        if method == 'redact': return 'MASK'
        if method == 'initials': return 'INITIALS'
        if method == 'aepd': return 'AEPD'
        if method == 'hash': return 'HASH'
        if method == 'faker': return 'FAKER'
        return 'MASK'

    async def anonymize_text(self, text: str, allowed_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Anonimiza texto libre detectando PII con regex y NER.

        Args:
            text: Texto a anonimizar
            allowed_types: Si se provee, solo anonimiza entidades de este tipo.

        Returns:
            Dict con:
            - 'anonymized_text': texto anonimizado
            - 'mapping': (placeholder -> original)
            - 'detected_anchors': metadatos de etiquetas de formulario detectadas
            - 'form_structure_hint': descripción textual de la estructura para IA
        """
        if not text:
            return {"anonymized_text": "", "mapping": {}, "detected_anchors": [], "form_structure_hint": None}

        # Guardar estado previo del mapping para calcular el delta
        prev_fake_to_real = self.ctx.fake_to_real.copy()

        # Anonimizar usando el motor subyacente
        anonymized = self.ctx.anonymize(text, allowed_types=allowed_types)

        # Obtener anclas detectadas (etiquetas de formulario como "Nombre:", "Apellidos:")
        detected_anchors = self.ctx.get_detected_anchors()
        form_structure_hint = self.ctx.get_form_structure_hint()

        # Calcular entidades NUEVAS (no existían antes de este texto)
        # Estas son las que realmente se "protegen" por primera vez
        truly_new_entities = {
            fake: real
            for fake, real in self.ctx.fake_to_real.items()
            if fake not in prev_fake_to_real
        }

        # El mapping completo incluye tanto nuevas como reutilizadas (para retorno al llamador)
        new_mapping = truly_new_entities.copy()
        for fake, real in self.ctx.fake_to_real.items():
            if fake in anonymized and fake not in new_mapping:
                new_mapping[fake] = real

        # Registrar en auditoría RGPD SOLO las entidades REALMENTE NUEVAS
        # Esto evita inflar el conteo cuando la misma entidad aparece múltiples veces
        if truly_new_entities:
            try:
                # Clasificar tipos de PII encontrados (solo nuevas)
                pii_types = {}
                for placeholder in truly_new_entities.keys():
                    # Inferir tipo desde el nombre del placeholder
                    if 'email' in placeholder.lower():
                        pii_types['EMAIL'] = pii_types.get('EMAIL', 0) + 1
                    elif 'nombre' in placeholder.lower() or 'name' in placeholder.lower():
                        pii_types['PERSON'] = pii_types.get('PERSON', 0) + 1
                    elif 'dni' in placeholder.lower() or 'nif' in placeholder.lower():
                        pii_types['ID'] = pii_types.get('ID', 0) + 1
                    else:
                        pii_types['OTHER'] = pii_types.get('OTHER', 0) + 1

                import asyncio
                asyncio.create_task(enterprise_audit_service.log_pii_operation(
                    operation="ANONYMIZE",
                    pii_types=pii_types,
                    method="regex+faker",
                    module="anonymization_service",
                    source_description=f"Texto de {len(text)} caracteres, {len(truly_new_entities)} entidades nuevas"
                ))
            except Exception as e:
                print(f"[AnonymizationService] Error registrando auditoría texto: {e}")

        return {
            "anonymized_text": anonymized,
            "mapping": new_mapping,
            "detected_anchors": detected_anchors,
            "form_structure_hint": form_structure_hint
        }
