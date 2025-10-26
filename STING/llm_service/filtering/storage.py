import json
import os
from typing import Dict, List, Any
import logging

class FilterStorage:
    """Manages persistence of custom filters"""
    
    def __init__(self, storage_dir: str = "/app/data/filters"):
        self.storage_dir = storage_dir
        self.logger = logging.getLogger("filter-storage")
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def save_filter_set(self, filter_id: str, filter_data: Dict[str, Any]) -> bool:
        """Save a filter set to persistent storage"""
        try:
            # Add metadata
            filter_data["last_updated"] = datetime.datetime.now().isoformat()
            
            filepath = os.path.join(self.storage_dir, f"{filter_id}.json")
            with open(filepath, 'w') as f:
                json.dump(filter_data, f, indent=2)
                
            self.logger.info(f"Saved filter set {filter_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save filter set {filter_id}: {e}")
            return False
    
    def load_filter_set(self, filter_id: str) -> Dict[str, Any]:
        """Load a filter set from persistent storage"""
        filepath = os.path.join(self.storage_dir, f"{filter_id}.json")
        
        if not os.path.exists(filepath):
            self.logger.warning(f"Filter set {filter_id} not found")
            return {}
            
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load filter set {filter_id}: {e}")
            return {}
    
    def list_filter_sets(self) -> List[str]:
        """List all available filter sets"""
        return [
            os.path.splitext(f)[0] 
            for f in os.listdir(self.storage_dir) 
            if f.endswith('.json')
        ]
    
    def delete_filter_set(self, filter_id: str) -> bool:
        """Delete a filter set"""
        filepath = os.path.join(self.storage_dir, f"{filter_id}.json")
        
        if not os.path.exists(filepath):
            self.logger.warning(f"Filter set {filter_id} not found for deletion")
            return False
            
        try:
            os.remove(filepath)
            self.logger.info(f"Deleted filter set {filter_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete filter set {filter_id}: {e}")
            return False
