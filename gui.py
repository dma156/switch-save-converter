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
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from convert import SaveConverterLogic
from mapping import get_mapper


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

        # Container frame holds both the entry and the listbox
        self.frame = tk.Frame(parent)

        # The text entry
        self.entry = tk.Entry(self.frame, width=width)
        self.entry.pack(fill=tk.X)

        # The suggestion listbox (hidden by default)
        self.listbox = None
        self._raw_results = []

        # Bind events
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
        # Ignore navigation keys — handled by dedicated bindings
        if event.keysym in ("Down", "Up", "Return", "Escape", "Tab", "Shift_L", "Shift_R"):
            return

        typed = self.entry.get().strip()

        if len(typed) < 2:
            self._close_listbox()
            return

        # Search the mapper
        results = self.mapper.search_games(typed, limit=15)

        if results:
            self._show_suggestions(results)
        else:
            self._close_listbox()

    def _show_suggestions(self, results):
        self._close_listbox()

        # Create a Listbox positioned right below the entry
        self.listbox = tk.Listbox(
            self.frame,
            width=45,
            height=min(len(results), 8),
            font=("Arial", 10),
            activestyle="dotbox",
            selectbackground="#6d4aff",
            selectforeground="white"
        )
        self.listbox.pack(fill=tk.X)

        # Populate results
        self._raw_results = results
        for tid, name in results:
            self.listbox.insert(tk.END, f"{name}  [{tid}]")

        # Bind selection
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
            if current:
                next_idx = min(current[0] + 1, self.listbox.size() - 1)
            else:
                next_idx = 0
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(next_idx)
            self.listbox.see(next_idx)
            self.listbox.activate(next_idx)
        elif self._raw_results:
            # No listbox yet but we have cached results, show them
            self._show_suggestions(self._raw_results)
        return "break"

    def _on_arrow_up(self, event):
        if self.listbox and self.listbox.size() > 0:
            current = self.listbox.curselection()
            if current:
                prev_idx = max(current[0] - 1, 0)
            else:
                prev_idx = 0
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(prev_idx)
            self.listbox.see(prev_idx)
            self.listbox.activate(prev_idx)
        return "break"

    def _on_enter(self, event):
        if self.listbox and self.listbox.curselection():
            self._select_current_item()
        elif self.listbox and self.listbox.size() > 0:
            # No selection but suggestions exist — pick first
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
        # Small delay so listbox click events register before closing
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
        self.newest_formats = ["Checkpoint", "Eden", "JKSV"]

        self.title_id_var = tk.StringVar()
        self.remove_tempfiles_var = tk.BooleanVar(value=False)
        self.disable_validation_var = tk.BooleanVar(value=False)

        # Get mapper instance
        self.mapper = get_mapper()
        self.override_title_id = None
        self.override_game_name = None

        # --- UI Layout ---

        title_label = tk.Label(root, text="Switch Save Converter", font=("Arial", 16, "bold"))
        title_label.pack(pady=5)

        # Mode Selection
        mode_frame = tk.Frame(root)
        mode_frame.pack(pady=5)
        tk.Label(mode_frame, text="Mode:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="Manual Select", variable=self.mode, value="manual", command=self.update_ui_state).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="Newest Save File", variable=self.mode, value="newest", command=self.update_ui_state).pack(side=tk.LEFT, padx=5)

        # Configuration Frame
        config_frame = tk.Frame(root)
        config_frame.pack(pady=10)

        left_frame = tk.Frame(config_frame)
        left_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(left_frame, text="Source Format:", font=("Arial", 10)).pack(anchor=tk.W)
        self.source_var = tk.StringVar(value=self.manual_formats[0])
        self.source_combo = ttk.Combobox(left_frame, textvariable=self.source_var, values=self.manual_formats, state="", width=15)
        self.source_combo.pack(pady=5)
        self.source_combo.bind("<<ComboboxSelected>>", lambda e: self.update_target_dropdowns())

        right_frame = tk.Frame(config_frame)
        right_frame.pack(side=tk.RIGHT, padx=20)
        tk.Label(right_frame, text="Target Format:", font=("Arial", 10)).pack(anchor=tk.W)
        self.target_var = tk.StringVar(value=self.manual_formats[1])
        self.target_combo = ttk.Combobox(right_frame, textvariable=self.target_var, values=self.all_formats, state="", width=15)
        self.target_combo.pack(pady=5)
        self.target_combo.bind("<<ComboboxSelected>>", lambda e: self.update_target_dropdowns())

        # Selection Frame
        select_frame = tk.Frame(root)
        select_frame.pack(pady=10)
        self.path_entry = tk.Entry(select_frame, width=55, relief=tk.SUNKEN, fg="gray")
        self.path_entry.insert(0, "No folder selected")
        self.path_entry.pack(side=tk.LEFT, padx=5)
        self.path_entry.bind("<Return>", self._on_path_enter)
        self.select_btn = tk.Button(select_frame, text="Browse...", command=self.browse_folder)
        self.select_btn.pack(side=tk.LEFT, padx=5)

        # Game Selection (Autocomplete)
        game_frame = tk.Frame(root)
        game_frame.pack(pady=5)
        tk.Label(game_frame, text="Game:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        self.autocomplete = AutocompleteEntry(
            game_frame,
            self.mapper,
            on_select_callback=self._on_game_selected,
            width=35
        )
        self.autocomplete.pack(side=tk.LEFT, padx=5)

        self.game_hint = tk.Label(game_frame, text="(Type to search game title)", fg="gray", font=("Arial", 9))
        self.game_hint.pack(side=tk.LEFT, padx=5)

        # Detected Title ID display
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

        # Cleanup checkbox
        cleanup_frame = tk.Frame(root)
        cleanup_frame.pack(pady=5)
        self.cleanup_checkbutton = tk.Checkbutton(
            cleanup_frame,
            text="Remove temporary extraction files after conversion",
            variable=self.remove_tempfiles_var,
            font=("Arial", 10)
        )
        self.cleanup_checkbutton.pack(anchor=tk.W, padx=20)
        self.cleanup_hint = tk.Label(
            cleanup_frame,
            text="(Recommended: Uncheck if you want to inspect extracted files)",
            fg="gray", font=("Arial", 9)
        )
        self.cleanup_hint.pack(anchor=tk.W, padx=20)

        # Validation checkbox
        validation_frame = tk.Frame(root)
        validation_frame.pack(pady=5)
        self.validation_checkbutton = tk.Checkbutton(
            validation_frame,
            text="Disable all format validation",
            variable=self.disable_validation_var,
            font=("Arial", 10)
        )
        self.validation_checkbutton.pack(anchor=tk.W, padx=20)
        self.validation_warning = tk.Label(
            validation_frame,
            text="Check this if you wish to manually name required saves yourself, or if you have issues with validation",
            font=("Arial", 9)
        )
        self.validation_warning.pack(anchor=tk.W, padx=20)

        # Mapping manager button
        mapping_btn = tk.Button(root, text="Manage Title ID Mappings", command=self.open_mapping_manager,
                                bg="#2196F3", font=("Arial", 10))
        mapping_btn.pack(pady=5)

        # Convert button
        self.process_btn = tk.Button(root, text="Convert", command=self.process_folder,
                                      bg="#4CAF50", fg="white", font=("Arial", 12), state=tk.DISABLED)
        self.process_btn.pack(pady=10)

        # Status bar
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.cleanup_frame = cleanup_frame
        self.validation_frame = validation_frame

        self.update_ui_state()

    def _on_path_enter(self, event):
        """Handle Enter key press in the path entry to set the source path."""
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
            # Validate file type for zip-based formats
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
            # Auto mode - must be a directory
            if not path_obj.is_dir():
                messagebox.showwarning("Invalid Path", "In Newest Save File mode, the path must be a directory.")
                return
            
            self.selected_path = path_obj
            self._set_path_display(str(path_obj), "black")
            self.process_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Selected: {path_obj.name}")

    def _on_game_selected(self, title_id, game_name):
        """Called when a game is selected from the autocomplete dropdown."""
        self.override_title_id = title_id
        self.override_game_name = game_name

        self.title_id_var.set(title_id)
        self.title_id_entry.config(fg="black")
        self.status_var.set(f"Selected: {game_name} ({title_id})")

    def _clear_title_id_override(self):
        """Clear the manually selected game/title ID."""
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
        """Open a window to manage title ID mappings with a two-column table."""
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
            """Refresh the Treeview with current manual overrides."""
            # Clear existing items
            treeview.delete(*treeview.get_children())
            
            # Insert new items
            for tid, name in mapper.get_manual_overrides():
                treeview.insert("", "end", values=(tid, name), tags=(tid,))

        def _on_treeview_select(event):
            """Enable/disable delete button based on selection."""
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
                    # Add to Treeview
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
            
            # Get selected item(s)
            selected_items = treeview.selection()
            deleted_count = 0
            
            for item in selected_items:
                tid = treeview.item(item)['values'][0]
                
                # Confirm deletion
                if messagebox.askyesno("Confirm Delete", 
                                       f"Delete manual override for {tid}?\n\nThis cannot be undone."):
                    if mapper.remove_manual_override(tid):
                        treeview.delete(item)
                        deleted_count += 1
            
            if deleted_count > 0:
                status.config(text=f"Removed {deleted_count} override(s)", fg="green")
                if deleted_count == len(selected_items):
                    delete_btn.config(state=tk.DISABLED)

        # Header
        header_label = tk.Label(refresh_window, text="Manual Overrides",
                                font=("Arial", 10, "bold"))
        header_label.pack(anchor=tk.W, padx=10, pady=5)

        # Treeview with scrollbars
        tree_frame = tk.Frame(refresh_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Create Treeview
        treeview = ttk.Treeview(
            tree_frame,
            columns=("title_id", "game_name"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        treeview.pack(fill=tk.BOTH, expand=True)

        scrollbar_y.config(command=treeview.yview)
        scrollbar_x.config(command=treeview.xview)

        # Configure columns
        treeview.heading("title_id", text="Title ID", anchor=tk.W)
        treeview.heading("game_name", text="Game Name", anchor=tk.W)
        
        treeview.column("title_id", width=200, minwidth=150)
        treeview.column("game_name", width=400, minwidth=300)

        # Bind selection event
        treeview.bind("<<TreeviewSelect>>", _on_treeview_select)

        # Populate with existing overrides
        for tid, name in mapper.get_manual_overrides():
            treeview.insert("", "end", values=(tid, name), tags=(mapper._normalize_tid(tid),))

        # Input frame
        add_frame = tk.Frame(refresh_window)
        add_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(add_frame, text="Title ID:").pack(side=tk.LEFT, padx=2)
        id_entry = Entry(add_frame, width=15)
        id_entry.pack(side=tk.LEFT, padx=2)

        tk.Label(add_frame, text="Game Name:").pack(side=tk.LEFT, padx=2)
        name_entry = Entry(add_frame, width=20)
        name_entry.pack(side=tk.LEFT, padx=2)

        # Buttons
        btn_frame = tk.Frame(add_frame)
        btn_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Add Override", command=add_override,
                  bg="#4CAF50").pack(side=tk.LEFT, padx=2)
        
        delete_btn = tk.Button(btn_frame, text="Delete Selected", command=remove_selected,
                               state=tk.DISABLED, bg="#d32f2f")
        delete_btn.pack(side=tk.LEFT, padx=2)
        self.delete_btn_ref = delete_btn

        # Refresh button
        refresh_btn_frame = tk.Frame(refresh_window)
        refresh_btn_frame.pack(pady=5)
        tk.Button(refresh_btn_frame, text="Refresh Remote Data",
                  command=_refresh_mappings_in_window, bg="#2196F3").pack(side=tk.LEFT, padx=5)

        # Close button
        close_btn_frame = tk.Frame(refresh_window)
        close_btn_frame.pack(pady=5)
        tk.Button(close_btn_frame, text="Close", command=refresh_window.destroy).pack()

        # Select first item by default (if exists)
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
        self.update_target_dropdowns()

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

    def update_target_dropdowns(self):
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
                file_selected = filedialog.askopenfilename(
                    title=f"Select {source_format} Save Zip",
                    filetypes=[("Zip files", "*.zip"), ("All files", "*.*")]
                )
                if file_selected:
                    path_obj = Path(file_selected)
                    if path_obj.suffix.lower() != ".zip":
                        messagebox.showwarning("Invalid File", "Please select a .zip file.")
                        return
                    self.selected_path = path_obj
                    self._set_path_display(str(self.selected_path), "black")
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
        """Executes conversion with validation for custom inputs."""
        if not self.selected_path:
            return

        source_format = self.source_var.get().strip()
        target_format = self.target_var.get().strip()
        is_auto = self.mode.get() == "newest"
        title_id = self.title_id_var.get().strip()
        remove_tempfiles = self.remove_tempfiles_var.get()

        # Validation for Custom Inputs
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

        # No longer restricting Eden in auto mode - now supports Eden -> Checkpoint/JKSV

        # Validate Title ID for Eden (optional but recommended)
        if source_format == "Eden" and not title_id:
            title_id = None  # Will trigger auto-detection in convert.py

        self.status_var.set("Processing...")
        self.process_btn.config(state=tk.DISABLED)
        self.root.update()

        try:
            # Pass title_id and remove_tempfiles to the converter
            converter = SaveConverterLogic(self.selected_path)
            zip_filename, original_name, status_msg = converter.convert(
                source_format, 
                target_format, 
                title_id=title_id, 
                is_auto_mode=is_auto, 
                remove_tempfiles_when_done=remove_tempfiles
            )
            
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