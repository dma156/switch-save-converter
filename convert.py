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
from typing import Tuple, Dict, Any, Union


class SaveConverterLogic:
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def _get_date_string(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    # --- Validation Logic ---

    def _validate_checkpoint_structure(self, target_path: Path) -> bool:
        """
        Validates Checkpoint structure for AUTO mode.
        1. Checks if Path directory (the game folder) starts with "0x".
        2. Finds the NEWEST folder inside that game folder.
        3. Validates the newest folder's name.
        """
        sub_dirs = [d for d in target_path.iterdir() if d.is_dir()]
        if not sub_dirs:
            return False

        # 1. Check if the selected folder name itself starts with "0x"
        if not target_path.name.startswith("0x"):
            return False
            
        # 2. Find the NEWEST folder inside the game folder
        inner_dirs = [d for d in save_folder.iterdir() if d.is_dir()]
        if not inner_dirs:
            return False
            
        newest_inner = max(inner_dirs, key=lambda p: p.stat().st_mtime)
        
        # 3. Validate the newest folder's name
        return self._validate_checkpoint_save(newest_inner)


    def _validate_checkpoint_save(self, save_folder_path: Path) -> bool:
        """
        Validates the specific folder name for the 'Date Time Username' structure.
        Expects format: YYYYMMDD-HHmmss Username
        Example: 20231025-143022 FOO
        """
        folder_name = save_folder_path.name
        
        # Regex: ^(\d{8})-(\d{6})\s+(.+)$
        return match = re.match(r"^(\d{8})-(\d{6})\s+(.+)$", folder_name)


    def _validate_jksv_structure(self, target_path: Path) -> bool:
        """
        Validates JKSV structure: Game Title -> User - YYYY-MM-DD-HH_mm_ss.zip
        Checks:
        1. Exists a subdirectory (Game Title).
        2. Inside that, exists a .zip file.
        3. The .zip filename matches: "AnyString - YYYY-MM-DD-HH_mm_ss"
        """
        sub_dirs = [d for d in target_path.iterdir() if d.is_dir()]
        if not sub_dirs:
            return False

        for d in sub_dirs:
            zip_files = [f for f in d.iterdir() if f.suffix == ".zip"]
            for zf in zip_files:
                if self._validate_jksv_save(zf):
                    return True
        
        return False

    def _validate_jksv_save(self, save_zip: Path) -> bool:
        """
        Check filename format: "String - YYYY-MM-DD-HH_mm_ss"
        Regex: ^(.+)\s+-\s+(\d{4}-\d{2}-\d{2}-\d{2}_\d{2}_\d{2})\.zip$
        1. (.+) Any characters (Title/User)
        2. \s+-\s+ Space, Hyphen, Space
        3. (\d{4}-\d{2}-\d{2}-\d{2}_\d{2}_\d{2}) Date and Time
        4. \.zip Extension
        """
        if re.match(r"^(.+)\s+-\s+(\d{4}-\d{2}-\d{2}-\d{2}_\d{2}_\d{2})\.zip$", save_zip.name):
            return True
        return False

    def _validate_eden_structure(self, target_path: Path) -> bool:
        """Validates Eden structure: Title Save Data - Date.zip (at root)"""
        return any(f.suffix == ".zip" for f in target_path.iterdir())

    def _verify_source_format(self, target_path: Path, expected_format: str) -> None:
        """Sanity check: Ensures the path matches the expected format."""
        if expected_format == "Checkpoint":
            if is_manual:
                if not self._validate_checkpoint_save(target_path):
                    raise ValueError(f"Format 'Checkpoint' mismatch in '{target_path.name}'.\nExpected folder name: \"DateTime User\" e.g. 20260422-193917 USERMAN")
            else:
                if not self._validate_checkpoint_structure(target_path):
                    raise ValueError(f"Format 'Checkpoint' mismatch in '{target_path.name}'.\nExpected: [Parent] -> 0xID Title -> Date User -> Files")
            if not self._validate_jksv_structure(target_path):
                raise ValueError(f"Format 'JKSV' mismatch in '{target_path.name}'.\nExpected: Game Title -> User - Date.zip")
        elif expected_format == "Eden":
            if not self._validate_eden_structure(target_path):
                raise ValueError(f"Format 'Eden' mismatch in '{target_path.name}'.\nExpected: Title Save Data - Date.zip")
        else:
            raise ValueError(f"Unknown source format: {expected_format}")

    # --- Extraction Logic ---

    def _extract_info_from_checkpoint(self, target_path: Path) -> Dict[str, Any]:
        sub_folders = [f for f in target_path.iterdir() if f.is_dir()]
        id_title_folder = sub_folders[0]
        folder_name = id_title_folder.name
        
        game_title = folder_name
        user_id = ""
        if folder_name.startswith("0x"):
            # Skip the first 2 characters ("0x") and take the rest as the title
            user_id = folder_name[:2]  # "0x"
            game_title = folder_name[2:].strip() # Everything after "0x", stripped of leading/trailing whitespace
            
            # If the result is empty after stripping, fallback to Unknown
            if not game_title:
                game_title = "Unknown Game"
        else:
            user_id = folder_name
            game_title = "Unknown Game"

        inner_folders = [f for f in id_title_folder.iterdir() if f.is_dir()]
        date_user_folder = inner_folders[0]
        inner_name = date_user_folder.name
        
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})\s+(.*)", inner_name)
        if date_match:
            date_str = date_match.group(1)
            username = date_match.group(2)
        else:
            date_str = self._get_date_string()
            username = inner_name

        return {"game_title": game_title, "user_id": user_id, "date": date_str, "username": username, "source_files": list(date_user_folder.iterdir())}

    def _extract_info_from_jksv(self, target_path: Path) -> Dict[str, Any]:
        sub_folders = [f for f in target_path.iterdir() if f.is_dir()]
        title_folder = sub_folders[0]
        game_title = title_folder.name
        
        zip_files = [f for f in title_folder.iterdir() if f.suffix == ".zip"]
        jksv_zip = zip_files[0]
        zip_name = jksv_zip.stem
        
        parts = zip_name.split(" - ")
        username = parts[0] if len(parts) >= 1 else "Unknown User"
        date_str = parts[-1] if len(parts) >= 2 else self._get_date_string()
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
        zip_files = [f for f in target_path.iterdir() if f.suffix == ".zip"]
        eden_zip = zip_files[0]
        zip_name = eden_zip.stem
        
        parts = zip_name.split(" - ")
        date_str = parts[-1] if len(parts) >= 2 else self._get_date_string()
        game_title = " ".join(parts[:-1]).replace(" Save Data", "")
        
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

    def convert_and_zip(self, source_format: str, target_format: str, is_auto_mode: bool = False) -> Tuple[str, str, str]:
        """
        Converts save data.
        Args:
            source_format: Selected format (Checkpoint, JKSV, Eden).
            target_format: Target format.
            is_auto_mode: If True, finds the latest modified folder in base_path.
                          If False, treats base_path as the specific save folder.
        Returns: (zip_filename, original_source_name, status_message)
        """
        if source_format == target_format:
            raise ValueError("Source and Target formats are identical.")

        # Determine the actual source path
        if is_auto_mode:
            # Find latest modified directory in base_path
            sub_dirs = [d for d in self.base_path.iterdir() if d.is_dir()]
            if not sub_dirs:
                raise FileNotFoundError("No save folders found in the selected directory.")
            
            latest_dir = max(sub_dirs, key=lambda p: p.stat().st_mtime)
            source_path = latest_dir
            original_source_name = latest_dir.name
            status_msg = f"Auto-detected: {original_source_name}"
        else:
            # Manual mode: base_path IS the save folder
            source_path = self.base_path
            original_source_name = source_path.name
            status_msg = f"Manual selection: {original_source_name}"

        # Sanity Check
        self._verify_source_format(source_path, source_format)

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

        # Construct Target
        target_path = self.base_path / target_format
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
            zip_path = self.base_path / zip_filename
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