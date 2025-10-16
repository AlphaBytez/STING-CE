"""
API endpoints for managing content filters in the LLM Gateway
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List
from pydantic import BaseModel

from ..filtering.filter_manager import FilterManager

router = APIRouter(prefix="/filters", tags=["filters"])

class FilterConfig(BaseModel):
    enabled: bool
    config: Dict[str, Any] = {}

# Dependency to get filter manager
def get_filter_manager():
    # In reality, this would be passed from the main app
    from main import filter_manager
    return filter_manager

@router.get("/")
async def list_filters(filter_mgr: FilterManager = Depends(get_filter_manager)):
    """List all available filters and their status"""
    return {
        "filters": list(filter_mgr.filters.keys()),
        "stats": filter_mgr.get_stats()
    }

@router.post("/{filter_name}/toggle")
async def toggle_filter(
    filter_name: str, 
    config: FilterConfig = Body(...),
    filter_mgr: FilterManager = Depends(get_filter_manager)
):
    """Enable or disable a specific filter"""
    if filter_name not in filter_mgr.filters:
        raise HTTPException(status_code=404, detail=f"Filter {filter_name} not found")
    
        # In a real implementation, we'd have proper filter enable/disable logic
    if config.enabled:
        # Update filter configuration if provided
        if hasattr(filter_mgr.filters[filter_name], "update_config"):
            filter_mgr.filters[filter_name].update_config(config.config)
        return {"status": "success", "message": f"Filter {filter_name} enabled"}
    else:
        # Temporarily remove from active filters
        filter_obj = filter_mgr.filters.pop(filter_name, None)
        return {"status": "success", "message": f"Filter {filter_name} disabled"}

@router.get("/{filter_name}/stats")
async def get_filter_stats(
    filter_name: str,
    filter_mgr: FilterManager = Depends(get_filter_manager)
):
    """Get detailed statistics for a specific filter"""
    if filter_name not in filter_mgr.filter_stats:
        raise HTTPException(status_code=404, detail=f"Filter {filter_name} not found")
    
    stats = filter_mgr.filter_stats[filter_name]
    
    # Calculate block rate
    block_rate = 0
    if stats["checked"] > 0:
        block_rate = stats["filtered"] / stats["checked"]
    
    return {
        "name": filter_name,
        "stats": stats,
        "block_rate": block_rate
    }

@router.post("/{filter_name}/test")
async def test_filter(
    filter_name: str,
    text: str = Body(..., embed=True),
    filter_mgr: FilterManager = Depends(get_filter_manager)
):
    """Test a specific filter on provided text"""
    if filter_name not in filter_mgr.filters:
        raise HTTPException(status_code=404, detail=f"Filter {filter_name} not found")
    
    try:
        should_filter, reason = filter_mgr.filters[filter_name].check(text)
        return {
            "should_filter": should_filter,
            "reason": reason,
            "filter_name": filter_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filter error: {str(e)}")
