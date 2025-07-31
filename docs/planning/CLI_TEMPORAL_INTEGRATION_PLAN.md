# CLI Temporal Integration Plan - Clean TDD Approach

## Discovery: The Temporal Endpoint EXISTS but is Invisible

After deep research, the `/predict/temporal` API endpoint is fully implemented but:
- ❌ No CLI access (users can't use it)
- ❌ No documentation (nobody knows it exists)
- ❌ Not in clinical reports (output doesn't show temporal separation)

## TDD Implementation Plan (Robert C. Martin Style)

### Phase 1: Write Failing Tests (Red)

```python
# tests/unit/cli/test_temporal_cli.py
def test_predict_with_temporal_flag_shows_now_and_tomorrow():
    """When user adds --temporal flag, they see NOW vs TOMORROW."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "predict", 
        "test_data.xml",
        "--temporal",
        "--report"
    ])
    
    assert result.exit_code == 0
    assert "NOW (PAT):" in result.output
    assert "TOMORROW (XGBoost):" in result.output
    assert "Temporal Concordance:" in result.output
    
def test_clinical_report_shows_temporal_separation():
    """Clinical report should clearly separate NOW vs TOMORROW."""
    # Test that report.txt contains temporal sections
```

### Phase 2: Minimal Implementation (Green)

1. **Add --temporal flag to CLI**
```python
@app.command()
def predict(
    health_file: Path,
    temporal: bool = typer.Option(False, "--temporal", help="Show NOW vs TOMORROW separation"),
    # ... other options
):
    if temporal:
        # Use TemporalEnsembleOrchestrator
        # Format output with temporal separation
```

2. **Update ClinicalReportFormatter**
```python
def _add_temporal_section(self, assessment: TemporalMoodAssessment):
    """Add NOW vs TOMORROW section to report."""
    self.sections.append(f"""
TEMPORAL ASSESSMENT
==================
NOW (Current State - PAT):     {assessment.current_state.depression_probability:.1%}
TOMORROW (Future Risk - XGB):  {assessment.future_risk.depression_risk:.1%}
Temporal Concordance:          {assessment.temporal_concordance:.1%}
Clinical Action:               {assessment.clinical_guidance}
""")
```

### Phase 3: Refactor (Clean)

1. **Extract temporal formatting to value object**
2. **Add proper error handling for missing PAT**
3. **Update documentation**

## Definition of Done

- [ ] CLI `predict --temporal` works with real data
- [ ] Clinical report shows NOW vs TOMORROW clearly
- [ ] Tests pass (unit + integration)
- [ ] Documentation updated (README, CLAUDE.md)
- [ ] No code duplication
- [ ] Type-safe (mypy clean)

## Time Estimate: 4-6 hours

1. Write tests: 1 hour
2. Implement CLI flag: 1 hour  
3. Update report formatter: 1 hour
4. Integration testing: 1 hour
5. Documentation: 1 hour
6. Buffer for issues: 1 hour

This is THE blocker for MVP - once users can access temporal predictions, the unique value proposition is complete.