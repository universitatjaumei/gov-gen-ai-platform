
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from automatia_shared.enums import ScreenshotPolicyEnum


class TestScreenshotGuardAction:
    """Tests para el enum de acciones del guard."""

    def test_action_enum_values(self):
        from client_app.app.services.screenshot_guard import ScreenshotGuardAction

        assert ScreenshotGuardAction.ALLOW.value == "ALLOW"
        assert ScreenshotGuardAction.REQUIRE_REVIEW.value == "REQUIRE_REVIEW"
        assert ScreenshotGuardAction.BLOCK.value == "BLOCK"


class TestScreenshotGuard:
    """Tests para el servicio ScreenshotGuard."""

    @pytest.fixture
    def mock_policy_block(self):
        """Mock de SecurityPolicy con BLOCK."""
        policy = MagicMock()
        policy.screenshot_policy = ScreenshotPolicyEnum.BLOCK.value
        policy.trusted_screenshot_domains = "[]"
        return policy

    @pytest.fixture
    def mock_policy_review(self):
        """Mock de SecurityPolicy con REVIEW."""
        policy = MagicMock()
        policy.screenshot_policy = ScreenshotPolicyEnum.REVIEW.value
        policy.trusted_screenshot_domains = "[]"
        return policy

    @pytest.fixture
    def mock_policy_trusted(self):
        """Mock de SecurityPolicy con TRUSTED y dominios."""
        policy = MagicMock()
        policy.screenshot_policy = ScreenshotPolicyEnum.TRUSTED.value
        policy.trusted_screenshot_domains = json.dumps(["boe.es", "sede.agenciatributaria.gob.es"])
        return policy

    @pytest.mark.asyncio
    async def test_block_policy_returns_block_action(self, mock_policy_block):
        """Política BLOCK siempre retorna BLOCK, independiente del dominio."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard, ScreenshotGuardAction

        guard = ScreenshotGuard()
        with patch.object(guard, '_get_active_policy', new_callable=AsyncMock, return_value=mock_policy_block):
            action = await guard.check_policy("https://cualquier-sitio.com/page")
            assert action == ScreenshotGuardAction.BLOCK

    @pytest.mark.asyncio
    async def test_review_policy_returns_require_review(self, mock_policy_review):
        """Política REVIEW siempre retorna REQUIRE_REVIEW."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard, ScreenshotGuardAction

        guard = ScreenshotGuard()
        with patch.object(guard, '_get_active_policy', new_callable=AsyncMock, return_value=mock_policy_review):
            action = await guard.check_policy("https://cualquier-sitio.com/page")
            assert action == ScreenshotGuardAction.REQUIRE_REVIEW

    @pytest.mark.asyncio
    async def test_trusted_policy_allows_whitelisted_domain(self, mock_policy_trusted):
        """Política TRUSTED permite dominios en whitelist."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard, ScreenshotGuardAction

        guard = ScreenshotGuard()
        with patch.object(guard, '_get_active_policy', new_callable=AsyncMock, return_value=mock_policy_trusted):
            action = await guard.check_policy("https://boe.es/diario_boe/txt.php?id=123")
            assert action == ScreenshotGuardAction.ALLOW

    @pytest.mark.asyncio
    async def test_trusted_policy_requires_review_for_unknown_domain(self, mock_policy_trusted):
        """Política TRUSTED requiere revisión para dominios no whitelisted."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard, ScreenshotGuardAction

        guard = ScreenshotGuard()
        with patch.object(guard, '_get_active_policy', new_callable=AsyncMock, return_value=mock_policy_trusted):
            action = await guard.check_policy("https://banco-privado.com/cuenta")
            assert action == ScreenshotGuardAction.REQUIRE_REVIEW

    @pytest.mark.asyncio
    async def test_trusted_matches_subdomain(self, mock_policy_trusted):
        """El matching de dominios incluye subdominios."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard, ScreenshotGuardAction

        guard = ScreenshotGuard()
        with patch.object(guard, '_get_active_policy', new_callable=AsyncMock, return_value=mock_policy_trusted):
            # www.boe.es debería matchear boe.es
            action = await guard.check_policy("https://www.boe.es/legislacion/")
            assert action == ScreenshotGuardAction.ALLOW

    @pytest.mark.asyncio
    async def test_extracts_domain_correctly(self):
        """Extrae correctamente el dominio de URLs complejas."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard

        guard = ScreenshotGuard()

        assert guard._extract_domain("https://www.example.com/path?q=1") == "example.com"
        assert guard._extract_domain("http://sub.domain.co.uk/") == "sub.domain.co.uk"
        assert guard._extract_domain("https://boe.es") == "boe.es"

    @pytest.mark.asyncio
    async def test_handles_malformed_url_gracefully(self):
        """URLs malformadas no causan excepción, retornan REQUIRE_REVIEW."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard, ScreenshotGuardAction

        guard = ScreenshotGuard()
        mock_policy = MagicMock()
        mock_policy.screenshot_policy = ScreenshotPolicyEnum.TRUSTED.value
        mock_policy.trusted_screenshot_domains = json.dumps(["example.com"])

        with patch.object(guard, '_get_active_policy', new_callable=AsyncMock, return_value=mock_policy):
            action = await guard.check_policy("not-a-valid-url")
            assert action == ScreenshotGuardAction.REQUIRE_REVIEW

    @pytest.mark.asyncio
    async def test_no_active_policy_defaults_to_review(self):
        """Sin política activa, se usa REVIEW como default seguro."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard, ScreenshotGuardAction

        guard = ScreenshotGuard()
        with patch.object(guard, '_get_active_policy', new_callable=AsyncMock, return_value=None):
            action = await guard.check_policy("https://any-site.com")
            assert action == ScreenshotGuardAction.REQUIRE_REVIEW


class TestScreenshotGuardLogging:
    """Tests para auditoría de decisiones."""

    @pytest.mark.asyncio
    async def test_logs_decision_to_connection_log(self):
        """Cada decisión debe registrarse en ConnectionLog."""
        from client_app.app.services.screenshot_guard import ScreenshotGuard, ScreenshotGuardAction

        guard = ScreenshotGuard()
        mock_policy = MagicMock()
        mock_policy.screenshot_policy = ScreenshotPolicyEnum.BLOCK.value
        mock_policy.trusted_screenshot_domains = "[]"

        with patch.object(guard, '_get_active_policy', new_callable=AsyncMock, return_value=mock_policy):
            with patch.object(guard, '_log_decision', new_callable=AsyncMock) as mock_log:
                await guard.check_policy("https://example.com")
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "example.com" in str(call_args)
                assert "BLOCK" in str(call_args)
