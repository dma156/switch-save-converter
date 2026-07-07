#!/usr/bin/env python3
"""
GUI for the Switch Save Converter.
Features:
- Editable Dropdowns (state=""): Users can select from list OR type.
- Logic: Source restricted by Mode; Target filtered by Source.
- No custom autocomplete logic; uses standard Tkinter behavior.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from convert import SaveConverterLogic


class FolderProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Switch Save Converter")
        self.root.geometry("750x350")
        
        self.selected_path = None
        self.mode = tk.StringVar(value="manual") # 'manual' or 'newest'
        self.status_var = tk.StringVar()
        self.status_var.set("Ready. Select mode and browse.")
        
        # Explicitly defined lists
        self.all_formats = ["Checkpoint", "Eden", "JKSV"]
        self.manual_formats = self.all_formats
        self.newest_formats = ["Checkpoint", "JKSV"]

        # --- UI Layout ---
        
        # Title
        title_label = tk.Label(root, text="Switch Save Converter", font=("Arial", 16, "bold"))
        title_label.pack(pady=5)

        # Mode Selection
        mode_frame = tk.Frame(root)
        mode_frame.pack(pady=5)
        tk.Label(mode_frame, text="Mode:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(mode_frame, text="Manual Select", variable=self.mode, value="manual", command=self.update_ui_state).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(mode_frame, text="Newest Save File", variable=self.mode, value="newest", command=self.update_ui_state).pack(side=tk.LEFT, padx=5)

        # Configuration Frame (Dropdowns)
        config_frame = tk.Frame(root)
        config_frame.pack(pady=10)

        # Left: Source Format
        left_frame = tk.Frame(config_frame)
        left_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(left_frame, text="Source Format:", font=("Arial", 10)).pack(anchor=tk.W)
        
        self.source_var = tk.StringVar(value=self.manual_formats[0])
        # state="" allows typing and standard dropdown behavior
        self.source_combo = ttk.Combobox(left_frame, textvariable=self.source_var, values=self.manual_formats, state="", width=15)
        self.source_combo.pack(pady=5)
        self.source_combo.bind("<<ComboboxSelected>>", lambda e: self.update_target_dropdowns())

        # Right: Target Format
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

        self.path_label = tk.Label(select_frame, text="No folder selected", fg="gray", width=50, anchor="w")
        self.path_label.pack(side=tk.LEFT, padx=5)

        self.select_btn = tk.Button(select_frame, text="Browse...", command=self.browse_folder)
        self.select_btn.pack(side=tk.LEFT, padx=5)

        # Action Button
        self.process_btn = tk.Button(root, text="Convert", command=self.process_folder, 
                                     bg="#4CAF50", fg="white", font=("Arial", 12), state=tk.DISABLED)
        self.process_btn.pack(pady=15)

        # Status Bar
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Initial setup
        self.update_ui_state()

    def update_ui_state(self):
        """Updates UI labels and Source dropdown options based on selected mode."""
        mode = self.mode.get()
        
        if mode == "manual":
            # Manual: Source allows ALL formats
            self.source_combo['values'] = ["Checkpoint", "Eden", "JKSV"]
            self.select_btn.config(text="Browse Save Folder")
            self.path_label.config(text="Select the specific save folder or zip file.")
            
            # Ensure source is valid
            if self.source_var.get() not in ["Checkpoint", "Eden", "JKSV"]:
                self.source_var.set("Checkpoint")

        else:
            # Newest: Source excludes Eden
            self.source_combo['values'] = ["Checkpoint", "JKSV"]
            self.select_btn.config(text="Browse Parent Directory")
            self.path_label.config(text="Select the parent directory. The newest save inside will be converted.")
            
            # If Eden was selected, force reset
            if self.source_var.get() == "Eden":
                self.source_var.set("Checkpoint")

        # Enable button only if path is selected
        if self.selected_path:
            self.process_btn.config(state=tk.NORMAL)
        else:
            self.process_btn.config(state=tk.DISABLED)

        # Call this to update the button text dynamically
        self.update_button_text()

        # Update Target dropdown based on the NEW Source selection
        self.update_target_dropdowns()

    def update_target_dropdowns(self):
        """Updates Target dropdown to exclude the currently selected Source format."""
        source_val = self.source_var.get()
        target_val = self.target_var.get()

        # 1. Calculate available targets (All formats MINUS Source)
        available_targets = [opt for opt in self.all_formats if opt != source_val]
        
        # 2. Update Target Combo Box
        self.target_combo['values'] = available_targets
        
        # 3. If current target is invalid (matches source), reset it to the first available
        if target_val == source_val:
            if available_targets:
                self.target_var.set(available_targets[0])
            else:
                self.target_var.set("")

        # FIX: Update button text whenever a dropdown changes
        self.update_button_text()

    def update_button_text(self):
        """Updates the Browse button text based on Mode and Source Format."""
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
            # Auto Mode
            self.select_btn.config(text="Select Game Folder")

    def browse_folder(self):
        """Opens file browser based on Mode and Source Format."""
        mode = self.mode.get()
        source_format = self.source_var.get()

        if mode == "manual":
            # MANUAL MODE: Behavior depends on Source Format
            if source_format == "Checkpoint":
                # Checkpoint expects a FOLDER structure
                folder_selected = filedialog.askdirectory(title="Select Checkpoint Save Folder")
                if folder_selected:
                    self.selected_path = Path(folder_selected)
                    self.path_label.config(text=str(self.selected_path), fg="black")
                    self.process_btn.config(state=tk.NORMAL)
                    self.status_var.set(f"Selected Folder: {self.selected_path.name}")
            
            elif source_format in ["Eden", "JKSV"]:
                # Eden and JKSV expect a ZIP file
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
                    self.path_label.config(text=str(self.selected_path), fg="black")
                    self.process_btn.config(state=tk.NORMAL)
                    self.status_var.set(f"Selected Zip: {path_obj.name}")
            else:
                messagebox.showerror("Error", "Invalid Source Format selected.")
                return

        else:
            # AUTO MODE: Always expects a Parent Directory
            folder_selected = filedialog.askdirectory(title="Select Parent Directory")
            if folder_selected:
                self.selected_path = Path(folder_selected)
                self.path_label.config(text=str(self.selected_path), fg="black")
                self.process_btn.config(state=tk.NORMAL)
                self.status_var.set(f"Selected: {self.selected_path.name}")

    def process_folder(self):
        """Executes conversion with validation for custom inputs."""
        if not self.selected_path:
            return

        source_format = self.source_var.get().strip()
        target_format = self.target_var.get().strip()
        is_auto = self.mode.get() == "newest"

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

        # Additional Mode Check for Source
        if is_auto and source_format == "Eden":
            messagebox.showerror("Mode Restriction", "Eden is not supported in 'Newest Save File' mode.")
            return

        self.status_var.set("Processing...")
        self.process_btn.config(state=tk.DISABLED)
        self.root.update()

        try:
            converter = SaveConverterLogic(self.selected_path)
            zip_filename, original_name, status_msg = converter.convert(
                source_format, target_format, is_auto_mode=is_auto
            )
            
            self.status_var.set(f"{status_msg} -> {target_format}")
            self.root.update()
            
            self.status_var.set(f"Success! Created {zip_filename}")
            messagebox.showinfo("Success", f"Conversion complete!\nSource: {original_name}\nCreated: {zip_filename}")

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