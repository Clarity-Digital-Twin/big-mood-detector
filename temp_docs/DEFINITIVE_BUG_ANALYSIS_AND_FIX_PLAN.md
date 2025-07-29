# DEFINITIVE BUG ANALYSIS & SEQUENTIAL FIX PLAN

## 🎯 RE-EVALUATION FROM FIRST PRINCIPLES

### What We KNOW For Certain

1. **FACT**: User got identical predictions (4.4%, 0.9%, 0.1%) for ALL days
2. **FACT**: User had sleep data on 4 out of 7 days  
3. **FACT**: Logs showed `"missing_domains": ["sleep", "activity"]` for every day
4. **FACT**: PAT failed with `'ProductionPATLoader' object has no attribute 'encode'`

### The DEFINITIVE Root Causes (After Re-evaluation)

#### 🔴 ROOT CAUSE #1: Date Assignment Mismatch (CONFIRMED)

**Evidence**:
```python
# In sleep_aggregator.py:124-152
def _determine_sleep_date(self, record: SleepRecord) -> date:
    wake_time = record.end_date
    if wake_time.hour < 15:
        assigned_date = wake_time.date()  # Assigns to WAKE date
```

**vs**

```python  
# In clinical_feature_extractor.py:346
for record in sleep_records:
    if record.start_date.date() == target_date:  # Looks for START date
```

**PROOF**: Sleep from June 26 22:00 → June 27 06:00
- Aggregator assigns to June 27 (wake date)
- Extractor looks for records STARTING June 27
- NO MATCH

#### 🔴 ROOT CAUSE #2: Default Feature Factory (CONFIRMED)

**Evidence** from `aggregation_pipeline.py:978-1040`:
```python
SeoulFeatures(
    sleep_efficiency=0.9,  # Default for now
    sleep_onset_hour=21.0,  # Default for now  
    wake_time_hour=7.0,  # Default for now
```

**PROOF**: When no sleep found → creates fake features → XGBoost returns 4.4%

#### 🔴 ROOT CAUSE #3: PAT Integration Broken (CONFIRMED)

**Evidence**: `temporal_ensemble_orchestrator.py:103`
```python
pat_embeddings = self.pat_encoder.encode(pat_sequence)  # This method doesn't exist!
```

**PROOF**: PAT always fails, falls back to XGBoost-only

#### 🟡 ROOT CAUSE #4: Misleading Confidence (SECONDARY)

**Evidence** from `xgboost_models.py:294`:
```python
confidence = abs(max_risk - 0.5) * 2  # 91.3% for 4.4% risk
```

**This is a SYMPTOM not a cause** - but makes the bug worse by appearing confident

## 🏗️ THE DEFINITIVE SOURCE OF TRUTH

### Date Assignment Strategy (MUST BE CONSISTENT)

```python
class UniversalDateAssignment:
    """
    SINGLE SOURCE OF TRUTH for date assignment.
    ALL components MUST use this.
    """
    
    @staticmethod
    def assign_sleep_to_date(record: SleepRecord) -> date:
        """
        Universal rule: Sleep belongs to the date you wake up.
        
        If wake time < 15:00 (3pm): Assign to wake date
        If wake time >= 15:00: Assign to next date
        
        This matches Apple Health convention.
        """
        wake_time = record.end_date
        if wake_time.hour < 15:
            return wake_time.date()
        else:
            return (wake_time + timedelta(days=1)).date()
    
    @staticmethod
    def find_sleep_for_date(records: list[SleepRecord], target_date: date) -> list[SleepRecord]:
        """Find all sleep records assigned to target date."""
        return [
            r for r in records 
            if UniversalDateAssignment.assign_sleep_to_date(r) == target_date
        ]
```

## 📋 SEQUENTIAL FIX PLAN WITH TDD

### PHASE 1: Prove The Bug (TDD Red)

#### Test 1: Date Mismatch Bug
```python
def test_midnight_crossing_sleep_date_mismatch_bug():
    """FAILING TEST: Proves the date mismatch exists."""
    # Sleep from 22:00 to 06:00 next day
    sleep = SleepRecord(
        start_date=datetime(2025, 6, 26, 22, 0),
        end_date=datetime(2025, 6, 27, 6, 0)
    )
    
    # How aggregator assigns it
    aggregator = SleepAggregator()
    assigned = aggregator._determine_sleep_date(sleep)
    assert assigned == date(2025, 6, 27)  # PASSES
    
    # How extractor looks for it
    extractor = ClinicalFeatureExtractor()
    features = extractor._extract_sleep_onset([sleep], date(2025, 6, 27))
    assert features != 23.0  # FAILS! Returns default because no match
```

#### Test 2: Default Features Bug
```python
def test_no_defaults_when_sleep_missing():
    """FAILING TEST: System creates defaults instead of failing."""
    pipeline = AggregationPipeline()
    features = list(pipeline.aggregate_seoul_features(
        sleep_records=[],  # No data!
        start_date=date(2025, 6, 27),
        end_date=date(2025, 6, 27)
    ))
    
    # Should be empty
    assert len(features) == 0  # FAILS! Returns default features
```

#### Test 3: PAT Encode Method Missing
```python
def test_pat_loader_has_encode_method():
    """FAILING TEST: PAT loader missing required method."""
    loader = ProductionPATLoader()
    assert hasattr(loader, 'encode')  # FAILS!
```

### PHASE 2: Fix Date Assignment (TDD Green)

#### Fix 1: Create Universal Date Assignment
```python
# src/big_mood_detector/domain/services/date_assignment.py
class UniversalDateAssignment:
    # Implementation from above
```

#### Fix 2: Update ALL Date Lookups
```python
# src/big_mood_detector/domain/services/clinical_feature_extractor.py
def _extract_sleep_onset(self, sleep_records, target_date):
    # OLD: if record.start_date.date() == target_date:
    # NEW:
    matching = UniversalDateAssignment.find_sleep_for_date(sleep_records, target_date)
    if matching:
        return matching[0].start_date.hour + matching[0].start_date.minute / 60.0
    return None  # NOT 23.0!
```

**Files to update**:
- [ ] `domain/services/clinical_feature_extractor.py` - 3 methods
- [ ] `domain/services/dlmo_calculator.py` - 1 method
- [ ] `domain/services/activity_sequence_extractor.py` - 1 method  
- [ ] `application/services/aggregation_pipeline.py` - 2 methods

### PHASE 3: Remove ALL Defaults (TDD Green)

#### Fix 3: No More Magic Numbers
```python
# src/big_mood_detector/application/services/aggregation_pipeline.py
def aggregate_seoul_features(self, ...):
    for current_date in date_range:
        sleep_for_date = UniversalDateAssignment.find_sleep_for_date(
            sleep_records, current_date
        )
        
        if not sleep_for_date:
            logger.warning(f"No sleep data for {current_date}, skipping")
            continue  # DON'T CREATE FAKE FEATURES!
        
        # Only process real data
        yield self._calculate_from_real_data(sleep_for_date)
```

**Remove these patterns**:
- [ ] `return 23.0  # Default`
- [ ] `sleep_efficiency=0.9,  # Default for now`
- [ ] All hardcoded defaults in `SeoulFeatures`

### PHASE 4: Fix PAT Integration (TDD Green)

#### Fix 4: Add Missing Encode Method
```python
# src/big_mood_detector/infrastructure/ml_models/pat_production_loader.py
def encode(self, activity_sequence: NDArray[np.float32]) -> NDArray[np.float32]:
    """Encode activity sequence to embeddings."""
    if not self.is_loaded:
        raise RuntimeError("Model not loaded")
    
    # Normalize and prepare
    normalized = self.normalizer.transform(activity_sequence)
    
    with torch.no_grad():
        input_tensor = torch.from_numpy(normalized).float()
        input_tensor = input_tensor.unsqueeze(0).to(self.device)
        
        # Get embeddings from encoder
        embeddings = self.model.encoder(input_tensor)
        return embeddings.cpu().numpy().squeeze()
```

### PHASE 5: Integration Tests (TDD Refactor)

#### Test 4: End-to-End with Real Sleep Pattern
```python
def test_full_pipeline_realistic_sleep():
    """Integration test with midnight-crossing sleep."""
    # Realistic sleep pattern
    sleep_records = [
        SleepRecord(
            start_date=datetime(2025, 6, 26, 22, 30),
            end_date=datetime(2025, 6, 27, 6, 45)
        )
    ]
    
    pipeline = MoodPredictionPipeline()
    result = pipeline.process_health_data(
        sleep_records=sleep_records,
        target_date=date(2025, 6, 27)
    )
    
    # Must find the sleep
    assert date(2025, 6, 27) in result.daily_predictions
    
    # Must NOT be default values
    pred = result.daily_predictions[date(2025, 6, 27)]
    assert pred["depression_risk"] != 0.044
    assert pred["confidence"] != 0.913
```

### PHASE 6: Data Validation (New Feature)

#### Fix 5: Add Safety Layer
```python
# src/big_mood_detector/domain/services/clinical_data_validator.py
class ClinicalDataValidator:
    MIN_COVERAGE = 0.70
    
    def validate_for_prediction(self, ...):
        if coverage < self.MIN_COVERAGE:
            return DataValidationResult(
                can_generate_predictions=False,
                reason=f"Only {coverage:.0%} coverage, need 70%"
            )
```

## ✅ CONCRETE ACCEPTANCE CRITERIA

### For v0.5.4 Emergency Release

1. **Date Assignment Fixed**
   - [ ] Test 1 passes (midnight sleep is found)
   - [ ] All components use UniversalDateAssignment
   - [ ] No more `start_date.date() == target_date`

2. **No More Defaults**
   - [ ] Test 2 passes (empty data returns empty)
   - [ ] All hardcoded defaults removed
   - [ ] System returns None/empty instead

3. **PAT Works or Fails Loudly**  
   - [ ] Test 3 passes (encode method exists)
   - [ ] PAT errors are surfaced to user
   - [ ] Clear fallback messaging

4. **Integration Tests Pass**
   - [ ] Test 4 passes (realistic sleep works)
   - [ ] No identical predictions across days
   - [ ] Confidence reflects actual data

5. **Data Validation Active**
   - [ ] <70% coverage refuses predictions
   - [ ] Clear user messaging
   - [ ] No fake confidence scores

## 🚀 EXECUTION ORDER

1. **Write all failing tests first** (30 min)
2. **Fix date assignment** - PR #1 (1 hour)
3. **Remove defaults** - PR #2 (30 min)  
4. **Fix PAT encode** - PR #3 (30 min)
5. **Add integration tests** - PR #4 (1 hour)
6. **Add data validator** - PR #5 (1 hour)
7. **Update docs & release v0.5.4** (30 min)

**Total: ~5 hours of focused work**

## THIS IS THE PLAN. NO FLIP-FLOPPING. EXECUTE.