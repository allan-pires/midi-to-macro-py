"""Tkinter GUI application."""

import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

from midi_to_macro import midi, playback
from midi_to_macro.online_sequencer import (
    fetch_sequences,
    open_sequence,
    download_sequence_midi,
    search_sequences,
    SORT_OPTIONS,
)
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

        # Header
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
        list_frame = tk.Frame(file_inner, bg=CARD)
        list_frame.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=(0, SMALL_PAD))
        file_inner.rowconfigure(3, weight=1)
        scrollbar = tk.Scrollbar(list_frame, bg=SUBTLE)
        scrollbar.pack(side='right', fill='y')
        self.file_listbox = tk.Listbox(
            list_frame, height=LISTBOX_MIN_ROWS, font=LABEL_FONT,
            bg=ENTRY_BG, fg=ENTRY_FG, selectbackground=ACCENT, selectforeground=BG,
            relief='flat', highlightthickness=0, yscrollcommand=scrollbar.set
        )
        self.file_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.file_listbox.yview)

        # Options section (radio buttons)
        opts_frame = tk.LabelFrame(
            file_tab, text='  Options  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        opts_frame.pack(fill='x', padx=PAD, pady=(0, PAD))
        opts_inner = tk.Frame(opts_frame, bg=CARD)
        opts_inner.pack(fill='x', padx=PAD, pady=(SMALL_PAD, PAD))
        rb_opts = {'font': LABEL_FONT, 'fg': FG, 'bg': CARD, 'activeforeground': FG, 'activebackground': CARD, 'selectcolor': ENTRY_BG}
        tk.Label(opts_inner, text='Tempo ×', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=0, sticky='w', pady=(0, SMALL_PAD))
        tempo_row = tk.Frame(opts_inner, bg=CARD)
        tempo_row.grid(row=1, column=0, sticky='w')
        for val, label in [(0.5, '0.5×'), (0.75, '0.75×'), (1.0, '1×'), (1.5, '1.5×')]:
            tk.Radiobutton(
                tempo_row, text=label, variable=self.tempo, value=val, **rb_opts
            ).pack(side='left', padx=(0, 12))
        tk.Label(opts_inner, text='Transpose', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=1, sticky='w', padx=(PAD * 2, 0), pady=(0, SMALL_PAD))
        transpose_row = tk.Frame(opts_inner, bg=CARD)
        transpose_row.grid(row=1, column=1, sticky='w', padx=(PAD * 2, 0))
        for val, label in [(-2, '−2'), (-1, '−1'), (0, '0'), (1, '+1'), (2, '+2')]:
            tk.Radiobutton(
                transpose_row, text=label, variable=self.transpose, value=val, **rb_opts
            ).pack(side='left', padx=(0, 10))

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
            relief='flat', highlightthickness=0, yscrollcommand=os_scroll.set
        )
        self.os_listbox.pack(side='left', fill='both', expand=True)
        self.os_listbox.bind('<Double-Button-1>', lambda e: self._open_selected_sequence())
        os_scroll.config(command=self.os_listbox.yview)
        # Info below list: status, progress bar
        os_info_frame = tk.Frame(os_inner, bg=CARD)
        os_info_frame.pack(fill='x', pady=(PAD, 0))
        self.os_status = tk.Label(
            os_info_frame,
            text='Choose sort and click Load list to show sequences.',
            font=SMALL_FONT, fg=SUBTLE, bg=CARD
        )
        self.os_status.pack(anchor='w')
        # Options (same as File tab: tempo and transpose are shared)
        os_opts_frame = tk.LabelFrame(
            os_tab, text='  Options  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        os_opts_frame.pack(fill='x', padx=PAD, pady=(0, PAD))
        os_opts_inner = tk.Frame(os_opts_frame, bg=CARD)
        os_opts_inner.pack(fill='x', padx=PAD, pady=(SMALL_PAD, PAD))
        tk.Label(os_opts_inner, text='Tempo ×', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=0, sticky='w', pady=(0, SMALL_PAD))
        os_tempo_row = tk.Frame(os_opts_inner, bg=CARD)
        os_tempo_row.grid(row=1, column=0, sticky='w')
        for val, label in [(0.5, '0.5×'), (0.75, '0.75×'), (1.0, '1×'), (1.5, '1.5×')]:
            tk.Radiobutton(
                os_tempo_row, text=label, variable=self.tempo, value=val, **rb_opts
            ).pack(side='left', padx=(0, 12))
        tk.Label(os_opts_inner, text='Transpose', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=1, sticky='w', padx=(PAD * 2, 0), pady=(0, SMALL_PAD))
        os_transpose_row = tk.Frame(os_opts_inner, bg=CARD)
        os_transpose_row.grid(row=1, column=1, sticky='w', padx=(PAD * 2, 0))
        for val, label in [(-2, '−2'), (-1, '−1'), (0, '0'), (1, '+1'), (2, '+2')]:
            tk.Radiobutton(
                os_transpose_row, text=label, variable=self.transpose, value=val, **rb_opts
            ).pack(side='left', padx=(0, 10))
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
        for sid, title in pairs:
            self.os_sequences.append((sid, title))
            display = f"  {title[:55] + '…' if len(title) > 55 else title}  (ID: {sid})"
            self.os_listbox.insert(tk.END, display)
        if pairs:
            self.os_listbox.selection_set(0)
            self.os_listbox.see(0)
        msg = f'{len(pairs)} sequences found.' if from_search else f'{len(pairs)} sequences loaded.'
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
                self.root.after(0, lambda: self._os_start_playback(path, tempo, transpose))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror('Load failed', str(e)))
                self.root.after(0, lambda: self.os_status.config(text='Load failed.'))

        threading.Thread(target=do_load_and_play, daemon=True).start()

    def _os_start_playback(self, path: str, tempo_multiplier: float, transpose: int):
        """Start playback for an OS-downloaded MIDI path (called on main thread)."""
        self._os_last_midi_path = path
        self.os_status.config(text='Playing… (focus game window)')
        self.root.focus_set()
        focus_process_window('wwm.exe')
        self.playing = True
        self.play_btn.config(state='disabled')
        self.os_play_btn.config(state='disabled')
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
        self.playing = True
        self.play_btn.config(state='disabled')
        self.os_play_btn.config(state='disabled')
        self.stop_btn.config(state='normal', bg=STOP_RED)
        self.os_stop_btn.config(state='normal', bg=STOP_RED)
        self.status.config(text='Playing... (focus game window)')
        threading.Thread(
            target=self._play_thread,
            args=(path, self.tempo.get(), self.transpose.get()),
            daemon=True
        ).start()

    def _set_progress(self, current, total):
        if total <= 0:
            return
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = current
        self.os_progress_bar['maximum'] = total
        self.os_progress_bar['value'] = current

    def _progress_done(self):
        self.progress_bar['value'] = self.progress_bar['maximum']
        self.os_progress_bar['value'] = self.os_progress_bar['maximum']
        if getattr(self, '_os_playing_path', None):
            self._os_playing_path = None
            self.root.after(0, lambda: self.play_btn.config(state='normal'))
            self.root.after(0, lambda: self.os_play_btn.config(state='normal'))
            self.root.after(0, lambda: self.stop_btn.config(state='disabled', bg=SUBTLE))
            self.root.after(0, lambda: self.os_stop_btn.config(state='disabled', bg=SUBTLE))
            self.root.after(0, lambda: self.os_status.config(text='Finished playing.'))

    def stop(self):
        self.playing = False
        self.status.config(text='Stopped')
        self.play_btn.config(state='normal')
        self.os_play_btn.config(state='normal')
        self.stop_btn.config(state='disabled', bg=SUBTLE)
        self.os_stop_btn.config(state='disabled', bg=SUBTLE)

    def _play_thread(self, path, tempo_multiplier, transpose):
        try:
            events = midi.parse_midi(
                path, tempo_multiplier=tempo_multiplier, transpose=transpose
            )
            total = len(events)
            self.root.after(0, lambda: self._set_progress(0, total))
            progress_cb = lambda c, t: self.root.after(0, lambda c=c, t=t: self._set_progress(c, t))
            playback.run_playback(events, lambda: self.playing, progress_callback=progress_cb)
            if self.playing:
                self.status.config(text='Finished playing')
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror('Playback error', str(e)))
            self.root.after(0, lambda: self.status.config(text='Error'))
        finally:
            self.root.after(0, self._progress_done)
            self.playing = False
            self.root.after(0, lambda: self.play_btn.config(state='normal'))
            self.root.after(0, lambda: self.os_play_btn.config(state='normal'))
            self.root.after(0, lambda: self.stop_btn.config(state='disabled', bg=SUBTLE))
            self.root.after(0, lambda: self.os_stop_btn.config(state='disabled', bg=SUBTLE))
