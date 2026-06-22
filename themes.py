"""
Theme definitions for StreamBot web player.
Set THEME in .env to switch: dark_gold | dark_blue | light
"""

THEMES = {
    "dark_gold": {
        "--bg":      "#0a0a0a",
        "--surface": "#151515",
        "--card":    "#1a1a1a",
        "--border":  "#332a17",
        "--accent":  "#d4af37",
        "--accent2": "#b8860b",
        "--text":    "#f7f1e1",
        "--muted":   "#a39474",
        "--green":   "#22c55e",
    },
    "dark_blue": {
        "--bg":      "#0a0d14",
        "--surface": "#111827",
        "--card":    "#1e2a3a",
        "--border":  "#1e3a5f",
        "--accent":  "#3b82f6",
        "--accent2": "#1d4ed8",
        "--text":    "#e2e8f0",
        "--muted":   "#64748b",
        "--green":   "#22c55e",
    },
    "light": {
        "--bg":      "#f8fafc",
        "--surface": "#ffffff",
        "--card":    "#f1f5f9",
        "--border":  "#e2e8f0",
        "--accent":  "#7c3aed",
        "--accent2": "#5b21b6",
        "--text":    "#0f172a",
        "--muted":   "#64748b",
        "--green":   "#16a34a",
    },
    "dark_red": {
        "--bg":      "#1a1a1a",
        "--surface": "#242424",
        "--card":    "#2d2d2d",
        "--border":  "#4a1a1a",
        "--accent":  "#ef4444",
        "--accent2": "#f97316",
        "--text":    "#f5f5f5",
        "--muted":   "#9ca3af",
        "--green":   "#22c55e",
    },
    "electric_purple": {
        "--bg":      "#1a0a2e",
        "--surface": "#2d1b4e",
        "--card":    "#3d2060",
        "--border":  "#6b21a8",
        "--accent":  "#a855f7",
        "--accent2": "#c026d3",
        "--text":    "#f3e8ff",
        "--muted":   "#a78bfa",
        "--green":   "#22c55e",
    },
}

def get_css_vars(theme_name: str = "dark_gold") -> str:
    theme = THEMES.get(theme_name, THEMES["dark_gold"])
    vars_str = " ".join(f"{k}:{v};" for k, v in theme.items())
    return f":root {{ {vars_str} }}"
