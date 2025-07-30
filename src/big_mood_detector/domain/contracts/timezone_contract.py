"""Contract for enforcing timezone consistency in the domain layer."""

from datetime import datetime, timezone
from typing import TypeVar

T = TypeVar('T', bound=datetime)


class TimezoneContract:
    """
    Enforces timezone consistency throughout the domain layer.
    
    Contract: All datetime objects in the domain MUST be timezone-naive,
    representing UTC time implicitly. This avoids timezone arithmetic
    errors and simplifies datetime operations.
    """
    
    @staticmethod
    def ensure_naive(dt: T) -> T:
        """
        Convert any datetime to naive (implicitly UTC).
        
        Args:
            dt: Datetime object (aware or naive)
            
        Returns:
            Naive datetime representing the same moment in UTC
        """
        if dt.tzinfo is not None:
            # Convert to UTC then make naive
            utc_dt = dt.astimezone(timezone.utc)
            return utc_dt.replace(tzinfo=None)
        return dt
    
    @staticmethod
    def validate_domain_datetime(dt: datetime) -> None:
        """
        Validate that a datetime meets domain requirements.
        
        Args:
            dt: Datetime to validate
            
        Raises:
            ValueError: If datetime is timezone-aware
        """
        if dt.tzinfo is not None:
            raise ValueError(
                f"Domain layer requires timezone-naive datetimes. "
                f"Got aware datetime: {dt}"
            )