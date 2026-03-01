"""Tkinter GUI application."""

import json
import os
import shutil
import socket
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

from midi_to_macro import midi, playback
from midi_to_macro.online_sequencer import (
    download_sequence_midi,
    fetch_sequences,
    open_sequence,
    search_sequences,
    SORT_OPTIONS,
)
from midi_to_macro.sync import DEFAULT_PORT, Room, START_DELAY_SEC, get_lan_ip
from midi_to_macro.window_focus import focus_process_window
from midi_to_macro.theme import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    BORDER,
    BTN_PAD,
    CARD,
    ENTRY_BG,
    ENTRY_FG,
    FONT_FAMILY,
    FG,
    FG_DISABLED,
    HINT_FONT,
    HINT_WRAP,
    LABEL_FONT,
    LISTBOX_MIN_ROWS,
    OS_LISTBOX_MIN_ROWS,
    PAD,
    PLAY_GREEN,
    PLAY_GREEN_HOVER,
    SMALL_FONT,
    SMALL_PAD,
    STOP_RED,
    STOP_RED_HOVER,
    SUBTLE,
    TITLE_FONT,
)


class App:
    def __init__(self, root):
        self.root = root
        root.title('MIDI → .mcr')
        root.attributes('-topmost', True)
        self.playing = False

        root.configure(bg=BG)
        root.minsize(420, 320)
        root.option_add('*Font', LABEL_FONT)
        root.option_add('*Background', BG)
        root.option_add('*Foreground', FG)
        root.option_add('*selectBackground', ACCENT)
        root.option_add('*selectForeground', BG)

        # ttk styles (clam for full control)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=BG)
        style.configure(
            'TNotebook.Tab',
            background=SUBTLE, foreground=FG, padding=[SMALL_PAD + 4, SMALL_PAD]
        )
        style.map(
            'TNotebook.Tab',
            background=[('selected', CARD)],
            padding=[('selected', [PAD + 4, SMALL_PAD + 2])],
        )
        style.configure(
            'Playback.Horizontal.TProgressbar',
            troughcolor=SUBTLE,
            background=ACCENT,
            darkcolor=ACCENT,
            lightcolor=ACCENT,
            bordercolor=BORDER,
        )
        style.configure(
            'TCombobox',
            fieldbackground=ENTRY_BG,
            foreground=ENTRY_FG,
            background=SUBTLE,
            arrowcolor=FG,
        )
        style.map('TCombobox', fieldbackground=[('readonly', ENTRY_BG)])

        self.folder_path = ''
        self.tempo = tk.DoubleVar(value=1.0)
        self.transpose = tk.IntVar(value=0)
        # Repeat options and current playback source
        self.repeat_file = tk.BooleanVar(value=False)
        self.repeat_os = tk.BooleanVar(value=False)
        self._current_source: str | None = None
        self._stopped_by_user: bool = False
        # Playlist: list of ('file', path) or ('os', sid, title)
        self._playlist: list[tuple[str, ...]] = []
        self._playlist_index: int = 0
        # Play together room (host or client)
        self._room = Room()
        self._sync_temp_paths: list[str] = []  # temp files from sync to delete later

        # Per-song tempo/transpose (persisted to JSON)
        self._song_settings: dict[str, dict[str, float | int]] = {}
        try:
            self._song_settings_dir = os.path.join(os.path.expanduser('~'), '.midi_to_macro')
            self._song_settings_path = os.path.join(self._song_settings_dir, 'song_settings.json')
            self._load_song_settings()
            self._os_favorites_path = os.path.join(self._song_settings_dir, 'os_favorites.json')
            self._os_favorites: list[tuple[str, str]] = []
            self._load_os_favorites()
        except Exception:
            self._song_settings_dir = ''
            self._song_settings_path = ''
            self._os_favorites_path = ''
            self._os_favorites = []

        header = tk.Frame(root, bg=BG)
        header.pack(fill='x', padx=PAD, pady=(PAD, SMALL_PAD))
        tk.Label(header, text='MIDI → .mcr', font=TITLE_FONT, fg=ACCENT, bg=BG).pack(anchor='w')
        tk.Label(
            header, text='Convert MIDI to macro and play with keyboard',
            font=SMALL_FONT, fg=SUBTLE, bg=BG
        ).pack(anchor='w')

        # Notebook: File tab + Online Sequencer tab
        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True, padx=PAD, pady=(0, PAD))

        # ---- Tab 1: File ----
        file_tab = tk.Frame(notebook, bg=CARD)
        notebook.add(file_tab, text='  File  ')

        # File section: folder + list of .mid files
        file_frame = tk.LabelFrame(
            file_tab, text='  File  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        file_frame.pack(fill='both', expand=True, padx=PAD, pady=(0, PAD))
        file_inner = tk.Frame(file_frame, bg=CARD)
        file_inner.pack(fill='both', expand=True, padx=PAD, pady=(SMALL_PAD, PAD))
        tk.Label(file_inner, text='Folder', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=0, sticky='w', pady=(0, SMALL_PAD))
        self.folder_label = tk.Label(
            file_inner, text='No folder selected', font=SMALL_FONT,
            fg=SUBTLE, bg=CARD, anchor='w'
        )
        self.folder_label.grid(row=1, column=0, sticky='ew', padx=(0, 8))
        file_inner.columnconfigure(0, weight=1)
        open_folder_btn = tk.Button(
            file_inner, text='Open folder', command=self.open_folder,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        open_folder_btn.grid(row=1, column=1)
        open_folder_btn.bind('<Enter>', lambda e: open_folder_btn.configure(bg=ACCENT))
        open_folder_btn.bind('<Leave>', lambda e: open_folder_btn.configure(bg=SUBTLE))
        tk.Label(file_inner, text='MIDI file', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=2, column=0, sticky='w', pady=(PAD, SMALL_PAD))
        add_to_playlist_file_btn = tk.Button(
            file_inner, text='Add to playlist', command=self._add_file_to_playlist,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        add_to_playlist_file_btn.grid(row=2, column=1, padx=(PAD, 0))
        add_to_playlist_file_btn.bind('<Enter>', lambda e: add_to_playlist_file_btn.configure(bg=ACCENT))
        add_to_playlist_file_btn.bind('<Leave>', lambda e: add_to_playlist_file_btn.configure(bg=SUBTLE))
        list_frame = tk.Frame(file_inner, bg=CARD)
        list_frame.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=(0, SMALL_PAD))
        file_inner.rowconfigure(3, weight=1)
        scrollbar = tk.Scrollbar(list_frame, bg=SUBTLE)
        scrollbar.pack(side='right', fill='y')
        self.file_listbox = tk.Listbox(
            list_frame, height=LISTBOX_MIN_ROWS, font=LABEL_FONT,
            bg=ENTRY_BG, fg=ENTRY_FG, selectbackground=ACCENT, selectforeground=BG,
            relief='flat', highlightthickness=0, yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED
        )
        self.file_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        self.file_listbox.bind('<<ListboxSelect>>', lambda e: self._on_file_selection_changed())

        # Options section (sliders for tempo and transpose)
        opts_frame = tk.LabelFrame(
            file_tab, text='  Options  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        opts_frame.pack(fill='x', padx=PAD, pady=(0, PAD))
        opts_inner = tk.Frame(opts_frame, bg=CARD)
        opts_inner.pack(fill='x', padx=PAD, pady=(SMALL_PAD, PAD))
        scale_opts = {'font': LABEL_FONT, 'fg': FG, 'bg': CARD, 'troughcolor': ENTRY_BG, 'activebackground': CARD, 'highlightthickness': 0}
        tk.Label(opts_inner, text='Tempo ×', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=0, sticky='w', pady=(0, SMALL_PAD))
        tempo_row = tk.Frame(opts_inner, bg=CARD)
        tempo_row.grid(row=1, column=0, sticky='ew', pady=(0, PAD))
        opts_inner.columnconfigure(0, weight=1)
        self._tempo_scale = tk.Scale(
            tempo_row, from_=0.5, to=2.0, resolution=0.05, orient='horizontal',
            variable=self.tempo, length=180, **scale_opts
        )
        self._tempo_scale.pack(side='left', fill='x', expand=True)
        self._tempo_label = tk.Label(tempo_row, text='1.0×', font=SMALL_FONT, fg=SUBTLE, bg=CARD, width=5)
        self._tempo_label.pack(side='left', padx=(SMALL_PAD, 0))
        tk.Label(opts_inner, text='Transpose', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=1, sticky='w', padx=(PAD * 2, 0), pady=(0, SMALL_PAD))
        transpose_row = tk.Frame(opts_inner, bg=CARD)
        transpose_row.grid(row=1, column=1, sticky='ew', padx=(PAD * 2, 0), pady=(0, PAD))
        opts_inner.columnconfigure(1, weight=1)
        self._transpose_scale = tk.Scale(
            transpose_row, from_=-12, to=12, resolution=1, orient='horizontal',
            variable=self.transpose, length=180, **scale_opts
        )
        self._transpose_scale.pack(side='left', fill='x', expand=True)
        self._transpose_label = tk.Label(transpose_row, text='0', font=SMALL_FONT, fg=SUBTLE, bg=CARD, width=4)
        self._transpose_label.pack(side='left', padx=(SMALL_PAD, 0))

        def _update_tempo_label(*_):
            v = self.tempo.get()
            self._tempo_label.config(text=f'{v:.2f}×')
            if hasattr(self, '_os_tempo_label'):
                self._os_tempo_label.config(text=f'{v:.2f}×')
        def _update_transpose_label(*_):
            v = self.transpose.get()
            s = f'+{v}' if v >= 0 else str(v)
            self._transpose_label.config(text=s)
            if hasattr(self, '_os_transpose_label'):
                self._os_transpose_label.config(text=s)
        self.tempo.trace_add('write', _update_tempo_label)
        self.transpose.trace_add('write', _update_transpose_label)
        _update_tempo_label()
        _update_transpose_label()

        # Save tempo/transpose for this song (File tab)
        save_file_btn = tk.Button(
            opts_inner, text='Save for this song', command=self._save_tempo_transpose_for_file,
            font=SMALL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=SMALL_PAD,
            cursor='hand2'
        )
        save_file_btn.grid(row=2, column=0, columnspan=2, sticky='w', pady=(PAD, 0))
        save_file_btn.bind('<Enter>', lambda e: save_file_btn.configure(bg=ACCENT))
        save_file_btn.bind('<Leave>', lambda e: save_file_btn.configure(bg=SUBTLE))

        # Actions
        actions = tk.Frame(file_tab, bg=CARD)
        actions.pack(fill='x', padx=PAD, pady=(0, SMALL_PAD))
        export_btn = tk.Button(
            actions, text='Export .mcr', command=self.export,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        export_btn.pack(side='left', padx=(0, 8))
        export_btn.bind('<Enter>', lambda e: export_btn.configure(bg=ACCENT))
        export_btn.bind('<Leave>', lambda e: export_btn.configure(bg=SUBTLE))
        self.play_btn = tk.Button(
            actions, text='▶ Play', command=self.play,
            font=LABEL_FONT, bg=PLAY_GREEN, fg=BG, activebackground=PLAY_GREEN_HOVER,
            activeforeground=BG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        self.play_btn.pack(side='left', padx=(0, 8))
        self.play_btn.bind('<Enter>', lambda e: self.play_btn.configure(bg=PLAY_GREEN_HOVER))
        self.play_btn.bind('<Leave>', lambda e: self.play_btn.configure(bg=PLAY_GREEN))
        self.stop_btn = tk.Button(
            actions, text='Stop', command=self.stop, state='disabled',
            font=LABEL_FONT, bg=SUBTLE, fg=FG, disabledforeground=FG_DISABLED,
            activebackground=STOP_RED_HOVER, activeforeground=FG,
            relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1], cursor='hand2'
        )
        self.stop_btn.pack(side='left')
        def _stop_enter(e):
            if self.stop_btn['state'] == 'normal':
                self.stop_btn.configure(bg=STOP_RED_HOVER)
        def _stop_leave(e):
            if self.stop_btn['state'] == 'normal':
                self.stop_btn.configure(bg=STOP_RED)
        self.stop_btn.bind('<Enter>', _stop_enter)
        self.stop_btn.bind('<Leave>', _stop_leave)
        repeat_file_btn = tk.Checkbutton(
            actions, text='Repeat', variable=self.repeat_file,
            font=LABEL_FONT, fg=FG, bg=CARD,
            activeforeground=FG, activebackground=CARD,
            selectcolor=ENTRY_BG, cursor='hand2'
        )
        repeat_file_btn.pack(side='right')

        # Progress bar (shown during playback)
        self.progress_frame = tk.Frame(file_tab, bg=CARD)
        self.progress_frame.pack(fill='x', padx=PAD, pady=(SMALL_PAD, 0))
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, style='Playback.Horizontal.TProgressbar',
            mode='determinate', maximum=100, value=0
        )
        self.progress_bar.pack(fill='x')

        # Status
        status_frame = tk.Frame(file_tab, bg=CARD)
        status_frame.pack(fill='x', padx=PAD, pady=(SMALL_PAD, PAD))
        self.status = tk.Label(
            status_frame,
            text='Ready — focus the game window before playing',
            font=SMALL_FONT, fg=SUBTLE, bg=CARD
        )
        self.status.pack(anchor='w')

        # ---- Tab 2: Online Sequencer ----
        os_tab = tk.Frame(notebook, bg=CARD)
        notebook.add(os_tab, text='  Online Sequencer  ')
        os_sequences_frame = tk.LabelFrame(
            os_tab, text='  Sequences  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        os_sequences_frame.pack(fill='both', expand=True, padx=PAD, pady=(0, PAD))
        os_inner = tk.Frame(os_sequences_frame, bg=CARD)
        os_inner.pack(fill='both', expand=True, padx=PAD, pady=(SMALL_PAD, PAD))
        tk.Label(os_inner, text='Sequences (onlinesequencer.net)', font=LABEL_FONT, fg=FG, bg=CARD).pack(anchor='w')
        os_toolbar = tk.Frame(os_inner, bg=CARD)
        os_toolbar.pack(fill='x', pady=(SMALL_PAD, PAD))
        tk.Label(os_toolbar, text='Sort:', font=LABEL_FONT, fg=FG, bg=CARD).pack(side='left', padx=(0, 6))
        self.os_sort_menu = ttk.Combobox(
            os_toolbar,
            values=[label for _, label in SORT_OPTIONS],
            state='readonly', width=14, font=LABEL_FONT
        )
        self.os_sort_menu.pack(side='left', padx=(0, 8))
        self.os_sort_menu.set('Newest')
        self.os_sequences: list[tuple[str, str]] = []
        load_btn = tk.Button(
            os_toolbar, text='Load list', command=self._load_sequences,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        load_btn.pack(side='left', padx=(0, 8))
        load_btn.bind('<Enter>', lambda e: load_btn.configure(bg=ACCENT))
        load_btn.bind('<Leave>', lambda e: load_btn.configure(bg=SUBTLE))
        os_open_btn = tk.Button(
            os_toolbar, text='Open selected in browser', command=self._open_selected_sequence,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        os_open_btn.pack(side='left')
        os_open_btn.bind('<Enter>', lambda e: os_open_btn.configure(bg=ACCENT))
        os_open_btn.bind('<Leave>', lambda e: os_open_btn.configure(bg=SUBTLE))
        os_fav_btn = tk.Button(
            os_toolbar, text='★ Add to favorites', command=self._os_add_to_favorites,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        os_fav_btn.pack(side='left', padx=(8, 0))
        os_fav_btn.bind('<Enter>', lambda e: os_fav_btn.configure(bg=ACCENT))
        os_fav_btn.bind('<Leave>', lambda e: os_fav_btn.configure(bg=SUBTLE))
        os_unfav_btn = tk.Button(
            os_toolbar, text='Remove from favorites', command=self._os_remove_from_favorites,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        os_unfav_btn.pack(side='left', padx=(4, 0))
        os_unfav_btn.bind('<Enter>', lambda e: os_unfav_btn.configure(bg=ACCENT))
        os_unfav_btn.bind('<Leave>', lambda e: os_unfav_btn.configure(bg=SUBTLE))
        os_add_playlist_btn = tk.Button(
            os_toolbar, text='Add to playlist', command=self._add_os_to_playlist,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        os_add_playlist_btn.pack(side='left', padx=(8, 0))
        os_add_playlist_btn.bind('<Enter>', lambda e: os_add_playlist_btn.configure(bg=ACCENT))
        os_add_playlist_btn.bind('<Leave>', lambda e: os_add_playlist_btn.configure(bg=SUBTLE))
        os_search_frame = tk.Frame(os_inner, bg=CARD)
        os_search_frame.pack(fill='x', pady=(0, SMALL_PAD))
        tk.Label(os_search_frame, text='Search:', font=LABEL_FONT, fg=FG, bg=CARD).pack(
            side='left', padx=(0, 6)
        )
        self.os_search_var = tk.StringVar()
        os_search_entry = tk.Entry(
            os_search_frame,
            textvariable=self.os_search_var,
            font=LABEL_FONT,
            bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=ENTRY_FG,
            relief='flat', highlightthickness=0, width=28
        )
        os_search_entry.pack(side='left', padx=(0, 8), fill='x', expand=True)
        os_search_btn = tk.Button(
            os_search_frame, text='Search', command=self._search_sequences,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        os_search_btn.pack(side='left')
        os_search_btn.bind('<Enter>', lambda e: os_search_btn.configure(bg=ACCENT))
        os_search_btn.bind('<Leave>', lambda e: os_search_btn.configure(bg=SUBTLE))
        os_search_entry.bind('<Return>', lambda e: self._search_sequences())
        os_list_frame = tk.Frame(os_inner, bg=CARD)
        os_list_frame.pack(fill='both', expand=True, pady=(0, PAD))
        os_scroll = tk.Scrollbar(os_list_frame, bg=SUBTLE)
        os_scroll.pack(side='right', fill='y')
        self.os_listbox = tk.Listbox(
            os_list_frame, font=LABEL_FONT, height=OS_LISTBOX_MIN_ROWS,
            bg=ENTRY_BG, fg=ENTRY_FG, selectbackground=ACCENT, selectforeground=BG,
            relief='flat', highlightthickness=0, yscrollcommand=os_scroll.set,
            selectmode=tk.EXTENDED
        )
        self.os_listbox.pack(side='left', fill='both', expand=True)
        self.os_listbox.bind('<Double-Button-1>', lambda e: self._open_selected_sequence())
        self.os_listbox.bind('<<ListboxSelect>>', lambda e: self._on_os_selection_changed())
        os_scroll.config(command=self.os_listbox.yview)
        # Show saved favorites in list immediately if any
        if self._os_favorites:
            self.os_sequences = list(self._os_favorites)
            self._refresh_os_listbox()
            self.os_listbox.selection_set(0)
            self.os_listbox.see(0)
        # Info below list: status, progress bar
        os_info_frame = tk.Frame(os_inner, bg=CARD)
        os_info_frame.pack(fill='x', pady=(PAD, 0))
        self.os_status = tk.Label(
            os_info_frame,
            text='Choose sort and click Load list to show sequences.',
            font=SMALL_FONT, fg=SUBTLE, bg=CARD
        )
        self.os_status.pack(anchor='w')
        if self._os_favorites:
            self.os_status.config(text=f'★ {len(self._os_favorites)} favorites. Load list for more.')
        # Options (same as File tab: tempo and transpose sliders, shared vars)
        os_opts_frame = tk.LabelFrame(
            os_tab, text='  Options  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        os_opts_frame.pack(fill='x', padx=PAD, pady=(0, PAD))
        os_opts_inner = tk.Frame(os_opts_frame, bg=CARD)
        os_opts_inner.pack(fill='x', padx=PAD, pady=(SMALL_PAD, PAD))
        os_scale_opts = {'font': LABEL_FONT, 'fg': FG, 'bg': CARD, 'troughcolor': ENTRY_BG, 'activebackground': CARD, 'highlightthickness': 0}
        tk.Label(os_opts_inner, text='Tempo ×', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=0, sticky='w', pady=(0, SMALL_PAD))
        os_tempo_row = tk.Frame(os_opts_inner, bg=CARD)
        os_tempo_row.grid(row=1, column=0, sticky='ew', pady=(0, PAD))
        os_opts_inner.columnconfigure(0, weight=1)
        self._os_tempo_scale = tk.Scale(
            os_tempo_row, from_=0.5, to=2.0, resolution=0.05, orient='horizontal',
            variable=self.tempo, length=180, **os_scale_opts
        )
        self._os_tempo_scale.pack(side='left', fill='x', expand=True)
        self._os_tempo_label = tk.Label(os_tempo_row, text='1.0×', font=SMALL_FONT, fg=SUBTLE, bg=CARD, width=5)
        self._os_tempo_label.pack(side='left', padx=(SMALL_PAD, 0))
        tk.Label(os_opts_inner, text='Transpose', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=1, sticky='w', padx=(PAD * 2, 0), pady=(0, SMALL_PAD))
        os_transpose_row = tk.Frame(os_opts_inner, bg=CARD)
        os_transpose_row.grid(row=1, column=1, sticky='ew', padx=(PAD * 2, 0), pady=(0, PAD))
        os_opts_inner.columnconfigure(1, weight=1)
        self._os_transpose_scale = tk.Scale(
            os_transpose_row, from_=-12, to=12, resolution=1, orient='horizontal',
            variable=self.transpose, length=180, **os_scale_opts
        )
        self._os_transpose_scale.pack(side='left', fill='x', expand=True)
        self._os_transpose_label = tk.Label(os_transpose_row, text='0', font=SMALL_FONT, fg=SUBTLE, bg=CARD, width=4)
        self._os_transpose_label.pack(side='left', padx=(SMALL_PAD, 0))
        # Sync OS labels with current vars (traces set in File tab update both)
        self._os_tempo_label.config(text=f'{self.tempo.get():.2f}×')
        self._os_transpose_label.config(text=f'+{self.transpose.get()}' if self.transpose.get() >= 0 else str(self.transpose.get()))
        # Save tempo/transpose for this song (OS tab)
        save_os_btn = tk.Button(
            os_opts_inner, text='Save for this song', command=self._save_tempo_transpose_for_os,
            font=SMALL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=SMALL_PAD,
            cursor='hand2'
        )
        save_os_btn.grid(row=2, column=0, columnspan=2, sticky='w', pady=(PAD, 0))
        save_os_btn.bind('<Enter>', lambda e: save_os_btn.configure(bg=ACCENT))
        save_os_btn.bind('<Leave>', lambda e: save_os_btn.configure(bg=SUBTLE))

        # OS tab: actions (Export .mcr, Stop), progress bar (same style as File tab)
        self._os_last_midi_path: str | None = None
        os_actions = tk.Frame(os_tab, bg=CARD)
        os_actions.pack(fill='x', padx=PAD, pady=(PAD, SMALL_PAD))
        os_export_btn = tk.Button(
            os_actions, text='Export .mcr', command=self._export_os_mcr,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        os_export_btn.pack(side='left', padx=(0, 8))
        os_export_btn.bind('<Enter>', lambda e: os_export_btn.configure(bg=ACCENT))
        os_export_btn.bind('<Leave>', lambda e: os_export_btn.configure(bg=SUBTLE))
        os_download_btn = tk.Button(
            os_actions, text='Download MIDI', command=self._download_os_midi,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        os_download_btn.pack(side='left', padx=(0, 8))
        os_download_btn.bind('<Enter>', lambda e: os_download_btn.configure(bg=ACCENT))
        os_download_btn.bind('<Leave>', lambda e: os_download_btn.configure(bg=SUBTLE))
        self.os_play_btn = tk.Button(
            os_actions, text='▶ Play', command=self._load_and_play_sequence,
            font=LABEL_FONT, bg=PLAY_GREEN, fg=BG, activebackground=PLAY_GREEN_HOVER,
            activeforeground=BG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        self.os_play_btn.pack(side='left', padx=(0, 8))
        self.os_play_btn.bind('<Enter>', lambda e: self.os_play_btn.configure(bg=PLAY_GREEN_HOVER))
        self.os_play_btn.bind('<Leave>', lambda e: self.os_play_btn.configure(bg=PLAY_GREEN))
        self.os_stop_btn = tk.Button(
            os_actions, text='Stop', command=self.stop, state='disabled',
            font=LABEL_FONT, bg=SUBTLE, fg=FG, disabledforeground=FG_DISABLED,
            activebackground=STOP_RED_HOVER, activeforeground=FG,
            relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1], cursor='hand2'
        )
        self.os_stop_btn.pack(side='left')
        def _os_stop_enter(e):
            if self.os_stop_btn['state'] == 'normal':
                self.os_stop_btn.configure(bg=STOP_RED_HOVER)
        def _os_stop_leave(e):
            if self.os_stop_btn['state'] == 'normal':
                self.os_stop_btn.configure(bg=STOP_RED)
        self.os_stop_btn.bind('<Enter>', _os_stop_enter)
        self.os_stop_btn.bind('<Leave>', _os_stop_leave)
        repeat_os_btn = tk.Checkbutton(
            os_actions, text='Repeat', variable=self.repeat_os,
            font=LABEL_FONT, fg=FG, bg=CARD,
            activeforeground=FG, activebackground=CARD,
            selectcolor=ENTRY_BG, cursor='hand2'
        )
        repeat_os_btn.pack(side='right')
        # Progress bar (below actions, like File tab)
        self.os_progress_frame = tk.Frame(os_tab, bg=CARD)
        self.os_progress_frame.pack(fill='x', padx=PAD, pady=(SMALL_PAD, 0))
        self.os_progress_bar = ttk.Progressbar(
            self.os_progress_frame, style='Playback.Horizontal.TProgressbar',
            mode='determinate', maximum=100, value=0
        )
        self.os_progress_bar.pack(fill='x')
        # Bottom: only "Ready — focus..." message
        os_ready_frame = tk.Frame(os_tab, bg=CARD)
        os_ready_frame.pack(fill='x', padx=PAD, pady=(SMALL_PAD, PAD))
        tk.Label(
            os_ready_frame,
            text='Ready — focus the game window before playing',
            font=SMALL_FONT, fg=SUBTLE, bg=CARD
        ).pack(anchor='w')

        # ---- Tab 3: Playlist ----
        playlist_tab = tk.Frame(notebook, bg=CARD)
        notebook.add(playlist_tab, text='  Playlist  ')
        pl_frame = tk.LabelFrame(
            playlist_tab, text='  Playlist  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        pl_frame.pack(fill='both', expand=True, padx=PAD, pady=(0, PAD))
        pl_inner = tk.Frame(pl_frame, bg=CARD)
        pl_inner.pack(fill='both', expand=True, padx=PAD, pady=(SMALL_PAD, PAD))
        tk.Label(pl_inner, text='Songs play in order. Add from File or Online Sequencer tab.', font=LABEL_FONT, fg=FG, bg=CARD).pack(anchor='w')
        pl_toolbar = tk.Frame(pl_inner, bg=CARD)
        pl_toolbar.pack(fill='x', pady=(SMALL_PAD, PAD))
        pl_remove_btn = tk.Button(
            pl_toolbar, text='Remove selected', command=self._remove_from_playlist,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        pl_remove_btn.pack(side='left', padx=(0, 8))
        pl_remove_btn.bind('<Enter>', lambda e: pl_remove_btn.configure(bg=ACCENT))
        pl_remove_btn.bind('<Leave>', lambda e: pl_remove_btn.configure(bg=SUBTLE))
        pl_clear_btn = tk.Button(
            pl_toolbar, text='Clear playlist', command=self._clear_playlist,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        pl_clear_btn.pack(side='left', padx=(0, 8))
        pl_clear_btn.bind('<Enter>', lambda e: pl_clear_btn.configure(bg=ACCENT))
        pl_clear_btn.bind('<Leave>', lambda e: pl_clear_btn.configure(bg=SUBTLE))
        self.pl_play_btn = tk.Button(
            pl_toolbar, text='▶ Play playlist', command=self._play_playlist,
            font=LABEL_FONT, bg=PLAY_GREEN, fg=BG, activebackground=PLAY_GREEN_HOVER,
            activeforeground=BG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        self.pl_play_btn.pack(side='left', padx=(0, 8))
        self.pl_play_btn.bind('<Enter>', lambda e: self.pl_play_btn.configure(bg=PLAY_GREEN_HOVER))
        self.pl_play_btn.bind('<Leave>', lambda e: self.pl_play_btn.configure(bg=PLAY_GREEN))
        self.pl_stop_btn = tk.Button(
            pl_toolbar, text='Stop', command=self.stop, state='disabled',
            font=LABEL_FONT, bg=SUBTLE, fg=FG, disabledforeground=FG_DISABLED,
            activebackground=STOP_RED_HOVER, activeforeground=FG,
            relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1], cursor='hand2'
        )
        self.pl_stop_btn.pack(side='left', padx=(0, 8))
        def _pl_stop_enter(e):
            if self.pl_stop_btn['state'] == 'normal':
                self.pl_stop_btn.configure(bg=STOP_RED_HOVER)
        def _pl_stop_leave(e):
            if self.pl_stop_btn['state'] == 'normal':
                self.pl_stop_btn.configure(bg=STOP_RED)
        self.pl_stop_btn.bind('<Enter>', _pl_stop_enter)
        self.pl_stop_btn.bind('<Leave>', _pl_stop_leave)
        pl_list_frame = tk.Frame(pl_inner, bg=CARD)
        pl_list_frame.pack(fill='both', expand=True, pady=(0, PAD))
        pl_scroll = tk.Scrollbar(pl_list_frame, bg=SUBTLE)
        pl_scroll.pack(side='right', fill='y')
        self.playlist_listbox = tk.Listbox(
            pl_list_frame, font=LABEL_FONT, height=OS_LISTBOX_MIN_ROWS,
            bg=ENTRY_BG, fg=ENTRY_FG, selectbackground=ACCENT, selectforeground=BG,
            relief='flat', highlightthickness=0, yscrollcommand=pl_scroll.set,
            selectmode=tk.EXTENDED
        )
        self.playlist_listbox.pack(side='left', fill='both', expand=True)
        pl_scroll.config(command=self.playlist_listbox.yview)
        # Progress bar (same as File / OS tabs)
        self.pl_progress_frame = tk.Frame(playlist_tab, bg=CARD)
        self.pl_progress_frame.pack(fill='x', padx=PAD, pady=(SMALL_PAD, 0))
        self.pl_progress_bar = ttk.Progressbar(
            self.pl_progress_frame, style='Playback.Horizontal.TProgressbar',
            mode='determinate', maximum=100, value=0
        )
        self.pl_progress_bar.pack(fill='x')
        # Status (same style as other tabs)
        pl_status_frame = tk.Frame(playlist_tab, bg=CARD)
        pl_status_frame.pack(fill='x', padx=PAD, pady=(SMALL_PAD, PAD))
        self.pl_status = tk.Label(
            pl_status_frame,
            text='Ready — focus the game window before playing',
            font=SMALL_FONT, fg=SUBTLE, bg=CARD
        )
        self.pl_status.pack(anchor='w')

        # ---- Tab 4: Play together ----
        sync_tab = tk.Frame(notebook, bg=CARD)
        notebook.add(sync_tab, text='  Play together  ')
        sync_frame = tk.LabelFrame(
            sync_tab, text='  Room  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        sync_frame.pack(fill='both', expand=True, padx=PAD, pady=(0, PAD))
        sync_inner = tk.Frame(sync_frame, bg=CARD)
        sync_inner.pack(fill='both', expand=True, padx=PAD, pady=(SMALL_PAD, PAD))
        tk.Label(
            sync_inner, text='Host a room or join one. When the host presses Play, everyone starts together.',
            font=LABEL_FONT, fg=FG, bg=CARD
        ).pack(anchor='w')
        # Host
        host_frame = tk.Frame(sync_inner, bg=CARD)
        host_frame.pack(fill='x', pady=(PAD, SMALL_PAD))
        tk.Label(host_frame, text='Host room', font=LABEL_FONT, fg=FG, bg=CARD).pack(side='left', padx=(0, 8))
        self.sync_port_var = tk.StringVar(value=str(DEFAULT_PORT))
        sync_port_entry = tk.Entry(
            host_frame, textvariable=self.sync_port_var, width=6,
            font=LABEL_FONT, bg=ENTRY_BG, fg=ENTRY_FG, relief='flat', highlightthickness=0
        )
        sync_port_entry.pack(side='left', padx=(0, 8))
        self.sync_host_btn = tk.Button(
            host_frame, text='Start hosting', command=self._sync_start_host,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1], cursor='hand2'
        )
        self.sync_host_btn.pack(side='left', padx=(0, 4))
        self.sync_host_btn.bind('<Enter>', lambda e: self.sync_host_btn.configure(bg=ACCENT))
        self.sync_host_btn.bind('<Leave>', lambda e: self.sync_host_btn.configure(bg=SUBTLE))
        self.sync_stop_host_btn = tk.Button(
            host_frame, text='Stop hosting', command=self._sync_stop_host, state='disabled',
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1], cursor='hand2'
        )
        self.sync_stop_host_btn.pack(side='left')
        self.sync_stop_host_btn.bind('<Enter>', lambda e: self.sync_stop_host_btn.configure(bg=ACCENT))
        self.sync_stop_host_btn.bind('<Leave>', lambda e: self.sync_stop_host_btn.configure(bg=SUBTLE))
        self.sync_host_status = tk.Label(
            host_frame, text='', font=SMALL_FONT, fg=SUBTLE, bg=CARD
        )
        self.sync_host_status.pack(side='left', padx=(PAD, 0))
        self.sync_firewall_hint = tk.Label(
            sync_inner, text='If others can\'t connect: allow this app in Windows Firewall (Private network).',
            font=HINT_FONT, fg=SUBTLE, bg=CARD
        )
        # Join
        join_frame = tk.Frame(sync_inner, bg=CARD)
        join_frame.pack(fill='x', pady=(SMALL_PAD, PAD))
        tk.Label(join_frame, text='Join room', font=LABEL_FONT, fg=FG, bg=CARD).pack(side='left', padx=(0, 8))
        self.sync_join_var = tk.StringVar(value='')
        sync_join_entry = tk.Entry(
            join_frame, textvariable=self.sync_join_var, width=24,
            font=LABEL_FONT, bg=ENTRY_BG, fg=ENTRY_FG, relief='flat', highlightthickness=0
        )
        sync_join_entry.pack(side='left', padx=(0, 8), fill='x', expand=True)
        tk.Label(join_frame, text='(host IP:port)', font=SMALL_FONT, fg=SUBTLE, bg=CARD).pack(side='left', padx=(0, 4))
        self.sync_join_btn = tk.Button(
            join_frame, text='Connect', command=self._sync_join,
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1], cursor='hand2'
        )
        self.sync_join_btn.pack(side='left', padx=(0, 4))
        self.sync_join_btn.bind('<Enter>', lambda e: self.sync_join_btn.configure(bg=ACCENT))
        self.sync_join_btn.bind('<Leave>', lambda e: self.sync_join_btn.configure(bg=SUBTLE))
        self.sync_disconnect_btn = tk.Button(
            join_frame, text='Disconnect', command=self._sync_disconnect, state='disabled',
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1], cursor='hand2'
        )
        self.sync_disconnect_btn.pack(side='left')
        self.sync_disconnect_btn.bind('<Enter>', lambda e: self.sync_disconnect_btn.configure(bg=ACCENT))
        self.sync_disconnect_btn.bind('<Leave>', lambda e: self.sync_disconnect_btn.configure(bg=SUBTLE))
        self.sync_status = tk.Label(
            sync_inner, text='Not connected.',
            font=SMALL_FONT, fg=SUBTLE, bg=CARD
        )
        self.sync_status.pack(anchor='w')
        self._sync_register_room_callbacks()

    def _sync_register_room_callbacks(self):
        """Register room callbacks; all run via root.after on main thread."""
        def on_clients_changed(n: int):
            self.root.after(0, lambda: self._sync_update_host_status(n))
        def on_connected():
            self.root.after(0, self._sync_update_joined_ui)
        def on_disconnected():
            self.root.after(0, self._sync_update_disconnected_ui)
        def on_play_file(start_in: float, midi_bytes: bytes, tempo: float, transpose: int):
            self.root.after(0, lambda: self._sync_received_play_file(start_in, midi_bytes, tempo, transpose))
        def on_play_os(start_in: float, sid: str, tempo: float, transpose: int):
            self.root.after(0, lambda: self._sync_received_play_os(start_in, sid, tempo, transpose))
        self._room.on_clients_changed = on_clients_changed
        self._room.on_connected = on_connected
        self._room.on_disconnected = on_disconnected
        self._room.on_play_file = on_play_file
        self._room.on_play_os = on_play_os

    def _sync_update_host_status(self, n: int):
        if not self._room.is_host():
            return
        addr = get_lan_ip()
        self.sync_host_status.config(text=f'Room: {addr}:{self.sync_port_var.get()}  —  {n} participant(s)')

    def _sync_start_host(self):
        try:
            port = int(self.sync_port_var.get().strip())
        except ValueError:
            messagebox.showwarning('Invalid port', 'Enter a number for the port.')
            return
        if port <= 0 or port > 65535:
            messagebox.showwarning('Invalid port', 'Port must be between 1 and 65535.')
            return
        actual = self._room.start_host(port)
        if actual == 0:
            messagebox.showerror('Host failed', 'Could not start the room (port in use?).')
            return
        self.sync_port_var.set(str(actual))
        self.sync_host_btn.config(state='disabled')
        self.sync_stop_host_btn.config(state='normal')
        self.sync_join_btn.config(state='disabled')
        self.sync_disconnect_btn.config(state='disabled')  # only for client
        self.sync_status.config(text='You are the host. Select music and press Play — others will follow.')
        self._sync_update_host_status(0)
        self.sync_firewall_hint.pack(anchor='w', pady=(0, SMALL_PAD))

    def _sync_stop_host(self):
        self._room.stop_host()
        self.sync_host_btn.config(state='normal')
        self.sync_stop_host_btn.config(state='disabled')
        self.sync_join_btn.config(state='normal')
        self.sync_host_status.config(text='')
        self.sync_firewall_hint.pack_forget()
        self.sync_status.config(text='Not connected.')

    def _sync_join(self):
        s = self.sync_join_var.get().strip()
        if ':' not in s:
            messagebox.showwarning('Invalid address', 'Enter host:port (e.g. 192.168.1.10:38472)')
            return
        host, port_str = s.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showwarning('Invalid port', 'Enter a number for the port.')
            return
        if not self._room.connect(host.strip(), port):
            messagebox.showerror('Connect failed', 'Could not connect to the host.')
            return
        self.sync_join_btn.config(state='disabled')
        self.sync_disconnect_btn.config(state='normal')
        self.sync_host_btn.config(state='disabled')
        self.sync_status.config(text='Connected. Waiting for host to play.')

    def _sync_update_joined_ui(self):
        self.sync_join_btn.config(state='disabled')
        self.sync_disconnect_btn.config(state='normal')
        self.sync_host_btn.config(state='disabled')
        self.sync_status.config(text='Connected. Waiting for host to play.')

    def _sync_update_disconnected_ui(self):
        self.sync_join_btn.config(state='normal')
        self.sync_disconnect_btn.config(state='disabled')
        self.sync_host_btn.config(state='normal')
        self.sync_status.config(text='Disconnected.')

    def _sync_disconnect(self):
        if not self._room.is_client():
            return
        self._room.disconnect()
        self.sync_join_btn.config(state='normal')
        self.sync_disconnect_btn.config(state='disabled')
        self.sync_host_btn.config(state='normal')
        self.sync_status.config(text='Disconnected.')

    def _sync_received_play_file(self, start_in_sec: float, midi_bytes: bytes, tempo: float, transpose: int):
        """Client (or host) received play_file: write temp file, schedule playback at now + start_in_sec."""
        if not playback.KEYBOARD_AVAILABLE:
            return
        try:
            f = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
            f.write(midi_bytes)
            f.close()
            path = f.name
            self._sync_temp_paths.append(path)
        except OSError:
            return
        start_at = time.time() + start_in_sec
        def wait_then_play():
            delay = start_at - time.time()
            if delay > 0:
                time.sleep(delay)
            self.root.after(0, lambda: self._sync_start_file_playback(path, tempo, transpose))
        threading.Thread(target=wait_then_play, daemon=True).start()

    def _sync_start_file_playback(self, path: str, tempo: float, transpose: int):
        """Start playback from a path (sync received file); runs on main thread."""
        self._current_source = 'sync'
        self._stopped_by_user = False
        self.playing = True
        self.play_btn.config(state='disabled')
        self.os_play_btn.config(state='disabled')
        if hasattr(self, 'pl_play_btn'):
            self.pl_play_btn.config(state='disabled')
        if hasattr(self, 'pl_stop_btn'):
            self.pl_stop_btn.config(state='normal', bg=STOP_RED)
        self.stop_btn.config(state='normal', bg=STOP_RED)
        self.os_stop_btn.config(state='normal', bg=STOP_RED)
        self.status.config(text='Playing… (synced)')
        self.os_status.config(text='Playing… (synced)')
        if hasattr(self, 'sync_status'):
            self.sync_status.config(text='Playing…')
        threading.Thread(
            target=self._play_thread,
            args=(path, tempo, transpose),
            daemon=True
        ).start()

    def _sync_received_play_os(self, start_in_sec: float, sid: str, tempo: float, transpose: int):
        """Client received play_os: download then schedule playback at now + start_in_sec."""
        if not playback.KEYBOARD_AVAILABLE:
            return
        start_at = time.time() + start_in_sec
        def download_and_schedule():
            try:
                path = download_sequence_midi(sid, bpm=110, timeout=20)
            except Exception:
                self.root.after(0, lambda: self.sync_status.config(text='Download failed.'))
                return
            delay = start_at - time.time()
            if delay > 0:
                time.sleep(delay)
            self.root.after(0, lambda: self._sync_start_os_playback(path, tempo, transpose))
        threading.Thread(target=download_and_schedule, daemon=True).start()

    def _sync_start_os_playback(self, path: str, tempo: float, transpose: int):
        """Start playback from OS path (sync); runs on main thread."""
        self._os_last_midi_path = path
        self._current_source = 'sync'
        self._stopped_by_user = False
        self.playing = True
        self.play_btn.config(state='disabled')
        self.os_play_btn.config(state='disabled')
        if hasattr(self, 'pl_play_btn'):
            self.pl_play_btn.config(state='disabled')
        if hasattr(self, 'pl_stop_btn'):
            self.pl_stop_btn.config(state='normal', bg=STOP_RED)
        self.stop_btn.config(state='normal', bg=STOP_RED)
        self.os_stop_btn.config(state='normal', bg=STOP_RED)
        self.status.config(text='Playing… (synced)')
        self.os_status.config(text='Playing… (synced)')
        if hasattr(self, 'sync_status'):
            self.sync_status.config(text='Playing…')
        self._os_playing_path = path
        threading.Thread(
            target=self._play_thread,
            args=(path, tempo, transpose),
            daemon=True
        ).start()

    def _load_sequences(self):
        label = (self.os_sort_menu.get() or 'Newest').strip()
        sort = next((v for v, l in SORT_OPTIONS if l == label), '1')
        self.os_status.config(text='Loading…')
        self.os_listbox.delete(0, tk.END)
        self.os_sequences.clear()

        def do_fetch():
            try:
                pairs = fetch_sequences(sort=sort or '1')
                self.root.after(0, lambda: self._on_sequences_loaded(pairs, None))
            except Exception as e:
                self.root.after(0, lambda: self._on_sequences_loaded([], str(e)))

        threading.Thread(target=do_fetch, daemon=True).start()

    def _search_sequences(self):
        label = (self.os_sort_menu.get() or 'Newest').strip()
        sort = next((v for v, l in SORT_OPTIONS if l == label), '1')
        query = (self.os_search_var.get() or '').strip()
        self.os_status.config(text='Searching…' if query else 'Loading…')
        self.os_listbox.delete(0, tk.END)
        self.os_sequences.clear()

        def do_search():
            try:
                pairs = search_sequences(query=query, sort=sort or '1')
                self.root.after(0, lambda: self._on_sequences_loaded(pairs, None, from_search=bool(query)))
            except Exception as e:
                self.root.after(0, lambda: self._on_sequences_loaded([], str(e), from_search=False))

        threading.Thread(target=do_search, daemon=True).start()

    def _on_sequences_loaded(
        self, pairs: list[tuple[str, str]], error: str | None, *, from_search: bool = False
    ):
        self.os_sequences.clear()
        self.os_listbox.delete(0, tk.END)
        if error:
            self.os_status.config(text=f'Error: {error}')
            return
        fav_ids = self._os_fav_ids()
        # Favorites first, then results (excluding ids already in favorites to avoid duplicate)
        ordered: list[tuple[str, str]] = list(self._os_favorites)
        for sid, title in pairs:
            if sid not in fav_ids:
                ordered.append((sid, title))
        self.os_sequences = ordered
        for sid, title in self.os_sequences:
            self.os_listbox.insert(tk.END, self._os_display_line(sid, title))
        if self.os_sequences:
            self.os_listbox.selection_set(0)
            self.os_listbox.see(0)
        msg = f'{len(pairs)} sequences found.' if from_search else f'{len(pairs)} sequences loaded.'
        if self._os_favorites:
            msg += f'  ★ {len(self._os_favorites)} favorites at top.'
        self.os_status.config(text=msg)

    def _open_selected_sequence(self):
        sel = self.os_listbox.curselection()
        if not sel or not self.os_sequences:
            messagebox.showwarning('No selection', 'Load list and select a sequence first.')
            return
        idx = sel[0]
        if idx >= len(self.os_sequences):
            return
        sid, _ = self.os_sequences[idx]
        open_sequence(sid)
        self.os_status.config(text=f'Opened sequence {sid} in browser.')

    def _os_add_to_favorites(self):
        sel = self.os_listbox.curselection()
        if not sel or not self.os_sequences:
            messagebox.showwarning('No selection', 'Select a sequence first.')
            return
        idx = sel[0]
        if idx >= len(self.os_sequences):
            return
        sid, title = self.os_sequences[idx]
        if sid in self._os_fav_ids():
            self.os_status.config(text='Already in favorites.')
            return
        self._os_favorites.append((sid, title))
        self._save_os_favorites()
        fav_ids = self._os_fav_ids()
        rest = [x for x in self.os_sequences if x[0] not in fav_ids]
        self.os_sequences = list(self._os_favorites) + rest
        self._refresh_os_listbox()
        if self.os_sequences:
            try:
                new_idx = next(i for i, (s, _) in enumerate(self.os_sequences) if s == sid)
                self.os_listbox.selection_clear(0, tk.END)
                self.os_listbox.selection_set(new_idx)
                self.os_listbox.see(new_idx)
            except StopIteration:
                pass
        self.os_status.config(text=f'Added to favorites: {title[:40]}…' if len(title) > 40 else f'Added to favorites: {title}')

    def _os_remove_from_favorites(self):
        sel = self.os_listbox.curselection()
        if not sel or not self.os_sequences:
            messagebox.showwarning('No selection', 'Select a sequence first.')
            return
        idx = sel[0]
        if idx >= len(self.os_sequences):
            return
        sid, title = self.os_sequences[idx]
        if sid not in self._os_fav_ids():
            self.os_status.config(text='Not in favorites.')
            return
        self._os_favorites = [(s, t) for s, t in self._os_favorites if s != sid]
        self._save_os_favorites()
        fav_ids = self._os_fav_ids()
        rest = [x for x in self.os_sequences if x[0] not in fav_ids]
        self.os_sequences = list(self._os_favorites) + rest
        self._refresh_os_listbox()
        if self.os_sequences:
            self.os_listbox.selection_set(0)
            self.os_listbox.see(0)
        self.os_status.config(text='Removed from favorites.')

    def _load_and_play_sequence(self):
        """Download selected sequence as MIDI and start playback (no browser)."""
        if not playback.KEYBOARD_AVAILABLE:
            messagebox.showerror(
                'Missing dependency',
                'pynput library not available. Install with: pip install pynput'
            )
            return
        sel = self.os_listbox.curselection()
        if not sel or not self.os_sequences:
            messagebox.showwarning('No selection', 'Load list and select a sequence first.')
            return
        idx = sel[0]
        if idx >= len(self.os_sequences):
            return
        sid, title = self.os_sequences[idx]
        self.os_status.config(text=f'Downloading sequence {sid}…')
        tempo = self.tempo.get()
        transpose = self.transpose.get()

        def do_load_and_play():
            try:
                path = download_sequence_midi(sid, bpm=110, timeout=20)
                self.root.after(0, lambda: self._on_os_downloaded_for_play(path, sid, tempo, transpose))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror('Load failed', str(e)))
                self.root.after(0, lambda: self.os_status.config(text='Load failed.'))

        threading.Thread(target=do_load_and_play, daemon=True).start()

    def _on_os_downloaded_for_play(self, path: str, sid: str, tempo: float, transpose: int):
        """Called on main thread when OS MIDI is downloaded. If host, broadcast and sync start; else start now."""
        if self._room.is_host():
            self._room.send_play_os(START_DELAY_SEC, sid, tempo, transpose)
            start_at = time.time() + START_DELAY_SEC
            def wait_then_play():
                delay = start_at - time.time()
                if delay > 0:
                    time.sleep(delay)
                self.root.after(0, lambda: self._sync_start_os_playback(path, tempo, transpose))
            threading.Thread(target=wait_then_play, daemon=True).start()
            self.os_status.config(text=f'Starting in {int(START_DELAY_SEC)}s… (synced)')
        else:
            self._os_start_playback(path, tempo, transpose)

    def _os_start_playback(self, path: str, tempo_multiplier: float, transpose: int, keep_source: bool = False):
        """Start playback for an OS-downloaded MIDI path (called on main thread). If keep_source True, do not set _current_source (playlist)."""
        self._os_last_midi_path = path
        self.os_status.config(text='Playing… (focus game window)')
        self.root.focus_set()
        focus_process_window('wwm.exe')
        if not keep_source:
            self._current_source = 'os'
        self._stopped_by_user = False
        self.playing = True
        self.play_btn.config(state='disabled')
        self.os_play_btn.config(state='disabled')
        if hasattr(self, 'pl_play_btn'):
            self.pl_play_btn.config(state='disabled')
        if hasattr(self, 'pl_stop_btn'):
            self.pl_stop_btn.config(state='normal', bg=STOP_RED)
        self.stop_btn.config(state='normal', bg=STOP_RED)
        self.os_stop_btn.config(state='normal', bg=STOP_RED)
        self.status.config(text='Playing… (focus game window)')
        self._os_playing_path = path
        threading.Thread(
            target=self._play_thread,
            args=(path, tempo_multiplier, transpose),
            daemon=True
        ).start()

    def _export_os_mcr(self):
        """Export the last loaded Online Sequencer MIDI to .mcr (from current tab)."""
        path = getattr(self, '_os_last_midi_path', None)
        if not path or not os.path.isfile(path):
            messagebox.showwarning(
                'Nothing to export',
                'Play a sequence first so we have a MIDI file to export.'
            )
            return
        try:
            events = midi.parse_midi(
                path,
                tempo_multiplier=self.tempo.get(),
                transpose=self.transpose.get(),
            )
            out = filedialog.asksaveasfilename(
                defaultextension='.mcr', filetypes=[('MCR', '*.mcr')]
            )
            if not out:
                return
            midi.export_mcr(out, events)
            self.os_status.config(text=f'Exported {out}')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _download_os_midi(self):
        """Download selected sequence as MIDI and save to a file chosen by the user."""
        sel = self.os_listbox.curselection()
        if not sel or not self.os_sequences:
            messagebox.showwarning(
                'No selection',
                'Load list and select a sequence first.'
            )
            return
        idx = sel[0]
        if idx >= len(self.os_sequences):
            return
        sid, title = self.os_sequences[idx]
        self.os_status.config(text='Downloading…')

        def do_download():
            try:
                path = download_sequence_midi(sid, bpm=110, timeout=20)
                self.root.after(0, lambda: self._on_os_midi_downloaded(path, sid, title))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror('Download failed', str(e)))
                self.root.after(0, lambda: self.os_status.config(text='Download failed.'))

        threading.Thread(target=do_download, daemon=True).start()

    def _on_os_midi_downloaded(self, temp_path: str, sid: str, title: str):
        """Called on main thread with the temp MIDI path; show Save As and copy."""
        safe_name = "".join(c for c in title[:40] if c.isalnum() or c in " -_").strip() or f"sequence_{sid}"
        if len(safe_name) > 35:
            safe_name = safe_name[:35]
        default_name = f"{safe_name}.mid"
        out = filedialog.asksaveasfilename(
            defaultextension='.mid',
            filetypes=[('MIDI', '*.mid')],
            initialfile=default_name,
        )
        if not out:
            self.os_status.config(text='Download ready (save cancelled).')
            return
        try:
            shutil.copy2(temp_path, out)
            self.os_status.config(text=f'Saved {os.path.basename(out)}')
        except OSError as e:
            messagebox.showerror('Save failed', str(e))
            self.os_status.config(text='Save failed.')

    def open_folder(self):
        folder = filedialog.askdirectory(title='Select folder with MIDI files')
        if not folder:
            return
        self.folder_path = folder
        self.folder_label.config(text=folder[:60] + '...' if len(folder) > 60 else folder)
        self.file_listbox.delete(0, tk.END)
        try:
            names = sorted(
                n for n in os.listdir(folder)
                if n.lower().endswith('.mid') or n.lower().endswith('.midi')
            )
            for n in names:
                self.file_listbox.insert(tk.END, n)
            if names:
                self.file_listbox.selection_set(0)
                self.file_listbox.see(0)
        except OSError as e:
            messagebox.showerror('Error', str(e))

    def get_selected_file(self):
        if not self.folder_path:
            return None
        sel = self.file_listbox.curselection()
        if not sel:
            return None
        name = self.file_listbox.get(sel[0])
        return os.path.join(self.folder_path, name)

    def _playlist_display_line(self, item: tuple[str, ...]) -> str:
        if item[0] == 'file':
            return os.path.basename(item[1])
        # 'os', sid, title
        title = item[2][:50] + '…' if len(item[2]) > 50 else item[2]
        return f"{title}  (ID: {item[1]})"

    def _refresh_playlist_listbox(self):
        self.playlist_listbox.delete(0, tk.END)
        for item in self._playlist:
            self.playlist_listbox.insert(tk.END, self._playlist_display_line(item))
        n = len(self._playlist)
        if not self.playing:
            self.pl_status.config(
                text=f'{n} song{"s" if n != 1 else ""} in playlist.' if n else 'Playlist is empty.'
            )

    def _pl_select_playing(self):
        """Select and scroll to the currently playing item in the playlist listbox."""
        if self._current_source != 'playlist' or self._playlist_index >= len(self._playlist):
            return
        self.playlist_listbox.selection_clear(0, tk.END)
        self.playlist_listbox.selection_set(self._playlist_index)
        self.playlist_listbox.see(self._playlist_index)
        self.playlist_listbox.activate(self._playlist_index)

    def _add_file_to_playlist(self):
        if not self.folder_path:
            messagebox.showwarning('No folder', 'Open a folder first.')
            return
        sel = list(self.file_listbox.curselection())
        if not sel:
            messagebox.showwarning('No selection', 'Select one or more MIDI files to add.')
            return
        for idx in sel:
            name = self.file_listbox.get(idx)
            path = os.path.join(self.folder_path, name)
            self._playlist.append(('file', path))
        self._refresh_playlist_listbox()

    def _add_os_to_playlist(self):
        sel = list(self.os_listbox.curselection())
        if not sel or not self.os_sequences:
            messagebox.showwarning('No selection', 'Load list and select one or more sequences to add.')
            return
        for idx in sel:
            if idx < len(self.os_sequences):
                sid, title = self.os_sequences[idx]
                self._playlist.append(('os', sid, title))
        self._refresh_playlist_listbox()

    def _remove_from_playlist(self):
        sel = list(self.playlist_listbox.curselection())
        if not sel:
            return
        # Remove in reverse order so indices stay valid
        for idx in sorted(sel, reverse=True):
            if 0 <= idx < len(self._playlist):
                self._playlist.pop(idx)
        self._refresh_playlist_listbox()

    def _clear_playlist(self):
        self._playlist.clear()
        self._refresh_playlist_listbox()

    def _play_playlist(self):
        if not playback.KEYBOARD_AVAILABLE:
            messagebox.showerror(
                'Missing dependency',
                'pynput library not available. Install with: pip install pynput'
            )
            return
        if not self._playlist:
            messagebox.showwarning('Empty playlist', 'Add songs from the File or Online Sequencer tab first.')
            return
        self.root.focus_set()
        focus_process_window('wwm.exe')
        self._current_source = 'playlist'
        self._playlist_index = 0
        self._stopped_by_user = False
        self.playing = True
        self.play_btn.config(state='disabled')
        self.os_play_btn.config(state='disabled')
        self.pl_play_btn.config(state='disabled')
        self.stop_btn.config(state='normal', bg=STOP_RED)
        self.os_stop_btn.config(state='normal', bg=STOP_RED)
        self.pl_stop_btn.config(state='normal', bg=STOP_RED)
        n = len(self._playlist)
        self.status.config(text=f'Playing 1/{n}… (focus game window)')
        self.os_status.config(text=f'Playing 1/{n}… (focus game window)')
        self.pl_status.config(text=f'Playing 1/{n}… (focus game window)')
        self._pl_select_playing()
        self._start_next_playlist_item()

    def _start_file_playback(self, path: str, keep_source: bool = False):
        """Start playback of a file MIDI. If keep_source is True, do not set _current_source (used by playlist)."""
        if not keep_source:
            self._current_source = 'file'
        self._stopped_by_user = False
        self.playing = True
        self.play_btn.config(state='disabled')
        self.os_play_btn.config(state='disabled')
        if hasattr(self, 'pl_play_btn'):
            self.pl_play_btn.config(state='disabled')
        if hasattr(self, 'pl_stop_btn'):
            self.pl_stop_btn.config(state='normal', bg=STOP_RED)
        self.stop_btn.config(state='normal', bg=STOP_RED)
        self.os_stop_btn.config(state='normal', bg=STOP_RED)
        self.status.config(text='Playing... (focus game window)')
        threading.Thread(
            target=self._play_thread,
            args=(path, self.tempo.get(), self.transpose.get()),
            daemon=True
        ).start()

    def _start_next_playlist_item(self):
        """Start playback of the current playlist item (main thread). Advances to next when finished via _on_playback_finished."""
        if self._playlist_index >= len(self._playlist):
            self.root.after(0, self._progress_done)
            return
        item = self._playlist[self._playlist_index]
        n = len(self._playlist)
        self.status.config(text=f'Playing {self._playlist_index + 1}/{n}… (focus game window)')
        self.os_status.config(text=f'Playing {self._playlist_index + 1}/{n}… (focus game window)')
        self.pl_status.config(text=f'Playing {self._playlist_index + 1}/{n}… (focus game window)')
        self._pl_select_playing()
        if item[0] == 'file':
            self._start_file_playback(item[1], keep_source=True)
        else:
            sid, title = item[1], item[2]
            tempo = self.tempo.get()
            transpose = self.transpose.get()

            def do_download():
                try:
                    path = download_sequence_midi(sid, bpm=110, timeout=20)
                    self.root.after(0, lambda: self._os_start_playback(path, tempo, transpose, keep_source=True))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror('Load failed', str(e)))
                    self.root.after(0, lambda: self.pl_status.config(text='Load failed.'))
                    self.playing = False
                    self.root.after(0, self._progress_done)

            threading.Thread(target=do_download, daemon=True).start()

    def _load_song_settings(self):
        """Load per-song tempo/transpose from JSON."""
        self._song_settings = {}
        if not os.path.isfile(self._song_settings_path):
            return
        try:
            with open(self._song_settings_path, encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._song_settings = data
        except (json.JSONDecodeError, OSError):
            pass

    def _save_song_settings(self):
        """Persist _song_settings to JSON."""
        if not getattr(self, '_song_settings_dir', None):
            return
        try:
            os.makedirs(self._song_settings_dir, exist_ok=True)
            with open(self._song_settings_path, 'w', encoding='utf-8') as f:
                json.dump(self._song_settings, f, indent=2)
        except OSError:
            pass

    def _load_os_favorites(self):
        """Load Online Sequencer favorites from JSON."""
        self._os_favorites = []
        if not getattr(self, '_os_favorites_path', None) or not os.path.isfile(self._os_favorites_path):
            return
        try:
            with open(self._os_favorites_path, encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get('favorites'), list):
                for item in data['favorites']:
                    if isinstance(item, dict) and isinstance(item.get('id'), str) and isinstance(item.get('title'), str):
                        self._os_favorites.append((item['id'], item['title']))
        except (json.JSONDecodeError, OSError):
            pass

    def _save_os_favorites(self):
        """Persist Online Sequencer favorites to JSON."""
        if not getattr(self, '_song_settings_dir', None):
            return
        try:
            os.makedirs(self._song_settings_dir, exist_ok=True)
            data = {'favorites': [{'id': sid, 'title': title} for sid, title in self._os_favorites]}
            with open(self._os_favorites_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _os_fav_ids(self):
        return {sid for sid, _ in self._os_favorites}

    def _os_display_line(self, sid: str, title: str) -> str:
        prefix = '★ ' if sid in self._os_fav_ids() else '  '
        short = title[:55] + '…' if len(title) > 55 else title
        return f"{prefix}{short}  (ID: {sid})"

    def _refresh_os_listbox(self):
        """Redraw OS listbox from current os_sequences (with ★ for favorites)."""
        self.os_listbox.delete(0, tk.END)
        for sid, title in self.os_sequences:
            self.os_listbox.insert(tk.END, self._os_display_line(sid, title))

    def _get_file_song_key(self) -> str | None:
        path = self.get_selected_file()
        return os.path.normpath(path) if path else None

    def _get_os_song_key(self) -> str | None:
        sel = self.os_listbox.curselection()
        if not sel or not self.os_sequences:
            return None
        idx = sel[0]
        if idx >= len(self.os_sequences):
            return None
        sid, _ = self.os_sequences[idx]
        return f'os:{sid}'

    def _apply_song_settings_for_key(self, key: str | None):
        """Set tempo and transpose from saved settings for this song, or defaults when none saved."""
        if not key:
            return
        if key not in self._song_settings:
            self.tempo.set(1.0)
            self.transpose.set(0)
            return
        s = self._song_settings[key]
        if isinstance(s.get('tempo'), (int, float)):
            self.tempo.set(max(0.5, min(2.0, float(s['tempo']))))
        if isinstance(s.get('transpose'), (int, float)):
            self.transpose.set(max(-12, min(12, int(s['transpose']))))

    def _save_tempo_transpose_for_file(self):
        key = self._get_file_song_key()
        if not key:
            messagebox.showwarning('No selection', 'Select a MIDI file first.')
            return
        self._song_settings[key] = {'tempo': self.tempo.get(), 'transpose': self.transpose.get()}
        self._save_song_settings()
        self.status.config(text='Tempo/transpose saved for this song.')

    def _save_tempo_transpose_for_os(self):
        key = self._get_os_song_key()
        if not key:
            messagebox.showwarning('No selection', 'Select a sequence first.')
            return
        self._song_settings[key] = {'tempo': self.tempo.get(), 'transpose': self.transpose.get()}
        self._save_song_settings()
        self.os_status.config(text='Tempo/transpose saved for this song.')

    def _on_file_selection_changed(self):
        self._apply_song_settings_for_key(self._get_file_song_key())

    def _on_os_selection_changed(self):
        self._apply_song_settings_for_key(self._get_os_song_key())

    def export(self):
        path = self.get_selected_file()
        if not path:
            messagebox.showwarning('No file', 'Open a folder and select a MIDI file first')
            return
        try:
            events = midi.parse_midi(
                path, tempo_multiplier=self.tempo.get(), transpose=self.transpose.get()
            )
            out = filedialog.asksaveasfilename(
                defaultextension='.mcr', filetypes=[('MCR', '*.mcr')]
            )
            if not out:
                return
            midi.export_mcr(out, events)
            self.status.config(text=f'Exported {out}')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def play(self):
        if not playback.KEYBOARD_AVAILABLE:
            messagebox.showerror(
                'Missing dependency',
                'pynput library not available. Install with: pip install pynput'
            )
            return
        path = self.get_selected_file()
        if not path:
            messagebox.showwarning('No file', 'Open a folder and select a MIDI file first')
            return
        self.root.focus_set()
        focus_process_window('wwm.exe')
        # Host: broadcast and start together after START_DELAY_SEC
        if self._room.is_host():
            try:
                with open(path, 'rb') as f:
                    midi_bytes = f.read()
            except OSError as e:
                messagebox.showerror('Error', str(e))
                return
            tempo = self.tempo.get()
            transpose = self.transpose.get()
            self._room.send_play_file(START_DELAY_SEC, midi_bytes, tempo, transpose)
            start_at = time.time() + START_DELAY_SEC
            def wait_then_play():
                delay = start_at - time.time()
                if delay > 0:
                    time.sleep(delay)
                self.root.after(0, lambda: self._sync_start_file_playback(path, tempo, transpose))
            threading.Thread(target=wait_then_play, daemon=True).start()
            self.status.config(text=f'Starting in {int(START_DELAY_SEC)}s… (synced)')
            return
        self._start_file_playback(path)

    def _set_progress(self, current, total):
        if total <= 0:
            return
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = current
        self.os_progress_bar['maximum'] = total
        self.os_progress_bar['value'] = current
        if hasattr(self, 'pl_progress_bar'):
            self.pl_progress_bar['maximum'] = total
            self.pl_progress_bar['value'] = current

    def _progress_done(self):
        self.progress_bar['value'] = self.progress_bar['maximum']
        self.os_progress_bar['value'] = self.os_progress_bar['maximum']
        if hasattr(self, 'pl_progress_bar'):
            self.pl_progress_bar['value'] = self.pl_progress_bar['maximum']
        # Only switch to "stopped" state if we're not playing (e.g. we didn't just start a repeat)
        if not self.playing:
            if getattr(self, '_os_playing_path', None):
                self._os_playing_path = None
            self.play_btn.config(state='normal')
            self.os_play_btn.config(state='normal')
            if hasattr(self, 'pl_play_btn'):
                self.pl_play_btn.config(state='normal')
            if hasattr(self, 'pl_stop_btn'):
                self.pl_stop_btn.config(state='disabled', bg=SUBTLE)
            self.stop_btn.config(state='disabled', bg=SUBTLE)
            self.os_stop_btn.config(state='disabled', bg=SUBTLE)
            self.os_status.config(text='Finished playing.')
            if self._current_source == 'playlist' and hasattr(self, 'pl_status'):
                self.pl_status.config(text='Finished playing.')
            if self._current_source == 'sync' and hasattr(self, 'sync_status'):
                self.sync_status.config(text='Finished. Waiting for host to play.' if self._room.is_client() else 'You are the host. Select music and press Play — others will follow.')

    def stop(self):
        self._stopped_by_user = True
        self.playing = False
        self.status.config(text='Stopped')
        if self._current_source == 'playlist' and hasattr(self, 'pl_status'):
            self.pl_status.config(text='Stopped.')
        if self._current_source == 'sync' and hasattr(self, 'sync_status'):
            self.sync_status.config(text='Stopped.')
        self.play_btn.config(state='normal')
        self.os_play_btn.config(state='normal')
        if hasattr(self, 'pl_play_btn'):
            self.pl_play_btn.config(state='normal')
        if hasattr(self, 'pl_stop_btn'):
            self.pl_stop_btn.config(state='disabled', bg=SUBTLE)
        self.stop_btn.config(state='disabled', bg=SUBTLE)
        self.os_stop_btn.config(state='disabled', bg=SUBTLE)

    def _play_thread(self, path, tempo_multiplier, transpose):
        finished_naturally = False
        try:
            events = midi.parse_midi(
                path, tempo_multiplier=tempo_multiplier, transpose=transpose
            )
            total = len(events)
            self.root.after(0, lambda: self._set_progress(0, total))
            progress_cb = lambda c, t: self.root.after(0, lambda c=c, t=t: self._set_progress(c, t))
            playback.run_playback(events, lambda: self.playing, progress_callback=progress_cb)
            # If we reach here without exception, playback reached the end of events
            finished_naturally = True
            if self.playing:
                self.status.config(text='Finished playing')
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror('Playback error', str(e)))
            self.root.after(0, lambda: self.status.config(text='Error'))
        finally:
            self.playing = False
            # Single main-thread callback so repeat and button state stay in sync
            self.root.after(0, lambda: self._on_playback_finished(finished_naturally))

    def _on_playback_finished(self, finished_naturally: bool):
        """Run on main thread when playback thread exits. Updates UI and optionally starts repeat or next playlist item."""
        if finished_naturally and not self._stopped_by_user:
            if self._current_source == 'playlist':
                self._playlist_index += 1
                if self._playlist_index < len(self._playlist):
                    self.root.after(0, self._start_next_playlist_item)
                    return
            else:
                self._maybe_repeat_current()
        self._progress_done()

    def _maybe_repeat_current(self):
        """If repeat is enabled, start playback again for the current source."""
        if self._current_source == 'file':
            if self.repeat_file.get():
                self.play()
        elif self._current_source == 'os':
            if self.repeat_os.get():
                path = getattr(self, '_os_last_midi_path', None)
                if path:
                    # Use current tempo/transpose controls
                    self._os_start_playback(path, self.tempo.get(), self.transpose.get())
