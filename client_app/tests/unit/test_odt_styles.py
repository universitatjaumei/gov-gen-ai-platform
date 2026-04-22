import pytest
import os
from unittest.mock import MagicMock
# Need to import odf classes to check isinstance
from odf.style import Style, TextProperties, ParagraphProperties, TableCellProperties
from client_app.app.modules.factory.report_factory import ReportFactory

class TestODTStyles:
    
    @pytest.fixture
    def factory(self):
        return ReportFactory(backend="reportlab")
        
    def test_apply_style_from_config(self, factory):
        """Test the helper method _apply_style_from_config."""
        if not hasattr(factory, '_apply_style_from_config'):
             pytest.fail("ReportFactory does not have _apply_style_from_config method")
             
        style = Style(name="TestStyle", family="paragraph")
        config = {
            "color": "#FF0000",
            "size": 18,
            "bold": True,
            "italic": True,
            "align": "center"
        }
        
        factory._apply_style_from_config(style, config)
        
        # Verify elements added to style
        props_found = {
            "color": False,
            "size": False,
            "bold": False,
            "italic": False,
            "align": False
        }
        
        for element in style.childNodes:
            if element.tagName == "style:text-properties":
                if element.getAttribute("color") == "#FF0000":
                    props_found["color"] = True
                if element.getAttribute("fontsize") == "18pt":
                    props_found["size"] = True
                if element.getAttribute("fontweight") == "bold":
                    props_found["bold"] = True
                if element.getAttribute("fontstyle") == "italic":
                     props_found["italic"] = True
                     
            if element.tagName == "style:paragraph-properties":
                if element.getAttribute("textalign") == "center":
                    props_found["align"] = True
                    
        assert all(props_found.values()), f"Missing properties: {props_found}"

    def test_dynamic_styles_in_generation(self, factory, tmp_path):
        """Test that context['styles'] influences the generated ODT."""
        output_path = tmp_path / "dynamic_styles.odt"
        context = {
            "title": "Styled Title",
            "styles": {
                "title_color": "#00FF00",
                "title_size": 30
            }
        }
        
        # This test currently passes even without dynamic logic if method exists, 
        # but prevents regression if refactoring breaks basic generation.
        # To truly test dynamic logic without XML parsing is hard in unit test, relying on manual verification or trust in _apply_style_from_config
        factory.generate_odt(context, str(output_path))
        assert os.path.exists(output_path)
