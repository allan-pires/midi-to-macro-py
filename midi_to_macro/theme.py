"""UI theme constants — Tokyo Night–inspired dark theme."""

# Base palette
BG = '#1a1b26'
FG = '#c0caf5'
ACCENT = '#7aa2f7'
ACCENT_HOVER = '#89b4fa'
PLAY_GREEN = '#22c55e'
PLAY_GREEN_HOVER = '#4ade80'
STOP_RED = '#ef4444'
STOP_RED_HOVER = '#f87171'
CARD = '#24283b'
CARD_BORDER = '#2d3047'
ENTRY_BG = '#414868'
ENTRY_FG = '#c0caf5'
SUBTLE = '#565f89'
FG_DISABLED = '#a0a8c0'  # Readable on SUBTLE when button is disabled
BORDER = '#414868'

# Typography
FONT_FAMILY = 'Segoe UI'
TITLE_FONT = (FONT_FAMILY, 12, 'bold')
LABEL_FONT = (FONT_FAMILY, 9)
SMALL_FONT = (FONT_FAMILY, 8)
HINT_FONT = (FONT_FAMILY, 8)

# Spacing (use PAD for section gaps, SMALL_PAD for related elements)
PAD = 8
SMALL_PAD = 4
BTN_PAD = (4, 0)
BTN_GAP = 4  # gap between icon buttons
ICON_BTN_WIDTH = 2  # width in chars for icon-only buttons (uniform size)

# Layout (taller, thinner window: more listbox rows, narrower wrap)
LISTBOX_MIN_ROWS = 8
OS_LISTBOX_MIN_ROWS = 8
HINT_WRAP = 280

# Button icons — use emoji so they render in color with ICON_FONT (Segoe UI Emoji)
ICON_FONT = ('Segoe UI Emoji', 10)
ICON_PLAY = '▶️'
ICON_STOP = '⏹️'
ICON_FOLDER = '📁'
ICON_ADD_LIST = '📋'
ICON_ADD_TO_PLAYLIST = '➕'
ICON_FAV = '⭐'
ICON_FAV_OFF = '☆'
ICON_SEARCH = '🔍'
ICON_RELOAD = '🔄'
ICON_BROWSER = '🌐'
ICON_REMOVE = '➖'
ICON_CLEAR = '🗑️'
ICON_HOST = '🏠'
ICON_CONNECT = '🔗'
ICON_DISCONNECT = '❌'
ICON_DOWNLOAD = '📥'
ICON_SAVE = '💾'
