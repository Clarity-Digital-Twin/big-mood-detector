"""Feature availability analysis results."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class FeatureAvailability:
    """Results of feature availability analysis."""
    
    available_features: List[Tuple[str, str]]  # [(feature_name, description), ...]
    unavailable_features: List[Tuple[str, str]]  # [(feature_name, reason), ...]
    record_counts: Dict[str, int]  # All record types found
    scan_duration_seconds: Optional[float] = None
    
    def has_minimum_features(self) -> bool:
        """Check if at least basic features are available."""
        # At minimum, we need depression or mania risk prediction
        required_basic = {"depression_risk", "mania_risk"}
        available_names = {name for name, _ in self.available_features}
        return bool(required_basic & available_names)
    
    def get_major_types(self) -> List[Tuple[str, int]]:
        """Get major record types with friendly names."""
        type_mapping = {
            "HKCategoryTypeIdentifierSleepAnalysis": "Sleep Analysis",
            "HKQuantityTypeIdentifierStepCount": "Step Count",
            "HKQuantityTypeIdentifierHeartRate": "Heart Rate",
            "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "HRV",
            "HKQuantityTypeIdentifierRespiratoryRate": "Respiratory Rate",
            "HKQuantityTypeIdentifierActiveEnergyBurned": "Active Energy",
            "HKQuantityTypeIdentifierDistanceWalkingRunning": "Walking Distance",
        }
        
        major_types = []
        for record_type, count in self.record_counts.items():
            if record_type in type_mapping and count > 0:
                major_types.append((type_mapping[record_type], count))
        
        # Sort by count descending
        return sorted(major_types, key=lambda x: x[1], reverse=True)
    
    def format_missing_data_summary(self) -> str:
        """Format a summary of missing data for user display."""
        if not self.unavailable_features:
            return "All data types available!"
        
        missing_types = set()
        for feature, reason in self.unavailable_features:
            if "missing required type:" in reason.lower():
                # Extract the missing type from reason
                parts = reason.split(":")
                if len(parts) > 1:
                    missing_types.add(parts[1].strip())
        
        if missing_types:
            return "Missing: " + ", ".join(sorted(missing_types))
        return "Some features have insufficient data"
    
    @property
    def total_records(self) -> int:
        """Total number of records found."""
        return sum(self.record_counts.values())