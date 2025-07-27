# Current XML Processing Flow

## Overview
This document details how XML processing currently works in Big Mood Detector v0.5.0, highlighting pain points that the proposed XML Probe system would address.

## The Journey of a 520MB export.xml File

### 1. CLI Entry Point (`main.py`)
```python
@click.command()
@click.argument('input_path', type=click.Path(exists=True))
def predict(input_path):
    # User runs: python main.py predict export.xml
    validate_input_path(input_path)  # Just checks file exists
    # Shows warning if >500MB but no other info
```

**Problem**: User gets size warning but no data preview

### 2. Validation (`commands.py`)
```python
def validate_input_path(input_path: Path):
    size_mb = input_path.stat().st_size / (1024 * 1024)
    if size_mb > 500:
        click.echo(f"⚠️  Very large file: {size_mb:.1f} MB")
        click.echo("   Processing may take 10+ minutes...")
        # That's it - no scan, no preview
```

**Problem**: Could scan here but doesn't

### 3. Pipeline Creation (`process_health_data_use_case.py`)
```python
pipeline = MoodPredictionPipeline(config)
result = pipeline.process_health_data(
    input_path=input_path,
    output_dir=output_dir,
    generate_report=True
)
# Pipeline has NO IDEA what's in the file yet
```

**Problem**: Pipeline blindly processes everything

### 4. Data Parsing Service (`data_parsing_service.py`)
```python
def parse_data(self, file_path: Path, config: PipelineConfig):
    if file_path.suffix.lower() == '.xml':
        parser = FastStreamingXMLParser()
        # This is where we FINALLY start reading the file
        sleep_records = []
        activity_records = []
        
        # But we read EVERYTHING, no matter what
        for record in parser.parse_xml(file_path):
            if is_sleep(record):
                sleep_records.append(record)
            elif is_activity(record):
                activity_records.append(record)
            # Every. Single. Record.
```

**Problem**: Parses all 738,946 records even if we only need sleep

### 5. Fast Streaming Parser (`fast_streaming_parser.py`)
```python
def fast_iter(self, context, func, start_date=None, end_date=None):
    for _event, elem in context:
        if elem.tag != "Record":
            elem.clear()
            continue
            
        # Date filtering happens HERE, during parse
        # Already read and parsed the element!
        record_date = parse_date(elem.get("startDate"))
        if start_date and record_date < start_date:
            elem.clear()  # Wasted work
            continue
```

**Problem**: Date filtering AFTER parsing elements

### 6. Entity Creation
```python
# For EACH of 738,946 records:
if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
    sleep_record = SleepRecord(
        source_name=elem.get("sourceName"),
        start_date=parse_date(elem.get("startDate")),
        end_date=parse_date(elem.get("endDate")),
        state=SleepState(elem.get("value"))
    )
    # Even if we're going to filter it out later!
```

**Problem**: Creates objects we might not need

### 7. Feature Extraction
```python
# Only NOW do we know what features we can extract
daily_features = aggregation_pipeline.aggregate_features(
    sleep_records,      # Might be empty
    activity_records,   # Might be empty  
    heart_records      # Might be empty
)
# User waited 10 minutes to find out HRV is empty
```

**Problem**: Feature availability known only at the end

### 8. Report Generation
```python
# Finally tells user what was missing
report = f"""
Depression Risk: {risk}% 
HRV Analysis: N/A (no data)  # User: "Why didn't you tell me?!"
Respiratory Rate: N/A (no data)
"""
```

**Problem**: Surprises and frustration

## Data Flow Bottlenecks

```mermaid
graph LR
    A[520MB XML] --> B[Parse ALL Records]
    B --> C[Filter Dates]
    C --> D[Create Entities]
    D --> E[Filter Again]
    E --> F[Extract Features]
    F --> G[Find Out What's Missing]
    
    style B fill:#ff9999
    style C fill:#ff9999
    style D fill:#ff9999
    style G fill:#ff9999
```

## Timing Breakdown (Typical 520MB File)

| Phase | Time | Waste | With Probe |
|-------|------|-------|------------|
| Open & Validate | 0.1s | - | 0.1s |
| Parse All Records | 180s | 60s parsing unused | 2s probe + 120s targeted |
| Entity Creation | 120s | 40s for filtered | 80s only needed |
| Date Filtering | 60s | All of it | 0s (probe pre-filters) |
| Feature Extract | 60s | 20s missing features | 40s known features |
| **Total** | **420s** | **140s wasted** | **242s** |

## Memory Usage Pattern

### Current (Worst Case)
```
Start: 50MB
After parsing: 800MB (all records in memory)
After filtering: 400MB (filtered records released)
After features: 100MB (only features kept)
```

### With Probe
```
Probe: 50MB constant (streaming)
Parsing: 400MB max (only needed records)
Features: 100MB (same)
```

## Why The Probe Solves This

1. **Fast First Pass** (2-3 seconds)
   - Just counts record types
   - Finds date ranges
   - No object creation

2. **Informed Decisions**
   - User sees what's available
   - Can choose to skip  
   - Sets correct expectations

3. **Targeted Parsing**
   - Skip entire record types
   - Pre-filter by date
   - 40% less work

4. **Better UX**
   - Progress shows "Parsing sleep records (2,190 total)"
   - No surprises
   - Can cancel early

## Code Paths Affected

Files that would need updates for probe system:

1. **New Files**
   - `infrastructure/parsers/xml/xml_probe.py`
   - `application/services/plan_builder.py`
   - `domain/value_objects/data_manifest.py`
   - `domain/value_objects/processing_plan.py`

2. **Modified Files**  
   - `interfaces/cli/commands.py` - Add probe step
   - `application/services/data_parsing_service.py` - Use plan
   - `infrastructure/parsers/xml/fast_streaming_parser.py` - Selective parsing

3. **Unchanged** 
   - All domain entities
   - All feature extractors
   - All ML models
   
This separation makes it safe to implement without breaking existing functionality!