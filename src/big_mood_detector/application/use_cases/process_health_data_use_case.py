"""
Mood Prediction Pipeline

End-to-end integration that processes Apple Health data through
all domain services to generate the 36 features required by XGBoost.

This is the crown jewel - where everything comes together!

Design Principles:
- Orchestration layer (no business logic)
- Dependency injection for services
- Stream processing for large datasets
- Clinical validation at each step
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from big_mood_detector.application.services.aggregation_pipeline import (
    AggregationPipeline,
)
from big_mood_detector.application.services.data_parsing_service import (
    DataParsingService,
)
from big_mood_detector.application.services.summary_calculator import (
    SummaryCalculator,
)
from big_mood_detector.application.services.temporal_ensemble_orchestrator import (
    TemporalEnsembleOrchestrator,
)
from big_mood_detector.application.use_cases.predict_mood_ensemble_use_case import (
    EnsembleConfig,
)
from big_mood_detector.domain.services.activity_sequence_extractor import (
    ActivitySequenceExtractor,
)
from big_mood_detector.domain.services.circadian_rhythm_analyzer import (
    CircadianRhythmAnalyzer,
)
from big_mood_detector.domain.services.clinical_feature_extractor import (
    ClinicalFeatureExtractor,
    ClinicalFeatureSet,
)
from big_mood_detector.domain.services.dlmo_calculator import DLMOCalculator
from big_mood_detector.domain.services.mood_predictor import (
    MoodPredictor,
)
from big_mood_detector.domain.services.sleep_window_analyzer import SleepWindowAnalyzer
from big_mood_detector.domain.services.sparse_data_handler import (
    SparseDataHandler,
)
from big_mood_detector.infrastructure.logging import get_module_logger

logger = get_module_logger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for mood prediction pipeline."""

    min_days_required: int = 7
    include_pat_sequences: bool = False
    confidence_threshold: float = 0.7
    model_dir: Path | None = None
    enable_sparse_handling: bool = True
    max_interpolation_days: int = 3
    ensemble_config: EnsembleConfig | None = None
    enable_personal_calibration: bool = False
    personal_calibrator: Any | None = None  # PersonalCalibrator instance
    user_id: str | None = None
    use_seoul_features: bool = True  # Use aggregation pipeline for XGBoost
    window_selection_strategy: Any | None = None  # WindowSelectionStrategy instance


@dataclass
class PipelineResult:
    """Result of mood prediction pipeline processing."""

    daily_predictions: dict[date, dict[str, Any]]
    overall_summary: dict[str, Any]
    confidence_score: float
    processing_time_seconds: float
    window_predictions: dict[tuple[date, date], dict[str, Any]] = field(default_factory=dict)
    records_processed: int = 0
    features_extracted: int = 0
    has_warnings: bool = False
    warnings: list[str] = field(default_factory=list)
    has_errors: bool = False
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])


class MoodPredictionPipeline:
    """
    Orchestrates the complete mood prediction pipeline.

    This brings together all domain services to process
    raw Apple Health data into XGBoost-ready features.
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        sleep_analyzer: SleepWindowAnalyzer | None = None,
        activity_extractor: ActivitySequenceExtractor | None = None,
        circadian_analyzer: CircadianRhythmAnalyzer | None = None,
        dlmo_calculator: DLMOCalculator | None = None,
        sparse_handler: SparseDataHandler | None = None,
        data_parsing_service: DataParsingService | None = None,
        aggregation_pipeline: AggregationPipeline | None = None,
        di_container: Any | None = None,
    ):
        """
        Initialize with domain services.

        Uses dependency injection for testability.
        """
        self.config = config or PipelineConfig()
        self.sleep_analyzer = sleep_analyzer or SleepWindowAnalyzer()
        self.activity_extractor = activity_extractor or ActivitySequenceExtractor()
        self.circadian_analyzer = circadian_analyzer or CircadianRhythmAnalyzer()
        self.dlmo_calculator = dlmo_calculator or DLMOCalculator()
        self.sparse_handler = sparse_handler or SparseDataHandler()

        # Initialize clinical_extractor - will be set below
        self.clinical_extractor: Any  # Union of ClinicalFeatureExtractor and OrchestratorAdapter

        # Initialize clinical feature extractor with orchestrator adapter if available
        if di_container:
            try:
                # Try to get orchestrator from DI container
                from big_mood_detector.application.adapters.orchestrator_adapter import (
                    OrchestratorAdapter,
                )
                from big_mood_detector.domain.services.feature_engineering_orchestrator import (
                    FeatureEngineeringOrchestrator,
                )

                orchestrator = di_container.resolve(FeatureEngineeringOrchestrator)
                self.clinical_extractor = OrchestratorAdapter(
                    orchestrator=orchestrator,
                    user_id=(
                        self.config.user_id
                        if self.config.enable_personal_calibration
                        else None
                    ),
                )
                logger.info(
                    "Using FeatureEngineeringOrchestrator with validation and anomaly detection"
                )
            except Exception as e:
                logger.debug(
                    f"Orchestrator not available, using standard extractor: {e}"
                )
                # Fall back to standard clinical extractor
                self.clinical_extractor = ClinicalFeatureExtractor(
                    user_id=(
                        self.config.user_id
                        if self.config.enable_personal_calibration
                        else None
                    ),
                )
        else:
            # No DI container, use standard extractor
            self.clinical_extractor = ClinicalFeatureExtractor(
                user_id=(
                    self.config.user_id
                    if self.config.enable_personal_calibration
                    else None
                ),
            )

        self.mood_predictor = MoodPredictor(model_dir=self.config.model_dir)
        self.xgboost_predictor = None  # Will be loaded separately for ensemble

        # Note: aggregation_pipeline will be set below after checking if one was provided

        # Initialize ensemble orchestrator if PAT sequences are enabled
        self.ensemble_orchestrator = None
        if self.config.include_pat_sequences:
            from big_mood_detector.infrastructure.ml_models import PAT_AVAILABLE

            # Lazy import to avoid module-level loading
            from big_mood_detector.infrastructure.ml_models.xgboost_models import (
                XGBoostMoodPredictor,
            )

            # Initialize XGBoost predictor for ensemble
            self.xgboost_predictor = XGBoostMoodPredictor()
            model_dir = self.config.model_dir or Path("model_weights/xgboost/converted")
            if self.xgboost_predictor.load_models(model_dir):
                logger.info("XGBoost models loaded for ensemble")

            # Initialize PAT model if available
            pat_model = None
            if PAT_AVAILABLE:
                import os

                from big_mood_detector.infrastructure.ml_models.pat_production_loader import (
                    ProductionPATLoader,
                )
                skip_loading = os.getenv("TESTING", "0") == "1"
                pat_model = ProductionPATLoader(skip_loading=skip_loading)
            else:
                logger.warning("PAT model not available - TensorFlow not installed")

            # Check if PAT model loaded successfully
            if pat_model is not None and not skip_loading:
                if not pat_model.is_loaded:
                    logger.warning("Failed to load PAT model weights")
                    pat_model = None
                else:
                    logger.info("PAT model loaded successfully")

            if self.xgboost_predictor and self.xgboost_predictor.is_loaded:
                # Create temporal ensemble orchestrator for NOW vs TOMORROW separation

                # Get PAT predictor from DI if available
                pat_predictor = None
                if di_container:
                    try:
                        from big_mood_detector.domain.services.pat_predictor import (
                            PATPredictorInterface,
                        )
                        pat_predictor = di_container.resolve(PATPredictorInterface)
                    except Exception:
                        logger.warning("PAT predictor not available from DI")

                # Only create temporal orchestrator if all components are available
                if pat_predictor and pat_model:
                    self.ensemble_orchestrator = TemporalEnsembleOrchestrator(
                        pat_predictor=pat_predictor,
                        xgboost_predictor=self.xgboost_predictor,
                        pat_encoder=pat_model,
                    )
                else:
                    logger.warning("Cannot create temporal orchestrator without PAT models")
                    self.ensemble_orchestrator = None

        # Data parsing service (extracted)
        self.data_parsing_service = data_parsing_service or DataParsingService()

        # Activity sequence extractor for PAT
        self.activity_sequence_extractor = ActivitySequenceExtractor()

        # Aggregation pipeline (extracted)
        self.aggregation_pipeline = aggregation_pipeline or AggregationPipeline(
            sleep_analyzer=self.sleep_analyzer,
            activity_extractor=self.activity_extractor,
            circadian_analyzer=self.circadian_analyzer,
            dlmo_calculator=self.dlmo_calculator,
        )

        # Initialize personal calibrator
        self.personal_calibrator = None
        if self.config.enable_personal_calibration:
            if self.config.personal_calibrator:
                # Use provided calibrator
                self.personal_calibrator = self.config.personal_calibrator
            elif self.config.user_id and self.config.model_dir:
                # Try to load existing personal model
                try:
                    from big_mood_detector.infrastructure.fine_tuning.personal_calibrator import (
                        PersonalCalibrator,
                    )

                    self.personal_calibrator = PersonalCalibrator.load(
                        user_id=self.config.user_id, model_dir=self.config.model_dir
                    )
                    logger.info(
                        f"Loaded personal model for user: {self.config.user_id}"
                    )
                except Exception as e:
                    logger.warning(f"Could not load personal model: {e}")
                    # Continue without personal calibration

        # Note: TemporalEnsembleOrchestrator doesn't use personal calibrator
        # as it separates NOW (PAT) from TOMORROW (XGBoost) predictions

    @classmethod
    def for_testing(
        cls,
        predictor: Any,
        config: PipelineConfig | None = None,
        disable_ensemble: bool = True
    ) -> "MoodPredictionPipeline":
        """Create a pipeline configured for testing with a custom predictor."""
        if config is None:
            config = PipelineConfig()

        pipeline = cls(config=config)
        pipeline.mood_predictor = predictor

        if disable_ensemble:
            pipeline.ensemble_orchestrator = None

        return pipeline

    def process_apple_health_file(
        self,
        file_path: Path,
        start_date: date | None = None,
        end_date: date | None = None,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> PipelineResult:
        """
        Process Apple Health export file and generate mood predictions.

        Args:
            file_path: Path to export.xml or JSON directory
            start_date: Optional start date filter
            end_date: Optional end date filter
            progress_callback: Optional callback for progress updates

        Returns:
            PipelineResult with predictions and metadata
        """
        # Delegate parsing to DataParsingService
        parsed_data = self.data_parsing_service.parse_health_data(
            file_path=file_path,
            start_date=start_date,
            end_date=end_date,
            continue_on_error=True,
            progress_callback=progress_callback,
        )

        # Extract records from parsed data
        sleep_records = parsed_data.get("sleep_records", [])
        activity_records = parsed_data.get("activity_records", [])
        heart_records = parsed_data.get("heart_rate_records", [])
        errors = parsed_data.get("errors", [])

        # Determine actual date range from data if end_date not specified
        actual_end_date = end_date
        if actual_end_date is None:
            data_dates = []
            if sleep_records:
                data_dates.extend([r.start_date.date() for r in sleep_records])
            if activity_records:
                data_dates.extend([r.start_date.date() for r in activity_records])
            if heart_records:
                data_dates.extend([r.timestamp.date() for r in heart_records])

            if data_dates:
                actual_end_date = max(data_dates)
                logger.info(f"Using latest data date as target: {actual_end_date}")
            else:
                # Only use today if there's literally no data
                actual_end_date = date.today()
                logger.warning("No data found, using today's date as target")

        # Process health data
        result = self.process_health_data(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            target_date=actual_end_date,
        )

        # Add any parsing errors to result
        if errors:
            result.errors.extend(errors)
            result.has_errors = True

        return result

    def process_health_data(
        self,
        sleep_records: list[Any],
        activity_records: list[Any],
        heart_records: list[Any],
        target_date: date,
    ) -> PipelineResult:
        """
        Process health data and generate mood predictions.

        Args:
            sleep_records: List of sleep records
            activity_records: List of activity records
            heart_records: List of heart rate records
            target_date: Target date for analysis

        Returns:
            PipelineResult with predictions and metadata
        """
        start_time = time.time()
        warnings = []
        errors = []

        # Validate target_date
        if target_date is None:
            raise ValueError("target_date cannot be None. Use process_apple_health_file() which determines dates automatically.")

        # Check if models are loaded
        if not self.mood_predictor.is_loaded:
            errors.append("Models not loaded")
            return PipelineResult(
                daily_predictions={},
                overall_summary={},
                confidence_score=0.0,
                processing_time_seconds=time.time() - start_time,
                has_errors=True,
                errors=errors,
            )

        # Determine date window to analyze
        window = None  # Track selected window for metadata
        window_analysis = None  # Track dual model analysis

        # Check if we should use dual model analysis
        if self.config.window_selection_strategy and hasattr(self.config.window_selection_strategy, '__class__') and 'Dual' in self.config.window_selection_strategy.__class__.__name__:
            # Use dual model window analysis
            from big_mood_detector.domain.services.dual_model_window_strategy import (
                DualModelWindowStrategy,
            )
            dual_strategy = DualModelWindowStrategy()
            window_analysis = dual_strategy.analyze_windows(sleep_records)

            if window_analysis.optimal_window:
                window = window_analysis.optimal_window
                start_date = window.start_date
                end_date = window.end_date
                logger.info(f"Using dual-selected window from {start_date} to {end_date}")

                # Add window analysis to metadata
                warnings.append(window_analysis.selection_reason)
            else:
                # No valid windows found
                return PipelineResult(
                    daily_predictions={},
                    overall_summary={},
                    confidence_score=0.0,
                    processing_time_seconds=time.time() - start_time,
                    has_warnings=True,
                    warnings=[window_analysis.selection_reason],
                    metadata={"window_analysis": window_analysis},
                )
        elif self.config.window_selection_strategy:
            # Use strategy to find valid windows
            windows = self.config.window_selection_strategy.find_windows(
                sleep_records,
                min_days=self.config.min_days_required
            )

            if not windows:
                # No valid windows found
                available_days = len({r.start_date.date() for r in sleep_records})
                return PipelineResult(
                    daily_predictions={},
                    overall_summary={},
                    confidence_score=0.0,
                    processing_time_seconds=time.time() - start_time,
                    has_warnings=True,
                    warnings=[
                        f"No valid {self.config.min_days_required}-day windows found. "
                        f"Found {available_days} days of data across "
                        f"{(max(r.start_date.date() for r in sleep_records) - min(r.start_date.date() for r in sleep_records)).days} days"
                    ],
                    metadata={"windows_checked": len(sleep_records)},
                )

            # Use the first (best) window from strategy
            window = windows[0]
            # Help mypy understand window is not None after assignment
            assert window is not None
            start_date = window.start_date
            end_date = window.end_date

            logger.info(f"Using window from {start_date} to {end_date} (quality: {window.data_quality:.2f})")

        else:
            # Legacy behavior: look back from target_date
            start_date = target_date - timedelta(days=self.config.min_days_required - 1)
            end_date = target_date

            # Check data sufficiency
            available_days = len({r.start_date.date() for r in sleep_records})
            if available_days < self.config.min_days_required:
                warnings.append(
                    f"Insufficient data: {available_days} days available, {self.config.min_days_required} required"
                )

        # Check for sparse data within the analysis window (for all cases)
        if sleep_records and start_date and end_date:
            # Count days with data in the analysis window
            days_in_window = {
                r.start_date.date()
                for r in sleep_records
                if start_date <= r.start_date.date() <= end_date
            }

            # Calculate window size
            window_size = (end_date - start_date).days + 1

            # Calculate density within the window
            window_density = len(days_in_window) / window_size if window_size > 0 else 0

            # Only warn if data is sparse within the analysis window
            if window_density < 0.5 and len(days_in_window) > 0:
                warnings.append(f"Sparse data in analysis window: {window_density:.1%} coverage ({len(days_in_window)}/{window_size} days)")

        # Extract features for date range
        features = self.extract_features_batch(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            start_date=start_date,
            end_date=end_date,
        )

        # Generate predictions
        daily_predictions: dict[date, dict[str, Any]] = {}
        window_predictions: dict[tuple[date, date], dict[str, Any]] = {}
        overall_summary: dict[str, Any] = {}
        confidence_score = 0.0

        # Check if we're in XGBoost-only mode (sparse data, no PAT)
        if window_analysis and window_analysis.can_run_xgboost and not window_analysis.can_run_pat:
            # XGBoost-only mode: generate ONE prediction for the entire window
            logger.info("Using XGBoost-only mode with window-level prediction")

            # Aggregate features across the entire window
            if self.config.use_seoul_features and self.aggregation_pipeline:
                # Get aggregated features for the window
                seoul_features_list = self.aggregation_pipeline.aggregate_seoul_features(
                    sleep_records=sleep_records,
                    activity_records=activity_records,
                    heart_records=heart_records,
                    start_date=start_date,
                    end_date=end_date,
                )

                if seoul_features_list:
                    # Aggregate all daily features into a single window feature
                    # This represents the overall pattern across the window
                    aggregated_features: dict[str, list[float]] = {}
                    feature_count = 0

                    for daily_feature in seoul_features_list:
                        feature_dict = daily_feature.to_xgboost_dict()
                        for key, value in feature_dict.items():
                            if key not in aggregated_features:
                                aggregated_features[key] = []
                            aggregated_features[key].append(value)
                        feature_count += 1

                    # Compute window-level statistics (mean of daily features)
                    window_features = {}
                    for key, values in aggregated_features.items():
                        window_features[key] = np.mean(values)

                    # Create feature vector for XGBoost
                    from big_mood_detector.infrastructure.ml_models.xgboost_models import (
                        XGBoostModelLoader,
                    )
                    feature_vector = np.array([window_features.get(name, 0.0) for name in XGBoostModelLoader.FEATURE_NAMES])

                    # Make single prediction for the window
                    prediction = self.mood_predictor.predict(feature_vector)

                    # Store as window prediction
                    window_key = (start_date, end_date)
                    window_predictions[window_key] = {
                        "depression_risk": prediction.depression_risk,
                        "hypomanic_risk": prediction.hypomanic_risk,
                        "manic_risk": prediction.manic_risk,
                        "confidence": prediction.confidence,
                        "model": "xgboost",
                        "window_coverage": window.data_quality if window else 1.0,
                        "days_analyzed": feature_count,
                        "feature_aggregation": "window_mean"
                    }

                    # For backward compatibility, also populate overall summary
                    overall_summary["depression_risk"] = prediction.depression_risk
                    overall_summary["hypomanic_risk"] = prediction.hypomanic_risk
                    overall_summary["manic_risk"] = prediction.manic_risk
                    overall_summary["primary_model"] = "xgboost"
                    overall_summary["analysis_type"] = "window"

                    # Don't create daily predictions in window mode
                    logger.info(f"Generated window prediction for {start_date} to {end_date}")

        # Original flow for ensemble mode or when PAT is available
        elif self.config.use_seoul_features and self.aggregation_pipeline and not self.ensemble_orchestrator:
            # Generate Seoul features specifically for XGBoost
            seoul_features_list = self.aggregation_pipeline.aggregate_seoul_features(
                sleep_records=sleep_records,
                activity_records=activity_records,
                heart_records=heart_records,
                start_date=start_date,
                end_date=target_date,
            )

            # Create predictions for each day that has Seoul features
            for daily_feature in seoul_features_list:
                feature_date = daily_feature.date
                feature_dict = daily_feature.to_xgboost_dict()

                # Create array in XGBoost expected order
                from big_mood_detector.infrastructure.ml_models.xgboost_models import (
                    XGBoostModelLoader,
                )
                feature_vector = np.array([feature_dict.get(name, 0.0) for name in XGBoostModelLoader.FEATURE_NAMES])

                prediction = self.mood_predictor.predict(feature_vector)

                daily_predictions[feature_date] = {
                    "depression_risk": prediction.depression_risk,
                    "hypomanic_risk": prediction.hypomanic_risk,
                    "manic_risk": prediction.manic_risk,
                    "confidence": prediction.confidence,
                }
        else:
            # Original flow using clinical features (will fail for XGBoost)
            for feature_date, feature_set in features.items():
                if feature_set and feature_set.seoul_features:
                    feature_vector = np.array(
                        feature_set.seoul_features.to_xgboost_features()
                    )

                    if self.ensemble_orchestrator:
                        # Use ensemble predictions
                        # Get activity records for the current date
                        date_activity_records = [
                            r
                            for r in activity_records
                            if r.start_date.date() <= feature_date <= r.end_date.date()
                        ]

                        # Convert activity records to PAT sequence
                        pat_sequence = None
                        if date_activity_records and hasattr(self, 'activity_sequence_extractor'):
                            try:
                                # Extract minute sequence and reshape to 7x1440
                                minute_seq = self.activity_sequence_extractor.extract_minute_sequence(
                                    date_activity_records,
                                    days=7
                                )
                                # Reshape from (10080,) to (7, 1440)
                                pat_sequence = minute_seq.reshape(7, 1440)
                            except Exception as e:
                                logger.warning(f"Failed to extract PAT sequence: {e}")

                        # Get temporal assessment
                        if pat_sequence is not None:
                            temporal_result = self.ensemble_orchestrator.predict(
                                statistical_features=feature_vector,
                                pat_sequence=pat_sequence,
                                user_id=self.config.user_id,
                            )
                        else:
                            # Create dummy sequence if PAT unavailable
                            dummy_sequence = np.zeros((7, 1440), dtype=np.float32)
                            temporal_result = self.ensemble_orchestrator.predict(
                                statistical_features=feature_vector,
                                pat_sequence=dummy_sequence,
                                user_id=self.config.user_id,
                            )

                        # Use future risk (XGBoost) for backward compatibility
                        future_risk = temporal_result.future_risk

                        daily_predictions[feature_date] = {
                            "depression_risk": future_risk.depression_risk,
                            "hypomanic_risk": future_risk.hypomanic_risk,
                            "manic_risk": future_risk.manic_risk,
                            "confidence": future_risk.confidence,
                            "models_used": ["xgboost", "pat"] if pat_sequence is not None else ["xgboost"],
                            "confidence_scores": {
                                "xgboost": future_risk.confidence,
                                "pat": temporal_result.current_state.confidence,
                            },
                            # Add temporal assessment data
                            "current_depression": temporal_result.current_state.depression_probability,
                            "temporal_concordance": temporal_result.temporal_concordance,
                        }

                        # Add warning if PAT failed
                        if pat_sequence is None:
                            warnings.append("PAT sequence unavailable")
                    else:
                        # Use XGBoost-only predictions
                        prediction = self.mood_predictor.predict(feature_vector)

                        daily_predictions[feature_date] = {
                            "depression_risk": prediction.depression_risk,
                            "hypomanic_risk": prediction.hypomanic_risk,
                            "manic_risk": prediction.manic_risk,
                            "confidence": prediction.confidence,
                        }

        # Calculate overall summary
        if daily_predictions:
            summary, new_confidence = SummaryCalculator.calculate_from_daily_predictions(
                daily_predictions
            )
            overall_summary.update(summary)
            if new_confidence > 0:
                confidence_score = new_confidence
        elif window_predictions and not overall_summary:
            # If we only have window predictions and no overall summary set yet
            summary, new_confidence = SummaryCalculator.calculate_from_window_predictions(
                window_predictions
            )
            overall_summary.update(summary)
            if new_confidence > 0:
                confidence_score = new_confidence

        # Adjust confidence based on data quality
        confidence_score = SummaryCalculator.adjust_confidence_for_warnings(
            confidence_score, has_warnings=bool(warnings)
        )

        # Build metadata
        metadata: dict[str, Any] = {}
        if window:
            metadata["window_used"] = window
        if window_analysis:
            metadata["window_analysis"] = window_analysis
        if self.personal_calibrator:
            metadata["personal_calibration_used"] = True
            metadata["user_id"] = self.personal_calibrator.user_id
            metadata["baseline_available"] = bool(self.personal_calibrator.baseline)

        # Add data date range metadata
        if sleep_records or activity_records or heart_records:
            all_dates = []
            if sleep_records:
                all_dates.extend([r.start_date.date() for r in sleep_records])
            if activity_records:
                all_dates.extend([r.start_date.date() for r in activity_records])
            if heart_records:
                all_dates.extend([r.timestamp.date() for r in heart_records])

            if all_dates:
                metadata["data_start_date"] = min(all_dates)
                metadata["data_end_date"] = max(all_dates)

        return PipelineResult(
            daily_predictions=daily_predictions,
            window_predictions=window_predictions,
            overall_summary=overall_summary,
            confidence_score=confidence_score,
            processing_time_seconds=time.time() - start_time,
            records_processed=len(sleep_records)
            + len(activity_records)
            + len(heart_records),
            features_extracted=len(features),
            has_warnings=bool(warnings),
            warnings=warnings,
            has_errors=bool(errors),
            errors=errors,
            metadata=metadata,
        )

    def extract_features_batch(
        self,
        sleep_records: list[Any],
        activity_records: list[Any],
        heart_records: list[Any],
        start_date: date,
        end_date: date,
    ) -> dict[date, ClinicalFeatureSet | None]:
        """
        Extract features for multiple days efficiently.

        Args:
            sleep_records: List of sleep records
            activity_records: List of activity records
            heart_records: List of heart rate records
            start_date: Start date for extraction
            end_date: End date for extraction

        Returns:
            Dictionary mapping dates to ClinicalFeatureSet
        """
        features: dict[date, ClinicalFeatureSet | None] = {}

        current_date = start_date
        while current_date <= end_date:
            try:
                feature_set = self.clinical_extractor.extract_clinical_features(
                    sleep_records=sleep_records,
                    activity_records=activity_records,
                    heart_records=heart_records,
                    target_date=current_date,
                    include_pat_sequence=self.config.include_pat_sequences,
                )
                features[current_date] = feature_set

            except Exception as e:
                # Log error but continue processing other dates
                logger.error(
                    "feature_extraction_failed",
                    date=str(current_date),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                features[current_date] = None

            current_date += timedelta(days=1)

        # Note: Baselines are now calculated using rolling windows in AggregationPipeline

        return features

    def update_personal_model(
        self,
        features: pd.DataFrame,
        labels: NDArray[np.float32],
        sample_weight: NDArray[np.float32] | None = None,
    ) -> dict[str, float] | None:
        """
        Update personal model with new labeled data.

        Args:
            features: Feature matrix
            labels: Ground truth labels
            sample_weight: Optional sample weights

        Returns:
            Dictionary of training metrics or None if no calibrator
        """
        if not self.personal_calibrator:
            logger.warning("No personal calibrator available for model update")
            return None

        # Calibrate the model
        metrics = self.personal_calibrator.calibrate(
            features=features,
            labels=labels,
            sample_weight=sample_weight or 1.0,
        )

        # Save the updated model
        self.personal_calibrator.save_model(metrics)

        return metrics  # type: ignore[no-any-return]

    def export_results(self, result: PipelineResult, output_path: Path) -> None:
        """
        Export pipeline results to CSV format.

        Args:
            result: PipelineResult to export
            output_path: Path to save CSV file
        """
        # Convert predictions to DataFrame
        rows = []
        for pred_date, prediction in result.daily_predictions.items():
            row: dict[str, Any] = {"date": pred_date}
            row.update(prediction)
            rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("date")

        # Save to CSV
        df.to_csv(output_path, index=False)

        # Also save summary
        summary_path = output_path.with_suffix(".summary.json")
        import json

        with open(summary_path, "w") as f:
            summary_data = {
                "overall_summary": result.overall_summary,
                "confidence_score": result.confidence_score,
                "processing_time_seconds": result.processing_time_seconds,
                "records_processed": result.records_processed,
                "warnings": result.warnings,
                "errors": result.errors,
            }

            # Add personal calibration info if available
            if result.metadata.get("personal_calibration_used"):
                summary_data["personal_calibration"] = {
                    "user_id": result.metadata.get("user_id"),
                    "baseline_available": result.metadata.get("baseline_available"),
                }

            json.dump(summary_data, f, indent=2, default=str)

    def process_parsed_health_data(
        self,
        parsed_data: dict[str, Any] | Any,  # Can be dict or ParsedHealthData
        output_path: Path,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        """
        Process already-parsed health data.

        Args:
            parsed_data: Already parsed health data (dict or ParsedHealthData)
            output_path: Where to save the 36 features CSV
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            DataFrame with 36 features per day
        """
        # Extract records from parsed data
        records: dict[str, list[Any]]
        if hasattr(parsed_data, "sleep_records"):
            # It's a ParsedHealthData object
            from big_mood_detector.application.services.data_parsing_service import (
                ParsedHealthData,
            )

            if isinstance(parsed_data, ParsedHealthData):
                records = {
                    "sleep": parsed_data.sleep_records,
                    "activity": parsed_data.activity_records,
                    "heart_rate": parsed_data.heart_rate_records,
                }
            else:
                # Fallback - should not happen
                records = {"sleep": [], "activity": [], "heart_rate": []}
        else:
            # It's a dict
            records = {
                "sleep": parsed_data.get("sleep_records", []),
                "activity": parsed_data.get("activity_records", []),
                "heart_rate": parsed_data.get("heart_rate_records", []),
            }

        # Validate parsed data - validator now handles both types
        validation_result = self.data_parsing_service.validate_parsed_data(parsed_data)
        if not validation_result.is_valid:
            logger.warning(
                "data_validation_failed",
                warnings=validation_result.warnings,
                warning_count=len(validation_result.warnings),
            )

        # Get data summary for analysis
        self.data_parsing_service.get_data_summary(
            parsed_data
            if isinstance(parsed_data, dict)
            else self.data_parsing_service._format_result(parsed_data)
        )

        # Continue with existing processing logic
        return self._process_parsed_data_internal(
            records, output_path, start_date, end_date
        )

    def process_health_export(
        self,
        export_path: Path,
        output_path: Path,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        """
        Process complete Apple Health export.

        Args:
            export_path: Path to export.xml or JSON directory
            output_path: Where to save the 36 features CSV
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            DataFrame with 36 features per day
        """
        # Use DataParsingService for all parsing operations
        parsed_data = self.data_parsing_service.parse_health_data(
            file_path=export_path,
            start_date=start_date,
            end_date=end_date,
            continue_on_error=True,
        )

        # Extract records from parsed data
        records = {
            "sleep": parsed_data.get("sleep_records", []),
            "activity": parsed_data.get("activity_records", []),
            "heart_rate": parsed_data.get("heart_rate_records", []),
        }

        # Validate parsed data
        validation_result = self.data_parsing_service.validate_parsed_data(parsed_data)
        if not validation_result.is_valid:
            logger.warning(
                "data_validation_failed",
                warnings=validation_result.warnings,
                warning_count=len(validation_result.warnings),
            )

        # Continue with existing processing logic
        return self._process_parsed_data_internal(
            records, output_path, start_date, end_date
        )

    def _process_parsed_data_internal(
        self,
        records: dict[str, list[Any]],
        output_path: Path,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        """Internal method to process parsed records."""
        # First, analyze data density and quality
        sleep_dates = [r.start_date.date() for r in records.get("sleep", [])]
        activity_dates = [r.start_date.date() for r in records.get("activity", [])]

        logger.info("data_quality_analysis_started")
        if sleep_dates:
            sleep_density = self.sparse_handler.assess_density(sleep_dates)
            logger.info(
                "sleep_data_quality",
                days_count=len(sleep_dates),
                coverage_ratio=round(sleep_density.coverage_ratio, 3),
                max_gap_days=sleep_density.max_gap_days,
                quality=sleep_density.density_class.name,
            )

        if activity_dates:
            activity_density = self.sparse_handler.assess_density(activity_dates)
            logger.info(
                "activity_data_quality",
                days_count=len(activity_dates),
                coverage_ratio=round(activity_density.coverage_ratio, 3),
                max_gap_days=activity_density.max_gap_days,
                quality=activity_density.density_class.name,
            )

        # Find overlapping windows
        if sleep_dates and activity_dates:
            windows = self.sparse_handler.find_analysis_windows(
                sleep_dates, activity_dates
            )
            logger.info(
                "overlapping_windows_found",
                window_count=len(windows),
                sample_windows=[
                    {
                        "start": str(start),
                        "end": str(end),
                        "days": (end - start).days + 1,
                    }
                    for start, end in windows[:3]
                ],
            )

        # Extract features for each day using aggregation pipeline
        features = self._extract_daily_features(records, start_date, end_date)

        # Convert to DataFrame
        if not features:
            logger.warning(
                "no_features_extracted",
                message="Check date range and data availability",
            )
            df = pd.DataFrame()  # Empty dataframe
        else:
            df = pd.DataFrame([f.to_dict() for f in features])
            df.set_index("date", inplace=True)
            df.sort_index(inplace=True)

            # Add confidence scores based on data density
            logger.info(
                "features_extracted", days_count=len(df), adding_confidence_scores=True
            )

        # Save to CSV
        df.to_csv(output_path)
        logger.info("features_saved", days_count=len(df), output_path=str(output_path))

        return df

    def _extract_daily_features(
        self,
        records: dict[str, list[Any]],
        start_date: date | None,
        end_date: date | None,
    ) -> list[ClinicalFeatureSet]:
        """
        Extract 36 features for each day using the aggregation pipeline.

        This delegates to the AggregationPipeline service for cleaner separation of concerns.
        """
        sleep_records = records["sleep"]
        activity_records = records["activity"]
        heart_records = records.get("heart_rate", [])

        # Determine date range
        if not sleep_records:
            return []

        all_dates = [r.start_date.date() for r in sleep_records]
        min_date = start_date or min(all_dates)
        max_date = end_date or max(all_dates)

        # Use aggregation pipeline
        return self.aggregation_pipeline.aggregate_daily_features(
            sleep_records=sleep_records,
            activity_records=activity_records,
            heart_records=heart_records,
            start_date=min_date,
            end_date=max_date,
        )


# Convenience function for CLI usage
def process_health_data(
    input_path: str,
    output_path: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """
    Process health data from command line.

    Args:
        input_path: Path to Apple Health export
        output_path: Path for output CSV
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        DataFrame with 36 features
    """
    pipeline = MoodPredictionPipeline()

    # Parse dates
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None

    return pipeline.process_health_export(
        Path(input_path), Path(output_path), start, end
    )
