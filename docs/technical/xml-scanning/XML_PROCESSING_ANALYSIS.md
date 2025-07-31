# XML Processing Analysis & Implementation Plan

## Executive Summary

**Should we implement the XML Probe & Planning System?** YES - This is the highest-impact feature we can add right now.

**Why?**
- Users currently wait 10+ minutes processing 500MB+ files only to discover critical data (HRV, respiratory) is missing
- We parse ALL records even when only sleep data is needed (30-40% wasted processing)
- No visibility into data availability until AFTER processing completes
- This frustrates users and wastes computational resources

## Current State Analysis

### The Problem in Practice

```bash
# Current user experience:
$ python main.py predict export.xml --report
⚠️  Very large file: 520.1 MB
Processing may take 10+ minutes...
[... user waits 10 minutes ...]
✅ Clinical report saved

[User opens report]
HRV: N/A (no data)
Respiratory Rate: N/A (no data)
# User: "Why did I wait 10 minutes for this?!"
```

### Technical Pain Points

1. **Blind Processing**: FastStreamingXMLParser processes EVERY record sequentially
2. **No Early Exit**: Can't skip sections we don't need
3. **Poor UX**: "N/A (no data)" doesn't explain WHY data is missing
4. **Inefficient**: Memory and CPU spent on unused data

## Proposed Solution: Two-Phase Processing

### Phase 1: Fast Probe (2-3 seconds)
```python
# Quick scan to count record types
manifest = XmlProbe.scan("export.xml")
```

### Phase 2: Informed Processing
```bash
Available Data:
✅ Sleep Analysis: 365 nights (2024-01-01 to 2024-12-31)
✅ Step Count: 365 days
⚠️  HRV: Not found
⚠️  Respiratory Rate: Not found

Processable Features:
✅ Sleep patterns (Seoul features)
✅ Activity patterns
⚠️  HRV variability (skipped - no data)

Continue? [Y/n]:
```

## Implementation Strategy

### Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  XmlProbe   │────▶│ PlanBuilder  │────▶│ SelectiveParser │
└─────────────┘     └──────────────┘     └─────────────────┘
      │                    │                      │
      ▼                    ▼                      ▼
  Manifest.json      Processing Plan      Optimized Parsing
  (2-3 seconds)      (what's possible)    (30-40% faster)
```

### Implementation Order & Timeline

#### Week 1: XmlProbe (Foundation)
**Priority: CRITICAL**

1. **Create `src/big_mood_detector/infrastructure/parsers/xml/xml_probe.py`**
   ```python
   class XmlProbe:
       def scan(self, file_path: str) -> DataManifest:
           # Fast streaming with minimal memory
           # Count record types without object creation
           # Track date ranges and sources
   ```

2. **Key Technical Decisions:**
   - Use lxml's iterparse with minimal overhead
   - Clear elements immediately after counting
   - Target: <5 seconds for 500MB files
   - Output standardized manifest format

3. **Deliverables:**
   - XmlProbe class with scan() method
   - DataManifest value object
   - Unit tests with small fixtures
   - CLI integration: `--scan-only` flag

#### Week 2: PlanBuilder (Intelligence)
**Priority: HIGH**

1. **Create `src/big_mood_detector/application/services/plan_builder.py`**
   ```python
   class PlanBuilder:
       def build_plan(self, manifest: DataManifest, 
                     request: ProcessingRequest) -> ProcessingPlan:
           # Apply feature requirement rules
           # Determine what's possible
           # Generate user-friendly explanations
   ```

2. **Feature Requirements Table (SSOT):**
   ```python
   FEATURE_REQUIREMENTS = {
       "sleep_percentage": {
           "required_types": ["HKCategoryTypeIdentifierSleepAnalysis"],
           "min_days": 7,
           "completeness": 0.5
       },
       "hrv_sdnn": {
           "required_types": ["HKQuantityTypeIdentifierHeartRateVariabilitySDNN"],
           "min_days": 30,
           "completeness": 0.3
       }
   }
   ```

3. **Deliverables:**
   - PlanBuilder with rule engine
   - Clear feature availability logic
   - User-friendly plan formatting
   - Unit tests with mock manifests

#### Week 3: Integration (Wiring)
**Priority: HIGH**

1. **Update existing pipeline:**
   - Add probe step before parsing
   - Show plan to user
   - Implement confirmation flow
   - Update progress indicators

2. **New CLI flags:**
   - `--explain`: Show plan without processing
   - `--auto-confirm`: Skip confirmation
   - `--manifest-cache`: Reuse previous scan

3. **Deliverables:**
   - Integrated probe→plan→parse flow
   - Updated CLI with new options
   - Integration tests
   - Documentation updates

#### Week 4: Optimization (Performance)
**Priority: MEDIUM**

1. **Selective Parsing:**
   - Skip record types not in plan
   - Early exit for date ranges
   - Reduced memory footprint

2. **Performance Targets:**
   - 30-40% speedup for partial datasets
   - <100MB memory for any file size
   - Maintain streaming characteristics

## Risk Mitigation

### Backwards Compatibility
- Keep existing pipeline as default
- New system behind `--use-probe` flag initially
- Gradual rollout with telemetry
- No breaking changes to APIs

### Testing Strategy
1. **Unit Tests**: Each component in isolation
2. **Integration Tests**: Full probe→plan→parse flow
3. **Performance Tests**: Regression checks
4. **E2E Tests**: Real Apple Health exports

### Potential Challenges
1. **XML Complexity**: Apple's format has quirks
   - Solution: Start with common record types
   - Incremental support for edge cases

2. **Performance Goals**: Achieving <5 second scans
   - Solution: Profile and optimize iteratively
   - Consider C extensions if needed

3. **User Confusion**: New workflow
   - Solution: Clear messaging and docs
   - Helpful error messages

## Success Metrics

1. **Performance**
   - Probe completes in <5 seconds for 500MB files
   - 30%+ speedup with selective parsing
   - Memory usage remains <100MB

2. **User Experience**
   - 90%+ users understand available data before processing
   - Reduced support tickets about missing data
   - Positive feedback on transparency

3. **Code Quality**
   - 90%+ test coverage on new components
   - Clean architecture adherence
   - Comprehensive documentation

## Decision: IMPLEMENT

### Why This Is The Right Choice

1. **High User Impact**: Solves the #1 user complaint
2. **Well-Scoped**: Clear boundaries, testable components
3. **Low Risk**: Backwards compatible, incremental rollout
4. **Technical Excellence**: Improves architecture and performance
5. **Community Ready**: Perfect for the contributor who isn't delivering

### Next Steps

1. Remove dhruvarayasam from Issue #64 assignment
2. Start with XmlProbe implementation
3. Use TDD - write tests first
4. Open draft PR early for feedback
5. Iterate based on real Apple Health data

This feature will transform the user experience from frustrating black-box processing to transparent, efficient, and predictable data analysis. Let's build it!