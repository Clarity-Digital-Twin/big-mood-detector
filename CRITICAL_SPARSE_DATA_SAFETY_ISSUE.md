# CRITICAL SAFETY ISSUE: Sparse Data Handling in Big Mood Detector

**Severity**: CRITICAL - Patient Safety Risk  
**Priority**: P0 - MUST FIX BEFORE ANY CLINICAL USE  
**Created**: 2025-07-29  
**Status**: ACTIVE BUG - SYSTEM UNSAFE FOR CLINICAL USE  

## 🚨 THE CRITICAL ISSUE

Big Mood Detector v0.5.3 **SILENTLY GENERATES FAKE CLINICAL PREDICTIONS** when users have sparse data, presenting them with **HIGH CONFIDENCE** as if they were real assessments. This is a **PATIENT SAFETY VIOLATION** that could lead to:

1. **Missed depression episodes** - Users see "4.4% LOW risk" when they might be at high risk
2. **False reassurance** - 91.3% confidence in fake data could prevent seeking help
3. **Clinical malpractice liability** - Providing medical advice based on synthetic data
4. **Loss of user trust** - When users discover predictions are identical daily

## 📊 EVIDENCE: User's Actual Experience

```
User's Apple Watch wearing pattern:
- June 26: ❌ No data
- June 27: ✅ Sleep tracked  
- June 28: ❌ No data
- June 29: ✅ Sleep tracked
- June 30: ✅ Sleep tracked
- July 1:  ❌ No data
- July 2:  ✅ Sleep tracked

Result: 4/7 days = 57% coverage
```

**What the system showed the user:**
```
CLINICAL DECISION SUPPORT (CDS) REPORT
==================================================
Depression Risk: 4.4% [LOW] ✓
Hypomanic Risk: 0.9% [LOW] ✓
Manic Risk: 0.1% [LOW] ✓
Data Quality Score: 91.3% ← THIS IS A LIE

Daily Analysis:
2025-06-26: Depression: 4.4% [LOW], Confidence: 91.3% ← NO DATA THIS DAY
2025-06-27: Depression: 4.4% [LOW], Confidence: 91.3% ← REAL DATA
2025-06-28: Depression: 4.4% [LOW], Confidence: 91.3% ← NO DATA THIS DAY
[... IDENTICAL FOR ALL 7 DAYS ...]
```

## 🔍 DEEP EXECUTION TRACE

### Step 1: Data Parsing (`predict_command` → `process_apple_health_file`)
```python
# User runs: python main.py predict export.xml --date-range 2025-06-26:2025-07-02

# CLI loads 520MB XML file
# Parser finds only 4 days of sleep records out of 7 requested
sleep_records = [
    SleepRecord(date="2025-06-27", ...),
    SleepRecord(date="2025-06-29", ...),
    SleepRecord(date="2025-06-30", ...),
    SleepRecord(date="2025-07-02", ...)
]
# Missing: June 26, 28, July 1
```

### Step 2: Feature Extraction (`process_health_data` → `extract_features_batch`)
```python
# For EACH day in range, system attempts to extract features
for current_date in [June 26, 27, 28, 29, 30, July 1, 2]:
    # clinical_extractor.extract_clinical_features() is called
    # When no data exists for the day, it returns features with DEFAULTS
```

### Step 3: The Default Factory (`aggregation_pipeline.py:978-1040`)
```python
# When no sleep data for a day, creates SYNTHETIC features:
SeoulFeatures(
    date=current_date,
    sleep_duration_mean=8.0,           # FAKE: Assumes 8 hours
    sleep_duration_std=0.0,            # FAKE: No variation
    sleep_efficiency=0.9,              # FAKE: 90% efficiency
    sleep_onset_hour=21.0,             # FAKE: 9 PM bedtime
    wake_time_hour=7.0,                # FAKE: 7 AM wake
    sleep_fragmentation=0.0,           # FAKE: Perfect sleep
    sleep_regularity_index=90.0,       # FAKE: Very regular
    # ... 29 more fake values ...
)
```

### Step 4: XGBoost Predictions (`mood_predictor.py`)
```python
# For EVERY day (real or fake data):
feature_vector = [8.0, 0.0, 0.0, 21.0, 0.0, 0.0, ...]  # Same defaults
prediction = xgboost_model.predict(feature_vector)
# Result: ALWAYS returns [0.044, 0.009, 0.001] for default features
```

### Step 5: PAT Failure (`temporal_ensemble_orchestrator.py:103`)
```python
try:
    # This line ALWAYS fails:
    pat_embeddings = self.pat_encoder.encode(pat_sequence)
    # ERROR: 'ProductionPATLoader' object has no attribute 'encode'
except Exception as e:
    # Silently logged, user never sees this failure
    logger.error(f"PAT assessment failed: {e}")
    # Falls back to XGBoost-only predictions
```

### Step 6: Confidence Calculation (`xgboost_models.py:294-306`)
```python
def _calculate_confidence(self, max_risk: float) -> float:
    # max_risk = 0.044 (4.4% depression)
    # confidence = abs(0.044 - 0.5) * 2 = 0.912
    return abs(max_risk - 0.5) * 2  # Returns 91.3%
```

### Step 7: Report Generation (`generate_clinical_report`)
```python
# Writes "professional looking" report with:
# - Fake risk assessments
# - Fake confidence scores  
# - Real clinical recommendations
# - No indication data is synthetic
```

## 🏗️ PROFESSIONAL ENGINEERING SOLUTION

### 1. DATA VALIDATION LAYER (NEW)

Create `domain/services/clinical_data_validator.py`:
```python
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

class DataQuality(Enum):
    INSUFFICIENT = "insufficient"      # < 70% coverage
    MARGINAL = "marginal"             # 70-85% coverage  
    ACCEPTABLE = "acceptable"         # 85-95% coverage
    EXCELLENT = "excellent"           # > 95% coverage

@dataclass
class DataValidationResult:
    quality: DataQuality
    coverage_percentage: float
    missing_days: list[date]
    missing_domains: list[str]  # ["sleep", "activity", "heart_rate"]
    can_generate_predictions: bool
    confidence_ceiling: float  # Max allowable confidence given data quality
    warnings: list[str]
    recommendation: str

class ClinicalDataValidator:
    """Validates data sufficiency for clinical predictions."""
    
    MIN_COVERAGE_FOR_PREDICTIONS = 0.70  # 70% minimum
    MIN_COVERAGE_FOR_HIGH_CONFIDENCE = 0.85  # 85% for confidence > 0.7
    
    def validate_data_sufficiency(
        self,
        sleep_records: list[SleepRecord],
        activity_records: list[ActivityRecord],
        heart_records: list[HeartRateRecord],
        start_date: date,
        end_date: date
    ) -> DataValidationResult:
        """
        Validates if we have sufficient data for clinical predictions.
        
        This is a SAFETY-CRITICAL function that prevents predictions
        on insufficient data.
        """
        total_days = (end_date - start_date).days + 1
        
        # Calculate coverage for each domain
        sleep_days = {r.date for r in sleep_records}
        activity_days = {r.date for r in activity_records}
        heart_days = {r.date for r in heart_records}
        
        sleep_coverage = len(sleep_days) / total_days
        activity_coverage = len(activity_days) / total_days
        heart_coverage = len(heart_days) / total_days
        
        # Overall coverage is the MINIMUM (not average)
        overall_coverage = min(sleep_coverage, activity_coverage)
        
        # Identify missing data
        all_dates = {start_date + timedelta(days=i) for i in range(total_days)}
        missing_sleep = sorted(all_dates - sleep_days)
        missing_activity = sorted(all_dates - activity_days)
        
        # Determine quality level
        if overall_coverage < 0.70:
            quality = DataQuality.INSUFFICIENT
            can_predict = False
            confidence_ceiling = 0.0
            recommendation = (
                f"Cannot generate predictions with only {overall_coverage:.0%} data coverage. "
                f"Please wear your device consistently for at least {int(total_days * 0.7)} "
                f"out of {total_days} days."
            )
        elif overall_coverage < 0.85:
            quality = DataQuality.MARGINAL
            can_predict = True
            confidence_ceiling = 0.5  # Cap confidence at 50%
            recommendation = (
                f"Predictions available but limited by {overall_coverage:.0%} data coverage. "
                f"For best results, aim for 85%+ coverage."
            )
        elif overall_coverage < 0.95:
            quality = DataQuality.ACCEPTABLE
            can_predict = True
            confidence_ceiling = 0.8  # Cap confidence at 80%
            recommendation = "Good data coverage. Predictions should be reliable."
        else:
            quality = DataQuality.EXCELLENT
            can_predict = True
            confidence_ceiling = 1.0  # Full confidence allowed
            recommendation = "Excellent data coverage. High confidence predictions available."
        
        # Build warnings
        warnings = []
        missing_domains = []
        
        if sleep_coverage < 0.70:
            missing_domains.append("sleep")
            warnings.append(f"Insufficient sleep data: {sleep_coverage:.0%} coverage")
            
        if activity_coverage < 0.70:
            missing_domains.append("activity")
            warnings.append(f"Insufficient activity data: {activity_coverage:.0%} coverage")
            
        if heart_coverage < 0.50:
            missing_domains.append("heart_rate")
            warnings.append(f"Limited heart rate data: {heart_coverage:.0%} coverage")
        
        # Check for sparse patterns (gaps > 2 days)
        if missing_sleep:
            gaps = self._find_gaps(missing_sleep)
            if any(gap > 2 for gap in gaps):
                warnings.append("Large gaps in sleep tracking detected")
        
        return DataValidationResult(
            quality=quality,
            coverage_percentage=overall_coverage,
            missing_days=sorted(set(missing_sleep + missing_activity)),
            missing_domains=missing_domains,
            can_generate_predictions=can_predict,
            confidence_ceiling=confidence_ceiling,
            warnings=warnings,
            recommendation=recommendation
        )
    
    def _find_gaps(self, missing_dates: list[date]) -> list[int]:
        """Find consecutive gaps in dates."""
        if not missing_dates:
            return []
        
        gaps = []
        current_gap = 1
        
        for i in range(1, len(missing_dates)):
            if (missing_dates[i] - missing_dates[i-1]).days == 1:
                current_gap += 1
            else:
                gaps.append(current_gap)
                current_gap = 1
        
        gaps.append(current_gap)
        return gaps
```

### 2. REFUSAL TO PREDICT (SAFETY-FIRST)

Update `process_health_data_use_case.py`:
```python
def process_health_data(self, ...):
    # FIRST: Validate data sufficiency
    validator = ClinicalDataValidator()
    validation = validator.validate_data_sufficiency(
        sleep_records, activity_records, heart_records,
        start_date, end_date
    )
    
    # REFUSE if insufficient data
    if not validation.can_generate_predictions:
        logger.warning(
            "REFUSING PREDICTIONS: Insufficient data",
            coverage=validation.coverage_percentage,
            missing_domains=validation.missing_domains
        )
        
        return PipelineResult(
            daily_predictions={},
            overall_summary={},
            confidence_score=0.0,
            processing_time_seconds=time.time() - start_time,
            has_errors=True,
            errors=[validation.recommendation],
            warnings=validation.warnings,
            metadata={
                "data_validation": validation,
                "refused_reason": "insufficient_data",
                "coverage": validation.coverage_percentage
            }
        )
    
    # If marginal data, proceed with capped confidence
    if validation.quality == DataQuality.MARGINAL:
        logger.warning(
            "MARGINAL DATA: Predictions will have reduced confidence",
            coverage=validation.coverage_percentage,
            confidence_cap=validation.confidence_ceiling
        )
```

### 3. REMOVE ALL DEFAULT FEATURES

Update `aggregation_pipeline.py`:
```python
def aggregate_seoul_features(self, ...):
    # NEVER create fake features
    if not sleep_records_for_date:
        logger.warning(f"No sleep data for {current_date}, skipping")
        continue  # DON'T create fake SeoulFeatures
    
    # Only create features from REAL data
    features = self._calculate_real_features(sleep_records_for_date)
    yield features
```

### 4. FIX PAT INTEGRATION

Update `ProductionPATLoader`:
```python
def encode(self, activity_sequence: NDArray[np.float32]) -> NDArray[np.float32]:
    """
    Encode 7-day activity sequence to embeddings.
    
    Args:
        activity_sequence: Shape (7, 1440) or (10080,)
        
    Returns:
        Embeddings of shape (96,)
    """
    if not self.is_loaded:
        raise RuntimeError("Model not loaded")
    
    # Ensure correct shape
    if activity_sequence.shape == (10080,):
        activity_sequence = activity_sequence.reshape(7, 1440)
    
    if activity_sequence.shape != (7, 1440):
        raise ValueError(f"Expected (7, 1440), got {activity_sequence.shape}")
    
    with torch.no_grad():
        # Normalize
        normalized = self.normalizer.transform(activity_sequence)
        
        # Convert to tensor
        input_tensor = torch.from_numpy(normalized).float()
        input_tensor = input_tensor.unsqueeze(0)  # Add batch dim
        input_tensor = input_tensor.to(self.device)
        
        # Get embeddings
        embeddings = self.model.encoder(input_tensor)
        
        return embeddings.cpu().numpy().squeeze()
```

### 5. HONEST CONFIDENCE CALCULATION

Create `domain/services/confidence_calculator.py`:
```python
class ClinicalConfidenceCalculator:
    """
    Calculates honest confidence scores based on:
    - Data completeness
    - Prediction uncertainty
    - Model agreement (if ensemble)
    - Temporal consistency
    """
    
    def calculate_confidence(
        self,
        prediction: MoodPrediction,
        data_quality: DataQuality,
        confidence_ceiling: float,
        has_ensemble: bool = False,
        temporal_consistency: Optional[float] = None
    ) -> float:
        """
        Calculate honest confidence score.
        
        Factors:
        1. Base confidence from prediction strength
        2. Data quality penalty
        3. Ensemble agreement bonus
        4. Temporal consistency factor
        """
        # Start with prediction-based confidence
        # But use better formula that considers uncertainty
        prediction_confidence = self._prediction_confidence(prediction)
        
        # Apply data quality ceiling
        confidence = min(prediction_confidence, confidence_ceiling)
        
        # Reduce for marginal data
        if data_quality == DataQuality.MARGINAL:
            confidence *= 0.7
        
        # Bonus for ensemble agreement
        if has_ensemble and temporal_consistency:
            confidence = confidence * 0.8 + temporal_consistency * 0.2
        
        # Never exceed ceiling
        return min(confidence, confidence_ceiling)
    
    def _prediction_confidence(self, prediction: MoodPrediction) -> float:
        """
        Better confidence calculation that considers:
        - Distance from decision boundary (0.5)
        - But penalizes very low probabilities
        """
        risks = [
            prediction.depression_risk,
            prediction.hypomanic_risk,
            prediction.manic_risk
        ]
        
        # If all risks are very low, that's actually LOW confidence
        # (might indicate model is seeing unusual/default patterns)
        if all(r < 0.1 for r in risks):
            return 0.3  # Low confidence for all-low predictions
        
        # Otherwise use distance from 0.5 for highest risk
        max_risk = max(risks)
        return min(abs(max_risk - 0.5) * 1.5, 0.9)
```

### 6. CLINICAL SAFETY WARNINGS

Update report generation:
```python
def generate_clinical_report(result: PipelineResult, output_path: Path):
    with open(output_path, "w") as f:
        # ALWAYS start with data quality assessment
        if "data_validation" in result.metadata:
            validation = result.metadata["data_validation"]
            
            f.write("⚠️  DATA QUALITY WARNING ⚠️\n")
            f.write("=" * 50 + "\n")
            f.write(f"Data Coverage: {validation.coverage_percentage:.0%}\n")
            f.write(f"Quality Level: {validation.quality.value.upper()}\n")
            
            if validation.missing_domains:
                f.write(f"Missing Data Types: {', '.join(validation.missing_domains)}\n")
            
            f.write(f"\n{validation.recommendation}\n")
            f.write("=" * 50 + "\n\n")
        
        # Only show predictions if we have them
        if not result.daily_predictions:
            f.write("CLINICAL PREDICTIONS UNAVAILABLE\n")
            f.write("-" * 30 + "\n")
            f.write("Insufficient data for mood risk assessment.\n")
            f.write("\nRequired:\n")
            f.write("- Minimum 70% data coverage over assessment period\n")
            f.write("- At least 5 days with both sleep and activity data\n")
            f.write("- Consistent device wearing pattern\n")
            return
```

### 7. COMPREHENSIVE TEST SUITE

Create `tests/test_sparse_data_safety.py`:
```python
import pytest
from datetime import date, timedelta

class TestSparseDataSafety:
    """Critical safety tests for sparse data handling."""
    
    def test_refuses_predictions_below_70_percent_coverage(self):
        """System MUST refuse predictions with <70% data."""
        # Create 3/7 days of data (43% coverage)
        sleep_records = create_sparse_sleep_records(days=[1, 3, 5], total=7)
        
        pipeline = MoodPredictionPipeline()
        result = pipeline.process_health_data(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            target_date=date.today()
        )
        
        assert result.daily_predictions == {}
        assert result.has_errors == True
        assert "insufficient_data" in result.metadata.get("refused_reason", "")
        assert result.confidence_score == 0.0
        assert "70%" in result.errors[0]
    
    def test_caps_confidence_for_marginal_data(self):
        """Confidence must be capped at 50% for 70-85% coverage."""
        # Create 5/7 days (71% coverage)
        sleep_records = create_sparse_sleep_records(days=[1, 2, 3, 5, 7], total=7)
        
        result = pipeline.process_health_data(...)
        
        # Should generate predictions but with capped confidence
        assert len(result.daily_predictions) > 0
        assert result.confidence_score <= 0.5
        assert "marginal" in str(result.metadata.get("data_validation"))
    
    def test_no_identical_predictions_across_days(self):
        """Each day must have unique predictions if data differs."""
        sleep_records = create_varied_sleep_records(days=7)
        
        result = pipeline.process_health_data(...)
        
        # Extract all predictions
        predictions = [
            (p["depression_risk"], p["hypomanic_risk"], p["manic_risk"])
            for p in result.daily_predictions.values()
        ]
        
        # All predictions should be unique
        assert len(set(predictions)) == len(predictions), \
            "Found identical predictions across different days!"
    
    def test_pat_encoder_method_exists(self):
        """PAT loader must have encode() method."""
        pat_loader = ProductionPATLoader()
        assert hasattr(pat_loader, 'encode')
        
        # Test encoding
        dummy_sequence = np.zeros((7, 1440), dtype=np.float32)
        embeddings = pat_loader.encode(dummy_sequence)
        assert embeddings.shape == (96,)
    
    def test_no_default_features_in_pipeline(self):
        """Pipeline must not create synthetic features."""
        # Day with no data
        sleep_records = []
        
        pipeline = MoodPredictionPipeline()
        features = pipeline.extract_features_batch(
            sleep_records=sleep_records,
            activity_records=[],
            heart_records=[],
            start_date=date.today(),
            end_date=date.today()
        )
        
        # Should return empty/None, not defaults
        assert features[date.today()] is None
    
    def test_clinical_report_shows_warnings(self):
        """Report must prominently display data quality warnings."""
        # Create marginal data
        result = create_marginal_result()
        
        report_path = tmp_path / "report.txt"
        generate_clinical_report(result, report_path)
        
        report_text = report_path.read_text()
        assert "DATA QUALITY WARNING" in report_text
        assert "Coverage:" in report_text
        assert "MARGINAL" in report_text or "INSUFFICIENT" in report_text
```

## 📋 IMPLEMENTATION CHECKLIST

### Immediate (P0 - Before ANY Clinical Use)
- [ ] Add `ClinicalDataValidator` class
- [ ] Implement prediction refusal for <70% coverage
- [ ] Remove ALL default feature generation
- [ ] Fix PAT `encode()` method
- [ ] Add data quality warnings to reports
- [ ] Deploy emergency patch v0.5.4

### Short-term (P1 - Next Sprint)
- [ ] Implement honest confidence calculation
- [ ] Add comprehensive sparse data tests
- [ ] Create data sufficiency dashboard
- [ ] Add user notifications for poor coverage
- [ ] Implement gradual degradation (not cliff at 70%)

### Long-term (P2 - Next Quarter)
- [ ] ML models trained on sparse data patterns
- [ ] Uncertainty quantification in predictions
- [ ] Personalized coverage requirements
- [ ] Missing data imputation research
- [ ] Clinical validation study with sparse data

## 🚦 CLINICAL SAFETY REQUIREMENTS

### 1. Transparency
- Users MUST know when predictions are based on incomplete data
- Confidence scores MUST reflect actual certainty
- Reports MUST show data coverage prominently

### 2. Conservative Predictions
- When uncertain, refuse to predict
- Never fill missing data with population averages
- Clearly separate "estimates" from "measurements"

### 3. Clinical Validation
- Test with real sparse data patterns
- Validate against clinical outcomes
- Get IRB approval for any claims

### 4. User Education
- Explain why consistent wearing matters
- Show impact of missing data on accuracy
- Provide actionable improvement steps

## 🎯 SUCCESS CRITERIA

1. **No False Confidence**: System never shows >50% confidence with <85% data
2. **No Identical Days**: Each prediction is unique based on actual data
3. **Clear Refusals**: Below 70% coverage shows "Insufficient Data" not predictions
4. **Honest Reports**: Data quality warnings appear BEFORE any predictions
5. **Safe Defaults**: Missing data results in NO prediction, not synthetic ones

## 🔴 CURRENT STATUS: SYSTEM UNSAFE

Until these fixes are implemented, Big Mood Detector should:
1. Display warning: "EXPERIMENTAL - Not for Clinical Use"
2. Refuse predictions on sparse data
3. Log all prediction attempts for audit
4. Require explicit consent acknowledging limitations

---

**This is not just a bug - it's a PATIENT SAFETY ISSUE that could cause real harm. Fix it like lives depend on it, because they might.**