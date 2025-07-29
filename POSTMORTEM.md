# Postmortem: Date Assignment Bug (Issue #73)

## Summary
From v0.1.0 to v0.5.3, Big Mood Detector could not process sleep data correctly,
resulting in all users receiving identical fake predictions.

## Timeline
- **2024-07-XX**: Bug introduced in initial implementation
- **2025-01-29 14:00**: User reports identical predictions across all days
- **2025-01-29 15:00**: Initially diagnosed as "sparse data" issue  
- **2025-01-29 16:00**: Root cause found - date assignment mismatch
- **2025-01-29 17:00**: Emergency patch v0.5.4 released

## Root Cause
Inconsistent date assignment between components:
1. SleepAggregator assigns sleep to the wake date (correct per Apple Health)
2. Feature extractors search by sleep start date (incorrect)
3. Midnight-crossing sleep never matched
4. Default features (21:00 sleep, 7:00 wake) generated identical 4.4% predictions

## Impact
- **Severity**: Critical - All predictions invalid
- **Scope**: 100% of users affected
- **Duration**: ~6 months (all versions before v0.5.4)
- **User Impact**: False reassurance with fake low-risk predictions

## Detection
The bug was discovered when a user noticed:
- Identical predictions (4.4%, 0.9%, 0.1%) for every single day
- 91.3% confidence despite having sparse data (4/7 days)
- Logs showing "missing_domains": ["sleep"] for days that had sleep

## Root Cause Analysis

### The Code Bug
```python
# SleepAggregator.py (CORRECT)
def _determine_sleep_date(self, record: SleepRecord) -> date:
    wake_time = record.end_date
    if wake_time.hour <= 15:
        return wake_time.date()  # Assigns to WAKE date

# ClinicalFeatureExtractor.py (WRONG)
def _extract_sleep_onset_hour(self, sleep_records, target_date):
    for record in sleep_records:
        if record.start_date.date() == target_date:  # Looks for START date
            return record.start_date.hour
    return 23.0  # Default when not found
```

### Why It Went Undetected
1. **Default values masked the bug** - System returned plausible values
2. **High confidence scores** - 91.3% confidence made it seem reliable
3. **Integration tests used non-midnight-crossing sleep** - Unrealistic test data
4. **No monitoring for identical predictions** - Lack of anomaly detection

## Lessons Learned
1. **Integration tests must use realistic data** - 99% of sleep crosses midnight
2. **Default values are dangerous** - Better to fail than fake
3. **Date/time logic must be centralized** - Distributed logic = bugs
4. **"It works" != "It works correctly"** - Need result validation
5. **Confidence scores need validation** - High confidence with missing data is a red flag

## Action Items
### Completed
- [x] Create UniversalDateAssignment as single source of truth
- [x] Fix all date lookups in feature extractors
- [x] Remove all default feature values
- [x] Add comprehensive integration tests with realistic sleep
- [x] Implement DataQualityValidator
- [x] Add tests that prove the bug existed

### Future Work
- [ ] Add monitoring for identical predictions across days
- [ ] Implement anomaly detection for suspicious patterns
- [ ] Add telemetry for data coverage vs confidence
- [ ] Create automated test data generator with realistic patterns
- [ ] Audit all other date/time comparisons in codebase

## Technical Details

### The Fix
Created `domain/services/date_assignment.py`:
```python
class UniversalDateAssignment:
    @staticmethod
    def assign_sleep_to_date(record: SleepRecord) -> date:
        """Sleep belongs to the date you wake up."""
        wake_time = record.end_date
        if wake_time.hour < 15:
            return wake_time.date()
        else:
            return (wake_time + timedelta(days=1)).date()
    
    @staticmethod
    def find_sleep_for_date(records: list[SleepRecord], target_date: date):
        """Find all sleep records assigned to target date."""
        return [r for r in records 
                if UniversalDateAssignment.assign_sleep_to_date(r) == target_date]
```

### Verification
The fix was verified with:
1. Unit tests proving the bug existed
2. Integration tests with realistic midnight-crossing sleep
3. End-to-end pipeline test showing varied predictions
4. Real user data showing different predictions per day

## Communication
- GitHub release with detailed notes
- README updated with critical warning banner
- CHANGELOG documenting emergency fix
- This postmortem for transparency

## Conclusion
This bug highlights the importance of:
- Testing with realistic data patterns
- Avoiding defaults that mask failures
- Centralizing complex business logic
- Monitoring for suspicious patterns

The swift fix and comprehensive testing give us confidence that v0.5.4 provides accurate predictions. We apologize to all users who relied on incorrect predictions from earlier versions.