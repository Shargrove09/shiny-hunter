# customtkinter style constants
import platform

_FONT_FAMILY = "Calibri" if platform.system() == "Windows" else "DejaVu Sans"

FONT_BOLD = (_FONT_FAMILY, 18, "bold")
FONT_BOLD_LG = (_FONT_FAMILY, 24, "bold")
FONT_SMALL = (_FONT_FAMILY, 14)

BTN_START = {
    "font": FONT_BOLD,
    "fg_color": "green",
    "hover_color": "#005500",
    "corner_radius": 6,
}

BTN_STANDARD = {
    "font": FONT_BOLD,
    "corner_radius": 6,
}

BTN_SET = {
    "font": (_FONT_FAMILY, 11),
    "corner_radius": 4,
    "width": 40,
}

DROPDOWN = {
    "font": FONT_BOLD_LG,
}
