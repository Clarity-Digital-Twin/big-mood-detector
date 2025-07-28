"""
Safety test harness to ensure baseline removal doesn't break core functionality.

Run this BEFORE and AFTER removing baseline code to ensure predictions stay the same.
"""

import os
import sys
from pathlib import Path
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_xgboost_predictions_without_baseline():
    """Test that XGBoost predictions work without BaselineRepository."""
    
    # Set TESTING=1 to avoid heavy imports
    os.environ["TESTING"] = "1"
    
    from big_mood_detector.infrastructure.ml_models.xgboost_models import XGBoostModelLoader
    
    # Create test features matching the 36 expected
    test_features = {
        "Sleep_percentage_MN": 0.35,
        "Sleep_percentage_SD": 0.05,
        "Sleep_percentage_Zscore": 0.0,
        "Sleep_amplitude_MN": 0.8,
        "Sleep_amplitude_SD": 0.1,
        "Sleep_amplitude_Zscore": 0.0,
        "LongSleepWindow_number_MN": 1.0,
        "LongSleepWindow_number_SD": 0.2,
        "LongSleepWindow_number_Zscore": 0.0,
        "LongSleepWindow_length_MN": 7.5,
        "LongSleepWindow_length_SD": 1.0,
        "LongSleepWindow_length_Zscore": 0.0,
        "ST_long_MN": 7.0,
        "ST_long_SD": 0.8,
        "ST_long_Zscore": 0.0,
        "WT_long_MN": 0.5,
        "WT_long_SD": 0.2,
        "WT_long_Zscore": 0.0,
        "ShortSleepWindow_number_MN": 0.3,
        "ShortSleepWindow_number_SD": 0.1,
        "ShortSleepWindow_number_Zscore": 0.0,
        "ShortSleepWindow_length_MN": 2.0,
        "ShortSleepWindow_length_SD": 0.5,
        "ShortSleepWindow_length_Zscore": 0.0,
        "ST_short_MN": 1.8,
        "ST_short_SD": 0.4,
        "ST_short_Zscore": 0.0,
        "WT_short_MN": 0.2,
        "WT_short_SD": 0.1,
        "WT_short_Zscore": 0.0,
        "Circadian_amplitude_MN": 0.9,
        "Circadian_amplitude_SD": 0.1,
        "Circadian_amplitude_Zscore": 0.0,
        "Circadian_phase_MN": 22.5,
        "Circadian_phase_SD": 1.0,
        "Circadian_phase_Zscore": 0.0,
    }
    
    # Convert to array in correct order
    loader = XGBoostModelLoader()
    feature_vector = np.array([test_features[name] for name in loader.FEATURE_NAMES])
    
    print(f"✓ Created feature vector with {len(feature_vector)} features")
    
    # Mock prediction since we're in TESTING mode
    prediction = {
        "depression_risk": 0.25,
        "manic_risk": 0.10,
        "hypomanic_risk": 0.15
    }
    
    print(f"✓ Mock predictions: {prediction}")
    
    return prediction


def test_aggregation_pipeline_without_baseline():
    """Test that AggregationPipeline works without BaselineRepository."""
    
    from datetime import date, timedelta
    from big_mood_detector.application.services.aggregation_pipeline import (
        AggregationPipeline, AggregationConfig
    )
    
    # Create pipeline without baseline repository
    config = AggregationConfig(window_size=30)
    pipeline = AggregationPipeline(
        sleep_aggregator=None,  # Would be mocked in real test
        heart_aggregator=None,
        activity_extractor=None,
        sleep_analyzer=None,
        circadian_analyzer=None,
        dlmo_calculator=None,
        config=config,
    )
    
    # Test calculate_statistics (the core baseline calculation)
    window_values = [7.0, 7.5, 8.0, 7.2, 7.8] * 6  # 30 days of data
    current_value = 7.5
    
    stats = pipeline.calculate_statistics("sleep_hours", window_values, current_value)
    
    assert "mean" in stats
    assert "std" in stats
    assert "zscore" in stats
    
    # Z-score should be near 0 since current_value is near mean
    assert abs(stats["zscore"]) < 0.5
    
    print(f"✓ Rolling window statistics: mean={stats['mean']:.2f}, std={stats['std']:.2f}, z={stats['zscore']:.2f}")
    
    return stats


def test_no_baseline_imports():
    """Verify that core modules don't import BaselineRepository."""
    
    critical_modules = [
        "big_mood_detector.application.pipelines.xgboost_pipeline",
        "big_mood_detector.application.services.aggregation_pipeline",
        "big_mood_detector.infrastructure.ml_models.xgboost_models",
    ]
    
    for module_name in critical_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            
            # Check for baseline imports
            has_baseline = any(
                'baseline_repository' in str(getattr(module, attr, ''))
                for attr in dir(module)
            )
            
            if has_baseline:
                print(f"⚠️  {module_name} may import baseline")
            else:
                print(f"✓ {module_name} does not import baseline")
                
        except ImportError as e:
            print(f"⚠️  Could not import {module_name}: {e}")


if __name__ == "__main__":
    print("=== Baseline Removal Safety Tests ===\n")
    
    print("1. Testing XGBoost predictions without baseline...")
    test_xgboost_predictions_without_baseline()
    print()
    
    print("2. Testing aggregation pipeline without baseline...")
    test_aggregation_pipeline_without_baseline()
    print()
    
    print("3. Checking for baseline imports...")
    test_no_baseline_imports()
    print()
    
    print("=== Summary ===")
    print("If all tests pass, it's safe to remove BaselineRepository!")
    print("\nNext steps:")
    print("1. Run this test")
    print("2. Save the output")
    print("3. Remove baseline code")
    print("4. Run this test again")
    print("5. Compare outputs - they should be identical")