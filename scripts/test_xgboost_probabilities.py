#!/usr/bin/env python3
"""Test XGBoost probability outputs to ensure they're valid."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from big_mood_detector.application.pipelines.xgboost_pipeline import XGBoostPipeline
from big_mood_detector.application.services.aggregation_pipeline import (
    AggregationPipeline,
)
from big_mood_detector.application.validators.pipeline_validators import (
    XGBoostValidator,
)
from big_mood_detector.domain.entities.activity_record import (
    ActivityRecord,
    ActivityType,
)
from big_mood_detector.domain.entities.heart_rate_record import (
    HeartMetricType,
    HeartRateRecord,
)
from big_mood_detector.domain.entities.sleep_record import SleepRecord, SleepState
from big_mood_detector.infrastructure.ml_models.xgboost_models import (
    XGBoostMoodPredictor,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_data(days: int = 35):
    """Create synthetic test data."""
    sleep_records = []
    activity_records = []
    heart_records = []
    
    base_date = datetime(2025, 6, 1, tzinfo=UTC)
    
    for day in range(days):
        current_date = base_date + timedelta(days=day)
        
        # Sleep record (varying durations)
        sleep_hours = 7 + (day % 3) - 1  # 6-8 hours
        sleep_records.append(
            SleepRecord(
                source_name="Test",
                start_date=current_date.replace(hour=22),
                end_date=(current_date + timedelta(days=1)).replace(hour=22-24+sleep_hours),
                state=SleepState.ASLEEP,
            )
        )
        
        # Activity record (varying steps)
        steps = 5000 + (day * 100) % 10000
        activity_records.append(
            ActivityRecord(
                source_name="Test",
                start_date=current_date.replace(hour=0),
                end_date=current_date.replace(hour=23, minute=59),
                activity_type=ActivityType.STEP_COUNT,
                value=float(steps),
                unit="count",
            )
        )
        
        # Heart rate record
        heart_records.append(
            HeartRateRecord(
                source_name="Test",
                timestamp=current_date.replace(hour=12),
                value=70.0 + (day % 10),
                metric_type=HeartMetricType.RESTING_HEART_RATE,
                unit="bpm",
            )
        )
    
    return sleep_records, activity_records, heart_records


def main():
    """Test XGBoost probability outputs."""
    logger.info("Testing XGBoost probability outputs...")
    
    # Create pipeline
    try:
        predictor = XGBoostMoodPredictor()
        predictor.load_models(Path("model_weights/xgboost/converted"))
    except Exception as e:
        logger.error(f"Could not load XGBoost models: {e}")
        logger.info("Make sure model weights are in place")
        return
    
    feature_extractor = AggregationPipeline()
    validator = XGBoostValidator()
    
    pipeline = XGBoostPipeline(
        feature_extractor=feature_extractor,
        predictor=predictor,
        validator=validator,
    )
    
    # Test with different data patterns
    test_cases = [
        ("Normal sleep pattern", 35, 7, 8000),
        ("Short sleep (mania risk)", 35, 3, 15000),
        ("Long sleep (depression risk)", 35, 12, 2000),
        ("Irregular pattern", 35, None, None),
    ]
    
    for test_name, days, sleep_hours, steps in test_cases:
        logger.info(f"\n{'='*60}")
        logger.info(f"Test case: {test_name}")
        logger.info(f"{'='*60}")
        
        # Create data
        sleep_records, activity_records, heart_records = create_test_data(days)
        
        # Modify data for specific test cases
        if sleep_hours is not None:
            # Replace sleep records for last 7 days with custom duration
            for i in range(-7, 0):
                old_record = sleep_records[i]
                sleep_records[i] = SleepRecord(
                    source_name=old_record.source_name,
                    start_date=old_record.start_date,
                    end_date=old_record.start_date + timedelta(hours=sleep_hours),
                    state=old_record.state,
                )
        
        if steps is not None:
            # Replace activity records for last 7 days with custom steps
            for i in range(-7, 0):
                old_record = activity_records[i]
                activity_records[i] = ActivityRecord(
                    source_name=old_record.source_name,
                    start_date=old_record.start_date,
                    end_date=old_record.end_date,
                    activity_type=old_record.activity_type,
                    value=float(steps),
                    unit=old_record.unit,
                )
        
        # Run pipeline
        result = pipeline.process(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            target_date=datetime.now().date(),
        )
        
        if result:
            logger.info("\n📊 RESULTS:")
            logger.info(f"  Depression: {result.depression_probability:.3f}")
            logger.info(f"  Mania: {result.mania_probability:.3f}")
            logger.info(f"  Hypomania: {result.hypomania_probability:.3f}")
            
            # Check probability sum
            prob_sum = (result.depression_probability + 
                       result.mania_probability + 
                       result.hypomania_probability)
            
            logger.info(f"\n  Sum: {prob_sum:.3f}")
            
            if prob_sum > 1.0:
                logger.error(f"  ❌ ERROR: Probabilities sum to {prob_sum:.3f} > 1.0!")
            else:
                logger.info(f"  ✅ Valid: Probabilities sum to {prob_sum:.3f} ≤ 1.0")
            
            # Check individual probabilities
            probs = [
                result.depression_probability,
                result.mania_probability,
                result.hypomania_probability
            ]
            
            for name, prob in zip(["Depression", "Mania", "Hypomania"], probs):
                if not (0.0 <= prob <= 1.0):
                    logger.error(f"  ❌ ERROR: {name} probability {prob:.3f} out of range [0,1]")
                else:
                    logger.info(f"  ✅ Valid: {name} probability {prob:.3f} in range [0,1]")
            
            logger.info(f"\n  Highest risk: {result.highest_risk_episode}")
            logger.info(f"  Interpretation: {result.clinical_interpretation}")
            
            # Show feature stats
            logger.info("\n📈 FEATURE EXTRACTION:")
            logger.info(f"  Days used: {result.data_days_used}")
            logger.info(f"  Confidence: {result.confidence_level}")
            
        else:
            logger.error("  ❌ Pipeline failed to produce results")
    
    logger.info(f"\n{'='*60}")
    logger.info("✅ PROBABILITY TESTING COMPLETE")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()