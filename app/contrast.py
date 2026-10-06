"""Primary button colors and the WCAG contrast math that checks them.

No Streamlit calls here, so tests can import it. `primary_button_css()` is
injected by `app/streamlit_app.py`. Streamlit draws primary buttons in the
theme's `primaryColor` (cream, #e8d9b8) with white text, about 1.4:1, so the
CSS below sets dark text for every state.
"""

from __future__ import annotations

# WCAG 2.x AA minimum for normal-size text.
AA_TEXT = 4.5

CREAM = "#e8d9b8"  # theme primaryColor (.streamlit/config.toml)
DARK_TEXT = "#16210f"  # same dark green as the score badge text

# State -> (text color, background color). Enabled states keep the cream
# family; hover/focus match Streamlit's own hover shade.
PRIMARY_BUTTON = {
    "normal": (DARK_TEXT, CREAM),
    "hover": (DARK_TEXT, "#d6bb80"),
    "focus": (DARK_TEXT, "#d6bb80"),
    "active": (DARK_TEXT, "#c9a96a"),
}

# Disabled buttons have no fill, so their text sits on the quiz card:
# rgba(6, 14, 10, .82) over the background photo. The card over a pure
# white photo is the lightest (worst) case for light text.
CARD_RGB = (6, 14, 10)
CARD_ALPHA = 0.82
DISABLED_TEXT = "#b3ad9f"
DISABLED_BORDER = "rgba(247, 241, 228, .35)"


def hex_rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"expected #rrggbb, got {color!r}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _channel(value: float) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    hi, lo = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def over(fg: tuple[float, float, float], alpha: float, bg: tuple[float, float, float]) -> tuple[float, float, float]:
    """Color of `fg` at `alpha` painted on an opaque `bg`."""
    return tuple(alpha * f + (1 - alpha) * b for f, b in zip(fg, bg))  # type: ignore[return-value]


def card_backgrounds() -> dict[str, tuple[float, float, float]]:
    """The quiz card over the darkest and lightest possible photo."""
    return {
        "over black photo": over(CARD_RGB, CARD_ALPHA, (0, 0, 0)),
        "over white photo": over(CARD_RGB, CARD_ALPHA, (255, 255, 255)),
    }


def primary_button_css() -> str:
    """CSS for Streamlit primary buttons (Start, Next, See parks) in all states.

    `button[data-testid=...]` outranks Streamlit's single-class styles, and
    the inner <p> is set too because Streamlit colors it directly.
    """
    sel = '.stApp button[data-testid="stBaseButton-primary"]'
    normal_text, normal_bg = PRIMARY_BUTTON["normal"]
    hover_text, hover_bg = PRIMARY_BUTTON["hover"]
    focus_text, focus_bg = PRIMARY_BUTTON["focus"]
    active_text, active_bg = PRIMARY_BUTTON["active"]
    return f"""
          {sel} {{ background: {normal_bg}; border-color: {normal_bg}; color: {normal_text}; }}
          {sel} p {{ color: inherit; }}
          {sel}:hover {{ background: {hover_bg}; border-color: {hover_bg}; color: {hover_text}; }}
          {sel}:focus-visible {{
            background: {focus_bg}; border-color: {focus_bg}; color: {focus_text};
            outline: 2px solid #f7f1e4; outline-offset: 2px;
          }}
          {sel}:active {{ background: {active_bg}; border-color: {active_bg}; color: {active_text}; }}
          {sel}:disabled, {sel}:disabled:hover, {sel}:disabled:active {{
            background: transparent; border: 1px dashed {DISABLED_BORDER};
            color: {DISABLED_TEXT}; cursor: not-allowed; outline: none;
          }}
"""
