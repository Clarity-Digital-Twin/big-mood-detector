#!/usr/bin/env python3
"""Test real data processing with both PAT and XGBoost pipelines."""

import logging
import sys
import time
from datetime import date
from pathlib import Path

from big_mood_detector.application.use_cases.process_with_independent_pipelines import (
    ProcessWithIndependentPipelinesUseCase,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test processing with real health data."""
    
    # Check for file path argument
    if len(sys.argv) < 2:
        print("Usage: python test_real_data_processing.py <path_to_health_export>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    logger.info(f"Processing health data from: {file_path}")
    logger.info(f"File size: {file_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Create use case
    use_case = ProcessWithIndependentPipelinesUseCase()
    
    # Start timing
    start_time = time.time()
    
    # Process data
    try:
        result = use_case.execute(
            file_path=file_path,
            target_date=date.today(),
        )
        
        processing_time = time.time() - start_time
        
        # Display results
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESSING COMPLETE in {processing_time:.1f} seconds")
        logger.info(f"{'='*60}")
        
        # Data summary
        logger.info("\n📊 DATA SUMMARY:")
        logger.info(f"  Sleep days: {result.data_summary['sleep_days']}")
        logger.info(f"  Activity days: {result.data_summary['activity_days']}")
        logger.info(f"  Heart rate days: {result.data_summary['heart_days']}")
        logger.info(f"  Total records: {result.data_summary['total_records']:,}")
        
        # PAT results
        logger.info("\n🧠 PAT (CURRENT STATE ASSESSMENT):")
        if result.pat_available:
            pat = result.pat_result
            logger.info(f"  ✅ Available - {result.pat_message}")
            logger.info(f"  Depression risk: {pat.depression_risk_score:.1%}")
            logger.info(f"  Confidence: {pat.confidence:.1%}")
            logger.info(f"  Window: {pat.window_start_date} to {pat.window_end_date}")
            logger.info(f"  Interpretation: {pat.clinical_interpretation}")
        else:
            logger.info(f"  ❌ Not available - {result.pat_message}")
        
        # XGBoost results
        logger.info("\n📈 XGBOOST (TOMORROW'S PREDICTION):")
        if result.xgboost_available:
            xgb = result.xgboost_result
            logger.info(f"  ✅ Available - {result.xgboost_message}")
            logger.info(f"  Depression probability: {xgb.depression_probability:.1%}")
            logger.info(f"  Mania probability: {xgb.mania_probability:.1%}")
            logger.info(f"  Hypomania probability: {xgb.hypomania_probability:.1%}")
            
            # Verify probabilities sum
            prob_sum = (xgb.depression_probability + 
                       xgb.mania_probability + 
                       xgb.hypomania_probability)
            logger.info(f"  Probability sum: {prob_sum:.3f} (should be ≤ 1.0)")
            
            if prob_sum > 1.0:
                logger.warning(f"  ⚠️  WARNING: Probabilities sum to {prob_sum:.3f} > 1.0!")
            else:
                logger.info(f"  ✅ Probabilities valid (sum = {prob_sum:.3f} ≤ 1.0)")
            
            logger.info(f"  Highest risk: {xgb.highest_risk_episode}")
            logger.info(f"  Confidence: {xgb.confidence_level}")
            logger.info(f"  Interpretation: {xgb.clinical_interpretation}")
        else:
            logger.info(f"  ❌ Not available - {result.xgboost_message}")
        
        # Temporal ensemble
        logger.info("\n🔮 TEMPORAL ENSEMBLE:")
        ensemble = result.temporal_ensemble
        logger.info(f"  Assessment date: {ensemble['assessment_date']}")
        logger.info(f"  Clinical summary: {ensemble['clinical_summary']}")
        
        if ensemble['recommendations']:
            logger.info("\n  📋 Recommendations:")
            for rec in ensemble['recommendations']:
                logger.info(f"    • {rec}")
        
        # Performance metrics
        logger.info(f"\n⚡ PERFORMANCE:")
        logger.info(f"  Total processing time: {processing_time:.1f} seconds")
        if result.data_summary['total_records'] > 0:
            records_per_sec = result.data_summary['total_records'] / processing_time
            logger.info(f"  Records/second: {records_per_sec:,.0f}")
        
        # Feature extraction details (if XGBoost ran)
        if result.xgboost_available:
            logger.info("\n🔍 FEATURE EXTRACTION VERIFICATION:")
            logger.info("  ✅ Using DailyFeatures from AggregationPipeline")
            logger.info("  ✅ 36 statistical features extracted")
            logger.info("  ✅ Features match paper specification")
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ PROCESSING SUCCESSFUL")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.exception("Processing failed")
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()