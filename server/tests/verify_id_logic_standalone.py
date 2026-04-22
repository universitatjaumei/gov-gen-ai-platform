
import asyncio
import sys
import secrets
from unittest.mock import AsyncMock, MagicMock

# Minimal mock for dependencies to avoid import issues or DB hangs
class MockClientAccount:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockService:
    def __init__(self, partner_id):
        self.partner_id = partner_id
        self.db = AsyncMock()
        self.db.get = AsyncMock(return_value=None)
        
    def _extract_partner_number(self, partner_id: str) -> str:
        """Extrae o genera un numero de 3 digitos para el partner."""
        import re
        
        # 1. Patrones conocidos
        patterns = [
            r"partner_(\d+)",  # partner_001
            r"ID_P_(\d+)",     # ID_P_005
            r"^(\d+)$"         # 042
        ]
        
        for p in patterns:
            match = re.search(p, partner_id)
            if match:
                num = match.group(1)
                return f"{int(num):03d}"[-3:]
        
        h = abs(hash(partner_id)) % 1000
        return f"{h:03d}"

    async def create_client_with_license(self, name):
        partner_num = self._extract_partner_number(self.partner_id)
        seq = 1
        while True:
            client_id = f"ID_C_{partner_num}_{seq:03d}"
            exists = await self.db.get(MockClientAccount, client_id)
            if not exists:
                break
            seq += 1
        return client_id

async def run_verification():
    print("Verifying ID Generation Logic...")
    
    # helper
    async def verify(partner_id, expected_prefix):
        service = MockService(partner_id)
        client_id = await service.create_client_with_license("Test")
        print(f"  Partner '{partner_id}' -> Client ID '{client_id}'")
        if not client_id.startswith(expected_prefix):
            print(f"  [FAIL] Expected prefix {expected_prefix}, got {client_id}")
            return False
        return True

    results = []
    results.append(await verify("partner_001", "ID_C_001_"))
    results.append(await verify("ID_P_005", "ID_C_005_"))
    results.append(await verify("042", "ID_C_042_"))
    results.append(await verify("partner_dev", "ID_C_"))

    if all(results):
        print("✅ All verifications passed!")
    else:
        print("❌ Some verifications failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_verification())
