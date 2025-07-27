# GitHub Issue: Implement XML Probe & Planning System for Transparent Data Processing

## Summary
Currently, users processing large Apple Health XML exports (often 500MB+) have no visibility into what data is available until AFTER the entire file is processed. This leads to frustration when expected features (like HRV) are missing after waiting 10+ minutes.

## Problem Description

### Current User Experience
```bash
$ python main.py predict export.xml --report
⚠️  Very large file: 520.1 MB
Processing may take 10+ minutes...
[... user waits 10 minutes ...]
✅ Clinical report saved

[User opens report]
HRV: N/A (no data)
Respiratory Rate: N/A (no data)
```

### Issues
1. **No upfront visibility** - Users don't know what data types are in their export
2. **Wasted processing** - We parse ALL records even if only sleep data is needed  
3. **Poor error messages** - "N/A (no data)" doesn't explain WHY
4. **No optimization path** - Can't skip sections we don't need

## Proposed Solution

Implement a two-phase processing system:

### Phase 1: Fast Probe
```python
manifest = XmlProbe.scan("export.xml")  # 2-3 seconds for 500MB
```

### Phase 2: Show Plan & Process
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

## Technical Approach

### 1. XmlProbe Class
- Fast streaming scan using lxml
- Counts record types without building objects
- Generates manifest JSON with metadata
- ~100x faster than full parse

### 2. PlanBuilder Class  
- Takes manifest + user request
- Determines what features are possible
- Single source of truth for requirements
- Returns actionable plan

### 3. Selective Parser
- Uses plan to skip irrelevant records
- 30-40% performance improvement
- Same memory-efficient streaming

## Implementation Tasks

### Week 1: XML Probe
- [ ] Create `src/big_mood_detector/infrastructure/parsers/xml/xml_probe.py`
- [ ] Implement fast scanning with record counting
- [ ] Generate manifest JSON format
- [ ] Unit tests with small fixtures
- [ ] CLI flag `--scan-only` for testing

### Week 2: Plan Builder
- [ ] Create `src/big_mood_detector/application/services/plan_builder.py`
- [ ] Define feature requirements table
- [ ] Implement availability checking logic
- [ ] Format user-friendly output
- [ ] Unit tests with mock manifests

### Week 3: Integration
- [ ] Add `--explain` flag to show plan without processing
- [ ] Wire probe → planner → parser flow
- [ ] Update progress indicators
- [ ] Integration tests
- [ ] Update CLI help text

### Week 4: Polish
- [ ] Optimize selective parsing
- [ ] Add manifest caching
- [ ] Performance benchmarks
- [ ] Documentation updates
- [ ] Example notebooks

## Success Criteria

1. **Performance**: Probe completes in <5 seconds for 500MB files
2. **Accuracy**: Plan correctly predicts what features will be available
3. **UX**: Users understand what will happen BEFORE processing
4. **Efficiency**: 30%+ speedup when using selective parsing
5. **Testing**: 90%+ coverage on new components

## Technical Details

See [XML_PROCESSING_ANALYSIS.md](./XML_PROCESSING_ANALYSIS.md) for:
- Current implementation analysis
- Detailed architecture diagrams  
- Example manifest format
- Migration strategy

## Why This Matters

- **User Trust**: No more surprises after long waits
- **Performance**: Skip data we don't need
- **Extensibility**: Easy to add new features
- **Developer Experience**: Clear SSOT for requirements

## How to Contribute

1. Comment on this issue to claim it
2. Read the analysis document
3. Start with XmlProbe (smallest scope)
4. Open draft PR early for feedback
5. We'll provide Apple Health test fixtures

## Questions for Discussion

1. Should manifest be cached between runs?
2. What other metadata would be useful in the manifest?
3. Should we support partial exports (e.g., only sleep data)?
4. How to handle incremental updates?

---

Labels: `enhancement`, `good first issue`, `performance`, `help wanted`
Milestone: v0.6.0
Assignee: [Unassigned]