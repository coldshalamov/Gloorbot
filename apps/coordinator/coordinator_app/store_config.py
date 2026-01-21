"""
Store configuration management for Gloorbot.
Allows admins to configure which stores to scrape by region/state.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import re

# All available Lowe's stores organized by state
ALL_STORES = {
    "WA": [
        {"id": "0061", "city": "Arlington", "url": "https://www.lowes.com/store/WA-Arlington/0061"},
        {"id": "1089", "city": "Auburn", "url": "https://www.lowes.com/store/WA-Auburn/1089"},
        {"id": "1631", "city": "Bellingham", "url": "https://www.lowes.com/store/WA-Bellingham/1631"},
        {"id": "2895", "city": "Bonney Lake", "url": "https://www.lowes.com/store/WA-BonneyLake/2895"},
        {"id": "1534", "city": "Bremerton", "url": "https://www.lowes.com/store/WA-Bremerton/1534"},
        {"id": "0149", "city": "Everett", "url": "https://www.lowes.com/store/WA-Everett/0149"},
        {"id": "2346", "city": "Federal Way", "url": "https://www.lowes.com/store/WA-FederalWay/2346"},
        {"id": "0140", "city": "Issaquah", "url": "https://www.lowes.com/store/WA-Issaquah/0140"},
        {"id": "0249", "city": "Kennewick", "url": "https://www.lowes.com/store/WA-Kennewick/0249"},
        {"id": "2561", "city": "Kent", "url": "https://www.lowes.com/store/WA-Kent/2561"},
        {"id": "2738", "city": "Lacey", "url": "https://www.lowes.com/store/WA-Lacey/2738"},
        {"id": "1081", "city": "Lakewood", "url": "https://www.lowes.com/store/WA-Lakewood/1081"},
        {"id": "1887", "city": "Longview", "url": "https://www.lowes.com/store/WA-Longview/1887"},
        {"id": "0285", "city": "Lynnwood", "url": "https://www.lowes.com/store/WA-Lynnwood/0285"},
        {"id": "1573", "city": "Mill Creek", "url": "https://www.lowes.com/store/WA-MillCreek/1573"},
        {"id": "2781", "city": "Monroe", "url": "https://www.lowes.com/store/WA-Monroe/2781"},
        {"id": "2956", "city": "Moses Lake", "url": "https://www.lowes.com/store/WA-MosesLake/2956"},
        {"id": "0035", "city": "Mount Vernon", "url": "https://www.lowes.com/store/WA-MountVernon/0035"},
        {"id": "1167", "city": "Olympia", "url": "https://www.lowes.com/store/WA-Olympia/1167"},
        {"id": "2344", "city": "Pasco", "url": "https://www.lowes.com/store/WA-Pasco/2344"},
        {"id": "2733", "city": "Port Orchard", "url": "https://www.lowes.com/store/WA-PortOrchard/2733"},
        {"id": "2734", "city": "Puyallup", "url": "https://www.lowes.com/store/WA-Puyallup/2734"},
        {"id": "2420", "city": "Renton", "url": "https://www.lowes.com/store/WA-Renton/2420"},
        {"id": "0004", "city": "Seattle", "url": "https://www.lowes.com/store/WA-Seattle/0004"},
        {"id": "0252", "city": "Seattle", "url": "https://www.lowes.com/store/WA-Seattle/0252"},
        {"id": "2746", "city": "Silverdale", "url": "https://www.lowes.com/store/WA-Silverdale/2746"},
        {"id": "0172", "city": "Spokane", "url": "https://www.lowes.com/store/WA-Spokane/0172"},
        {"id": "3045", "city": "Spokane", "url": "https://www.lowes.com/store/WA-Spokane/3045"},
        {"id": "2793", "city": "Spokane Valley", "url": "https://www.lowes.com/store/WA-SpokaneValley/2793"},
        {"id": "0026", "city": "Tacoma", "url": "https://www.lowes.com/store/WA-Tacoma/0026"},
        {"id": "0010", "city": "Tukwila", "url": "https://www.lowes.com/store/WA-Tukwila/0010"},
        {"id": "1632", "city": "Vancouver", "url": "https://www.lowes.com/store/WA-Vancouver/1632"},
        {"id": "2954", "city": "Vancouver", "url": "https://www.lowes.com/store/WA-Vancouver/2954"},
        {"id": "0152", "city": "Wenatchee", "url": "https://www.lowes.com/store/WA-Wenatchee/0152"},
        {"id": "3240", "city": "Yakima", "url": "https://www.lowes.com/store/WA-Yakima/3240"},
    ],
    "OR": [
        {"id": "3057", "city": "Albany", "url": "https://www.lowes.com/store/OR-Albany/3057"},
        {"id": "1690", "city": "Bend", "url": "https://www.lowes.com/store/OR-Bend/1690"},
        {"id": "2940", "city": "Eugene", "url": "https://www.lowes.com/store/OR-Eugene/2940"},
        {"id": "1558", "city": "Hillsboro", "url": "https://www.lowes.com/store/OR-Hillsboro/1558"},
        {"id": "2619", "city": "Keizer", "url": "https://www.lowes.com/store/OR-Keizer/2619"},
        {"id": "1693", "city": "McMinnville", "url": "https://www.lowes.com/store/OR-McMinnville/1693"},
        {"id": "0248", "city": "Medford", "url": "https://www.lowes.com/store/OR-Medford/0248"},
        {"id": "1824", "city": "Milwaukie", "url": "https://www.lowes.com/store/OR-Milwaukie/1824"},
        {"id": "2579", "city": "Portland", "url": "https://www.lowes.com/store/OR-Portland/2579"},
        {"id": "2865", "city": "Redmond", "url": "https://www.lowes.com/store/OR-Redmond/2865"},
        {"id": "1741", "city": "Roseburg", "url": "https://www.lowes.com/store/OR-Roseburg/1741"},
        {"id": "1600", "city": "Salem", "url": "https://www.lowes.com/store/OR-Salem/1600"},
        {"id": "1108", "city": "Tigard", "url": "https://www.lowes.com/store/OR-Tigard/1108"},
        {"id": "1114", "city": "Wood Village", "url": "https://www.lowes.com/store/OR-WoodVillage/1114"},
    ],
    "FL": [
        {"id": "0513", "city": "Altamonte Springs", "url": "https://www.lowes.com/store/FL-AltamonteSprings/0513"},
        {"id": "0514", "city": "Apopka", "url": "https://www.lowes.com/store/FL-Apopka/0514"},
        {"id": "2748", "city": "Auburndale", "url": "https://www.lowes.com/store/FL-Auburndale/2748"},
        {"id": "1817", "city": "Bayshore", "url": "https://www.lowes.com/store/FL-Bayshore/1817"},
        {"id": "1069", "city": "Boca Raton", "url": "https://www.lowes.com/store/FL-Boca-Raton/1069"},
        {"id": "2750", "city": "Bonita Springs", "url": "https://www.lowes.com/store/FL-BonitaSprings/2750"},
        {"id": "1111", "city": "Boynton Beach", "url": "https://www.lowes.com/store/FL-Boynton-Beach/1111"},
        {"id": "1705", "city": "Bradenton", "url": "https://www.lowes.com/store/FL-Bradenton/1705"},
        {"id": "2751", "city": "Brandon", "url": "https://www.lowes.com/store/FL-Brandon/2751"},
        {"id": "1706", "city": "Cape Coral", "url": "https://www.lowes.com/store/FL-CapeCoral/1706"},
        {"id": "1707", "city": "Clearwater", "url": "https://www.lowes.com/store/FL-Clearwater/1707"},
        {"id": "1708", "city": "Clermont", "url": "https://www.lowes.com/store/FL-Clermont/1708"},
        {"id": "0704", "city": "Coral Springs", "url": "https://www.lowes.com/store/FL-Coral-Springs/0704"},
        {"id": "3315", "city": "Davie", "url": "https://www.lowes.com/store/FL-Davie/3315"},
        {"id": "1712", "city": "Daytona Beach", "url": "https://www.lowes.com/store/FL-DaytonaBeach/1712"},
        {"id": "2753", "city": "Deltona", "url": "https://www.lowes.com/store/FL-Deltona/2753"},
        {"id": "1715", "city": "Destin", "url": "https://www.lowes.com/store/FL-Destin/1715"},
        {"id": "1718", "city": "Fort Myers", "url": "https://www.lowes.com/store/FL-FortMyers/1718"},
        {"id": "2754", "city": "Fort Pierce", "url": "https://www.lowes.com/store/FL-FortPierce/2754"},
        {"id": "1719", "city": "Fort Walton Beach", "url": "https://www.lowes.com/store/FL-FortWaltonBeach/1719"},
        {"id": "1841", "city": "Hialeah (N.W. Miami-Dade)", "url": "https://www.lowes.com/store/FL-Hialeah/1841"},
        {"id": "2254", "city": "Hialeah", "url": "https://www.lowes.com/store/FL-Hialeah/2254"},
        {"id": "2707", "city": "Homestead", "url": "https://www.lowes.com/store/FL-Homestead/2707"},
        {"id": "1723", "city": "Jacksonville", "url": "https://www.lowes.com/store/FL-Jacksonville/1723"},
        {"id": "2755", "city": "Jacksonville", "url": "https://www.lowes.com/store/FL-Jacksonville/2755"},
        {"id": "1725", "city": "Kissimmee", "url": "https://www.lowes.com/store/FL-Kissimmee/1725"},
        {"id": "1720", "city": "Lake Park", "url": "https://www.lowes.com/store/FL-Lake-Park/1720"},
        {"id": "1727", "city": "Lakeland", "url": "https://www.lowes.com/store/FL-Lakeland/1727"},
        {"id": "1728", "city": "Largo", "url": "https://www.lowes.com/store/FL-Largo/1728"},
        {"id": "1729", "city": "Leesburg", "url": "https://www.lowes.com/store/FL-Leesburg/1729"},
        {"id": "1730", "city": "Lutz", "url": "https://www.lowes.com/store/FL-Lutz/1730"},
        {"id": "1731", "city": "Melbourne", "url": "https://www.lowes.com/store/FL-Melbourne/1731"},
        {"id": "2904", "city": "Miami (Kendall)", "url": "https://www.lowes.com/store/FL-Miami/2904"},
        {"id": "1733", "city": "Naples", "url": "https://www.lowes.com/store/FL-Naples/1733"},
        {"id": "1734", "city": "New Port Richey", "url": "https://www.lowes.com/store/FL-NewPortRichey/1734"},
        {"id": "3413", "city": "North Miami Beach", "url": "https://www.lowes.com/store/FL-N.-Miami-Beach/3413"},
        {"id": "0754", "city": "Oakland Park", "url": "https://www.lowes.com/store/FL-Oakland-Park/0754"},
        {"id": "1735", "city": "Ocala", "url": "https://www.lowes.com/store/FL-Ocala/1735"},
        {"id": "1736", "city": "Orange Park", "url": "https://www.lowes.com/store/FL-OrangePark/1736"},
        {"id": "1737", "city": "Orlando", "url": "https://www.lowes.com/store/FL-Orlando/1737"},
        {"id": "2757", "city": "Orlando", "url": "https://www.lowes.com/store/FL-Orlando/2757"},
        {"id": "1738", "city": "Oviedo", "url": "https://www.lowes.com/store/FL-Oviedo/1738"},
        {"id": "1739", "city": "Palm Bay", "url": "https://www.lowes.com/store/FL-PalmBay/1739"},
        {"id": "1740", "city": "Palm Coast", "url": "https://www.lowes.com/store/FL-PalmCoast/1740"},
        {"id": "1742", "city": "Panama City", "url": "https://www.lowes.com/store/FL-PanamaCity/1742"},
        {"id": "1681", "city": "Pembroke Pines", "url": "https://www.lowes.com/store/FL-Pembroke-Pines/1681"},
        {"id": "1744", "city": "Pensacola", "url": "https://www.lowes.com/store/FL-Pensacola/1744"},
        {"id": "1745", "city": "Pinellas Park", "url": "https://www.lowes.com/store/FL-PinellasPark/1745"},
        {"id": "1746", "city": "Plant City", "url": "https://www.lowes.com/store/FL-PlantCity/1746"},
        {"id": "1792", "city": "Pompano Beach", "url": "https://www.lowes.com/store/FL-Pompano-Beach/1792"},
        {"id": "1748", "city": "Port Charlotte", "url": "https://www.lowes.com/store/FL-PortCharlotte/1748"},
        {"id": "1749", "city": "Port Orange", "url": "https://www.lowes.com/store/FL-PortOrange/1749"},
        {"id": "1750", "city": "Port St. Lucie", "url": "https://www.lowes.com/store/FL-PortStLucie/1750"},
        {"id": "1751", "city": "Riverview", "url": "https://www.lowes.com/store/FL-Riverview/1751"},
        {"id": "0654", "city": "Royal Palm Beach", "url": "https://www.lowes.com/store/FL-Royal-Palm-Beach/0654"},
        {"id": "1753", "city": "Sanford", "url": "https://www.lowes.com/store/FL-Sanford/1753"},
        {"id": "1754", "city": "Sarasota", "url": "https://www.lowes.com/store/FL-Sarasota/1754"},
        {"id": "2758", "city": "Sarasota", "url": "https://www.lowes.com/store/FL-Sarasota/2758"},
        {"id": "0725", "city": "Southwest Ranches (W. Davie)", "url": "https://www.lowes.com/store/FL-Southwest-Ranches/0725"},
        {"id": "1755", "city": "Spring Hill", "url": "https://www.lowes.com/store/FL-SpringHill/1755"},
        {"id": "1756", "city": "St. Augustine", "url": "https://www.lowes.com/store/FL-StAugustine/1756"},
        {"id": "1757", "city": "St. Petersburg", "url": "https://www.lowes.com/store/FL-StPetersburg/1757"},
        {"id": "1109", "city": "Stuart", "url": "https://www.lowes.com/store/FL-Stuart/1109"},
        {"id": "1113", "city": "Sunrise", "url": "https://www.lowes.com/store/FL-Sunrise/1113"},
        {"id": "1759", "city": "Tallahassee", "url": "https://www.lowes.com/store/FL-Tallahassee/1759"},
        {"id": "1760", "city": "Tampa", "url": "https://www.lowes.com/store/FL-Tampa/1760"},
        {"id": "2759", "city": "Tampa", "url": "https://www.lowes.com/store/FL-Tampa/2759"},
        {"id": "1761", "city": "Titusville", "url": "https://www.lowes.com/store/FL-Titusville/1761"},
        {"id": "1762", "city": "Venice", "url": "https://www.lowes.com/store/FL-Venice/1762"},
        {"id": "1763", "city": "Vero Beach", "url": "https://www.lowes.com/store/FL-VeroBeach/1763"},
        {"id": "1962", "city": "West Palm Beach", "url": "https://www.lowes.com/store/FL-West-Palm-Beach/1962"},
        {"id": "1766", "city": "Winter Garden", "url": "https://www.lowes.com/store/FL-WinterGarden/1766"},
        {"id": "1767", "city": "Winter Haven", "url": "https://www.lowes.com/store/FL-WinterHaven/1767"},
    ],
}


class StoreConfigManager:
    """Manages store configuration for scraping."""
    
    def __init__(self, config_file: Path | None = None):
        """Initialize the store config manager."""
        if config_file is None:
            # Default to coordinator app data directory
            data_dir = os.getenv("DATA_DIR", "").strip()
            if data_dir:
                config_file = Path(data_dir).expanduser() / "store_config.json"
            else:
                base_dir = Path(__file__).resolve().parents[1]
                config_file = base_dir / "data" / "store_config.json"
        
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create default
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default configuration (WA/OR stores)
        return {
            "enabled_states": ["WA", "OR"],
            "enabled_stores": [],  # Empty means all stores in enabled_states
            "last_updated": None,
        }
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        self.config["last_updated"] = datetime.utcnow().isoformat()
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_enabled_states(self) -> List[str]:
        """Get list of enabled states."""
        return self.config.get("enabled_states", [])
    
    def set_enabled_states(self, states: List[str]) -> None:
        """Set which states are enabled for scraping."""
        # Validate states
        valid_states = [s for s in states if s in ALL_STORES]
        self.config["enabled_states"] = valid_states
        self.config["enabled_stores"] = []  # Reset specific store selection
        self._save_config()
    
    def get_enabled_stores(self) -> List[dict]:
        """Get list of enabled stores with full details."""
        enabled_states = self.config.get("enabled_states", [])
        specific_stores = self.config.get("enabled_stores", [])
        
        if specific_stores:
            # Return only specifically selected stores
            result = []
            for state in enabled_states:
                for store in ALL_STORES.get(state, []):
                    if store["id"] in specific_stores:
                        result.append({**store, "state": state})
            return result
        else:
            # Return all stores from enabled states
            result = []
            for state in enabled_states:
                for store in ALL_STORES.get(state, []):
                    result.append({**store, "state": state})
            return result
    
    def set_enabled_stores(self, store_ids: List[str]) -> None:
        """Set specific stores to enable (overrides state-level selection)."""
        self.config["enabled_stores"] = store_ids
        self._save_config()
    
    def get_all_stores_by_state(self) -> Dict[str, List[dict]]:
        """Get all available stores organized by state."""
        return ALL_STORES
    
    def generate_urls_txt(self) -> str:
        """Generate the urls.txt content based on current configuration."""
        lines = [
            "# Lowe's Store and Department Map",
            "# This file is auto-generated by the Gloorbot Admin Interface",
            f"# Last updated: {datetime.utcnow().isoformat()}",
            "",
        ]
        
        enabled_stores = self.get_enabled_stores()
        
        # Group by state
        by_state: Dict[str, List[dict]] = {}
        for store in enabled_stores:
            state = store["state"]
            if state not in by_state:
                by_state[state] = []
            by_state[state].append(store)
        
        # Add stores
        for state in sorted(by_state.keys()):
            lines.append(f"## {state} STORES")
            for store in sorted(by_state[state], key=lambda x: x["city"]):
                lines.append(store["url"])
            lines.append("")
        
        # Add categories (load from existing urls.txt if available)
        lines.append("## CATEGORIES")
        categories = self._load_categories()
        lines.extend(categories)
        
        return "\n".join(lines)
    
    def _load_categories(self) -> List[str]:
        """Load category URLs from the PARALLEL/urls.txt file."""
        # Try multiple possible locations for the PARALLEL/urls.txt file
        base_dir = Path(__file__).resolve().parent
        
        # Possible locations (in order of preference)
        possible_paths = [
            # Local dev: apps/coordinator/coordinator_app -> repo_root/PARALLEL/urls.txt
            base_dir.parent.parent / "PARALLEL" / "urls.txt",
            # Render: /app/coordinator_app -> /app/PARALLEL/urls.txt
            base_dir.parent / "PARALLEL" / "urls.txt",
            # Fallback: check if PARALLEL is a sibling
            base_dir / "PARALLEL" / "urls.txt",
        ]
        
        parallel_urls = None
        for path in possible_paths:
            if path.exists():
                parallel_urls = path
                break
        
        if not parallel_urls:
            # No PARALLEL/urls.txt found, return empty (will use default categories)
            return []
        
        categories = []
        in_categories = False
        
        try:
            with open(parallel_urls, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("## CATEGORIES"):
                        in_categories = True
                        continue
                    if in_categories and line and not line.startswith("#"):
                        if "/pl/" in line:
                            categories.append(line)
        except Exception:
            # If we can't read the file, return empty
            return []
        
        return categories


# Global instance
_store_config_manager: StoreConfigManager | None = None


def get_store_config_manager() -> StoreConfigManager:
    """Get the global store configuration manager instance."""
    global _store_config_manager
    if _store_config_manager is None:
        _store_config_manager = StoreConfigManager()
    return _store_config_manager
