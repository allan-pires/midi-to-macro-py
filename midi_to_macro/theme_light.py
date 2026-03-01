"""UI theme constants — light mode template (same variable names as theme.py)."""

# Base palette (light) — SUBTLE is a visible grey for scrollbars/tabs and readable secondary text
BG = '#f5f5f7'
FG = '#1d1d1f'
ACCENT = '#0071e3'
ACCENT_HOVER = '#0077ed'
PLAY_GREEN = '#22c55e'
PLAY_GREEN_HOVER = '#16a34a'
STOP_RED = '#ef4444'
STOP_RED_HOVER = '#dc2626'
CARD = '#ffffff'
CARD_BORDER = '#d2d2d7'
ENTRY_BG = '#fafafa'  # Slightly off-white so listboxes/entries stand out from CARD
ENTRY_FG = '#1d1d1f'
SUBTLE = '#6e6e73'  # Readable secondary text and visible scrollbars/tabs (not too light)
FG_DISABLED = '#9e9ea3'  # Readable on SUBTLE when button is disabled
BORDER = '#c7c7cc'
# Unselected tab — lighter grey so tabs don’t feel too dark
TAB_BG_UNSELECTED = '#a1a1a6'

# Typography (same as dark theme)
FONT_FAMILY = 'Segoe UI'
TITLE_FONT = (FONT_FAMILY, 12, 'bold')
LABEL_FONT = (FONT_FAMILY, 9)
SMALL_FONT = (FONT_FAMILY, 8)
HINT_FONT = (FONT_FAMILY, 8)

# Spacing (use PAD for section gaps, SMALL_PAD for related elements)
PAD = 8
SMALL_PAD = 4
BTN_PAD = (4, 0)
BTN_GAP = 4
BTN_GAP_TIGHT = 0
BTN_PAD_LARGE = (1, 0)
ICON_BTN_WIDTH = 3

# Layout
LISTBOX_MIN_ROWS = 8
OS_LISTBOX_MIN_ROWS = 8
HINT_WRAP = 280

# Button icons — same emoji as dark theme
ICON_FONT = ('Segoe UI Emoji', 14)
ICON_PLAY = '▶️'
ICON_STOP = '⏹️'
ICON_FOLDER = '📁'
ICON_ADD_LIST = '📋'
ICON_ADD_TO_PLAYLIST = '📝'
ICON_FAV = '➕'
ICON_FAV_OFF = '➖'
ICON_SEARCH = '🔍'
ICON_RELOAD = '🔃'
ICON_BROWSER = '🌎'
ICON_REMOVE = '➖'
ICON_CLEAR = '❌'
ICON_HOST = '🌎'
ICON_STOP_HOST = '🛑'
ICON_CONNECT = '⚡️'
ICON_DISCONNECT = '❌'
ICON_DOWNLOAD = '💾'
ICON_SAVE = '💾'
ICON_UPDATE = '🔄'
# Theme switch: show sun in dark theme (click to switch to light), moon in light theme (click to switch to dark)
ICON_THEME_SWITCH = '🌙'
