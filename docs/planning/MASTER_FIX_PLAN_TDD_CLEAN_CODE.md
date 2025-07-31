# MASTER FIX PLAN: TDD + Clean Code Approach
**Date**: 2025-07-29  
**Branch**: `bugfix/ensemble-integration-complete-fix`
**Approach**: Test-Driven Development (Red → Green → Refactor)

## 🎯 OBJECTIVE
Fix ALL identified bugs to make CDS reports show REAL data with CORRECT dates using PROPER ensemble predictions. NO MORE FAKE DATA. NO MORE LIES.

## 📋 COMPLETE BUG LIST (From Our 8 Investigations)

### Critical Bugs to Fix:
1. **BUG-001**: PAT method name wrong (`extract_multi_day_sequence` → `extract_minute_sequence`)
2. **BUG-002**: Date handling uses `date.today()` instead of actual data dates
3. **BUG-003**: Hardcoded medical fallbacks (0.5, 0.33, etc.)
4. **BUG-004**: DI container missing PAT service registrations
5. **BUG-005**: PAT gets 1 day of activity instead of 7 days needed
6. **BUG-006**: Silent exception handling hides all failures
7. **BUG-007**: TESTING=1 stubs out real models
8. **BUG-008**: No user-visible error messages

## 🧪 TDD APPROACH (Uncle Bob Style)

### PHASE 1: Write ALL Failing Tests First

#### Test Set 1: PAT Integration Tests
```python
# tests/integration/test_pat_real_integration.py
class TestPATRealIntegration:
    """NO MOCKS ALLOWED - Real models only"""
    
    def test_pat_sequence_extraction_returns_correct_shape(self):
        """PAT needs (7, 1440) shape array"""
        # Arrange
        activity_records = create_7_days_activity_data()
        extractor = ActivitySequenceExtractor()
        
        # Act
        sequence = extractor.extract_minute_sequence(activity_records, days=7)
        
        # Assert
        assert sequence.shape == (7 * 1440,)  # Will be reshaped later
        assert not np.all(sequence == 0)  # Has real data
        
    def test_pat_predictions_vary_by_day(self):
        """PAT should give different predictions for different data"""
        # This will FAIL until we fix the method name
        
    def test_pat_loads_real_weights(self):
        """Verify real model weights are loaded, not stubs"""
        # This will FAIL with TESTING=1
```

#### Test Set 2: Date Handling Tests
```python
# tests/integration/test_date_handling_reality.py
class TestDateHandlingReality:
    """Ensure dates match actual data, not today()"""
    
    def test_predictions_use_data_dates_not_today(self):
        """When processing 2024 data in 2025, use 2024 dates"""
        # Arrange
        old_data = load_test_data_from_2024()
        
        # Act
        result = pipeline.process_apple_health_file(old_data)
        
        # Assert
        max_prediction_date = max(result.daily_predictions.keys())
        assert max_prediction_date.year == 2024  # NOT 2025!
        
    def test_report_shows_actual_data_date_range(self):
        """Report header should show real data range"""
        # Will FAIL until we fix date handling
```

#### Test Set 3: No Fake Data Tests
```python
# tests/integration/test_no_fake_medical_data.py
class TestNoFakeMedicalData:
    """System must NEVER return hardcoded medical values"""
    
    def test_pat_failure_raises_exception_not_fake_data(self):
        """When PAT fails, raise error, don't return 0.5"""
        # Arrange
        broken_pat = Mock(side_effect=Exception("PAT broken"))
        
        # Act & Assert
        with pytest.raises(PredictionError):
            orchestrator.predict()  # Should NOT return 0.5!
            
    def test_no_hardcoded_depression_values(self):
        """Search codebase for hardcoded medical predictions"""
        # Grep for 0.5, 0.33, etc. in prediction contexts
```

#### Test Set 4: DI Container Tests
```python
# tests/integration/test_di_container_registration.py
class TestDIContainerRegistration:
    """Verify all services properly registered"""
    
    def test_pat_services_registered(self):
        """PAT interfaces must be resolvable"""
        container = get_container()
        
        # These will FAIL until we register them
        pat_encoder = container.resolve(PATEncoderInterface)
        pat_predictor = container.resolve(PATPredictorInterface)
        
        assert pat_encoder is not None
        assert pat_predictor is not None
        assert isinstance(pat_encoder, ProductionPATLoader)
```

#### Test Set 5: End-to-End Clinical Tests
```python
# tests/e2e/test_clinical_report_accuracy.py
class TestClinicalReportAccuracy:
    """Full pipeline with real data produces accurate reports"""
    
    def test_ensemble_report_shows_both_models(self):
        """When --ensemble used, both PAT and XGBoost run"""
        # Will show "models: xgboost, pat" in report
        
    def test_temporal_predictions_different(self):
        """NOW and TOMORROW should have different values"""
        # Not both 56.3%!
```

### PHASE 2: Make Tests Pass (Clean Implementation)

#### Fix 1: PAT Method Name (BUG-001)
```python
# src/big_mood_detector/application/use_cases/process_health_data_use_case.py
# Line 478
- minute_seq = self.activity_sequence_extractor.extract_multi_day_sequence(
+ minute_seq = self.activity_sequence_extractor.extract_minute_sequence(
```

#### Fix 2: Date Handling (BUG-002)
```python
# src/big_mood_detector/application/use_cases/process_health_data_use_case.py
def process_apple_health_file(self, file_path: Path, start_date: date | None = None, 
                            end_date: date | None = None) -> PipelineResult:
    # ... parsing code ...
    
    # NEW: Calculate actual date range from data
    actual_end_date = self._get_latest_data_date(
        sleep_records, activity_records, heart_records
    )
    
    result = self.process_health_data(
        sleep_records=sleep_records,
        activity_records=activity_records,
        heart_records=heart_records,
        target_date=end_date or actual_end_date,  # NOT date.today()!
    )

def _get_latest_data_date(self, sleep_records, activity_records, heart_records) -> date:
    """Get the latest date from actual data"""
    dates = []
    if sleep_records:
        dates.extend([r.start_date.date() for r in sleep_records])
    if activity_records:
        dates.extend([r.start_date.date() for r in activity_records])
    if heart_records:
        dates.extend([r.timestamp.date() for r in heart_records])
    
    return max(dates) if dates else date.today()  # Only use today() if NO data
```

#### Fix 3: Remove Hardcoded Fallbacks (BUG-003)
```python
# src/big_mood_detector/application/services/temporal_ensemble_orchestrator.py
def predict(self, pat_sequence, statistical_features, user_id=None):
    # Step 1: Assess current state with PAT
    try:
        pat_embeddings = self.pat_encoder.encode(pat_sequence)
        pat_predictions = self.pat_predictor.predict_from_embeddings(pat_embeddings)
        current_state = CurrentMoodState(
            depression_probability=pat_predictions.depression_probability,
            on_benzodiazepine_probability=pat_predictions.benzodiazepine_probability,
            confidence=pat_predictions.confidence,
        )
    except Exception as e:
        # NO MORE FAKE DATA!
        logger.error(f"PAT assessment failed: {e}")
        raise PredictionError(
            f"Cannot generate temporal assessment: PAT model failed - {str(e)}"
        )
```

#### Fix 4: DI Container Registration (BUG-004)
```python
# src/big_mood_detector/infrastructure/di/service_registration.py
"""Service registration for dependency injection"""

def register_ml_services(container: Container) -> None:
    """Register all ML-related services"""
    
    # Register PAT services as singletons
    @container.singleton
    def pat_loader() -> ProductionPATLoader:
        return ProductionPATLoader()
    
    # Register interfaces pointing to same instance
    container.register(
        PATEncoderInterface,
        factory=lambda: container.resolve(ProductionPATLoader),
        lifetime=Lifetime.SINGLETON
    )
    
    container.register(
        PATPredictorInterface,
        factory=lambda: container.resolve(ProductionPATLoader),
        lifetime=Lifetime.SINGLETON
    )
    
    # Register XGBoost
    container.register(
        XGBoostMoodPredictor,
        factory=XGBoostMoodPredictor,
        lifetime=Lifetime.SINGLETON
    )
```

#### Fix 5: PAT Activity Window (BUG-005)
```python
# src/big_mood_detector/application/use_cases/process_health_data_use_case.py
# Get 7 days of activity for PAT, not just current day
def _get_pat_activity_window(self, activity_records, target_date):
    """Get 7 days of activity ending on target_date"""
    end_date = target_date
    start_date = target_date - timedelta(days=6)
    
    # Filter records within 7-day window
    window_records = [
        r for r in activity_records
        if start_date <= r.start_date.date() <= end_date
    ]
    
    return window_records
```

#### Fix 6: Error Visibility (BUG-006, BUG-008)
```python
# src/big_mood_detector/interfaces/cli/commands.py
def predict_command(...):
    try:
        result = pipeline.process_apple_health_file(...)
    except PredictionError as e:
        # User-visible error!
        click.echo(f"❌ ERROR: {e}", err=True)
        click.echo("\n💡 Troubleshooting tips:")
        click.echo("  - Ensure model weights are installed")
        click.echo("  - Check you have at least 7 days of data")
        click.echo("  - Try without --ensemble flag")
        sys.exit(1)
```

#### Fix 7: Separate Testing from Stubbing (BUG-007)
```python
# src/big_mood_detector/infrastructure/ml_models/pat_production_loader.py
# Change from TESTING=1 to STUB_MODELS=1
if os.getenv("STUB_MODELS", "0") == "1":  # NOT TESTING!
    # Stub imports
else:
    # Real imports
```

### PHASE 3: Refactor for Clean Code

#### Extract Methods (Uncle Bob: Small Functions)
```python
class MoodPredictionPipeline:
    def process_health_data(self, ...):
        # Before: 200 lines
        # After: Composed of small methods
        
        validated_data = self._validate_input_data(records)
        date_range = self._determine_date_range(validated_data)
        features = self._extract_features_for_range(validated_data, date_range)
        predictions = self._generate_predictions(features)
        report = self._format_clinical_report(predictions)
        
        return report
```

#### Single Responsibility Classes
```python
# Before: One giant orchestrator
# After: Separated concerns

class PATSequenceBuilder:
    """Only builds PAT sequences"""
    
class TemporalPredictor:
    """Only makes temporal predictions"""
    
class ClinicalReportGenerator:
    """Only formats reports"""
```

#### Dependency Injection Everywhere
```python
# No more hidden dependencies!
class TemporalEnsembleOrchestrator:
    def __init__(
        self,
        pat_encoder: PATEncoderInterface,
        pat_predictor: PATPredictorInterface,
        xgboost_predictor: XGBoostPredictorInterface,
        logger: LoggerInterface,
    ):
        # All dependencies injected, fully testable
```

## 📝 GitHub Issues to Create

### Issue #1: Fix PAT Method Name Bug
```markdown
**Title**: Fix AttributeError: extract_multi_day_sequence method doesn't exist

**Description**: 
PAT integration calls non-existent method causing all PAT predictions to fail.

**Acceptance Criteria**:
- [ ] Change method call to extract_minute_sequence
- [ ] Add integration test verifying PAT runs
- [ ] Verify shape is (7*1440,) for 7-day window

**Labels**: bug, critical, ensemble
```

### Issue #2: Fix Date Handling to Use Actual Data Dates
```markdown
**Title**: Predictions use current date instead of data dates

**Description**:
When no end_date specified, system uses date.today() causing predictions for future dates.

**Acceptance Criteria**:
- [ ] Calculate max date from actual data
- [ ] Never show predictions beyond data range
- [ ] Add test with old data processed today

**Labels**: bug, critical, dates
```

### Issue #3: Remove All Hardcoded Medical Values
```markdown
**Title**: Remove hardcoded fallback medical predictions

**Description**:
System returns fake values (0.5, 0.33) when predictions fail instead of raising errors.

**Acceptance Criteria**:
- [ ] Remove all hardcoded medical values
- [ ] Raise PredictionError on failures
- [ ] Show errors to users clearly

**Labels**: bug, critical, patient-safety
```

### Issue #4: Fix DI Container Registration
```markdown
**Title**: Register PAT services in DI container

**Description**:
PAT interfaces not registered causing silent resolution failures.

**Acceptance Criteria**:
- [ ] Create service_registration.py module
- [ ] Register all PAT interfaces
- [ ] Add tests for DI resolution

**Labels**: bug, architecture, di
```

### Issue #5: Fix PAT Activity Window Collection
```markdown
**Title**: PAT needs 7 days of activity, not 1 day

**Description**:
Current implementation only passes current day's activity to PAT.

**Acceptance Criteria**:
- [ ] Collect 7-day activity window
- [ ] Verify shape matches PAT requirements
- [ ] Add test for multi-day sequences

**Labels**: bug, ensemble, pat
```

### Issue #6: Add Real Integration Test Suite
```markdown
**Title**: Create integration tests with real models (no mocks)

**Description**:
Current tests use mocks/stubs and don't catch integration bugs.

**Acceptance Criteria**:
- [ ] New test marker: @pytest.mark.real_integration
- [ ] Tests load actual model files
- [ ] Run in CI with STUB_MODELS=0

**Labels**: testing, quality, ci-cd
```

### Issue #7: Separate TESTING from Model Stubbing
```markdown
**Title**: TESTING=1 should not stub models

**Description**:
Can't run real integration tests because TESTING=1 stubs everything.

**Acceptance Criteria**:
- [ ] New env var: STUB_MODELS
- [ ] TESTING only affects test discovery
- [ ] Update all stubbing checks

**Labels**: testing, architecture
```

### Issue #8: Add User-Visible Error Messages
```markdown
**Title**: Surface errors to CLI/API users instead of logs

**Description**:
Errors only go to log files, users see success with fake data.

**Acceptance Criteria**:
- [ ] CLI shows clear error messages
- [ ] API returns proper error responses
- [ ] Include troubleshooting tips

**Labels**: ux, error-handling
```

## 🚀 Execution Plan

### Day 1: Setup & Failing Tests
```bash
# Create branch
git checkout -b bugfix/ensemble-integration-complete-fix

# Write ALL failing tests first (TDD)
touch tests/integration/test_pat_real_integration.py
touch tests/integration/test_date_handling_reality.py
touch tests/integration/test_no_fake_medical_data.py
touch tests/integration/test_di_container_registration.py
touch tests/e2e/test_clinical_report_accuracy.py

# Commit failing tests
git add tests/
git commit -m "test: add failing tests for all identified bugs (TDD)"
```

### Day 2: Fix Critical Bugs
```bash
# Fix method name (1 line)
# Fix date handling
# Remove hardcoded values
git commit -m "fix: correct PAT method name and date handling"
```

### Day 3: DI & Architecture
```bash
# Add service registration
# Fix activity window collection
# Separate TESTING from stubs
git commit -m "fix: register PAT services and fix activity window"
```

### Day 4: Error Handling & Visibility
```bash
# Add PredictionError exception
# Update CLI error display
# Remove silent catches
git commit -m "fix: add user-visible errors and remove silent failures"
```

### Day 5: Integration & Polish
```bash
# Run full test suite with real models
# Update documentation
# Performance optimization
git commit -m "test: verify ensemble works end-to-end with real data"
```

## ✅ Definition of Done

1. **ALL tests pass** including new integration tests
2. **NO hardcoded medical values** anywhere
3. **Dates match actual data** not today()
4. **PAT actually runs** and gives varied predictions
5. **Errors visible to users** not hidden in logs
6. **Clean code principles** followed throughout
7. **Documentation updated** with troubleshooting
8. **Performance acceptable** (<1s for predictions)

## 🎯 Success Metrics

After this fix:
- CDS report shows REAL predictions, not 56.3% for everything
- Dates in report match actual data dates
- PAT and XGBoost both contribute to ensemble
- Failures show clear error messages
- Integration tests catch future regressions

---

**LET'S FUCKING DO THIS. CLEAN CODE. TDD. NO COMPROMISES.**