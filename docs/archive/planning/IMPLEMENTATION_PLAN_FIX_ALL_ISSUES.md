# Implementation Plan: Fix All Issues

## Priority Order (Based on User Impact)

### 🔥 Phase 1: Critical UX Fix (1-2 days) - v0.5.3

#### Issue: Date Window Selection Bug
**Impact**: Users get 0 predictions despite valid data

- [ ] **1.1 Create WindowSelectionStrategy Interface**
  ```python
  # domain/services/window_selection_strategy.py
  class WindowSelectionStrategy(ABC):
      @abstractmethod
      def find_windows(self, records: List[HealthRecord], 
                      min_days: int = 7) -> List[DateWindow]:
          """Find valid prediction windows in health data."""
  ```

- [ ] **1.2 Implement Smart Window Strategies**
  ```python
  # application/services/window_strategies.py
  class MostRecentValidWindowStrategy(WindowSelectionStrategy):
      """Finds most recent window with sufficient data"""
      
  class BestQualityWindowStrategy(WindowSelectionStrategy):
      """Finds window with highest data quality"""
      
  class AllValidWindowsStrategy(WindowSelectionStrategy):
      """Finds all windows meeting criteria"""
  ```

- [ ] **1.3 Update MoodPredictionPipeline**
  ```python
  # process_health_data_use_case.py
  def process_health_data(self, window_strategy=None):
      if not window_strategy:
          window_strategy = MostRecentValidWindowStrategy()
      
      windows = window_strategy.find_windows(records)
      if not windows:
          raise NoValidWindowsError(
              "No valid 7-day windows found. "
              "Need 7+ consecutive days of sleep data. "
              f"Found {len(sleep_days)} days across {date_range}"
          )
  ```

- [ ] **1.4 Add CLI Flag**
  ```python
  # interfaces/cli/commands.py
  @click.option('--auto-find-window', is_flag=True,
                help='Automatically find best data window')
  @click.option('--show-windows', is_flag=True,
                help='Show all valid windows before processing')
  ```

- [ ] **1.5 Add Integration Tests**
  ```python
  # tests/integration/test_window_selection.py
  def test_finds_valid_window_in_sparse_data():
      """Should find June window when July is empty"""
  
  def test_reports_no_valid_windows_clearly():
      """Should explain why no windows found"""
  ```

### ⚡ Phase 2: Complete Temporal Integration (2-3 days) - v0.5.4

#### Issue: PAT Not Wired in CLI
**Impact**: No NOW vs TOMORROW separation

- [ ] **2.1 Fix DI Container Passing**
  ```python
  # interfaces/cli/commands.py
  def predict_command(...):
      from big_mood_detector.infrastructure.di import get_container
      container = get_container()
      
      pipeline = MoodPredictionPipeline(
          config=config,
          di_container=container  # Pass container!
      )
  ```

- [ ] **2.2 Update Clinical Report Format**
  ```python
  # interfaces/cli/report_generator.py
  def generate_temporal_report(assessment: TemporalMoodAssessment):
      """
      TEMPORAL MOOD ASSESSMENT
      =======================
      
      CURRENT STATE (NOW - PAT Analysis)
      Depression Probability: 72%
      Confidence: 85%
      
      FUTURE RISK (TOMORROW - XGBoost)
      Depression Risk: 35%
      Hypomanic Risk: 15%
      
      TEMPORAL CONCORDANCE: 63%
      CLINICAL GUIDANCE: Immediate intervention recommended
      """
  ```

- [ ] **2.3 Add Temporal Tests**
  ```python
  # tests/integration/test_temporal_cli.py
  def test_cli_creates_temporal_orchestrator():
      """CLI should wire PAT through DI"""
  
  def test_clinical_report_shows_temporal():
      """Report should show NOW vs TOMORROW"""
  ```

- [ ] **2.4 Update Documentation**
  - CLAUDE.md with temporal capabilities
  - README with NOW/TOMORROW explanation
  - Clinical interpretation guide

### 🚀 Phase 3: Performance & Polish (3-4 days) - v0.5.5

#### Issue: XML Date Filter Bug (Issue #38)
**Impact**: Slow parsing, can't filter efficiently

- [ ] **3.1 Fix Date Comparison Bug**
  ```python
  # infrastructure/parsers/xml/fast_streaming_parser.py
  def _should_include_record(self, record_date):
      # Fix string/datetime comparison
      if isinstance(record_date, str):
          record_date = parse_date(record_date)
      
      return self.start_date <= record_date <= self.end_date
  ```

- [ ] **3.2 Add Date Filter Tests**
  ```python
  # tests/unit/parsers/test_xml_date_filter.py
  def test_filters_by_date_range():
      """Should only parse records in range"""
  
  def test_handles_string_dates():
      """Should parse string dates correctly"""
  ```

#### Issue: Misleading Density Warnings
**Impact**: Users think data is bad when it's fine

- [ ] **3.3 Improve Density Detection**
  ```python
  # domain/services/data_quality_analyzer.py
  class DataQualityAnalyzer:
      def analyze_windows(self, records) -> QualityReport:
          # Find all dense windows
          windows = self.find_consecutive_windows(records)
          
          return QualityReport(
              total_days=total,
              days_with_data=len(records),
              overall_density=len(records)/total,
              dense_windows=windows,
              best_window=max(windows, key=quality_score)
          )
  ```

- [ ] **3.4 Better User Feedback**
  ```python
  # When no predictions:
  print("No valid prediction windows found in default range.")
  print(f"Your data has {len(windows)} valid windows:")
  for window in windows[:5]:
      print(f"  {window.start} to {window.end} ({window.days} days)")
  print("\nTry: --date-range {start}:{end}")
  ```

### 📊 Phase 4: Monitoring & Validation (1 day)

- [ ] **4.1 Add Metrics**
  - Window selection success rate
  - PAT vs XGBoost availability
  - Parse time by file size

- [ ] **4.2 Create Debug Mode**
  ```bash
  predict export.xml --debug
  # Shows:
  # - Date ranges checked
  # - Windows found/rejected
  # - Model loading status
  # - DI container state
  ```

## Testing Strategy

### Immediate Smoke Tests
```bash
# Test default behavior finds windows
predict export.xml --auto-find-window

# Test temporal integration works
predict export.xml --date-range 2025-06-26:2025-07-02 --verbose

# Test error messages are clear
predict empty_data.xml
```

### Integration Test Suite
```python
class TestRealWorldScenarios:
    def test_sporadic_apple_watch_usage(self):
        """User wears watch 2-3 nights/week"""
    
    def test_device_transition_gaps(self):
        """User switched devices, 30 day gap"""
    
    def test_vacation_gaps(self):
        """User has 2 week gaps every few months"""
```

## Success Criteria

### User Experience
- [ ] Zero predictions → Clear explanation + valid windows shown
- [ ] Auto-find works for 90% of real data patterns
- [ ] Clinical report shows NOW vs TOMORROW
- [ ] Parse time <30s for 500MB files with date filter

### Technical
- [ ] All tests passing
- [ ] Type safety maintained
- [ ] <5% performance regression
- [ ] Backward compatible

## Rollout Plan

### v0.5.3 (Phase 1) - 2 days
- Fix date window selection
- Add --auto-find-window
- Clear error messages
- **User Impact**: Predictions work without manual dates

### v0.5.4 (Phase 2) - 3 days  
- Wire PAT in CLI
- Temporal reports
- NOW vs TOMORROW
- **User Impact**: Full temporal assessment

### v0.5.5 (Phase 3) - 4 days
- Fix XML date filtering
- Improve density detection
- Performance optimization
- **User Impact**: Faster, clearer, more accurate

## Code Review Checklist

- [ ] No hardcoded date assumptions
- [ ] DI container properly wired
- [ ] Error messages guide users
- [ ] Tests cover sparse data
- [ ] Documentation updated
- [ ] Backward compatible

## Risk Mitigation

### Risk: Breaking existing workflows
**Mitigation**: Keep default behavior, add new flags

### Risk: Performance regression
**Mitigation**: Benchmark before/after, add caching

### Risk: Unclear temporal results
**Mitigation**: Extensive clinical guidance in reports