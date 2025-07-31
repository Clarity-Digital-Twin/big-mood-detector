"""Feature requirements mapping for clinical predictions."""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class FeatureRequirement:
    """Requirements for a clinical feature to be available."""
    
    required_types: List[str]
    optional_types: List[str] 
    min_days: int
    completeness: float  # 0.0 to 1.0 (percentage of days with data)
    description: str


# Clinical feature requirements based on model needs
FEATURE_REQUIREMENTS: Dict[str, FeatureRequirement] = {
    "depression_risk": FeatureRequirement(
        required_types=[
            "HKCategoryTypeIdentifierSleepAnalysis",
            "HKQuantityTypeIdentifierStepCount",
        ],
        optional_types=[
            "HKQuantityTypeIdentifierHeartRate",
            "HKQuantityTypeIdentifierActiveEnergyBurned",
        ],
        min_days=7,
        completeness=0.5,
        description="Depression risk prediction (XGBoost)",
    ),
    "mania_risk": FeatureRequirement(
        required_types=[
            "HKCategoryTypeIdentifierSleepAnalysis",
            "HKQuantityTypeIdentifierStepCount",
        ],
        optional_types=[
            "HKQuantityTypeIdentifierHeartRate",
        ],
        min_days=7,
        completeness=0.5,
        description="Mania/hypomania risk prediction (XGBoost)",
    ),
    "hrv_analysis": FeatureRequirement(
        required_types=[
            "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        ],
        optional_types=[],
        min_days=30,
        completeness=0.3,
        description="Heart rate variability trends",
    ),
    "circadian_rhythm": FeatureRequirement(
        required_types=[
            "HKCategoryTypeIdentifierSleepAnalysis",
        ],
        optional_types=[
            "HKQuantityTypeIdentifierHeartRate",
        ],
        min_days=14,
        completeness=0.7,
        description="Circadian rhythm analysis",
    ),
    "activity_patterns": FeatureRequirement(
        required_types=[
            "HKQuantityTypeIdentifierStepCount",
        ],
        optional_types=[
            "HKQuantityTypeIdentifierDistanceWalkingRunning",
            "HKQuantityTypeIdentifierFlightsClimbed",
        ],
        min_days=7,
        completeness=0.7,
        description="Daily activity pattern analysis",
    ),
    "sleep_quality": FeatureRequirement(
        required_types=[
            "HKCategoryTypeIdentifierSleepAnalysis",
        ],
        optional_types=[
            "HKQuantityTypeIdentifierRespiratoryRate",
        ],
        min_days=7,
        completeness=0.5,
        description="Sleep quality assessment",
    ),
    "ensemble_prediction": FeatureRequirement(
        required_types=[
            "HKCategoryTypeIdentifierSleepAnalysis",
            "HKQuantityTypeIdentifierStepCount",
            "HKQuantityTypeIdentifierHeartRate",
        ],
        optional_types=[
            "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        ],
        min_days=7,
        completeness=0.5,
        description="Ensemble model prediction (XGBoost + PAT)",
    ),
}


def get_all_required_types() -> set[str]:
    """Get all unique required record types across all features."""
    types = set()
    for req in FEATURE_REQUIREMENTS.values():
        types.update(req.required_types)
    return types


def get_all_optional_types() -> set[str]:
    """Get all unique optional record types across all features."""
    types = set()
    for req in FEATURE_REQUIREMENTS.values():
        types.update(req.optional_types)
    return types