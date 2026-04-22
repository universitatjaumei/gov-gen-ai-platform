# client_app/app/modules/privacy/anonymizer.py
"""
Motor de anonimizacion hibrido (regex + NER spaCy) con persistencia cifrada.
"""
from dataclasses import dataclass
from typing import Any, List, Dict, Optional, TYPE_CHECKING
from pathlib import Path
import json
import re
from faker import Faker
import pandas as pd

if TYPE_CHECKING:
    from client_app.app.modules.security.encryption_service import EncryptionService

try:
    import spacy
    # Cambio a versión medium para mayor precisión en la utilidad manual
    _NLP = spacy.load("es_core_news_md")
except Exception as e:
    # Log de advertencia para el desarrollador/administrador
    print(f"[Anonymizer] Alerta: Modelo medium no encontrado. Fallback a None: {e}")
    _NLP = None


@dataclass
class Entity:
    """Representa una entidad detectada en el texto."""
    text: str
    type: str
    start: int
    end: int
    context: str = ""  # Contexto opcional (ej: etiqueta de formulario que precedía al valor)


class AnonymizationContext:
    """
    Motor de anonimizacion hibrido con persistencia cifrada.

    Estrategias:
    1. Regex: DNI, IBAN, Email, Telefono
    2. NER (spaCy): Nombres propios (PER)
    3. Persistencia: Mapa cifrado con Fernet

    Usage:
        ctx = AnonymizationContext()
        anon = ctx.anonymize("DNI: 12345678Z")
        original = ctx.deanonymize(anon)
    """

    PATTERNS = {
        "DNI": r"\b\d{1,2}(?:[\.\s]?\d{3}){2}[\-\s]?[A-Z]\b|\b\d{8}[\-\s]?[A-Z]\b",
        "EMAIL": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        "IBAN": r"\bES\d{22}\b",
        "PHONE": r"\b[6-9]\d{8}\b",
        "NIE": r"\b[XYZ]\d{7}[A-Z]\b",
        "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "NSS": r"\b\d{2}[/-]?\d{8}[/-]?\d{2}\b",
        "DATE": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "POSTAL_CODE": r"\b\d{5}\b",
    }

    def __init__(
        self,
        locale: str = "es_ES",
        encryption_service: Optional["EncryptionService"] = None
    ):
        """
        Inicializa el contexto de anonimizacion.

        Args:
            locale: Locale para Faker (default: es_ES)
            encryption_service: Servicio de cifrado para persistencia
        """
        self.faker = Faker(locale)
        self.fake_to_real: Dict[str, str] = {}
        self.real_to_fake: Dict[str, str] = {}  # Cache inverso para colisiones
        self.encryption_service = encryption_service
        self._nlp = _NLP
        self.stats: Dict[str, int] = {}
        # Almacén de anclas detectadas durante la anonimización (para contexto a IA)
        self._detected_anchors: List[Dict[str, Any]] = []

    def _detect_with_regex(self, text: str) -> List[Entity]:
        """Detecta entidades usando patrones regex."""
        entities: List[Entity] = []
        for typ, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text):
                entities.append(Entity(
                    text=match.group(0),
                    type=typ,
                    start=match.start(),
                    end=match.end()
                ))
        return entities

    # Palabras comunes que spaCy detecta erróneamente como nombres de persona
    _COMMON_WORDS_EXCLUSION = {
        # Sustantivos comunes
        'duración', 'duracion', 'título', 'titulo', 'nombre', 'apellido', 'apellidos',
        'cargo', 'puesto', 'dirección', 'direccion', 'provincia', 'municipio',
        'entidad', 'departamento', 'centro', 'facultad', 'universidad',
        'proyecto', 'resumen', 'palabras', 'clave', 'área', 'area', 'tipo',
        'código', 'codigo', 'referencia', 'administrativa', 'forma', 'ejecución', 'ejecucion',
        'individual', 'información', 'informacion', 'datos', 'contacto',
        # Meses y tiempo
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
        'años', 'meses', 'días', 'semanas', 'horas',
        # Otros términos técnicos
        'ministerio', 'ciencia', 'innovación', 'innovacion', 'universidades',
        'proyectos', 'generación', 'generacion', 'conocimiento', 'investigación', 'investigacion',
        'temática', 'tematica', 'secundaria', 'principal', 'subárea', 'subarea',
        'modalidad', 'orientada', 'carácter', 'caracter', 'multidisciplinar', 'interdisciplinar',
    }

    def _is_likely_person_name(self, text: str) -> bool:
        """
        Valida si un texto detectado como PER es realmente un nombre de persona.
        Filtra falsos positivos comunes de spaCy.
        """
        if not text or len(text.strip()) < 2:
            return False

        text_clean = text.strip()
        text_lower = text_clean.lower()

        # 1. Excluir palabras comunes
        if text_lower in self._COMMON_WORDS_EXCLUSION:
            return False

        # 2. Excluir si es una sola palabra común (sin mayúscula de nombre propio)
        words = text_clean.split()
        if len(words) == 1:
            # Una sola palabra: verificar que parezca un nombre propio
            # Debe empezar con mayúscula y tener más de 2 caracteres
            if not text_clean[0].isupper() or len(text_clean) < 3:
                return False
            # Excluir si está en la lista de exclusión
            if text_lower in self._COMMON_WORDS_EXCLUSION:
                return False

        # 3. Para múltiples palabras, verificar patrón de nombre
        # Al menos una palabra debe empezar con mayúscula
        has_proper_capitalization = any(w[0].isupper() for w in words if w)
        if not has_proper_capitalization:
            return False

        # 4. Excluir si todas las palabras son comunes
        non_common_words = [w for w in words if w.lower() not in self._COMMON_WORDS_EXCLUSION]
        if len(non_common_words) == 0:
            return False

        # 5. Verificar que no contenga solo números o caracteres especiales
        alpha_chars = sum(1 for c in text_clean if c.isalpha())
        if alpha_chars < len(text_clean) * 0.5:  # Al menos 50% letras
            return False

        return True

    def _detect_with_ner(self, text: str) -> List[Entity]:
        """Detecta entidades usando spaCy NER (ampliado) con filtrado de falsos positivos."""
        if not self._nlp:
            return []

        doc = self._nlp(text)
        entities = []
        for ent in doc.ents:
            if ent.label_ == "PER":
                # Filtrar falsos positivos para nombres de persona
                if self._is_likely_person_name(ent.text):
                    entities.append(Entity(
                        text=ent.text,
                        type="PERSON_NAME",
                        start=ent.start_char,
                        end=ent.end_char
                    ))
            elif ent.label_ == "LOC":
                entities.append(Entity(
                    text=ent.text,
                    type="ADDRESS",
                    start=ent.start_char,
                    end=ent.end_char
                ))
            elif ent.label_ == "ORG":
                entities.append(Entity(
                    text=ent.text,
                    type="ORGANIZATION",
                    start=ent.start_char,
                    end=ent.end_char
                ))
        return entities

    # Patrones de anclaje para formularios estructurados
    # Cada patrón captura: grupo(1)=etiqueta, grupo(2)=valor
    ANCHOR_PATTERNS = {
        # Nombre de pila
        "ANCHOR_FIRSTNAME": (
            r"(?i)(Nombre|Nom|First\s*Name|Nombre\s*de\s*pila)"
            r"\s*[:=]?\s*"
            r"([A-ZÁÉÍÓÚÑÀÈÌÒÙÇ][a-záéíóúñàèìòùç]+(?:\s+[A-ZÁÉÍÓÚÑÀÈÌÒÙÇ][a-záéíóúñàèìòùç]+)?)"
        ),
        # Apellidos
        "ANCHOR_LASTNAME": (
            r"(?i)(Apellidos?|Cognoms?|Surname|Last\s*Name|Primer\s*Apellido|Segundo\s*Apellido)"
            r"\s*[:=]?\s*"
            r"([A-ZÁÉÍÓÚÑÀÈÌÒÙÇ][a-záéíóúñàèìòùç]+(?:\s+[A-ZÁÉÍÓÚÑÀÈÌÒÙÇ][a-záéíóúñàèìòùç]+)?)"
        ),
        # Nombre completo (representante, contacto, etc.)
        "ANCHOR_FULLNAME": (
            r"(?i)(Representante\s*Legal|Contacto|Titular|Solicitante|Interesado|Firmante)"
            r"\s*[:=]?\s*"
            r"([A-ZÁÉÍÓÚÑÀÈÌÒÙÇ][a-záéíóúñàèìòùç]+(?:\s+[A-ZÁÉÍÓÚÑÀÈÌÒÙÇ][a-záéíóúñàèìòùç]+){1,4})"
        ),
    }

    def _detect_with_anchors(self, text: str) -> tuple[List[Entity], List[Dict[str, Any]]]:
        """
        Detecta nombres y apellidos basándose en etiquetas de formulario.

        Este método tiene PRIORIDAD sobre el NER general porque las etiquetas
        de formulario son indicadores deterministas de PII. El NER de spaCy
        puede fallar en contextos no gramaticales (celdas de formulario),
        pero "Nombre: Juan" siempre indica que "Juan" es un nombre.

        Returns:
            Tupla con:
            - Lista de entidades detectadas para anonimización
            - Lista de metadatos de anclas (para contexto a la IA programadora)
        """
        entities: List[Entity] = []
        anchor_metadata: List[Dict[str, Any]] = []

        for anchor_type, pattern in self.ANCHOR_PATTERNS.items():
            for match in re.finditer(pattern, text):
                label = match.group(1).strip()  # La etiqueta (ej: "Nombre", "Apellidos")
                captured_value = match.group(2).strip()  # El valor (ej: "Luis", "Pérez")

                # Validar que el valor capturado parece un nombre real
                if not captured_value or len(captured_value) < 2:
                    continue

                # Filtrar si es una palabra común (no un nombre propio)
                if not self._is_likely_person_name(captured_value):
                    continue

                # Determinar el tipo de entidad y el contexto para Faker
                if anchor_type == "ANCHOR_FIRSTNAME":
                    entity_type = "PERSON_NAME"
                    context = "nombre"
                    field_type = "firstname"
                elif anchor_type == "ANCHOR_LASTNAME":
                    entity_type = "PERSON_NAME"
                    context = "apellido"
                    field_type = "lastname"
                else:
                    entity_type = "PERSON_NAME"
                    context = "fullname"
                    field_type = "fullname"

                # Calcular offsets exactos del valor capturado
                start_offset = match.start(2)
                end_offset = match.end(2)

                entities.append(Entity(
                    text=captured_value,
                    type=entity_type,
                    start=start_offset,
                    end=end_offset,
                    context=context
                ))

                # Registrar metadatos del ancla para contexto a la IA
                anchor_metadata.append({
                    "label": label,
                    "label_normalized": label.lower().replace(" ", "_"),
                    "field_type": field_type,
                    "value_start": start_offset,
                    "value_end": end_offset,
                    "full_match_start": match.start(),
                    "full_match_end": match.end(),
                })

        return entities, anchor_metadata

    def _remove_overlapping_entities(
        self,
        priority_entities: List[Entity],
        secondary_entities: List[Entity]
    ) -> List[Entity]:
        """
        Filtra entidades secundarias que solapen con las de prioridad.

        Las entidades de ancla tienen prioridad porque son más específicas
        al formato del documento (etiquetas deterministas vs NER probabilístico).
        """
        result = []
        for sec in secondary_entities:
            overlaps = False
            for pri in priority_entities:
                # Verificar solapamiento: [pri.start, pri.end) ∩ [sec.start, sec.end) ≠ ∅
                if not (sec.end <= pri.start or sec.start >= pri.end):
                    overlaps = True
                    break
            if not overlaps:
                result.append(sec)
        return result

    def _generate_fake(self, entity_type: str, original: str, context: str = "") -> str:
        """
        Genera un valor falso consistente para un valor original.
        Usa persistencia para mantener consistencia.
        Context: nombre de columna para refinar generación (ej: "Nombre", "Apellidos")
        """
        if not original or pd.isna(original):
            return original
            
        # Check cache
        if original in self.real_to_fake:
            return self.real_to_fake[original]
            
        # Generar nuevo
        fake = ""
        attempts = 0
        while attempts < 10:
            if entity_type == "EMAIL":
                fake = self.faker.email()
            elif entity_type == "PHONE":
                fake = f"+34 {self.faker.phone_number()}"
            elif entity_type in ["DNI", "ID"]:
                 fake = self.faker.bothify(text='########?')
            elif entity_type == "NIE":
                 fake = self.faker.bothify(text='?#######?')
            elif entity_type == "PASSPORT":
                 fake = self.faker.bothify(text='???######')
            elif entity_type == "IBAN":
                fake = f"ES{self.faker.random_number(digits=22, fix_len=True)}"
            elif entity_type == "PERSON_NAME" or entity_type == "PERSON":
                # Check context for granularity
                ctx_lower = context.lower()
                if any(x in ctx_lower for x in ['apellido', 'surname', 'cognom']):
                    fake = self.faker.last_name()
                    if self.faker.random_int(0, 1):
                        fake += f" {self.faker.last_name()}"
                elif any(x in ctx_lower for x in ['nom', 'name', 'nombre']):
                    fake = self.faker.first_name()
                else:
                    fake = self.faker.name()
            elif entity_type == "CREDIT_CARD":
                fake = self.faker.credit_card_number(card_type=None)
            elif entity_type == "NSS":
                fake = self.faker.numerify("##/########/##")
            elif entity_type == "DATE":
                fake = self.faker.date_between(start_date="-80y", end_date="today").strftime("%d/%m/%Y")
            elif entity_type == "ADDRESS":
                fake = self.faker.address().replace("\n", ", ")
            elif entity_type == "POSTAL_CODE":
                fake = self.faker.postcode()
            elif entity_type == "ORGANIZATION":
                fake = self.faker.company()
            else:
                 # Default fallback if unknown type but requested fake
                 fake = self.faker.word() if not original[0].isdigit() else self.faker.numerify("####")

            # Verificar colision
            if fake not in self.fake_to_real:
                # Sin colision, registrar en ambos mapas
                self.fake_to_real[fake] = original
                self.real_to_fake[original] = fake
                
                # Incrementar estadisticas
                self.stats[entity_type] = self.stats.get(entity_type, 0) + 1
                
                return fake

        # Si despues de 10 intentos sigue colisionando, anadir sufijo
        fake_with_suffix = f"{fake}_{len(self.fake_to_real)}"
        self.fake_to_real[fake_with_suffix] = original
        self.real_to_fake[original] = fake_with_suffix
        
        # Incrementar estadisticas
        self.stats[entity_type] = self.stats.get(entity_type, 0) + 1
        
        return fake_with_suffix

    def _mask_generic(self, entity_type: str, value: str) -> str:
        """
        Enmascara valores genericamente.
        """
        if not value: return value
        s = str(value)
        l = len(s)
        
        if entity_type == "EMAIL":
            # j***@g***.com
            parts = s.split('@')
            if len(parts) != 2: return "*" * l
            user, domain = parts
            
            u_shown = user[:1] + "*" * (len(user)-1) if len(user)>1 else user
            d_parts = domain.split('.')
            if len(d_parts) >= 2:
                 d_shown = d_parts[0][:1] + "*" * (len(d_parts[0])-1) + "." + d_parts[-1]
            else:
                 d_shown = "*" * len(domain)
            return f"{u_shown}@{d_shown}"
            
        elif entity_type == "PHONE":
            # 6********
            if l <= 3: return "*" * l
            return s[:2] + "*" * (l-2)
            
        elif entity_type == "PERSON_NAME" or entity_type == "ORGANIZATION" or entity_type == "ADDRESS":
            # First char of each word
            words = s.split()
            masked_words = []
            for w in words:
                if len(w) > 1:
                     masked_words.append(w[0] + "*" * (len(w)-1))
                else:
                     masked_words.append(w)
            return " ".join(masked_words)
            
        elif entity_type == "IBAN" or entity_type == "CREDIT_CARD":
            # Show last 4
            if l <= 4: return "*" * l
            return "*" * (l-4) + s[-4:]
            
        else:
            # Default
            return "*" * l

    def anonymize_document_id(self, value: str, mode: str = 'MASK') -> str:
        """
        Anonimiza un documento de identidad (DNI, NIE, Pasaporte, etc).
        
        Args:
            value: Valor del documento (str)
            mode: 'MASK' (default, *********) o 'AEPD' (Criterio LOPDGDD)
            
        Returns:
            Valor anonimizado
        """
        if not value: return value
        
        if mode == 'MASK':
            # Mascara completa con asteriscos (misma longitud o fija)
            # El usuario pidio "*******"
            return "*" * len(value) if len(value) > 4 else "*********"
            
        elif mode == 'AEPD':
            # Lógica AEPD (Disposición Adicional Séptima LOPDGDD)
            
            # Limpiar valor para análisis (opcional, pero las reglas hablan de posiciones sobre el formato original)
            # Reglas estrictas sobre el string proporcionado.
            
            s = value
            length = len(s)
            
            # Detectar tipo (heurística simple basada en formato)
            # DNI: 8 dígitos + Letra (aprox 9 chars). Ejemplo: 12345678X
            # NIE: Letra + 7 dígitos + Letra (aprox 9 chars). Ejemplo: L1234567X
            # Pasaporte: 3 Letras + 6 dígitos? Ejemplo: ABC123456 (9 chars)
            # El prompt da ejemplos explicitos.
            
            is_nie = False
            is_passport = False
            
            # Check NIE (Starts with X, Y, Z usually, but example says 'L')
            # Regex simple para NIE: ^[A-Z]\d{7}[A-Z]$
            if re.match(r'^[A-Z]\d{7}[A-Z]$', s):
                is_nie = True
            
            # Check Passport (Example ABC123456: 3 letters + 6 digits)
            # Regex: ^[A-Z]{3}\d{6}$
            elif re.match(r'^[A-Z]{3}\d{6}$', s):
                is_passport = True
                
            # Check DNI (8 digits + 1 letter)
            # Regex: ^\d{8}[A-Z]$
            # Ojo: tratamos como DNI si no es NIE ni pasaporte y tiene formato compatible
            
            chars = list(s)
            
            if is_passport:
                # Caso Pasaporte: ABC123456
                # "evitando los tres caracteres alfabéticos, tercera, cuarta, quinta y sexta [de los digitos]"
                # Digitos son 123456 (indices 3,4,5,6,7,8 en string 0-indexed)
                # "tercera, cuarta, quinta y sexta" de los dígitos...
                # Dígitos: 1(1º), 2(2º), 3(3º), 4(4º), 5(5º), 6(6º)
                # Queremos mostrar 3º, 4º, 5º, 6º. -> 3, 4, 5, 6.
                # En el string original indices: 5('3'), 6('4'), 7('5'), 8('6')
                # Por tanto, mostramos los ultimos 4 caracteres.
                # El ejemplo dice: *****3456
                # ABC123456 -> *****3456
                # Indices visibles: 5,6,7,8.
                # Logica generalizada: mostrar los ultimos 4 caracteres si len=9?
                # Vamos a seguir la logica de "evitar caracteres alfabeticos"
                
                # Indices de digitos
                digit_indices = [i for i, c in enumerate(s) if c.isdigit()]
                
                # Si tenemos al menos 6 digitos, mostramos del 3er al 6to digito (indices relativos 2,3,4,5)
                # Wait, el ejemplo *****3456 muestra 4 digitos. '3456'.
                # Digitos encontrados: 1, 2, 3, 4, 5, 6
                # Indices array digitos: 0, 1, 2, 3, 4, 5
                # Mostramos indices: 2, 3, 4, 5.
                # Exacto. Indices 3º, 4º, 5º, 6º (human-readable) -> indices array 2,3,4,5.
                
                to_show_indices = set()
                if len(digit_indices) >= 6:
                     # Tomar indices 2,3,4,5 de la lista de digitos
                     subset = digit_indices[2:6] 
                     to_show_indices.update(subset)
                     
                return "".join([c if i in to_show_indices else '*' for i, c in enumerate(s)])

            elif is_nie:
                 # Caso NIE: L1234567X
                 # "evitando el primer carácter alfabético... [digitos] cuarta, quinta, sexta y séptima."
                 # Digitos: 1, 2, 3, 4, 5, 6, 7
                 # Posiciones 4, 5, 6, 7.
                 # Indices array digitos: 3, 4, 5, 6.
                 # Digitos a mostrar: 4, 5, 6, 7.
                 # Ejemplo: ****4567*
                 # L1234567X
                 # Visible: 4567. Correcto.
                 
                 digit_indices = [i for i, c in enumerate(s) if c.isdigit()]
                 
                 to_show_indices = set()
                 if len(digit_indices) >= 7:
                     subset = digit_indices[3:7] # Indices 3,4,5,6
                     to_show_indices.update(subset)
                     
                 return "".join([c if i in to_show_indices else '*' for i, c in enumerate(s)])
                 
            else:
                # Caso Genérico / DNI / Otros
                # "Dado otro tipo de identificación, siempre que esa identificación contenga al menos 7 dígitos numéricos..."
                # "...se numerarán dichos dígitos de izquierda a derecha, evitando todos los caracteres alfabéticos..."
                # "...y se publicarán aquellos caracteres numéricos que ocupen las posiciones cuarta, quinta, sexta y séptima."
                
                # Caso DNI: 12345678X. 8 digitos.
                # Pos 4,5,6,7 -> Digitos 4,5,6,7.
                # Indices array digitos: 3,4,5,6.
                # 1(0) 2(1) 3(2) 4(3) 5(4) 6(5) 7(6) 8(7)
                # Mostramos digitos 4,5,6,7.
                # Ejemplo DNI: ***4567** -> Correcto.
                
                digit_indices = [i for i, c in enumerate(s) if c.isdigit()]
                
                if len(digit_indices) >= 7:
                    # Logica standard >= 7 digitos
                    to_show_indices = set()
                    if len(digit_indices) >= 7:
                        subset = digit_indices[3:7] # Indices 3,4,5,6
                        to_show_indices.update(subset)
                    return "".join([c if i in to_show_indices else '*' for i, c in enumerate(s)])
                    
                else:
                    # Caso corto (< 7 digitos numericos)
                    # "se numerarán todos los caracteres, alfabéticos incluidos... se seleccionarán aquellos que ocupen las cuatro últimas posiciones."
                    # ABCD123XY (9 chars) -> *****23XY (last 4 chars)
                    
                    if length <= 4:
                        return s  # If shorter than 4 chars, show all (no masking possible)

                    # Show last 4 chars
                    # Example: *****23XY
                    return '*' * (length - 4) + s[-4:]

        return value

    def anonymize_name(self, value: str, mode: str = 'MASK') -> str:
        """
        Anonimiza un nombre de persona.
        
        Args:
            value: Nombre completo (str)
            mode: 'MASK' (default, asteriscos) o 'INITIALS' (iniciales)
            
        Returns:
            Valor anonimizado
        """
        if not value: return value
        
        if mode == 'MASK':
             return self._mask_generic("PERSON_NAME", value)
             
        elif mode == 'INITIALS':
             # Convertir "Juan Pérez" -> "J. P."
             parts = [p.strip()[0] + '.' for p in value.split() if p.strip()]
             return " ".join(parts)
             
        # Fallback
        return self._mask_generic("PERSON_NAME", value)

    def anonymize_dataframe(self, df: pd.DataFrame, columns_config: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        Anonimiza un DataFrame segun la configuracion de columnas.
        """
        result_df = df.copy()
        
        for col, config in columns_config.items():
            if col not in result_df.columns:
                continue
                
            entity_type = config.get("type", "UNKNOWN")
            mode = config.get("mode", "FAKER") # Default FAKER if not specified
            
            # 1. DNI Special Handling
            if entity_type in ["DNI", "NIE", "PASSPORT", "ID"]:
                # DNI always supports MASK (std) or AEPD (special mask) or FAKER
                if mode in ['MASK', 'AEPD']:
                     result_df[col] = result_df[col].astype(str).apply(lambda x: self.anonymize_document_id(x, mode=mode))
                else:
                     # Faker
                     result_df[col] = result_df[col].astype(str).apply(lambda x: self._generate_fake(entity_type, x, context=col))
            
            elif mode == 'MASK':
                # Generic Masking for all other types
                result_df[col] = result_df[col].astype(str).apply(lambda x: self._mask_generic(entity_type, x))
                
            elif entity_type in ["PERSON_NAME", "PERSON"]:
                if mode == 'INITIALS':
                    result_df[col] = result_df[col].astype(str).apply(lambda x: self.anonymize_name(x, mode='INITIALS'))
                else:
                    # Default: Faker
                    result_df[col] = result_df[col].astype(str).apply(lambda x: self._generate_fake("PERSON_NAME", x, context=col))
                
            elif entity_type == "EMAIL":
                result_df[col] = result_df[col].astype(str).apply(lambda x: self._generate_fake("EMAIL", x, context=col))
                
            elif entity_type == "PHONE":
                result_df[col] = result_df[col].astype(str).apply(lambda x: self._generate_fake("PHONE", x, context=col))
                
            elif entity_type == "IBAN":
                result_df[col] = result_df[col].astype(str).apply(lambda x: self._generate_fake("IBAN", x, context=col))
                
            else:
                # Fallback general usando deteccion automatica (mas lento)
                # Si es un tipo conocido pero sin handler especifico (ej ADDRESS), usa _generate_fake
                if entity_type in self.PATTERNS or entity_type in ["ADDRESS", "ORGANIZATION"]:
                     result_df[col] = result_df[col].astype(str).apply(lambda x: self._generate_fake(entity_type, x, context=col))
                else:
                    # Auto detection fallback
                    result_df[col] = result_df[col].astype(str).apply(self.anonymize)
                
        return result_df



    def anonymize(self, data: Any, allowed_types: Optional[List[str]] = None) -> Any:
        """
        Anonimiza texto usando regex + NER. Soporta estructuras recursivas.

        Args:
            data: Texto o estructura (dict/list) a anonimizar
            allowed_types: Si se provee, solo anonimiza entidades de este tipo. 
                           Por defecto, anonimiza un subconjunto seguro para LLM.

        Returns:
            Datos anonimizados
        """
        if allowed_types is None:
            allowed_types = ["PERSON_NAME", "EMAIL", "DNI", "NIE", "PHONE", "PASSPORT"]

        if isinstance(data, dict):
            return {k: self.anonymize(v, allowed_types) for k, v in data.items()}
        if isinstance(data, list):
            return [self.anonymize(item, allowed_types) for item in data]
        
        if not isinstance(data, str):
            return data

        text = data

        # 1. Detectar con ANCLAS primero (prioridad máxima para formularios)
        #    Retorna tupla: (entidades, metadatos de anclas para contexto IA)
        anchor_entities, anchor_metadata = self._detect_with_anchors(text)

        # Almacenar metadatos de anclas para que la IA programadora tenga contexto
        # sobre la estructura real del formulario
        self._detected_anchors.extend(anchor_metadata)

        # 2. Detectar con regex y NER
        regex_ner_entities = self._detect_with_regex(text) + self._detect_with_ner(text)

        # 3. Filtrar entidades regex/NER que solapen con las de ancla
        #    Las anclas son deterministas y más fiables en formularios
        non_overlapping = self._remove_overlapping_entities(anchor_entities, regex_ner_entities)

        # 4. Combinar: anclas + (regex/NER sin solapamientos)
        entities = anchor_entities + non_overlapping

        if allowed_types is not None:
            entities = [e for e in entities if e.type in allowed_types]

        # Ordenar por offset descendente para reemplazos seguros
        entities.sort(key=lambda e: e.start, reverse=True)

        result = text
        for entity in entities:
            # Usar el contexto de la entidad (si viene de ancla) para generar datos coherentes
            fake = self._generate_fake(entity.type, entity.text, context=entity.context)
            result = result[:entity.start] + fake + result[entity.end:]

        return result

    def deanonymize(self, data: Any) -> Any:
        """
        Desanonimiza datos recursivamente.

        Args:
            data: Datos anonimizados (str, dict, o list)

        Returns:
            Datos con valores originales restaurados
        """
        if isinstance(data, str):
            result = data
            for fake, real in self.fake_to_real.items():
                result = result.replace(fake, real)
            return result

        if isinstance(data, dict):
            return {k: self.deanonymize(v) for k, v in data.items()}

        if isinstance(data, list):
            return [self.deanonymize(item) for item in data]

        return data

    def save_state(self, path: Path):
        """
        Persiste el mapa de forma CIFRADA.

        Args:
            path: Ruta donde guardar el mapa cifrado
        """
        if self.encryption_service:
            # El EncryptionService existente trabaja con Dict
            encrypted = self.encryption_service.encrypt(self.fake_to_real)
            path.write_text(encrypted, encoding='utf-8')
        else:
            # Fallback sin cifrado (solo para dev)
            data = json.dumps(self.fake_to_real, ensure_ascii=False)
            path.write_text(data, encoding='utf-8')

    def load_state(self, path: Path):
        """
        Carga el mapa cifrado.

        Args:
            path: Ruta del archivo con el mapa cifrado
        """
        if not path.exists():
            return

        try:
            content = path.read_text(encoding='utf-8')

            if self.encryption_service:
                # Descifrar usando EncryptionService
                self.fake_to_real = self.encryption_service.decrypt(content)
            else:
                self.fake_to_real = json.loads(content)

            # Reconstruir cache inverso
            self.real_to_fake = {v: k for k, v in self.fake_to_real.items()}

        except Exception as e:
            # No crashear si el archivo esta corrupto
            print(f"Warning: Could not load anonymization map: {e}")
            self.fake_to_real = {}
            self.real_to_fake = {}

    def get_stats(self) -> Dict[str, int]:
        """Retorna las estadisticas de entidades anonimizadas en esta sesion."""
        return self.stats.copy()

    def get_detected_anchors(self) -> List[Dict[str, Any]]:
        """
        Retorna los metadatos de las anclas de formulario detectadas.

        Esta información es útil para dar contexto a la IA programadora
        sobre la estructura real del documento. Por ejemplo, si el documento
        tiene etiquetas separadas "Nombre:" y "Apellidos:", esta función
        devolverá esa información para que la IA pueda generar scripts
        que extraigan ambos campos y los concatenen correctamente.

        Returns:
            Lista de diccionarios con metadatos de cada ancla detectada:
            - label: Etiqueta original (ej: "Nombre", "Apellidos")
            - label_normalized: Etiqueta normalizada (ej: "nombre", "apellidos")
            - field_type: Tipo de campo ("firstname", "lastname", "fullname")
            - value_start/value_end: Offsets del valor en el texto
            - full_match_start/full_match_end: Offsets del match completo

        Example:
            >>> ctx = AnonymizationContext()
            >>> ctx.anonymize("Nombre: Luis Apellidos: Pérez Martínez")
            >>> ctx.get_detected_anchors()
            [
                {"label": "Nombre", "field_type": "firstname", ...},
                {"label": "Apellidos", "field_type": "lastname", ...}
            ]
        """
        return self._detected_anchors.copy()

    def clear_detected_anchors(self) -> None:
        """Limpia las anclas detectadas (útil al procesar múltiples documentos)."""
        self._detected_anchors = []

    def get_form_structure_hint(self) -> Optional[str]:
        """
        Genera una descripción textual de la estructura del formulario
        basada en las anclas detectadas, para inyectar como contexto al LLM.

        Returns:
            Texto descriptivo de la estructura o None si no hay anclas.

        Example:
            >>> ctx.get_form_structure_hint()
            "ESTRUCTURA DEL FORMULARIO DETECTADA:
             - Etiqueta 'Nombre:' contiene nombre de pila
             - Etiqueta 'Apellidos:' contiene apellidos
             NOTA: Si se solicita 'Nombre y Apellidos' como campo único,
             extraer ambas etiquetas y concatenar."
        """
        if not self._detected_anchors:
            return None

        # Agrupar por tipo de campo
        firstname_labels = []
        lastname_labels = []
        fullname_labels = []

        for anchor in self._detected_anchors:
            label = anchor.get("label", "")
            field_type = anchor.get("field_type", "")

            if field_type == "firstname":
                firstname_labels.append(label)
            elif field_type == "lastname":
                lastname_labels.append(label)
            elif field_type == "fullname":
                fullname_labels.append(label)

        # Generar descripción
        lines = ["ESTRUCTURA DEL FORMULARIO DETECTADA:"]

        if firstname_labels:
            unique_labels = list(dict.fromkeys(firstname_labels))  # Preservar orden, eliminar duplicados
            for lbl in unique_labels:
                lines.append(f"  - Etiqueta '{lbl}:' contiene NOMBRE DE PILA")

        if lastname_labels:
            unique_labels = list(dict.fromkeys(lastname_labels))
            for lbl in unique_labels:
                lines.append(f"  - Etiqueta '{lbl}:' contiene APELLIDOS")

        if fullname_labels:
            unique_labels = list(dict.fromkeys(fullname_labels))
            for lbl in unique_labels:
                lines.append(f"  - Etiqueta '{lbl}:' contiene NOMBRE COMPLETO")

        # Añadir nota si hay nombre y apellidos separados
        if firstname_labels and lastname_labels:
            lines.append("")
            lines.append("IMPORTANTE: El formulario tiene NOMBRE y APELLIDOS en campos SEPARADOS.")
            lines.append("Si el usuario solicita 'Nombre y Apellidos' o 'Nombre completo' como")
            lines.append("campo único, DEBES:")
            lines.append("  1. Extraer el valor de la etiqueta de nombre (ej: 'Nombre:')")
            lines.append("  2. Extraer el valor de la etiqueta de apellidos (ej: 'Apellidos:')")
            lines.append("  3. Concatenar ambos valores con un espacio: '{nombre} {apellidos}'")

        return "\n".join(lines)

    def _analyze_header(self, col_name: str) -> Optional[str]:
        """
        Analiza el nombre de la columna para inferir tipos sensibles.
        Heurística simple y eficiente para listas sin contexto.
        """
        name_lower = col_name.lower().strip()
        
        # Mapeo de términos comunes a tipos PII
        heuristics = {
            "PERSON_NAME": ["nombre", "name", "nom", "cognom", "apellido", "firstname", "lastname", "fullname", "cliente", "empleado", "usuario"],
            "EMAIL": ["email", "correo", "mail", "e-mail"],
            "PHONE": ["telefono", "phone", "movil", "celular", "tel"],
            "DNI": ["dni", "nif", "documento", "identificacion", "id_card"],
            "NIE": ["nie"],
            "IBAN": ["iban", "cuenta", "banco", "ccc"],
            "ADDRESS": ["direccion", "domicilio", "calle", "address", "ciudad", "poblacion", "cp", "postal"],
            "CREDIT_CARD": ["tarjeta", "card", "cc_num"]
        }
        
        for pii_type, keywords in heuristics.items():
            if any(k in name_lower for k in keywords):
                return pii_type
        return None

    def analyze_fields(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Analiza las columnas de un DataFrame para detectar PII y recomendar estrategias.
        
        Args:
            df: DataFrame a analizar.
            
        Returns:
            Lista de diccionarios con la clasificación y estrategia recomendada por cada campo.
        """
        results = []
        sample_size = min(len(df), 10)
        sample_df = df.head(sample_size)

        for col in df.columns:
            findings = []
            
            # 1. Heurística de Cabecera (Prioridad alta para boosting)
            header_type = self._analyze_header(str(col))
            if header_type:
                # Añadimos peso extra a lo encontrado por cabecera
                findings.extend([header_type] * 3)

            # 2. Análisis de Contenido
            for value in sample_df[col].dropna().astype(str):
                # Usar regex y NER para detectar entidades
                entities = self._detect_with_regex(value) + self._detect_with_ner(value)
                for ent in entities:
                    findings.append(ent.type)

            # Clasificación simple basada en hallazgos
            detected_type = "NONE"
            confidence = 0.0
            if findings:
                # Contar ocurrencias de cada tipo
                counts = {}
                for f in findings:
                    counts[f] = counts.get(f, 0) + 1
                
                # Elegir el tipo más frecuente
                best_type = max(counts, key=counts.get)
                # Map internal types to user-friendly types
                type_map = {
                    "EMAIL": "EMAIL",
                    "PERSON_NAME": "PERSON",
                    "DNI": "ID",
                    "NIE": "ID",
                    "PASSPORT": "ID",
                    "PHONE": "ID",
                    "IBAN": "ID",
                    "CREDIT_CARD": "ID"
                }
                detected_type = type_map.get(best_type, "NONE")
                
                # Calcular confianza (ajustada si vino por cabecera)
                total_samples = sample_size + (3 if header_type else 0)
                confidence = counts[best_type] / total_samples if total_samples > 0 else 0.0

            # Recomendar estrategia
            strategy = "none"
            if detected_type in ["EMAIL", "ID"]:
                strategy = "masking"
            elif detected_type == "PERSON":
                strategy = "synthetic"

            results.append({
                'field': col,
                'type': detected_type,
                'is_sensitive': detected_type != "NONE",
                'confidence': min(confidence, 1.0),
                'recommended_strategy': strategy
            })

        return results


if __name__ == "__main__":
    # Test unitario rápido
    import pandas as pd
    
    ctx = AnonymizationContext()
    data = {
        "Nombre": ["Juan Pérez", "María García", "Carlos Ruiz"],
        "Apellidos": ["García", "López", "Martínez"],
        "Ventas": [100.5, 200.0, 150.75],
        "Correo": ["juan@example.com", "maria@gmail.com", None]
    }
    df_test = pd.DataFrame(data)
    
    analysis = ctx.analyze_fields(df_test)
    
    print("Resultados del análisis:")
    for res in analysis:
        print(res)
        
    # Validaciones solicitadas
    nombre_res = next(r for r in analysis if r['field'] == "Nombre")
    apellidos_res = next(r for r in analysis if r['field'] == "Apellidos")
    ventas_res = next(r for r in analysis if r['field'] == "Ventas")
    
    assert nombre_res['is_sensitive'] is True, "Nombre debería ser sensible"
    assert apellidos_res['is_sensitive'] is True, "Apellidos debería ser sensible"
    assert ventas_res['is_sensitive'] is False, "Ventas NO debería ser sensible"
    assert nombre_res['recommended_strategy'] == "synthetic", "Nombre debería recomendar 'synthetic'"
    
    print("\n¡Tests pasados exitosamente!")
