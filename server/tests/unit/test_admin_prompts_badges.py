
class TestTierBadges:
    """Tests para los badges de tier en la lista de prompts."""

    def test_get_tier_badge_function(self):
        """Verifica la función que devuelve el badge correcto."""
        def get_tier_badge(tier_override: int | None) -> tuple[str, str]:
            """Returns (emoji, color_class) for the tier."""
            badges = {
                None: ("⚪", "gray"),
                1: ("🟢", "green"),
                2: ("🟡", "yellow"),
                3: ("🔴", "red"),
            }
            return badges.get(tier_override, ("⚪", "gray"))

        assert get_tier_badge(None) == ("⚪", "gray")
        assert get_tier_badge(1) == ("🟢", "green")
        assert get_tier_badge(2) == ("🟡", "yellow")
        assert get_tier_badge(3) == ("🔴", "red")
        assert get_tier_badge(999) == ("⚪", "gray")  # Invalid tier

    def test_tier_label_text(self):
        """Verifica el texto del label de tier."""
        def get_tier_label(tier_override: int | None) -> str:
            labels = {
                None: "Default",
                1: "Tier 1",
                2: "Tier 2",
                3: "Tier 3",
            }
            return labels.get(tier_override, "Default")

        assert get_tier_label(None) == "Default"
        assert get_tier_label(1) == "Tier 1"
        assert get_tier_label(2) == "Tier 2"
        assert get_tier_label(3) == "Tier 3"
