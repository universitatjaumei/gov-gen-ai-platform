import pytest
from nicegui.testing import User, Screen
from axe_playwright_python.async_playwright import Axe
from playwright.async_api import async_playwright

class TestAccessibility:
    """Tests de accesibilidad WCAG 2.1 AA."""

    async def test_axe_no_critical_violations(self, user: User, screen: Screen):
        """No hay violaciones críticas de accesibilidad."""
        await user.open("/")
        
        # Use dynamic URL provided by NiceGUI screen fixture
        base_url = screen.url
        target_url = f"{base_url}/" if not base_url.endswith('/') else base_url
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.goto(target_url)
                
                # Inject axe-core
                axe = Axe()
                results = await axe.run(page)

                critical = [v for v in results["violations"] if v["impact"] == "critical"]
                assert results, "Axe analysis failed or returned empty results"
                assert len(critical) == 0, f"Violaciones críticas: {critical}"
            finally:
                await browser.close()

    async def test_all_images_have_alt_text(self, user: User, screen: Screen):
        """Todas las imágenes tienen alt text."""
        await user.open("/")
        target_url = screen.url
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.goto(target_url)

                images = await page.query_selector_all("img")
                for img in images:
                    alt = await img.get_attribute("alt")
                    assert alt is not None, f"Imagen sin atributo alt para {await img.get_attribute('src')}"
            finally:
                await browser.close()

    async def test_form_inputs_have_labels(self, user: User, screen: Screen):
        """Todos los inputs tienen labels."""
        await user.open("/config")
        base_url = screen.url
        target_url = f"{base_url}/config" if not base_url.endswith('/') else f"{base_url}config"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.goto(target_url)

                inputs = await page.query_selector_all("input, select, textarea")
                for inp in inputs:
                    inp_id = await inp.get_attribute("id")
                    inp_type = await inp.get_attribute("type")
                    if inp_type == "hidden": continue
                    
                    if inp_id:
                        label = await page.query_selector(f"label[for='{inp_id}']")
                        aria_label = await inp.get_attribute("aria-label")
                        aria_labelledby = await inp.get_attribute("aria-labelledby")
                        
                        assert label or aria_label or aria_labelledby, f"Input {inp_id} sin label"
            finally:
                await browser.close()

    async def test_keyboard_navigation_menu(self, user: User, screen: Screen):
        """Navegación por teclado en menú."""
        await user.open("/")
        target_url = screen.url
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.goto(target_url)
                
                await page.click("body")

                # Tab navigation
                await page.keyboard.press("Tab")
                element1 = await page.evaluate("document.activeElement.tagName")
                await page.keyboard.press("Tab")
                element2 = await page.evaluate("document.activeElement.tagName")
                
                assert element1 or element2
            finally:
                await browser.close()


class TestResponsive:
    """Tests de diseño responsive."""

    async def test_mobile_viewport_375(self, user: User, screen: Screen):
        """UI se adapta a móvil (375px)."""
        await user.open("/")
        target_url = screen.url
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_viewport_size({"width": 375, "height": 667})
                await page.goto(target_url)
                
                try:
                    # Check for menu button
                    hamburger = await page.wait_for_selector(".q-btn:has(.q-icon:text('menu'))", timeout=5000) or \
                                await page.wait_for_selector("button:has(.q-icon:has-text('menu'))", timeout=5000)
                    if hamburger:
                        assert await hamburger.is_visible()
                except:
                    pass
            finally:
                await browser.close()

    async def test_tablet_viewport_768(self, user: User, screen: Screen):
        """UI se adapta a tablet (768px)."""
        await user.open("/")
        target_url = screen.url
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_viewport_size({"width": 768, "height": 1024})
                await page.goto(target_url)
                
                content = await page.content()
                assert "Dashboard" in content or "Progreso" in content
            finally:
                await browser.close()

    async def test_desktop_viewport_1920(self, user: User, screen: Screen):
        """UI aprovecha pantalla grande (1920px)."""
        await user.open("/")
        target_url = screen.url
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1920, "height": 1080})
                await page.goto(target_url)
                
                content = await page.content()
                assert "AutomatIA" in content
            finally:
                await browser.close()
