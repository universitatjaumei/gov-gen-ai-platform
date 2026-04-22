import pytest
from client_app.app.services.privacy_guardian import PrivacyGuardian

def test_anonymize_email():
    guardian = PrivacyGuardian()
    text = "Contact me at user@example.com for info."
    sanitized, mapping = guardian.anonymize(text)
    
    assert "user@example.com" not in sanitized
    assert "[EMAIL_1]" in sanitized
    assert mapping["[EMAIL_1]"] == "user@example.com"

def test_anonymize_phone():
    guardian = PrivacyGuardian()
    # Simple fake phone detection test
    text = "Call me at +34 600 123 456 now."
    sanitized, mapping = guardian.anonymize(text)
    
    assert "+34 600 123 456" not in sanitized
    assert "[PHONE_1]" in sanitized
    assert mapping["[PHONE_1]"] == "+34 600 123 456"

def test_deanonymize():
    guardian = PrivacyGuardian()
    text = "Please reply to [EMAIL_1]."
    mapping = {"[EMAIL_1]": "boss@company.com"}
    
    original = guardian.deanonymize(text, mapping)
    assert original == "Please reply to boss@company.com."
