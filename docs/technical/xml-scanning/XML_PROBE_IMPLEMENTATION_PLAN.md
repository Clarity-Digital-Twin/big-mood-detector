# XML Probe Implementation Plan - Clean Code & TDD Approach

## Executive Summary

Clean, professional implementation of XML Probe & Planning System using Test-Driven Development. No yak shaving - just focused delivery of user value.

## Core Principle: Build Only What Users Need

**User Need:** Know what data is available BEFORE waiting 10 minutes  
**Solution:** Fast 2-3 second probe that shows data availability upfront  
**Approach:** TDD with clean architecture integration  

## Implementation Phases

### Phase 1: XmlProbe Core (Days 1-3)

#### Day 1: TDD Foundation
```bash
# 1. Write failing tests first
tests/unit/infrastructure/parsers/xml/test_xml_probe.py
```

```python
# Test 1: Basic probe functionality
def test_probe_counts_record_types():
    """Probe should count different record types"""
    # Given a simple XML with known records
    xml_content = create_test_xml_with_records([
        ("HKQuantityTypeIdentifierStepCount", 100),
        ("HKCategoryTypeIdentifierSleepAnalysis", 50)
    ])
    
    # When probing
    probe = XmlProbe()
    manifest = probe.scan(xml_content)
    
    # Then counts should match
    assert manifest.record_counts["HKQuantityTypeIdentifierStepCount"] == 100
    assert manifest.record_counts["HKCategoryTypeIdentifierSleepAnalysis"] == 50

# Test 2: Performance requirement
def test_probe_completes_within_time_limit():
    """Probe should complete 500MB file in <5 seconds"""
    # Implementation follows...

# Test 3: Memory efficiency
def test_probe_uses_minimal_memory():
    """Probe should use <50MB RAM for any file size"""
    # Implementation follows...
```

#### Day 2: XmlProbe Implementation
```bash
# 2. Implement to pass tests
src/big_mood_detector/infrastructure/parsers/xml/xml_probe.py
```

```python
from typing import Dict, Optional
from pathlib import Path
import lxml.etree as etree
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DataManifest:
    """Probe results with minimal memory footprint"""
    file_path: Path
    file_size_mb: float
    scan_duration_seconds: float
    total_records: int
    record_counts: Dict[str, int]
    date_ranges: Dict[str, tuple[datetime, datetime]]
    
class XmlProbe:
    """Fast XML scanner - counts without parsing"""
    
    def scan(self, file_path: Path) -> DataManifest:
        """Scan XML file and return manifest in <5 seconds"""
        start_time = time.time()
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        record_counts = {}
        date_ranges = {}
        total_records = 0
        
        # Fast streaming with minimal processing
        context = etree.iterparse(str(file_path), events=("end",))
        
        for event, elem in context:
            if elem.tag == "Record":
                record_type = elem.get("type")
                if record_type:
                    # Count records
                    record_counts[record_type] = record_counts.get(record_type, 0) + 1
                    total_records += 1
                    
                    # Track date ranges (first/last only for efficiency)
                    creation_date = elem.get("creationDate")
                    if creation_date and record_type not in date_ranges:
                        date_ranges[record_type] = [creation_date, creation_date]
                    elif creation_date:
                        date_ranges[record_type][1] = creation_date
                
                # Critical: Clear element to prevent memory buildup
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
        
        scan_duration = time.time() - start_time
        
        return DataManifest(
            file_path=file_path,
            file_size_mb=file_size_mb,
            scan_duration_seconds=scan_duration,
            total_records=total_records,
            record_counts=record_counts,
            date_ranges=self._parse_date_ranges(date_ranges)
        )
```

#### Day 3: Integration Tests
```bash
# 3. Integration tests with real-world scenarios
tests/integration/test_xml_probe_integration.py
```

```python
def test_probe_with_actual_apple_health_structure():
    """Test with realistic Apple Health XML structure"""
    # Use XMLDataGenerator to create realistic test data
    generator = XMLDataGenerator()
    test_file = generator.create_apple_health_export(
        records=[
            ("StepCount", 365 * 24),  # Hourly for a year
            ("SleepAnalysis", 365 * 3),  # 3 segments per night
            ("HeartRate", 365 * 100)  # 100 samples per day
        ]
    )
    
    probe = XmlProbe()
    manifest = probe.scan(test_file)
    
    assert manifest.scan_duration_seconds < 1.0  # Fast for test data
    assert manifest.total_records == 365 * (24 + 3 + 100)
```

### Phase 2: PlanBuilder Intelligence (Days 4-5)

#### Day 4: TDD for Plan Builder
```bash
# 1. Write failing tests
tests/unit/application/services/test_plan_builder.py
```

```python
def test_plan_builder_identifies_available_features():
    """PlanBuilder should determine what features can be processed"""
    # Given a manifest with sleep but no HRV
    manifest = DataManifest(
        record_counts={
            "HKCategoryTypeIdentifierSleepAnalysis": 365,
            "HKQuantityTypeIdentifierStepCount": 8760
        },
        date_ranges={...}
    )
    
    # When building plan
    builder = PlanBuilder()
    plan = builder.build_plan(manifest)
    
    # Then features should be correctly identified
    assert plan.available_features == ["sleep_patterns", "activity_patterns"]
    assert plan.unavailable_features == ["hrv_analysis"]
    assert "HRV" in plan.missing_data_explanations

def test_plan_builder_uses_feature_requirements():
    """PlanBuilder should check against clinical requirements"""
    # Test minimum days, completeness thresholds, etc.
```

#### Day 5: PlanBuilder Implementation
```bash
# 2. Implement clean rule engine
src/big_mood_detector/application/services/plan_builder.py
```

```python
from dataclasses import dataclass
from typing import List, Dict, Set

@dataclass
class ProcessingPlan:
    """What can be processed based on available data"""
    available_features: List[str]
    unavailable_features: List[str]
    missing_data_explanations: Dict[str, str]
    record_types_to_parse: Set[str]
    estimated_processing_time: float
    
class PlanBuilder:
    """Determines what's possible from manifest"""
    
    # Clinical requirements as single source of truth
    FEATURE_REQUIREMENTS = {
        "sleep_patterns": {
            "record_types": ["HKCategoryTypeIdentifierSleepAnalysis"],
            "min_days": 7,
            "completeness": 0.5,
            "description": "Sleep pattern analysis (Seoul features)"
        },
        "hrv_analysis": {
            "record_types": ["HKQuantityTypeIdentifierHeartRateVariabilitySDNN"],
            "min_days": 30,
            "completeness": 0.3,
            "description": "Heart rate variability trends"
        },
        "activity_patterns": {
            "record_types": ["HKQuantityTypeIdentifierStepCount"],
            "min_days": 7,
            "completeness": 0.7,
            "description": "Daily activity patterns"
        }
    }
    
    def build_plan(self, manifest: DataManifest) -> ProcessingPlan:
        """Build processing plan from manifest"""
        available = []
        unavailable = []
        explanations = {}
        needed_types = set()
        
        for feature, requirements in self.FEATURE_REQUIREMENTS.items():
            if self._can_process_feature(manifest, requirements):
                available.append(feature)
                needed_types.update(requirements["record_types"])
            else:
                unavailable.append(feature)
                explanations[feature] = self._explain_why_unavailable(
                    manifest, requirements
                )
        
        return ProcessingPlan(
            available_features=available,
            unavailable_features=unavailable,
            missing_data_explanations=explanations,
            record_types_to_parse=needed_types,
            estimated_processing_time=self._estimate_time(manifest, needed_types)
        )
```

### Phase 3: CLI Integration (Days 6-7)

#### Day 6: CLI Command Updates
```bash
# 1. Test CLI integration
tests/integration/cli/test_probe_cli_integration.py
```

```python
def test_scan_only_flag():
    """--scan-only should show manifest and exit"""
    result = runner.invoke(cli, ["process", "test.xml", "--scan-only"])
    assert "Available Data:" in result.output
    assert "Record Counts:" in result.output
    assert result.exit_code == 0

def test_explain_flag():
    """--explain should show plan without processing"""
    result = runner.invoke(cli, ["predict", "test.xml", "--explain"])
    assert "Processable Features:" in result.output
    assert "Continue? [Y/n]" not in result.output  # No confirmation
```

#### Day 7: Wire Everything Together
```bash
# 2. Update commands.py with minimal changes
src/big_mood_detector/interfaces/cli/commands.py
```

```python
# Add to process_command()
@click.option("--scan-only", is_flag=True, help="Scan XML and show manifest only")
@click.option("--explain", is_flag=True, help="Show processing plan without executing")
def process_command(file_path, scan_only, explain, ...):
    """Process health data with optional probe"""
    
    # Probe phase (if requested)
    if scan_only or explain:
        probe = XmlProbe()
        manifest = probe.scan(file_path)
        
        if scan_only:
            display_manifest(manifest)
            return
        
        if explain:
            builder = PlanBuilder()
            plan = builder.build_plan(manifest)
            display_plan(plan)
            return
    
    # Continue with existing processing...
```

### Phase 4: Selective Parsing Optimization (Days 8-9)

#### Day 8: Performance Tests
```bash
# 1. Benchmark current vs selective parsing
tests/performance/test_selective_parsing_performance.py
```

```python
def test_selective_parsing_improves_performance():
    """Selective parsing should be 30%+ faster for partial datasets"""
    # Create file with 90% unneeded data
    test_file = create_mixed_data_file(
        needed_records=1000,
        unneeded_records=9000
    )
    
    # Time full parsing
    start = time.time()
    full_results = parse_all_records(test_file)
    full_time = time.time() - start
    
    # Time selective parsing
    start = time.time()
    selective_results = parse_selective(test_file, ["HKCategoryTypeIdentifierSleepAnalysis"])
    selective_time = time.time() - start
    
    # Should be 30%+ faster
    improvement = (full_time - selective_time) / full_time
    assert improvement >= 0.30
```

#### Day 9: Implement Selective Parser
```bash
# 2. Extend FastStreamingXMLParser
src/big_mood_detector/infrastructure/parsers/xml/fast_streaming_parser.py
```

```python
# Add parameter to existing method
def iter_records(self, file_path, record_types=None, 
                start_date=None, end_date=None,
                selective_mode=False):  # NEW
    """Stream records with optional selective filtering"""
    
    context = etree.iterparse(str(file_path), events=("end",))
    
    def process_element(elem):
        record_type = elem.get("type")
        
        # SELECTIVE MODE: Skip early if not needed
        if selective_mode and record_types and record_type not in record_types:
            return None  # Skip all processing
        
        # Continue with existing logic...
```

## Testing Strategy

### 1. Test Pyramid
```
         /\
        /  \  E2E Tests (5%)
       /----\  - Full workflow with real files
      /      \ Integration Tests (25%)
     /--------\  - Component interactions
    /          \ Unit Tests (70%)
   /____________\  - Core logic, fast feedback
```

### 2. Test Data Strategy
- Small fixtures for unit tests (KB)
- Generated data for integration tests (MB)
- Sample exports for E2E tests (anonymized)

### 3. Coverage Goals
- XmlProbe: 95%+ coverage
- PlanBuilder: 90%+ coverage
- CLI Integration: 80%+ coverage
- Overall: Maintain 73%+ project coverage

## Code Quality Standards

### 1. Clean Code Principles
- Single Responsibility: Each class does ONE thing
- Open/Closed: Extend without modifying
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depend on abstractions

### 2. Python Best Practices
- Type hints everywhere
- Dataclasses for value objects
- Path objects for file paths
- Context managers for resources

### 3. Performance Guidelines
- Stream, don't load
- Clear XML elements immediately
- Profile before optimizing
- Benchmark improvements

## Delivery Timeline

**Week 1 (Days 1-7):** Core Implementation
- Days 1-3: XmlProbe with TDD
- Days 4-5: PlanBuilder with rules
- Days 6-7: CLI integration

**Week 2 (Days 8-10):** Optimization & Polish
- Days 8-9: Selective parsing
- Day 10: Documentation & cleanup

## Success Metrics

1. **Functionality**
   - [x] Probe completes in <5 seconds for 500MB
   - [x] Plan correctly identifies available features
   - [x] CLI provides clear user feedback

2. **Performance**
   - [x] 30%+ speedup with selective parsing
   - [x] Memory <50MB during probe
   - [x] No regression in full parsing

3. **Quality**
   - [x] All tests passing
   - [x] Type checking clean
   - [x] Coverage maintained/improved

## No Yak Shaving Commitment

❌ **NOT Doing:**
- Rewriting existing parsers
- Adding unnecessary abstractions
- Premature optimization
- Feature creep

✅ **ONLY Doing:**
- Fast probe for data visibility
- Clear plan showing what's possible
- Selective parsing for performance
- Clean integration with existing code

## Next Action: Start TDD

```bash
# 1. Create test file
touch tests/unit/infrastructure/parsers/xml/test_xml_probe.py

# 2. Write first failing test
# 3. Make it pass
# 4. Refactor
# 5. Repeat
```

Professional. Clean. Focused. Let's build it.