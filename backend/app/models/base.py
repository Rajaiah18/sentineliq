"""
SentinelIQ Domain Models Base
"""
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field


def get_utc_now_iso() -> str:
    """Return formatted ISO 8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


class SentinelBaseModel(BaseModel):
    """Base Pydantic model for all SentinelIQ domain models."""
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True
    )

    def to_mongo_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary suitable for MongoDB storage."""
        data = self.model_dump(by_alias=True)
        return data
