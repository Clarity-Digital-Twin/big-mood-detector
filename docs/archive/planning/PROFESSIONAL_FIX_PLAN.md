# PROFESSIONAL FIX PLAN - IMPLEMENTING DUAL PIPELINE ARCHITECTURE

## 🎯 OBJECTIVE
Replace the deprecated `EnsembleOrchestrator` with `TemporalEnsembleOrchestrator` to achieve proper temporal separation:
- **PAT**: Current state (NOW) - "Are you depressed right now?"
- **XGBoost**: Future risk (TOMORROW) - "Will you have an episode tomorrow?"

## ✅ VERIFICATION CHECKLIST

### Current State Verification
- [x] XGBoost models: Working, predicting tomorrow
- [x] PAT models: Trained (0.5929 AUC), can predict
- [x] TemporalEnsembleOrchestrator: Implemented, tested
- [x] EnsembleOrchestrator: Deprecated, doesn't ensemble
- [x] Roadmap alignment: Confirms "Wire PAT predictions" is pending

## 🛠️ IMPLEMENTATION PLAN

### Phase 1: Update Core Orchestrator (2-3 hours)

#### 1.1 Update API Dependencies
**File**: `src/big_mood_detector/interfaces/api/dependencies.py`
```python
# Line 97: Replace
orchestrator = EnsembleOrchestrator(...)
# With:
from big_mood_detector.application.services.temporal_ensemble_orchestrator import TemporalEnsembleOrchestrator

orchestrator = TemporalEnsembleOrchestrator(
    pat_predictor=pat_predictor,
    xgboost_predictor=xgboost_predictor,
    pat_encoder=pat_encoder  # Need to add this
)
```

#### 1.2 Update CLI Pipeline
**File**: `src/big_mood_detector/application/use_cases/process_health_data_use_case.py`
```python
# Line 220: Replace EnsembleOrchestrator with TemporalEnsembleOrchestrator
```

#### 1.3 Update Return Types
- Change `EnsemblePrediction` → `TemporalMoodAssessment`
- Update all consumers to handle new structure

### Phase 2: Create Temporal API Endpoint (2 hours)

#### 2.1 Add New Route
**File**: `src/big_mood_detector/interfaces/api/routes/predictions.py`
```python
@router.post("/predict/temporal", response_model=TemporalPredictionResponse)
async def predict_temporal(
    features: FeatureInput,
    activity_data: ActivitySequenceInput,  # 7-day sequence
    orchestrator: TemporalEnsembleOrchestrator = Depends(get_temporal_orchestrator)
) -> TemporalPredictionResponse:
    """
    Temporal mood assessment with NOW vs TOMORROW separation.
    
    Returns:
    - current_state: PAT assessment of current depression (NOW)
    - future_risk: XGBoost prediction for tomorrow
    - temporal_concordance: Agreement between models
    - clinical_alerts: If rapid cycling detected
    """
```

#### 2.2 Response Model
```python
class TemporalPredictionResponse(BaseModel):
    # Current state (PAT)
    current_state: CurrentStateAssessment
    
    # Future risk (XGBoost)  
    future_risk: FutureRiskAssessment
    
    # Temporal analysis
    temporal_concordance: float
    requires_immediate_intervention: bool
    requires_preventive_action: bool
    
    # Clinical guidance
    clinical_alerts: list[str]
    monitoring_frequency: str
```

### Phase 3: Update Display & Reports (2-3 hours)

#### 3.1 CLI Output Format
```
═══════════════════════════════════════════════════════════════
                    TEMPORAL MOOD ASSESSMENT                    
═══════════════════════════════════════════════════════════════

📍 CURRENT STATE (PAT Analysis - NOW)
├─ Depression: 72% probability ⚠️
├─ Confidence: 85%
└─ Assessment: Currently experiencing depressive symptoms

🔮 FUTURE RISK (XGBoost Prediction - NEXT 24 HOURS)
├─ Depression Risk: 35% ↓
├─ Hypomanic Risk: 15%
├─ Manic Risk: 5%
└─ Trend: Improving trajectory expected

⚡ TEMPORAL ANALYSIS
├─ Concordance: LOW (37%) - Models disagree
├─ Pattern: Current depression, but improving tomorrow
└─ Alert: Monitor for rapid mood cycling

💊 CLINICAL RECOMMENDATIONS
1. Continue current treatment regimen
2. Schedule follow-up within 48 hours
3. Monitor for mood instability
```

#### 3.2 Update Clinical Report Generator
- Add temporal section
- Show both NOW and TOMORROW assessments
- Include concordance analysis

### Phase 4: Testing & Validation (2 hours)

#### 4.1 Integration Tests
```python
def test_temporal_pipeline_flow():
    """Test full flow returns temporal assessment."""
    # Process health data
    # Verify TemporalMoodAssessment returned
    # Check both current_state and future_risk populated
```

#### 4.2 API Tests
```python
def test_temporal_endpoint():
    """Test /predict/temporal endpoint."""
    # Send features + activity data
    # Verify response structure
    # Check temporal separation
```

#### 4.3 Clinical Validation
- Verify DSM-5 compliance maintained
- Check temporal logic makes clinical sense
- Validate alert thresholds

### Phase 5: Cleanup & Documentation (1-2 hours)

#### 5.1 Remove Old Code
- Delete `EnsembleOrchestrator` class
- Remove old `EnsemblePrediction` types
- Clean up deprecated imports

#### 5.2 Update Documentation
- Update API docs with temporal endpoint
- Add temporal assessment to README
- Update CLAUDE.md with new flow

#### 5.3 Migration Guide
- For API consumers switching endpoints
- For CLI users understanding new output

## 🚧 POTENTIAL ISSUES & MITIGATIONS

### Issue 1: PAT Encoder Not Available
**Problem**: TemporalEnsembleOrchestrator needs PAT encoder
**Solution**: Add to DI container or pass through pipeline

### Issue 2: Breaking API Changes
**Problem**: Existing consumers expect old format
**Solution**: Keep old endpoints, add new temporal ones

### Issue 3: Activity Data Not Always Available
**Problem**: Some paths don't have 7-day sequences
**Solution**: Graceful degradation in TemporalEnsembleOrchestrator

## 📊 SUCCESS METRICS

1. **Functional**: Both models making independent predictions
2. **Temporal**: Clear NOW vs TOMORROW separation
3. **Clinical**: Concordance analysis working
4. **Performance**: <200ms response time maintained
5. **Testing**: All tests passing, including new temporal ones

## 🚀 ROLLOUT STRATEGY

1. **Branch**: `feature/temporal-ensemble-integration`
2. **Testing**: Full test suite + manual validation
3. **Staging**: Deploy to staging for validation
4. **Production**: Gradual rollout with monitoring

## 📅 TIMELINE

- **Day 1**: Phases 1-2 (Core implementation)
- **Day 2**: Phases 3-4 (Display & testing)
- **Day 3**: Phase 5 (Cleanup & docs)
- **Total**: 2-3 days with buffer

## ✅ DONE CRITERIA

- [ ] TemporalEnsembleOrchestrator used everywhere
- [ ] CLI shows temporal separation
- [ ] API has /predict/temporal endpoint
- [ ] Tests pass with >90% coverage
- [ ] Documentation updated
- [ ] Old orchestrator removed
- [ ] Clinical report shows both assessments