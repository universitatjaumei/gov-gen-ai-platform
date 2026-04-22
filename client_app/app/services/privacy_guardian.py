import re
from typing import Tuple, Dict

class PrivacyGuardian:
    """
    Security Barrier that intercepts text and redacts PII before it leaves the system.
    Connects to prompt 4 requirements.
    """
    
    def __init__(self):
        # Regex patterns for deterministic detection
        self.patterns = {
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # Simple global phone matcher (approximate)
            'PHONE': r'\+34\s?\d{3}\s?\d{3}\s?\d{3}|\b\d{9}\b', 
        }

    def anonymize(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replaces sensitive info with placeholders.
        Returns: (sanitized_text, mapping_dict)
        """
        mapping = {}
        sanitized_text = text
        
        # Redact Emails
        emails = re.findall(self.patterns['EMAIL'], text)
        for i, email in enumerate(set(emails), 1):
            placeholder = f"[EMAIL_{i}]"
            mapping[placeholder] = email
            sanitized_text = sanitized_text.replace(email, placeholder)
            
        # Redact Phones
        phones = re.findall(self.patterns['PHONE'], text)
        for i, phone in enumerate(set(phones), 1):
            placeholder = f"[PHONE_{i}]"
            mapping[placeholder] = phone
            sanitized_text = sanitized_text.replace(phone, placeholder)
            
        return sanitized_text, mapping

    def deanonymize(self, text: str, mapping: Dict[str, str]) -> str:
        """Restores original information from placeholders."""
        restored_text = text
        for placeholder, original in mapping.items():
            restored_text = restored_text.replace(placeholder, original)
        return restored_text
