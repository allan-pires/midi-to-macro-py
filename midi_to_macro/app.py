"""Tkinter GUI application."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

from midi_to_macro import midi, playback
from midi_to_macro.window_focus import focus_process_window
from midi_to_macro.theme import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    BTN_PAD,
    CARD,
    ENTRY_BG,
    ENTRY_FG,
    FONT_FAMILY,
    FG,
    LABEL_FONT,
    PAD,
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

        self.folder_path = ''
        self.tempo = tk.DoubleVar(value=1.0)
        self.transpose = tk.IntVar(value=0)

        # Header
        header = tk.Frame(root, bg=BG)
        header.pack(fill='x', padx=PAD, pady=(PAD, 4))
        tk.Label(header, text='MIDI → .mcr', font=TITLE_FONT, fg=ACCENT, bg=BG).pack(anchor='w')
        tk.Label(
            header, text='Convert MIDI to macro and play with keyboard',
            font=(FONT_FAMILY, 9), fg=SUBTLE, bg=BG
        ).pack(anchor='w')

        # File section: folder + list of .mid files
        file_frame = tk.LabelFrame(
            root, text='  File  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        file_frame.pack(fill='x', padx=PAD, pady=(0, PAD))
        file_inner = tk.Frame(file_frame, bg=CARD)
        file_inner.pack(fill='x', padx=PAD, pady=(4, PAD))
        tk.Label(file_inner, text='Folder', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=0, sticky='w', pady=(0, 4)
        )
        self.folder_label = tk.Label(
            file_inner, text='No folder selected', font=(FONT_FAMILY, 9),
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
            row=2, column=0, sticky='w', pady=(8, 4)
        )
        list_frame = tk.Frame(file_inner, bg=CARD)
        list_frame.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=(0, 4))
        file_inner.rowconfigure(3, weight=1)
        scrollbar = tk.Scrollbar(list_frame, bg=SUBTLE)
        scrollbar.pack(side='right', fill='y')
        self.file_listbox = tk.Listbox(
            list_frame, height=12, font=LABEL_FONT,
            bg=ENTRY_BG, fg=ENTRY_FG, selectbackground=ACCENT, selectforeground=BG,
            relief='flat', highlightthickness=0, yscrollcommand=scrollbar.set
        )
        self.file_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.file_listbox.yview)

        # Options section (radio buttons)
        opts_frame = tk.LabelFrame(
            root, text='  Options  ', font=LABEL_FONT,
            fg=SUBTLE, bg=CARD, labelanchor='n'
        )
        opts_frame.pack(fill='x', padx=PAD, pady=(0, PAD))
        opts_inner = tk.Frame(opts_frame, bg=CARD)
        opts_inner.pack(fill='x', padx=PAD, pady=(4, PAD))
        rb_opts = {'font': LABEL_FONT, 'fg': FG, 'bg': CARD, 'activeforeground': FG, 'activebackground': CARD, 'selectcolor': ENTRY_BG}
        tk.Label(opts_inner, text='Tempo ×', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=0, sticky='w', pady=(0, 6)
        )
        tempo_row = tk.Frame(opts_inner, bg=CARD)
        tempo_row.grid(row=1, column=0, sticky='w')
        for val, label in [(0.5, '0.5×'), (1.0, '1×'), (1.5, '1.5×'), (2.0, '2×')]:
            tk.Radiobutton(
                tempo_row, text=label, variable=self.tempo, value=val, **rb_opts
            ).pack(side='left', padx=(0, 12))
        tk.Label(opts_inner, text='Transpose', font=LABEL_FONT, fg=FG, bg=CARD).grid(
            row=0, column=1, sticky='w', padx=(24, 0), pady=(0, 6)
        )
        transpose_row = tk.Frame(opts_inner, bg=CARD)
        transpose_row.grid(row=1, column=1, sticky='w', padx=(24, 0))
        for val, label in [(-2, '−2'), (-1, '−1'), (0, '0'), (1, '+1'), (2, '+2')]:
            tk.Radiobutton(
                transpose_row, text=label, variable=self.transpose, value=val, **rb_opts
            ).pack(side='left', padx=(0, 10))

        # Actions
        actions = tk.Frame(root, bg=BG)
        actions.pack(fill='x', padx=PAD, pady=(0, PAD))
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
            font=LABEL_FONT, bg=ACCENT, fg=BG, activebackground=ACCENT_HOVER,
            activeforeground=BG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        self.play_btn.pack(side='left', padx=(0, 8))
        self.play_btn.bind('<Enter>', lambda e: self.play_btn.configure(bg=ACCENT_HOVER))
        self.play_btn.bind('<Leave>', lambda e: self.play_btn.configure(bg=ACCENT))
        self.stop_btn = tk.Button(
            actions, text='Stop', command=self.stop, state='disabled',
            font=LABEL_FONT, bg=SUBTLE, fg=FG, activebackground=ENTRY_BG,
            activeforeground=FG, relief='flat', padx=BTN_PAD[0], pady=BTN_PAD[1],
            cursor='hand2'
        )
        self.stop_btn.pack(side='left')
        def _stop_enter(e):
            if self.stop_btn['state'] == 'normal':
                self.stop_btn.configure(bg=ACCENT)
        def _stop_leave(e):
            if self.stop_btn['state'] == 'normal':
                self.stop_btn.configure(bg=SUBTLE)
        self.stop_btn.bind('<Enter>', _stop_enter)
        self.stop_btn.bind('<Leave>', _stop_leave)

        # Progress bar (shown during playback)
        self.progress_frame = tk.Frame(root, bg=BG)
        self.progress_frame.pack(fill='x', padx=PAD, pady=(4, 0))
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'Playback.Horizontal.TProgressbar',
            troughcolor=SUBTLE,
            background=ACCENT,
            darkcolor=ACCENT,
            lightcolor=ACCENT,
            bordercolor=CARD,
        )
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, style='Playback.Horizontal.TProgressbar',
            mode='determinate', maximum=100, value=0
        )
        self.progress_bar.pack(fill='x')

        # Status
        status_frame = tk.Frame(root, bg=BG)
        status_frame.pack(fill='x', padx=PAD, pady=(0, PAD))
        self.status = tk.Label(
            status_frame,
            text='Ready — focus the game window before playing',
            font=(FONT_FAMILY, 9), fg=SUBTLE, bg=BG
        )
        self.status.pack(anchor='w')

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
        self.stop_btn.config(state='normal')
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

    def _progress_done(self):
        self.progress_bar['value'] = self.progress_bar['maximum']

    def stop(self):
        self.playing = False
        self.status.config(text='Stopped')
        self.play_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

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
            self.root.after(0, lambda: self.stop_btn.config(state='disabled'))
