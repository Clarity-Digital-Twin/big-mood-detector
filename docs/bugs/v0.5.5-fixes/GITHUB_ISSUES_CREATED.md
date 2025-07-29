# GitHub Issues - Created in v0.5.5 Release

**UPDATE**: All issues below were created on GitHub on 2025-07-29 and resolved in the v0.5.5 release.

## Created Issues:
- Issue #79: PAT integration method name bug ✅
- Issue #80: Date handling using today() instead of data dates ✅
- Issue #81: Hardcoded medical predictions (patient safety) ✅
- Issue #82: DI container missing registrations ✅

All critical bugs have been fixed and the system is now production-ready.

---

## 🐛 Issue #1: [CRITICAL] PAT integration calls non-existent method

**Labels**: `bug`, `critical`, `ensemble`, `good first issue`

**Description**:
The PAT integration is completely broken due to calling a method that doesn't exist. This causes all PAT predictions to fail silently and return hardcoded values.

**Current Behavior**:
- Code calls `extract_multi_day_sequence()` 
- Method doesn't exist (actual method is `extract_minute_sequence()`)
- Exception caught silently, returns fake data

**Expected Behavior**:
- PAT should process 7 days of activity data
- Return real predictions, not hardcoded 0.5

**Location**:
`src/big_mood_detector/application/use_cases/process_health_data_use_case.py:478`

**Acceptance Criteria**:
- [ ] Change `extract_multi_day_sequence` to `extract_minute_sequence`
- [ ] Verify PAT actually runs (no AttributeError)
- [ ] Add test that PAT returns shape (7*1440,) array
- [ ] Ensure predictions vary (not all 56.3%)

---

## 🐛 Issue #2: [CRITICAL] Reports show wrong dates - uses today() instead of data dates

**Labels**: `bug`, `critical`, `data-integrity`

**Description**:
When processing historical data, the system uses `date.today()` as the target date, causing reports to show future dates that don't exist in the data.

**Current Behavior**:
- Process 2024 data in 2025
- Report shows predictions for "2025-07-29"
- Dates don't match actual data

**Expected Behavior**:
- Use the latest date found in actual data
- Never show predictions beyond data range

**Location**:
`src/big_mood_detector/application/use_cases/process_health_data_use_case.py:364`

**Acceptance Criteria**:
- [ ] Calculate `actual_end_date` from data
- [ ] Use `end_date or actual_end_date` (not `date.today()`)
- [ ] Add test: old data shows old dates
- [ ] Report header shows correct date range

**Test Case**:
```python
def test_historical_data_uses_historical_dates():
    # Load 2024 data
    result = pipeline.process("2024_export.xml")
    # Should NOT have 2025 dates
    assert all(d.year == 2024 for d in result.daily_predictions.keys())
```

---

## 🐛 Issue #3: [PATIENT SAFETY] Remove hardcoded medical predictions

**Labels**: `bug`, `critical`, `patient-safety`, `security`

**Description**:
System returns fake medical values when predictions fail. This is a patient safety issue as users receive fabricated health data.

**Hardcoded Values Found**:
- Depression: 0.5 (shows as 56.3%)
- Hypomania: 0.33 (33%)
- Mania: 0.34 (34%)

**Location**:
`src/big_mood_detector/application/services/temporal_ensemble_orchestrator.py:94-100`

**Acceptance Criteria**:
- [ ] Remove ALL hardcoded medical values
- [ ] Raise `PredictionError` on failures
- [ ] Show clear error to users
- [ ] Add test that failures don't return fake data

**Required Changes**:
```python
# DELETE THIS:
except Exception as e:
    current_state = CurrentMoodState(
        depression_probability=0.5,  # FAKE!
        ...
    )

# REPLACE WITH:
except Exception as e:
    raise PredictionError(f"PAT model failed: {e}")
```

---

## 🐛 Issue #4: DI container missing PAT service registrations

**Labels**: `bug`, `architecture`, `dependency-injection`

**Description**:
PAT services are never registered in the DI container, causing resolution to fail silently.

**Current Behavior**:
- `container.resolve(PATPredictorInterface)` fails
- Exception caught, continues without PAT
- Ensemble runs as XGBoost-only

**Required Implementation**:
Create `infrastructure/di/service_registration.py`:
```python
def register_ml_services(container: Container):
    # Register PAT loader
    container.register_singleton(
        ProductionPATLoader,
        lambda: ProductionPATLoader()
    )
    
    # Register interfaces
    container.register(
        PATPredictorInterface,
        lambda: container.resolve(ProductionPATLoader)
    )
```

**Acceptance Criteria**:
- [ ] Create service registration module
- [ ] Register all PAT interfaces
- [ ] DI resolution succeeds
- [ ] Add test for container.resolve()

---

## 🐛 Issue #5: PAT receives 1 day of activity instead of required 7 days

**Labels**: `bug`, `ml-models`, `data-processing`

**Description**:
PAT model expects 7 days of activity data but current implementation only provides current day.

**Current Code**:
```python
# Only gets current day!
date_activity_records = [
    r for r in activity_records
    if r.start_date.date() <= feature_date <= r.end_date.date()
]
```

**Required**:
```python
# Get 7-day window
end_date = feature_date
start_date = feature_date - timedelta(days=6)
window_records = [r for r in activity_records 
                  if start_date <= r.start_date.date() <= end_date]
```

**Acceptance Criteria**:
- [ ] Collect 7 days of activity for PAT
- [ ] Verify shape is (7, 1440) after reshape
- [ ] Add test for multi-day window
- [ ] PAT predictions should vary by day

---

## 🧪 Issue #6: Create real integration test suite (no mocks)

**Labels**: `testing`, `quality`, `technical-debt`

**Description**:
Current tests use mocks/stubs and don't catch integration bugs. We need tests with real models.

**Requirements**:
- New pytest marker: `@pytest.mark.real_integration`
- Environment variable: `STUB_MODELS=0`
- Load actual model weights
- Test actual predictions

**Test Structure**:
```python
@pytest.mark.real_integration
@pytest.mark.skipif(not Path("model_weights").exists(), 
                    reason="Model weights not available")
class TestRealIntegration:
    def test_ensemble_with_real_models(self):
        # NO MOCKS!
        result = pipeline.process(real_data)
        assert "pat" in result.models_used
        assert "xgboost" in result.models_used
```

**Acceptance Criteria**:
- [ ] Create real_integration test directory
- [ ] Tests use actual model files
- [ ] Add to CI with separate job
- [ ] Document how to run locally

---

## 🏗️ Issue #7: Separate TESTING flag from model stubbing

**Labels**: `architecture`, `testing`, `refactor`

**Description**:
`TESTING=1` stubs all models, making real integration tests impossible.

**Current Problem**:
```python
if os.getenv("TESTING", "0") == "1":
    # Everything stubbed!
```

**Solution**:
```python
if os.getenv("STUB_MODELS", "0") == "1":
    # Stubs only when explicitly requested
```

**Acceptance Criteria**:
- [ ] New env var: `STUB_MODELS`
- [ ] Update all stubbing checks
- [ ] TESTING only affects pytest
- [ ] Document in README

---

## 💬 Issue #8: Add user-visible error messages

**Labels**: `ux`, `error-handling`, `cli`

**Description**:
Errors only go to log files. Users see success messages with fake data.

**Current**:
```python
logger.warning("PAT failed")  # User never sees
return fake_data              # User gets lies
```

**Required**:
```python
click.echo("❌ ERROR: PAT model failed", err=True)
click.echo("💡 Try: Check model weights are installed")
sys.exit(1)
```

**Acceptance Criteria**:
- [ ] CLI shows errors with click.echo
- [ ] API returns proper error codes
- [ ] Include troubleshooting tips
- [ ] Test error visibility

---

## 📋 Quick Copy Templates

### For Issue Creation:
1. Copy title and description
2. Add appropriate labels
3. Assign to sprint/milestone
4. Link related issues

### Priority Order:
1. **#1** - PAT method name (1-line fix)
2. **#2** - Date handling (prevents confusion)
3. **#3** - Remove fake data (patient safety)
4. **#4** - DI registration (enables ensemble)
5. **#5** - PAT window (correct data)
6. **#7** - Separate flags (enables testing)
7. **#6** - Integration tests (prevents regression)
8. **#8** - Error visibility (UX improvement)

### Grouping for PRs:
- **PR 1**: Issues #1, #2, #3 (Critical fixes)
- **PR 2**: Issues #4, #5 (PAT functionality)
- **PR 3**: Issues #6, #7 (Testing improvements)
- **PR 4**: Issue #8 (UX enhancement)