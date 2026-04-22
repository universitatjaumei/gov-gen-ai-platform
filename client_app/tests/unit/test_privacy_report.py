import pytest
from client_app.app.modules.privacy.anonymizer import AnonymizationContext

def test_privacy_stats_increments():
    ctx = AnonymizationContext()
    
    # Initial stats should be empty or zeroed
    stats = ctx.get_stats()
    assert all(count == 0 for count in stats.values()) or not stats

    # Anonymize some data
    ctx.anonymize("Mi DNI es 12345678Z y mi nombre es Juan Perez")
    
    stats = ctx.get_stats()
    assert stats.get("DNI", 0) == 1
    assert stats.get("PERSON_NAME", 0) == 1

def test_privacy_stats_no_leakage():
    ctx = AnonymizationContext()
    real_dni = "12345678Z"
    ctx.anonymize(f"DNI: {real_dni}")
    
    stats = ctx.get_stats()
    stats_str = str(stats)
    
    # Ensure real data is not in the stats dictionary values or keys (except if the key is the type)
    assert real_dni not in stats_str
    assert "12345678Z" not in stats_str

def test_privacy_stats_multiple_calls():
    ctx = AnonymizationContext()
    ctx.anonymize("DNI: 11111111A")
    ctx.anonymize("DNI: 22222222B")
    ctx.anonymize("Email: test@example.com")
    
    stats = ctx.get_stats()
    assert stats.get("DNI") == 2
    assert stats.get("EMAIL") == 1
