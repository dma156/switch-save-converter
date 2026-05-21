#!/usr/bin/env python3
"""
Core logic for Switch Save Converter.
Supports two modes:
1. Manual: Convert a specific selected folder/zip.
2. Auto: Find the latest modified save in a parent directory and convert it.
"""
import os
import shutil
import zipfile
import re
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any


class SaveConverterLogic:
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def _parse_date_string(self, date, save_format) -> Date:
        """
        return a converted Date obj corresponding to the selected save_format
        """
        # YYYY-MM-DD HH_mm
        if save_format == "Eden":
            return datetime.strptime(date, "%Y-%m-%d %H_%M")
        # YYYYMMDD-HHmmss
        if save_format == "Checkpoint":
            return datetime.strptime(date, "%Y%m%d-%H%M%S")
        # YYYY-MM-DD_HH-mm-ss
        if save_format == "JKSV":
            return datetime.strptime(date, "%Y-%m-%d_%H-%M-%S")


    def _get_date_string(self, date : Date, save_format) -> str:
        """
        return a converted date string in a different date string format corresponding to the selected save_format
        """
        # YYYY-MM-DD HH_mm
        if save_format == "Eden":
            return datetime.strftime("%Y-%m-%d %H_%M")
        # YYYYMMDD-HHmmss
        if save_format == "Checkpoint":
            return datetime.strftime("%Y%m%d-%H%M%S")
        # YYYY-MM-DD_HH-mm-ss
        if save_format == "JKSV":
            return datetime.strftime("%Y-%m-%d_%H-%M-%S")

    # --- Validation Logic ---

    def _validate_checkpoint_structure(self, target_path: Path) -> bool:
        """
        Validates Checkpoint structure for AUTO mode.
        1. Checks if Path directory (the game folder) starts with "0x".
        2. Finds the NEWEST folder inside that game folder.
        3. Validates the newest folder's name.
        """
        if not target_path.name.startswith("0x"):
            return False
            
        inner_dirs = [d for d in target_path.iterdir() if d.is_dir()]
        if not inner_dirs:
            return False
            
        newest_inner = max(inner_dirs, key=lambda p: p.stat().st_mtime)
        return self._validate_checkpoint_save(newest_inner)

    def _validate_checkpoint_save(self, save_folder_path: Path) -> bool:
        """
        Validates the specific folder name for the 'Date Time Username' structure.
        Expects format: YYYYMMDD-HHmmss Username
        """
        folder_name = save_folder_path.name
        match = re.match(r"^(\d{8})-(\d{6})\s+(.+)$", folder_name)
        return bool(match)

    def _validate_jksv_structure(self, target_path: Path) -> bool:
        """
        Validates JKSV structure: Game Title -> User - YYYY-MM-DD-HH_mm_ss.zip
        Finds the NEWEST zip file in the directory and validates it.
        """
        if target_path.is_file():
            return self._validate_jksv_save(target_path)
        
        # Directory mode: Find all zips, pick newest
        zip_files = [f for f in target_path.iterdir() if f.is_file() and f.suffix == ".zip"]
        if not zip_files:
            return False
        
        newest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
        return self._validate_jksv_save(newest_zip)

    def _validate_jksv_save(self, save_zip: Path) -> bool:
        """
        Check filename format: "String - YYYY-MM-DD_HH-mm-ss"
        Allows whitespace in 'String' (e.g., "User Name - Date").
        """
        # Regex breakdown:
        # ^              : Start of string
        # (.+)           : Capture Group 1: One or more of ANY character (including spaces) for the "String" part
        # \s+-\s+        : One or more spaces, a hyphen, one or more spaces (the separator " - ")
        # (\d{4}-...)    : Capture Group 2: The specific date/time format
        # \.zip$         : Ends with .zip
        pattern = r"^(.+)\s+-\s+(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.zip$"
        
        if re.match(pattern, save_zip.name):
            return True
        return False

    def _validate_eden_structure(self, target_path: Path) -> bool:
        """
        Validates Eden structure.
        Finds the NEWEST zip file if directory, or validates file directly.
        """
        if target_path.is_file():
            if target_path.suffix != ".zip":
                return False
            return self._validate_eden_save(target_path)
        
        # Directory mode: Find all zips, pick newest
        zip_files = [f for f in target_path.iterdir() if f.is_file() and f.suffix == ".zip"]
        if not zip_files:
            return False
        
        newest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
        return self._validate_eden_save(newest_zip)

    def _validate_eden_save(self, save_zip: Path) -> bool:
        """
        Check filename format: "Game Name save data - YYYY-MM-DD HH_mm"
        """
        if re.match(r'^(.+)\s+save\s+data\s+-\s+(\d{4}-\d{2}-\d{2}\s+\d{2}_\d{2})\.zip$', save_zip.name):
            return True
        return False

    def _verify_source_format(self, target_path: Path, expected_format: str, is_auto_mode: bool) -> None:
        """Sanity check: Ensures the path matches the expected format."""
        if expected_format == "Checkpoint":
            if not is_auto_mode:
                if not self._validate_checkpoint_save(target_path):
                    raise ValueError(f"Format 'Checkpoint' mismatch in '{target_path.name}'.\nExpected folder name: \"DateTime User\" e.g. 20260422-193917 USERMAN")
            else:
                if not self._validate_checkpoint_structure(target_path):
                    raise ValueError(f"Format 'Checkpoint' mismatch in '{target_path.name}'.\nExpected: Folder starts with '0x' and contains a 'DateTime User' subfolder.")
        
        elif expected_format == "JKSV":
            if not is_auto_mode:
                if target_path.is_file():
                    if not self._validate_jksv_save(target_path):
                        raise ValueError(f"Format 'JKSV' mismatch in '{target_path.name}'.\nExpected zip file named \"User - DateTime\".")
                else:
                    if not self._validate_jksv_structure(target_path):
                        raise ValueError(f"Format 'JKSV' mismatch in '{target_path.name}'.\nExpected a zip file named \"User - DateTime\" inside the folder.")
            else:
                if not self._validate_jksv_structure(target_path):
                    raise ValueError(f"Format 'JKSV' mismatch in '{target_path.name}'.\nExpected: Game Title folder -> User - DateTime.zip")

        elif expected_format == "Eden":
            if not self._validate_eden_structure(target_path):
                raise ValueError(f"Format 'Eden' mismatch in '{target_path.name}'.\nExpected: \"[Game Name] save data - DateTime\".zip")
        else:
            raise ValueError(f"Unknown source format: {expected_format}")

    # --- Extraction Logic ---

    def _extract_info_from_checkpoint(self, target_path: Path) -> Dict[str, Any]:
        if target_path.name.startswith("0x"):
            # Auto Mode: target_path is the Game Folder
            id_title_folder = target_path
            folder_name = target_path.name
            
            inner_folders = [f for f in id_title_folder.iterdir() if f.is_dir()]
            if not inner_folders:
                raise ValueError("Checkpoint structure invalid: No save folder found.")
            date_user_folder = max(inner_folders, key=lambda p: p.stat().st_mtime)
        else:
            # Manual Mode: target_path IS the save folder (YYYYMMDD...)
            date_user_folder = target_path
            folder_name = target_path.name
            match = re.match(r"(\d{8})-(\d{6})\s+(.+)$", folder_name)
            if match:
                username = match.group(3)
                y, m, d = folder_name[:4], folder_name[4:6], folder_name[6:8]
                date_str = f"{y}-{m}-{d}"
            else:
                username = "Unknown"
                date_str = self._get_date_string()
            
            return {
                "game_title": "Unknown_Game",
                "user_id": "Unknown_ID",
                "date": date_str,
                "username": username,
                "source_files": list(date_user_folder.iterdir())
            }

        game_title = folder_name
        user_id = ""
        if folder_name.startswith("0x"):
            user_id = folder_name[:2]
            game_title = folder_name[2:].strip()
            if not game_title:
                game_title = "Unknown Game"
        else:
            user_id = folder_name
            game_title = "Unknown Game"

        inner_name = date_user_folder.name
        match = re.match(r"(\d{8})-(\d{6})\s+(.+)$", inner_name)
        if match:
            y, m, d = match.group(1)[:4], match.group(1)[4:6], match.group(1)[6:8]
            date_str = f"{y}-{m}-{d}"
            username = match.group(3)
        else:
            date_str = self._get_date_string()
            username = inner_name

        return {"game_title": game_title, "user_id": user_id, "date": date_str, "username": username, "source_files": list(date_user_folder.iterdir())}

    def _extract_info_from_jksv(self, target_path: Path) -> Dict[str, Any]:
        # Determine the zip file to use
        if target_path.is_file():
            if target_path.suffix != ".zip":
                raise ValueError("JKSV source must be a .zip file.")
            jksv_zip = target_path
            game_title = "Unknown_Game"
        else:
            # Directory mode: Find all zips, pick newest
            zip_files = [f for f in target_path.iterdir() if f.is_file() and f.suffix == ".zip"]
            if not zip_files:
                raise ValueError("JKSV structure invalid: No zip file found.")
            
            jksv_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
            
            # Try to find game title from parent folder name if possible
            # If the zip is directly in the root, we don't have a title folder
            # If the zip is in a subfolder, we use that subfolder name
            parent = jksv_zip.parent
            if parent == target_path:
                game_title = "Unknown_Game"
            else:
                game_title = parent.name

        zip_name = jksv_zip.stem
        parts = zip_name.split(" - ")
        username = parts[0] if len(parts) >= 1 else "Unknown User"
        date_str = parts[-1] if len(parts) >= 2 else self._get_date_string() # is this parsing the data properly???
        print(username)
        print(date_str)
        
        #wtf is this
        # if "-" in date_str:
        #     date_str = date_str.split("-")[0]
        # else:
        date_str = self._get_date_string()

        print(date_str)
            
        user_id = "Unknown_ID" 
        
        temp_extract_dir = self.base_path / "_temp_extract"
        temp_extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(jksv_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
            
        files_to_process = []
        for item in temp_extract_dir.iterdir():
            if item.is_file(): files_to_process.append(item)
            elif item.is_dir():
                for f in item.rglob("*"):
                    if f.is_file(): files_to_process.append(f)
        shutil.rmtree(temp_extract_dir)

        return {"game_title": game_title, "user_id": user_id, "date": date_str, "username": username, "source_files": files_to_process}

    def _extract_info_from_eden(self, target_path: Path) -> Dict[str, Any]:
        # Determine the zip file to use
        if target_path.is_file():
            if target_path.suffix != ".zip":
                raise ValueError("Eden source must be a .zip file.")
            eden_zip = target_path
        else:
            # Directory mode: Find all zips, pick newest
            zip_files = [f for f in target_path.iterdir() if f.is_file() and f.suffix == ".zip"]
            if not zip_files:
                raise ValueError("Eden structure invalid: No zip file found.")
            
            eden_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
            
        zip_name = eden_zip.stem
        parts = zip_name.split(" - ")
        date_str = parts[-1] if len(parts) >= 2 else self._get_date_string()
        if " " in date_str:
            date_str = date_str.split(" ")[0]
        elif "-" in date_str:
            date_str = date_str.split("-")[0]
        else:
            date_str = self._get_date_string()
            
        game_title = " ".join(parts[:-1]).replace(" save data", "").replace("Save Data", "").strip()
        
        temp_extract_dir = self.base_path / "_temp_extract"
        temp_extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(eden_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
            
        sub_folders = [f for f in temp_extract_dir.iterdir() if f.is_dir()]
        if not sub_folders: raise ValueError("Eden structure invalid: No Hex ID folder found.")
        
        id_folder = sub_folders[0]
        user_id = id_folder.name
        
        files_to_process = []
        for f in id_folder.rglob("*"):
            if f.is_file(): files_to_process.append(f)
        shutil.rmtree(temp_extract_dir)

        return {"game_title": game_title, "user_id": user_id, "date": date_str, "username": "Unknown", "source_files": files_to_process}

    # --- Main Conversion Logic ---

    def convert(self, source_format: str, target_format: str, is_auto_mode: bool = False) -> Tuple[str, str, str]:
        """
        Converts save data.
        Output files are saved in: script_directory/output/target_format/
        """
        if source_format == target_format:
            raise ValueError("Source and Target formats are identical.")

        # Determine the actual source path
        if is_auto_mode:
            candidates = []
            for item in self.base_path.iterdir():
                if item.is_dir():
                    candidates.append(item)
                elif item.is_file() and item.suffix == ".zip":
                    candidates.append(item)
            
            if not candidates:
                raise FileNotFoundError("No save folders or zip files found in the selected directory.")
            
            latest_item = max(candidates, key=lambda p: p.stat().st_mtime)
            source_path = latest_item
            original_source_name = latest_item.name
            status_msg = f"Auto-detected: {original_source_name}"
        else:
            source_path = self.base_path
            original_source_name = source_path.name
            status_msg = f"Manual selection: {original_source_name}"

        # Sanity Check
        self._verify_source_format(source_path, source_format, is_auto_mode)

        # Extract Info
        info = {}
        try:
            if source_format == "Checkpoint":
                info = self._extract_info_from_checkpoint(source_path)
            elif source_format == "JKSV":
                info = self._extract_info_from_jksv(source_path)
            elif source_format == "Eden":
                info = self._extract_info_from_eden(source_path)
            else:
                raise ValueError(f"Unsupported source format: {source_format}")
        except Exception as e:
            raise RuntimeError(f"Failed to parse source data: {str(e)}")

        # --- Output Directory Logic ---
        script_dir = Path(__file__).parent.resolve()
        output_base_dir = script_dir / "output"
        target_path = output_base_dir / target_format
        
        output_base_dir.mkdir(exist_ok=True)
        target_path.mkdir(exist_ok=True)
        
        files_to_copy = info["source_files"]
        game_title = info["game_title"]
        user_id = info["user_id"]
        date_str = info["date"]
        username = info["username"]

        if target_format == "Checkpoint":
            cp_id_title = f"{user_id} {game_title}"
            cp_inner_folder = target_path / cp_id_title
            cp_inner_folder.mkdir(exist_ok=True)
            cp_date_user = cp_inner_folder / f"{date_str} {username}"
            cp_date_user.mkdir(exist_ok=True)
            for src_file in files_to_copy:
                shutil.copy2(src_file, cp_date_user / src_file.name)
            
            zip_filename = f"{cp_id_title}.zip"
            zip_path = target_path / zip_filename
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(cp_inner_folder):
                    for file in files:
                        fp = Path(root) / file
                        arcname = fp.relative_to(target_path)
                        zipf.write(fp, arcname)

        elif target_format == "JKSV":
            jksv_title_folder = target_path / game_title
            jksv_title_folder.mkdir(exist_ok=True)
            jksv_zip_name = f"{username} - {date_str}.zip"
            jksv_zip_path = jksv_title_folder / jksv_zip_name
            with zipfile.ZipFile(jksv_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for src_file in files_to_copy:
                    zipf.write(src_file, src_file.name)
            zip_filename = jksv_zip_name

        elif target_format == "Eden":
            eden_zip_name = f"{game_title} Save Data - {date_str}.zip"
            eden_zip_path = target_path / eden_zip_name
            with zipfile.ZipFile(eden_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for src_file in files_to_copy:
                    arcname = f"{user_id}/{src_file.name}"
                    zipf.write(src_file, arcname)
            zip_filename = eden_zip_name

        else:
            raise ValueError(f"Unsupported target format: {target_format}")

        return zip_filename, original_source_name, status_msg