#!/usr/bin/env python3
"""
Mapping switch games to their title IDs and vice versa for the Switch Save Converter.
- Fetches from https://producdevity.github.io/switch-games-json/switchbrew_id_names.json
  to get Program ID and Game name mappings
- Provides cache and manual override support
- Title IDs are stored WITHOUT 0x prefix, all uppercase
- Search is accent-insensitive (e matches é, etc.)
"""

import json
import os
import unicodedata
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import urllib.request
import ssl


class TitleIdMapper:
    """Maps Nintendo Switch title IDs to game names and vice versa.
    
    Title IDs are normalized internally as:
    - No 0x prefix
    - All uppercase hex digits
    Example: 0100000000010000 (not 0x0100000000010000)
    
    Game name search is accent-insensitive.
    """
    
    # Remote JSON source
    REMOTE_URL = "https://producdevity.github.io/switch-games-json/switchbrew_id_names.json"
    
    # Local cache location
    CACHE_DIR = Path(__file__).parent / "cache"
    CACHE_FILE = CACHE_DIR / "title_id_mappings.json"
    CACHE_TIMESTAMP_FILE = CACHE_DIR / "cache_timestamp.txt"
    
    # Cache duration: 24 hours (in seconds)
    CACHE_DURATION = 86400
    
    def __init__(self):
        """Initialize the mapper and load cached data if available."""
        self.CACHE_DIR.mkdir(exist_ok=True)
        
        self.id_to_name: Dict[str, str] = {}
        self.name_to_id: Dict[str, str] = {}
        self.manual_overrides: Dict[str, str] = {}
        self.manual_reverse_overrides: Dict[str, str] = {}
        
        # Load manual overrides first
        self._load_manual_overrides()
        
        # Load cache if available, otherwise fetch from remote
        if not self._load_cache():
            print("[TitleIdMapper] No cache found, fetching from remote...")
            self.fetch_remote_data()
    
    def _normalize_tid(self, tid: str) -> str:
        """Normalize a title ID: strip 0x prefix, uppercase."""
        if not tid:
            return ""
        t = tid.strip()
        # Strip 0x or 0X prefix
        if t.lower().startswith("0x"):
            t = t[2:]
        # Uppercase
        return t.upper()
    
    @staticmethod
    def _remove_accents(text: str) -> str:
        """Remove diacritical marks (accents) from a string.
        
        Example: 'café' -> 'cafe', 'naïve' -> 'naive', 'résumé' -> 'resume'
        """
        if not text:
            return ""
        # Normalize to NFD (decomposed form - separates base chars from accents)
        nfd = unicodedata.normalize('NFD', text)
        # Filter out combining characters (accents)
        without_accents = ''.join(
            c for c in nfd 
            if unicodedata.category(c) != 'Mn'
        )
        return without_accents
    
    def _load_cache(self) -> bool:
        """Load cached data from local file if valid."""
        if not self.CACHE_FILE.exists():
            return False
        
        # Check if cache is expired
        if self._is_cache_expired():
            return False
        
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                if not content:
                    print("[TitleIdMapper] Cache file is empty")
                    return False
                
                data = json.loads(content)
                
                self.id_to_name = {}
                self.name_to_id = {}
                
                # Handle different data formats
                if isinstance(data, dict):
                    # Format: {"0100xxx": "Game Name"}
                    for tid, name in data.items():
                        norm_tid = self._normalize_tid(tid)
                        if norm_tid and name:
                            self._add_mapping(norm_tid, name)
                elif isinstance(data, list):
                    # Format: [{"id": "0100xxx", "name": "Game Name"}, ...]
                    for entry in data:
                        if isinstance(entry, dict):
                            tid = entry.get('id') or entry.get('title_id') or entry.get('program_id')
                            name = entry.get('name') or entry.get('title') or entry.get('game_name')
                            if tid and name:
                                norm_tid = self._normalize_tid(tid)
                                if norm_tid:
                                    self._add_mapping(norm_tid, name)
                else:
                    print(f"[TitleIdMapper] Unexpected cache format: {type(data)}")
                    return False
                
                # Apply manual overrides
                for tid, name in self.manual_overrides.items():
                    self.id_to_name[tid] = name
                    self.name_to_id[name.lower().strip()] = tid
                
                print(f"[TitleIdMapper] Loaded {len(self.id_to_name)} mappings from cache")
                return True
        
        except json.JSONDecodeError as e:
            print(f"[TitleIdMapper] Invalid JSON in cache file: {e}")
            try:
                self.CACHE_FILE.unlink()
                print("[TitleIdMapper] Removed corrupt cache file")
            except:
                pass
            return False
        
        except (IOError, OSError) as e:
            print(f"[TitleIdMapper] Failed to load cache: {e}")
            return False
    
    def _is_cache_expired(self) -> bool:
        """Check if the cached data is older than CACHE_DURATION seconds."""
        if not self.CACHE_TIMESTAMP_FILE.exists():
            return True
        
        try:
            with open(self.CACHE_TIMESTAMP_FILE, 'r') as f:
                timestamp = float(f.read().strip())
            
            import time
            return (time.time() - timestamp) > self.CACHE_DURATION
        
        except (ValueError, IOError):
            return True
    
    def fetch_remote_data(self) -> bool:
        """Fetch fresh data from the remote JSON source."""
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.REMOTE_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Process the fetched data
            self._process_fetched_data(data)
            
            # Save to cache
            self._save_cache(data)
            
            print(f"[TitleIdMapper] Updated from remote source: {len(self.id_to_name)} mappings")
            return True
        
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"[TitleIdMapper] Failed to fetch remote data: {e}")
            return False
    
    def _process_fetched_data(self, data: Dict) -> None:
        """Process fetched JSON data into mappings."""
        self.id_to_name.clear()
        self.name_to_id.clear()
        
        if isinstance(data, dict):
            for tid, name in data.items():
                norm_tid = self._normalize_tid(tid)
                if norm_tid and name:
                    self._add_mapping(norm_tid, name)
        elif isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    tid = entry.get('id') or entry.get('title_id') or entry.get('program_id')
                    name = entry.get('name') or entry.get('title') or entry.get('game_name')
                    if tid and name:
                        norm_tid = self._normalize_tid(tid)
                        if norm_tid:
                            self._add_mapping(norm_tid, name)
        
        # Apply manual overrides (they take precedence)
        for tid, name in self.manual_overrides.items():
            self.id_to_name[tid] = name
            self.name_to_id[name.lower().strip()] = tid
    
    def _add_mapping(self, tid: str, name: str) -> None:
        """Add a single mapping to both lookup dictionaries.
        
        tid should already be normalized (no 0x, uppercase).
        """
        if tid and name:
            name_stripped = name.strip()
            self.id_to_name[tid] = name_stripped
            self.name_to_id[name_stripped.lower()] = tid
    
    def _save_cache(self, data) -> None:
        """Save fetched data and timestamp to cache files."""
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            import time
            with open(self.CACHE_TIMESTAMP_FILE, 'w') as f:
                f.write(str(time.time()))
        
        except IOError as e:
            print(f"[TitleIdMapper] Failed to save cache: {e}")
    
    def _load_manual_overrides(self) -> None:
        """Load manual overrides from local file."""
        overrides_file = self.CACHE_DIR / "manual_overrides.json"
        
        if overrides_file.exists():
            try:
                with open(overrides_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Normalize all override TIDs (strip 0x, uppercase)
                raw_id_to_name = data.get('id_to_name', {})
                self.manual_overrides = {}
                self.manual_reverse_overrides = {}
                
                for tid, name in raw_id_to_name.items():
                    norm_tid = self._normalize_tid(tid)
                    if norm_tid and name:
                        self.manual_overrides[norm_tid] = name.strip()
                        self.manual_reverse_overrides[name.strip().lower()] = norm_tid
                
                print(f"[TitleIdMapper] Loaded {len(self.manual_overrides)} manual overrides")
            
            except (json.JSONDecodeError, IOError) as e:
                print(f"[TitleIdMapper] Failed to load manual overrides: {e}")
    
    def save_manual_overrides(self) -> None:
        """Save manual overrides to file."""
        overrides_file = self.CACHE_DIR / "manual_overrides.json"
        
        try:
            with open(overrides_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'id_to_name': self.manual_overrides,
                    'name_to_id': self.manual_reverse_overrides
                }, f, indent=2, ensure_ascii=False)
            
            print(f"[TitleIdMapper] Saved {len(self.manual_overrides)} manual overrides")
        
        except IOError as e:
            print(f"[TitleIdMapper] Failed to save manual overrides: {e}")
    
    def add_manual_override(self, title_id: str, game_name: str) -> bool:
        """Add a manual override mapping. Returns True on success.
        
        Strips 0x prefix and uppercases the title ID automatically.
        """
        if not title_id or not game_name:
            return False
        
        # Normalize: strip 0x, uppercase
        norm_tid = self._normalize_tid(title_id)
        if not norm_tid:
            return False
        
        game_name_stripped = game_name.strip()
        
        self.manual_overrides[norm_tid] = game_name_stripped
        self.manual_reverse_overrides[game_name_stripped.lower()] = norm_tid
        
        # Also update runtime lookup
        self.id_to_name[norm_tid] = game_name_stripped
        self.name_to_id[game_name_stripped.lower()] = norm_tid
        
        self.save_manual_overrides()
        
        return True
    
    def remove_manual_override(self, title_id: str) -> bool:
        """Remove a manual override by title_id. Returns True if removed.
        
        Accepts title IDs with or without 0x prefix.
        """
        norm_tid = self._normalize_tid(title_id)
        
        if norm_tid in self.manual_overrides:
            game_name = self.manual_overrides[norm_tid].lower()
            del self.manual_overrides[norm_tid]
            
            if game_name in self.manual_reverse_overrides:
                del self.manual_reverse_overrides[game_name]
            
            self.save_manual_overrides()
            return True
        
        return False
    
    def lookup_game_by_id(self, title_id: str) -> Optional[str]:
        """Look up game name by title ID. Returns None if not found.
        
        Accepts title IDs with or without 0x prefix, any case.
        """
        if not title_id:
            return None
        
        norm_tid = self._normalize_tid(title_id)
        print("Looking up " + title_id + "(" + norm_tid + ")")

        # Manual overrides take precedence
        if norm_tid in self.manual_overrides:
            return self.manual_overrides[norm_tid]
        
        # Then check cache/remote
        if norm_tid in self.id_to_name:
            return self.id_to_name[norm_tid]
        
        return None
    
    def lookup_id_by_name(self, game_name: str) -> Optional[str]:
        """Look up title ID by game name. Returns None if not found.
        
        Returned title ID has no 0x prefix and is uppercase.
        """
        if not game_name:
            return None
        
        name_lower = game_name.strip().lower()
        
        # Manual overrides take precedence
        if name_lower in self.manual_reverse_overrides:
            return self.manual_reverse_overrides[name_lower]
        
        # Then check cache/remote
        if name_lower in self.name_to_id:
            return self.name_to_id[name_lower]
        
        # Fuzzy matching (partial match on game name)
        for mapped_name, tid in self.name_to_id.items():
            if name_lower in mapped_name or mapped_name in name_lower:
                return tid
        
        return None
    
    def get_all_mappings(self) -> List[Tuple[str, str]]:
        """Return all mappings as a list of (title_id, game_name) tuples."""
        return [(tid, name) for tid, name in sorted(self.id_to_name.items())]
    
    def get_manual_overrides(self) -> List[Tuple[str, str]]:
        """Return all manual overrides as a list of (title_id, game_name) tuples."""
        return [(tid, name) for tid, name in sorted(self.manual_overrides.items())]
    
    def search_games(self, query: str, limit: int = 10) -> List[Tuple[str, str]]:
        """Search games by partial name match. Returns top matches.
        
        Search is accent-insensitive: e matches é, a matches á, etc.
        """
        if not query:
            return []
        
        # Remove accents from query for comparison
        query_lower = query.lower().strip()
        query_normalized = self._remove_accents(query_lower)
        
        results = []
        
        for tid, name in self.id_to_name.items():
            name_lower = name.lower()
            # Remove accents from game name for comparison
            name_normalized = self._remove_accents(name_lower)
            
            score = 0
            
            # Exact match (accent-insensitive)
            if query_normalized == name_normalized:
                score = 100
            # Starts with (accent-insensitive)
            elif name_normalized.startswith(query_normalized):
                score = 90
            # Contains (accent-insensitive)
            elif query_normalized in name_normalized:
                score = 80
            # Word match (accent-insensitive)
            elif any(word in name_normalized for word in query_normalized.split()):
                score = 60
            else:
                continue
            
            # Check if manual override
            is_manual = tid in self.manual_overrides
            if is_manual:
                score += 10
            
            results.append((score, tid, name, is_manual))
        
        # Sort by score descending
        results.sort(key=lambda x: (-x[0], x[2]))
        
        # Return top N matches (without score)
        return [(tid, name) for _, tid, name, _ in results[:limit]]
    
    def clear_cache(self) -> bool:
        """Clear all cached data."""
        try:
            if self.CACHE_FILE.exists():
                self.CACHE_FILE.unlink()
            if self.CACHE_TIMESTAMP_FILE.exists():
                self.CACHE_TIMESTAMP_FILE.unlink()
            
            self.id_to_name.clear()
            self.name_to_id.clear()
            
            print("[TitleIdMapper] Cache cleared")
            return True
        
        except IOError as e:
            print(f"[TitleIdMapper] Failed to clear cache: {e}")
            return False


# Singleton instance for easy access
_mapper_instance: Optional[TitleIdMapper] = None

def get_mapper() -> TitleIdMapper:
    """Get the singleton mapper instance."""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = TitleIdMapper()
    return _mapper_instance

def lookup_game_by_id(title_id: str) -> Optional[str]:
    """Convenience function to lookup game name by title ID."""
    return get_mapper().lookup_game_by_id(title_id)

def lookup_id_by_name(game_name: str) -> Optional[str]:
    """Convenience function to lookup title ID by game name."""
    return get_mapper().lookup_id_by_name(game_name)

def add_manual_override(title_id: str, game_name: str) -> bool:
    """Convenience function to add a manual override."""
    return get_mapper().add_manual_override(title_id, game_name)

def refresh_mappings(fetch_new: bool = True) -> bool:
    """Refresh mappings from remote source."""
    mapper = get_mapper()
    if fetch_new:
        return mapper.fetch_remote_data()
    return mapper._load_cache()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing TitleIdMapper")
    print("=" * 60)
    
    mapper = TitleIdMapper()
    
    print("\nFetching remote data...")
    mapper.fetch_remote_data()
    
    # Test lookups
    test_ids = ["0100000000010000", "0x0100b2b00a6ac000", "0X0100b2b00a6ac000"]
    for tid in test_ids:
        name = mapper.lookup_game_by_id(tid)
        print(f"\nID: {tid}")
        print(f"  Game: {name if name else '(not found)'}")
    
    # Test name lookup
    print("\n\nTesting name lookup:")
    test_names = ["Mario Kart 8 Deluxe", "Zelda"]
    for name in test_names:
        tid = mapper.lookup_id_by_name(name)
        print(f"  Name: '{name}'")
        print(f"  ID: {tid if tid else '(not found)'}")
    
    # Test search
    print("\n\nTesting search:")
    results = mapper.search_games("zelda", limit=5)
    for tid, name in results:
        print(f"  {tid}: {name}")
    
    # Test accent-insensitive search
    print("\n\nTesting accent-insensitive search:")
    test_queries = ["cafe", "naive", "resume"]  # Without accents
    for q in test_queries:
        results = mapper.search_games(q, limit=5)
        print(f"  Query: '{q}'")
        for tid, name in results[:3]:  # Show top 3
            print(f"    {tid}: {name}")
    
    # Test manual override with 0x prefix
    print("\n\nTesting manual override (with 0x prefix):")
    mapper.add_manual_override("0xDEADBEEF", "Test Game Override")
    result = mapper.lookup_game_by_id("0xDEADBEEF")
    print(f"  Override lookup (input 0xDEADBEEF): {result}")
    result2 = mapper.lookup_game_by_id("deadbeef")
    print(f"  Override lookup (input deadbeef): {result2}")
    
    # Show manual overrides
    overrides = mapper.get_manual_overrides()
    if overrides:
        print(f"\nManual overrides ({len(overrides)}):")
        for tid, name in overrides:
            print(f"  {tid}: {name}")
    
    print("\n" + "=" * 60)