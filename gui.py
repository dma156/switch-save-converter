#!/usr/bin/env python3
"""
GUI for the Switch Save Converter.
Features:
- Editable Dropdowns (state=""): Users can select from list OR type.
- Logic: Source restricted by Mode; Target filtered by Source.
- Autocomplete game selection with dropdown results from mapping data.
- Checkbox for cleaning temporary extraction files after conversion.
- Scrollable path display for long filepaths.
- Option to disable all validation checks.
- Format icons with automatic fallback to colored letter placeholders.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from convert import SaveConverterLogic
from mapping import get_mapper

try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PILLOW = True
    print("[DEBUG] ✓ Pillow imported successfully!")
except ImportError as e:
    HAS_PILLOW = False
    print(f"[DEBUG] ✗ Pillow import failed: {e}")

class IconFactory:
    """Loads images from icons/ folder with fallback to colored letter placeholders."""
    
    @staticmethod
    def load_checkpoint_icon(size=32):
        """Load checkpoint.jpg or checkpoint.png from icons/ folder, fallback to blue 'C'"""
        if not HAS_PILLOW:
            return None
        
        # Try both .jpg and .png extensions
        img_paths = [
            Path(__file__).parent / "icons" / "checkpoint.jpg",
            Path(__file__).parent / "icons" / "checkpoint.png"
        ]
        
        for img_path in img_paths:
            if img_path.exists():
                try:
                    img = Image.open(img_path).resize((size, size))
                    img = img.convert('RGB')  # Ensure RGB for PhotoImage
                    photo = ImageTk.PhotoImage(img)
                    print(f"[ICON] ✓ Loaded: {img_path}")
                    return photo
                except Exception as e:
                    print(f"[ICON] Failed to load {img_path}: {e}")
        
        # Fallback: Create blue square with 'C'
        print("[ICON] Creating fallback checkpoint icon (blue 'C')")
        img = Image.new('RGB', (size, size), color='#2196F3')
        draw = ImageDraw.Draw(img)
        draw.text((size//3, size//4), 'C', fill='white')
        return ImageTk.PhotoImage(img)
    
    @staticmethod
    def load_eden_icon(size=32):
        """Load eden.jpg or eden.png from icons/ folder, fallback to green 'E'"""
        if not HAS_PILLOW:
            return None
        
        img_paths = [
            Path(__file__).parent / "icons" / "eden.jpg",
            Path(__file__).parent / "icons" / "eden.png"
        ]
        
        for img_path in img_paths:
            if img_path.exists():
                try:
                    img = Image.open(img_path).resize((size, size))
                    img = img.convert('RGB')
                    photo = ImageTk.PhotoImage(img)
                    print(f"[ICON] ✓ Loaded: {img_path}")
                    return photo
                except Exception as e:
                    print(f"[ICON] Failed to load {img_path}: {e}")
        
        # Fallback: Create green square with 'E'
        print("[ICON] Creating fallback eden icon (green 'E')")
        img = Image.new('RGB', (size, size), color='#4CAF50')
        draw = ImageDraw.Draw(img)
        draw.text((size//4, size//4), 'E', fill='white')
        return ImageTk.PhotoImage(img)
    
    @staticmethod
    def load_jksv_icon(size=32):
        """Load jksv.jpg or jksv.png from icons/ folder, fallback to orange 'J'"""
        if not HAS_PILLOW:
            return None
        
        img_paths = [
            Path(__file__).parent / "icons" / "jksv.jpg",
            Path(__file__).parent / "icons" / "jksv.png"
        ]
        
        for img_path in img_paths:
            if img_path.exists():
                try:
                    img = Image.open(img_path).resize((size, size))
                    img = img.convert('RGB')
                    photo = ImageTk.PhotoImage(img)
                    print(f"[ICON] ✓ Loaded: {img_path}")
                    return photo
                except Exception as e:
                    print(f"[ICON] Failed to load {img_path}: {e}")
        
        # Fallback: Create orange square with 'J'
        print("[ICON] Creating fallback jksv icon (orange 'J')")
        img = Image.new('RGB', (size, size), color='#FF9800')
        draw = ImageDraw.Draw(img)
        draw.text((size//3, size//4), 'J', fill='white')
        return ImageTk.PhotoImage(img)

class AutocompleteEntry:
    """
    A custom autocomplete widget with an inline dropdown listbox.
    Uses the TitleIdMapper to search games by partial name.
    """
    def __init__(self, parent, mapper, on_select_callback=None, width=35):
        self.mapper = mapper
        self.on_select_callback = on_select_callback
        self.selected_title_id = None
        self.selected_game_name = None
        self.frame = tk.Frame(parent)
        self.entry = tk.Entry(self.frame, width=width)
        self.entry.pack(fill=tk.X)
        self.listbox = None
        self._raw_results = []
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Down>", self._on_arrow_down)
        self.entry.bind("<Up>", self._on_arrow_up)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Escape>", self._close_listbox)
        self.entry.bind("<FocusOut>", self._on_focus_out)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)

    def clear(self):
        self.entry.delete(0, tk.END)
        self.selected_title_id = None
        self.selected_game_name = None
        self._close_listbox()

    def _on_key_release(self, event):
        if event.keysym in ("Down", "Up", "Return", "Escape", "Tab", "Shift_L", "Shift_R"):
            return
        typed = self.entry.get().strip()
        if len(typed) < 2:
            self._close_listbox()
            return
        results = self.mapper.search_games(typed, limit=15)
        if results:
            self._show_suggestions(results)
        else:
            self._close_listbox()

    def _show_suggestions(self, results):
        self._close_listbox()
        self.listbox = tk.Listbox(
            self.frame, width=45, height=min(len(results), 8),
            font=("Arial", 10), activestyle="dotbox",
            selectbackground="#6d4aff", selectforeground="white"
        )
        self.listbox.pack(fill=tk.X)
        self._raw_results = results
        for tid, name in results:
            self.listbox.insert(tk.END, f"{name}  [{tid}]")
        self.listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

    def _close_listbox(self):
        if self.listbox is not None:
            self.listbox.destroy()
            self.listbox = None
        self._raw_results = []

    def _on_listbox_select(self, event):
        self._select_current_item()

    def _on_arrow_down(self, event):
        if self.listbox and self.listbox.size() > 0:
            current = self.listbox.curselection()
            next_idx = min(current[0] + 1, self.listbox.size() - 1) if current else 0
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(next_idx)
            self.listbox.see(next_idx)
            self.listbox.activate(next_idx)
        elif self._raw_results:
            self._show_suggestions(self._raw_results)
        return "break"

    def _on_arrow_up(self, event):
        if self.listbox and self.listbox.size() > 0:
            current = self.listbox.curselection()
            prev_idx = max(current[0] - 1, 0) if current else 0
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(prev_idx)
            self.listbox.see(prev_idx)
            self.listbox.activate(prev_idx)
        return "break"

    def _on_enter(self, event):
        if self.listbox and self.listbox.curselection():
            self._select_current_item()
        elif self.listbox and self.listbox.size() > 0:
            self.listbox.selection_set(0)
            self._select_current_item()
        return "break"

    def _select_current_item(self):
        if not self.listbox or not self.listbox.curselection():
            return
        idx = self.listbox.curselection()[0]
        if idx < len(self._raw_results):
            tid, name = self._raw_results[idx]
            self.selected_title_id = tid
            self.selected_game_name = name
            self.entry.delete(0, tk.END)
            self.entry.insert(0, name)
            self.entry.icursor(tk.END)
            self._close_listbox()
            if self.on_select_callback:
                self.on_select_callback(tid, name)

    def _on_focus_out(self, event):
        self.frame.after(250, self._close_listbox)

class FolderProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Switch Save Converter")
        self.root.geometry("850x550")
        self.selected_path = None
        self.mode = tk.StringVar(value="manual")
        self.status_var = tk.StringVar()
        self.status_var.set("Ready. Select mode and browse.")
        self.all_formats = ["Checkpoint", "Eden", "JKSV"]
        self.manual_formats = self.all_formats
        self.title_id_var = tk.StringVar()
        self.remove_tempfiles_var = tk.BooleanVar(value=False)
        self.disable_validation_var = tk.BooleanVar(value=False)
        self.mapper = get_mapper()
        self.override_title_id = None
        self.override_game_name = None

        # Store PhotoImages as CLASS ATTRIBUTES to prevent garbage collection
        self._icon_checkpoint = None
        self._icon_eden = None
        self._icon_jksv = None
        self.icons = {}

        if HAS_PILLOW:
            print("[ICON SETUP] Loading icons...")
            self._icon_checkpoint = IconFactory.load_checkpoint_icon(32)
            self._icon_eden = IconFactory.load_eden_icon(32)
            self._icon_jksv = IconFactory.load_jksv_icon(32)
            self.icons = {
                'checkpoint': self._icon_checkpoint,
                'eden': self._icon_eden,
                'jksv': self._icon_jksv
            }
            print(f"[ICON SETUP] Loaded {len([i for i in self.icons.values() if i])} icons")
            
            # Debug: List icons folder contents
            icons_dir = Path(__file__).parent / "icons"
            if icons_dir.exists():
                print(f"[FILES] Contents of icons/: {[f.name for f in icons_dir.iterdir()]}")
            else:
                print(f"[FILES] icons/ folder does not exist (fallback icons will be used)")
        else:
            print("[ICON SETUP] Pillow not available, no icons")

        # --- UI Layout ---
        title_label = tk.Label(root, text="Switch Save Converter", font=("Arial", 16, "bold"))
        title_label.pack(pady=5)

        mode_frame = tk.Frame(root)
        mode_frame.pack(pady=5)
        tk.Label(mode_frame, text="Mode:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="Manual Select", variable=self.mode, value="manual", command=self.update_ui_state).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="Newest Save File", variable=self.mode, value="newest", command=self.update_ui_state).pack(side=tk.LEFT, padx=5)

        config_frame = tk.Frame(root)
        config_frame.pack(pady=10)

        left_frame = tk.Frame(config_frame)
        left_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(left_frame, text="Source Format:", font=("Arial", 10)).pack(anchor=tk.W, pady=5)
        self.source_var = tk.StringVar(value=self.manual_formats[0])
        self.source_combo = ttk.Combobox(left_frame, textvariable=self.source_var, values=self.manual_formats, state="", width=15)
        self.source_combo.pack(pady=5)
        self.source_combo.bind("<<ComboboxSelected>>", lambda e: self.update_dropdowns())

        # SOURCE ICON LABEL - NO border, no yellow background
        self.source_icon_label = tk.Label(left_frame, width=32, height=32)
        self.source_icon_label.pack(pady=2)

        right_frame = tk.Frame(config_frame)
        right_frame.pack(side=tk.RIGHT, padx=20)
        tk.Label(right_frame, text="Target Format:", font=("Arial", 10)).pack(anchor=tk.W, pady=5)
        self.target_var = tk.StringVar(value=self.manual_formats[1])
        self.target_combo = ttk.Combobox(right_frame, textvariable=self.target_var, values=self.all_formats, state="", width=15)
        self.target_combo.pack(pady=5)
        self.target_combo.bind("<<ComboboxSelected>>", lambda e: self.update_dropdowns())

        # TARGET ICON LABEL - NO border, no yellow background
        self.target_icon_label = tk.Label(right_frame, width=32, height=32)
        self.target_icon_label.pack(pady=2)

        # GREEN ARROW
        arrow_frame = tk.Frame(config_frame, width=60)
        arrow_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        self.arrow_label = tk.Label(arrow_frame, text="➜", font=("Arial", 24, "bold"), fg="#4CAF50", bg="white", width=3)
        self.arrow_label.pack(expand=True)

        select_frame = tk.Frame(root)
        select_frame.pack(pady=10)
        self.path_entry = tk.Entry(select_frame, width=55, relief=tk.SUNKEN, fg="gray")
        self.path_entry.insert(0, "No folder selected")
        self.path_entry.pack(side=tk.LEFT, padx=5)
        self.path_entry.bind("<Return>", self._on_path_enter)
        self.select_btn = tk.Button(select_frame, text="Browse...", command=self.browse_folder)
        self.select_btn.pack(side=tk.LEFT, padx=5)

        game_frame = tk.Frame(root)
        game_frame.pack(pady=5)
        tk.Label(game_frame, text="Game:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.autocomplete = AutocompleteEntry(game_frame, self.mapper, on_select_callback=self._on_game_selected, width=35)
        self.autocomplete.pack(side=tk.LEFT, padx=5)
        self.game_hint = tk.Label(game_frame, text="(Type to search game title)", fg="gray", font=("Arial", 9))
        self.game_hint.pack(side=tk.LEFT, padx=5)

        title_id_frame = tk.Frame(root)
        title_id_frame.pack(pady=5)
        tk.Label(title_id_frame, text="Title ID:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.title_id_entry = tk.Entry(title_id_frame, textvariable=self.title_id_var, width=25, relief=tk.SUNKEN, fg="gray")
        self.title_id_entry.insert(0, "Auto-detected on conversion")
        self.title_id_entry.pack(side=tk.LEFT, padx=5)
        self.title_id_clear_btn = tk.Button(title_id_frame, text="Clear", command=self._clear_title_id_override)
        self.title_id_clear_btn.pack(side=tk.LEFT, padx=5)
        self.game_frame = game_frame
        self.title_id_frame = title_id_frame

        cleanup_frame = tk.Frame(root)
        cleanup_frame.pack(pady=5)
        self.cleanup_checkbutton = tk.Checkbutton(cleanup_frame, text="Remove temporary extraction files after conversion", variable=self.remove_tempfiles_var, font=("Arial", 10))
        self.cleanup_checkbutton.pack(anchor=tk.W, padx=20)
        self.cleanup_hint = tk.Label(cleanup_frame, text="(Recommended: Uncheck if you want to inspect extracted files)", fg="gray", font=("Arial", 9))
        self.cleanup_hint.pack(anchor=tk.W, padx=20)

        validation_frame = tk.Frame(root)
        validation_frame.pack(pady=5)
        self.validation_checkbutton = tk.Checkbutton(validation_frame, text="Disable all format validation", variable=self.disable_validation_var, font=("Arial", 10))
        self.validation_checkbutton.pack(anchor=tk.W, padx=20)
        self.validation_warning = tk.Label(validation_frame, text="Check this if you wish to manually name required saves yourself, or if you have issues with validation", font=("Arial", 9))
        self.validation_warning.pack(anchor=tk.W, padx=20)

        mapping_btn = tk.Button(root, text="Manage Title ID Mappings", command=self.open_mapping_manager, bg="#2196F3", font=("Arial", 10))
        mapping_btn.pack(pady=5)

        self.process_btn = tk.Button(root, text="Convert", command=self.process_folder, bg="#4CAF50", fg="white", font=("Arial", 12), state=tk.DISABLED)
        self.process_btn.pack(pady=10)

        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.cleanup_frame = cleanup_frame
        self.validation_frame = validation_frame

        # INITIALIZE ICONS AFTER ALL WIDGETS CREATED
        self._set_icon(self.source_icon_label, 'checkpoint')
        self._set_icon(self.target_icon_label, 'eden')

        self.update_ui_state()

    def _set_icon(self, label_widget, format_key):
        """Set icon on label - CRITICAL: keep PhotoImage reference"""
        if format_key in self.icons and self.icons[format_key]:
            label_widget.config(image=self.icons[format_key])
            # Keep reference on the widget
            label_widget.image = self.icons[format_key]
        else:
            label_widget.config(image='')
            label_widget.image = None

    def _update_source_icon(self):
        fmt = self.source_var.get().lower()
        self._set_icon(self.source_icon_label, fmt)

    def _update_target_icon(self):
        fmt = self.target_var.get().lower()
        self._set_icon(self.target_icon_label, fmt)

    def _on_path_enter(self, event):
        text = self.path_entry.get().strip()
        if not text or text == "No folder selected":
            messagebox.showwarning("Empty Path", "Please enter a valid file or folder path.")
            return
        path_obj = Path(text)
        if not path_obj.exists():
            messagebox.showerror("Path Not Found", f"The path does not exist:\n{text}")
            return
        source_format = self.source_var.get()
        mode = self.mode.get()
        if mode == "manual":
            if source_format in ["Eden", "JKSV"] and path_obj.is_file():
                if path_obj.suffix.lower() != ".zip":
                    messagebox.showwarning("Invalid File", "Eden/JKSV sources must be .zip files.")
                    return
            self.selected_path = path_obj
            self._set_path_display(str(path_obj), "black")
            self.process_btn.config(state=tk.NORMAL)
            if path_obj.is_dir():
                self.status_var.set(f"Selected Folder: {path_obj.name}")
            else:
                self.status_var.set(f"Selected File: {path_obj.name}")
        else:
            if not path_obj.is_dir():
                messagebox.showwarning("Invalid Path", "In Newest Save File mode, the path must be a directory.")
                return
            self.selected_path = path_obj
            self._set_path_display(str(path_obj), "black")
            self.process_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Selected: {path_obj.name}")

    def _on_game_selected(self, title_id, game_name):
        self.override_title_id = title_id
        self.override_game_name = game_name
        self.title_id_var.set(title_id)
        self.title_id_entry.config(fg="black")
        self.status_var.set(f"Selected: {game_name} ({title_id})")

    def _clear_title_id_override(self):
        self.autocomplete.clear()
        self.override_title_id = None
        self.override_game_name = None
        self.title_id_var.set("")
        self.title_id_entry.config(fg="gray")
        self.title_id_entry.config(state=tk.NORMAL)
        self.title_id_entry.delete(0, tk.END)
        self.title_id_entry.insert(0, "Auto-detected on conversion")
        self.title_id_entry.config(state='readonly')

    def _set_path_display(self, text, color="gray"):
        self.path_entry.config(state=tk.NORMAL)
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, text)
        self.path_entry.config(fg=color)
        self.path_entry.xview_moveto(1.0)

    def open_mapping_manager(self):
        from tkinter import Toplevel, Entry, messagebox
        import tkinter.ttk as ttk
        mapper = self.mapper
        refresh_window = Toplevel(self.root)
        refresh_window.title("Title ID Mapper Manager")
        refresh_window.geometry("750x600")
        status = tk.Label(refresh_window, text="", fg="blue")
        status.pack(pady=5)

        def _refresh_mappings_in_window():
            status.config(text="Refreshing...", fg="blue")
            refresh_window.update()
            mapper.fetch_remote_data()
            refresh_treeview()
            status.config(text=f"Loaded {len(mapper.id_to_name)} mappings", fg="green")

        def refresh_treeview():
            treeview.delete(*treeview.get_children())
            for tid, name in mapper.get_manual_overrides():
                treeview.insert("", "end", values=(tid, name), tags=(tid,))

        def _on_treeview_select(event):
            selection = treeview.selection()
            if selection:
                delete_btn.config(state=tk.NORMAL)
            else:
                delete_btn.config(state=tk.DISABLED)

        def add_override():
            tid = id_entry.get().strip()
            name = name_entry.get().strip()
            if tid and name:
                if mapper.add_manual_override(tid, name):
                    treeview.insert("", "end", values=(tid, name), tags=(mapper._normalize_tid(tid),))
                    status.config(text=f"Added: {tid} -> {name}", fg="green")
                else:
                    status.config(text="Failed to add override", fg="red")
            else:
                status.config(text="Please fill in both fields", fg="red")

        def remove_selected():
            selection = treeview.selection()
            if not selection:
                status.config(text="Please select an override to remove", fg="red")
                return
            selected_items = treeview.selection()
            deleted_count = 0
            for item in selected_items:
                tid = treeview.item(item)['values'][0]
                if messagebox.askyesno("Confirm Delete", f"Delete manual override for {tid}?\n\nThis cannot be undone."):
                    if mapper.remove_manual_override(tid):
                        treeview.delete(item)
                        deleted_count += 1
            if deleted_count > 0:
                status.config(text=f"Removed {deleted_count} override(s)", fg="green")
                if deleted_count == len(selected_items):
                    delete_btn.config(state=tk.DISABLED)

        header_label = tk.Label(refresh_window, text="Manual Overrides", font=("Arial", 10, "bold"))
        header_label.pack(anchor=tk.W, padx=10, pady=5)
        tree_frame = tk.Frame(refresh_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        treeview = ttk.Treeview(tree_frame, columns=("title_id", "game_name"), show="headings", yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        treeview.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.config(command=treeview.yview)
        scrollbar_x.config(command=treeview.xview)
        treeview.heading("title_id", text="Title ID", anchor=tk.W)
        treeview.heading("game_name", text="Game Name", anchor=tk.W)
        treeview.column("title_id", width=200, minwidth=150)
        treeview.column("game_name", width=400, minwidth=300)
        treeview.bind("<<TreeviewSelect>>", _on_treeview_select)
        for tid, name in mapper.get_manual_overrides():
            treeview.insert("", "end", values=(tid, name), tags=(mapper._normalize_tid(tid),))
        add_frame = tk.Frame(refresh_window)
        add_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(add_frame, text="Title ID:").pack(side=tk.LEFT, padx=2)
        id_entry = Entry(add_frame, width=15)
        id_entry.pack(side=tk.LEFT, padx=2)
        tk.Label(add_frame, text="Game Name:").pack(side=tk.LEFT, padx=2)
        name_entry = Entry(add_frame, width=20)
        name_entry.pack(side=tk.LEFT, padx=2)
        btn_frame = tk.Frame(add_frame)
        btn_frame.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Add Override", command=add_override, bg="#4CAF50").pack(side=tk.LEFT, padx=2)
        delete_btn = tk.Button(btn_frame, text="Delete Selected", command=remove_selected, state=tk.DISABLED, bg="#d32f2f")
        delete_btn.pack(side=tk.LEFT, padx=2)
        self.delete_btn_ref = delete_btn
        refresh_btn_frame = tk.Frame(refresh_window)
        refresh_btn_frame.pack(pady=5)
        tk.Button(refresh_btn_frame, text="Refresh Remote Data", command=_refresh_mappings_in_window, bg="#2196F3").pack(side=tk.LEFT, padx=5)
        close_btn_frame = tk.Frame(refresh_window)
        close_btn_frame.pack(pady=5)
        tk.Button(close_btn_frame, text="Close", command=refresh_window.destroy).pack()
        if treeview.get_children():
            treeview.selection_set(treeview.get_children()[0])
            delete_btn.config(state=tk.NORMAL)

    def update_ui_state(self):
        mode = self.mode.get()
        if mode == "manual":
            self.source_combo['values'] = ["Checkpoint", "Eden", "JKSV"]
            self.select_btn.config(text="Browse Save Folder")
            self._set_path_display("Select the specific save folder or zip file.")
            if self.source_var.get() not in ["Checkpoint", "Eden", "JKSV"]:
                self.source_var.set("Checkpoint")
        else:
            self.source_combo['values'] = ["Checkpoint", "Eden", "JKSV"]
            self.select_btn.config(text="Browse Parent Directory")
            self._set_path_display("Select the parent directory. The newest save inside will be converted.")
            if self.source_var.get() not in ["Checkpoint", "Eden", "JKSV"]:
                self.source_var.set("Checkpoint")
        if self.selected_path:
            self.process_btn.config(state=tk.NORMAL)
        else:
            self.process_btn.config(state=tk.DISABLED)
        self.update_button_text()
        self.toggle_title_id_field()
        self.toggle_cleanup_field()
        self.update_dropdowns()

    def toggle_title_id_field(self):
        source_format = self.source_var.get()
        if source_format == "Eden":
            self.title_id_frame.pack(pady=5)
        else:
            self.title_id_frame.pack(pady=5)

    def toggle_cleanup_field(self):
        source_format = self.source_var.get()
        if source_format in ["Eden", "JKSV"]:
            self.cleanup_frame.pack(pady=5)
            self.remove_tempfiles_var.set(False)
        else:
            self.cleanup_frame.pack_forget()
            self.remove_tempfiles_var.set(False)

    def update_cleanup_visibility(self):
        source_format = self.source_var.get()
        mode = self.mode.get()
        if source_format in ["Eden", "JKSV"] and mode == "manual":
            self.cleanup_hint.config(text="(Recommended: Uncheck if you want to inspect extracted files)")
        else:
            self.cleanup_hint.config(text="(Only affects zip extractions)")

    def update_dropdowns(self):
        source_val = self.source_var.get()
        target_val = self.target_var.get()
        available_targets = [opt for opt in self.all_formats if opt != source_val]
        self.target_combo['values'] = available_targets
        if target_val == source_val:
            if available_targets:
                self.target_var.set(available_targets[0])
            else:
                self.target_var.set("")
        self.update_button_text()
        self.toggle_title_id_field()
        self.toggle_cleanup_field()
        self.update_cleanup_visibility()
        self._update_source_icon()
        self._update_target_icon()

    def update_button_text(self):
        mode = self.mode.get()
        source_format = self.source_var.get()
        if mode == "manual":
            if source_format == "Checkpoint":
                self.select_btn.config(text="Select Checkpoint Folder")
            elif source_format in ["Eden", "JKSV"]:
                self.select_btn.config(text=f"Select {source_format} Zip")
            else:
                self.select_btn.config(text="Browse...")
        else:
            self.select_btn.config(text="Select Game Folder")

    def browse_folder(self):
        mode = self.mode.get()
        source_format = self.source_var.get()
        if mode == "manual":
            if source_format == "Checkpoint":
                folder_selected = filedialog.askdirectory(title="Select Checkpoint Save Folder")
                if folder_selected:
                    self.selected_path = Path(folder_selected)
                    self._set_path_display(str(self.selected_path), "black")
                    self.process_btn.config(state=tk.NORMAL)
                    self.status_var.set(f"Selected Folder: {self.selected_path.name}")
            elif source_format in ["Eden", "JKSV"]:
                file_selected = filedialog.askopenfilename(title=f"Select {source_format} Save Zip", filetypes=[("Zip files", "*.zip"), ("All files", "*.*")])
                if file_selected:
                    path_obj = Path(file_selected)
                    if path_obj.suffix.lower() != ".zip":
                        messagebox.showwarning("Invalid File", "Please select a .zip file.")
                        return
                    self.selected_path = path_obj
                    self._set_path_display(str(path_obj), "black")
                    self.process_btn.config(state=tk.NORMAL)
                    self.status_var.set(f"Selected Zip: {path_obj.name}")
            else:
                messagebox.showerror("Error", "Invalid Source Format selected.")
                return
        else:
            folder_selected = filedialog.askdirectory(title="Select Parent Directory")
            if folder_selected:
                self.selected_path = Path(folder_selected)
                self._set_path_display(str(self.selected_path), "black")
                self.process_btn.config(state=tk.NORMAL)
                self.status_var.set(f"Selected: {self.selected_path.name}")

    def process_folder(self):
        if not self.selected_path:
            return
        source_format = self.source_var.get().strip()
        target_format = self.target_var.get().strip()
        is_auto = self.mode.get() == "newest"
        title_id = self.title_id_var.get().strip()
        remove_tempfiles = self.remove_tempfiles_var.get()
        valid_formats = ["Checkpoint", "Eden", "JKSV"]
        if source_format not in valid_formats:
            messagebox.showerror("Invalid Source", f"'{source_format}' is not a valid format.\nPlease select from: {', '.join(valid_formats)}")
            return
        if target_format not in valid_formats:
            messagebox.showerror("Invalid Target", f"'{target_format}' is not a valid format.\nPlease select from: {', '.join(valid_formats)}")
            return
        if source_format == target_format:
            messagebox.showerror("Invalid Selection", "Source and Target cannot be the same!")
            return
        if source_format == "Eden" and not title_id:
            title_id = None
        self.status_var.set("Processing...")
        self.process_btn.config(state=tk.DISABLED)
        self.root.update()
        try:
            converter = SaveConverterLogic(self.selected_path)
            zip_filename, original_name, status_msg = converter.convert(source_format, target_format, title_id=title_id, is_auto_mode=is_auto, remove_tempfiles_when_done=remove_tempfiles)
            self.status_var.set(f"{status_msg} -> {target_format}")
            self.root.update()
            cleanup_note = " (temp files removed)" if remove_tempfiles else ""
            self.status_var.set(f"Success! Created {zip_filename}{cleanup_note}")
            messagebox.showinfo("Success", f"Conversion complete!\nSource: {original_name}\nCreated: {zip_filename}{cleanup_note}")
        except FileNotFoundError as e:
            self.status_var.set("Error: Folder not found.")
            messagebox.showerror("Error", str(e))
        except ValueError as e:
            self.status_var.set("Error: Format mismatch.")
            messagebox.showerror("Format Error", str(e))
        except Exception as e:
            self.status_var.set("Error occurred.")
            messagebox.showerror("Error", str(e))
        finally:
            self.process_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = FolderProcessorApp(root)
        root.mainloop()
    except tk.TclError as e:
        messagebox.showerror("Tkinter Error", f"Could not initialize GUI. Ensure 'python-tk' is installed.\nError: {e}")