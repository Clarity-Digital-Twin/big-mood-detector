# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.7] - 2025-07-30 - Production Fixes & Robustness

### Fixed
- **Timezone Handling** - Fixed TypeError with timezone-aware vs naive datetimes
  - Implemented `TimezoneContract` to ensure UTC consistency
  - All XML parsers now convert to naive datetimes
  - Resolves crashes with real Apple Health exports
- **Window-Level Predictions** - Fixed duplicate predictions in XGBoost-only mode
  - Added proper window-level aggregation
  - Single prediction per analysis window (not daily)
  - Correct handling of sparse data scenarios
- **Cross-Platform Compatibility** - Fixed Windows WSL2 timeout issues
  - Platform-aware timeout handling
  - Graceful degradation when SIGALRM unavailable
  - Dynamic timeout based on file size

### Added
- **Summary Calculator Service** - Refactored overall summary logic
  - Centralized calculation for daily and window predictions
  - Improved code organization and testability
  - Consistent confidence score handling
- **Enhanced Report Format** - Improved clinical report clarity
  - DATA WINDOW SELECTION section with coverage stats
  - WINDOW-LEVEL ANALYSIS for non-daily predictions
  - Clear model availability messaging

### Improved
- **Dynamic Timeouts** - File-size based timeout configuration
  - <50MB: 2 minutes
  - 50-200MB: 5 minutes
  - >200MB: No timeout
  - Progress messages for large files
- **Test Coverage** - Added regression tests for edge cases
  - PAT-only mode scenarios
  - Cross-platform timeout behavior
  - Window-level prediction logic

### Technical
- All mypy type errors resolved
- Ruff linting clean
- Test coverage at 73%
- Version bumped to 0.5.7

## [0.5.6] - 2025-07-29 - Intelligent Auto-Window Selection

### Added
- **Auto-Window Selection** (#83) - Automatically finds optimal data windows for both models
  - `--auto-window` flag (enabled by default) analyzes available data
  - Finds windows for PAT (7 consecutive days) and XGBoost (30+ days, sparse OK)
  - Prioritizes overlapping windows where both models can run
  - Clear feedback showing all found windows and selection reasoning
- **Sparse Window Strategy** - New window selection for non-consecutive data
  - `SparseWindowStrategy` finds windows with configurable coverage (default 50%)
  - `SparseDataWindow` value object tracks coverage statistics
  - Supports XGBoost's ability to work with gaps in data
- **Dual Model Window Analysis** - Coordinates window selection between models
  - `DualModelWindowStrategy` analyzes data for both model requirements
  - `WindowAnalysisResult` provides comprehensive window availability
  - Graceful degradation to single model when only one has valid data
- **Enhanced CDS Report** - Window selection information in clinical reports
  - Shows selected window dates and strategy
  - Indicates which models are available for analysis
  - Improves clinical decision support with data availability context

### Changed
- **WindowSelectionStrategy Interface** - Extended for sparse data support
  - Added optional `min_coverage` parameter (backward compatible)
  - All existing strategies updated to accept new parameter
  - Maintains Liskov Substitution Principle with clean inheritance

### Fixed
- **PAT Inference Smoke Test** - Fixed YAML indentation in GitHub workflow
  - Python script block properly indented for YAML compliance
  - CI/CD pipeline now runs without syntax errors

### Technical Debt
- Extended `WindowSelectionStrategy.find_windows()` to accept optional `min_coverage` parameter
  - All existing implementations ignore this parameter (backward compatible)
  - Future refactor could convert to Protocol with generics

## [0.5.5] - 2025-07-29 - CDS Report Fixes & Clean Integration

### Fixed
- **PAT Integration Method Bug** (#79) - Fixed AttributeError from non-existent method
  - Changed `extract_multi_day_sequence()` to `extract_minute_sequence()`
  - PAT predictions now actually work instead of failing silently
- **Date Handling Bug** (#80) - Reports now show actual data dates
  - Removed `date.today()` usage that showed future dates
  - Uses actual end date from data range
- **Hardcoded Medical Values** (#81) - PATIENT SAFETY FIX
  - Removed fake predictions (0.5, 0.33, 0.34) on failures
  - Now raises exceptions instead of returning fabricated data
- **DI Container Registration** (#82) - PAT services properly registered
  - Both `PATPredictorInterface` and `PATEncoderInterface` resolve correctly
  - Single shared instance for both interfaces
- **Data Completeness Calculation** - Now calculates from actual data
  - Was hardcoded to 1.0, now checks for real data presence
  - Detects default activity value patterns
- **DLMO Confidence** - Uses real confidence from CircadianPhaseResult
  - Was hardcoded to 0.0, now flows from actual calculation
  - Field renamed dlmo_hour → estimated_dlmo_hour throughout
- **Test & CI/CD Failures** - All tests pass with clean typing
  - Fixed all test failures from field renames
  - Added type ignore comments for abstract type registration
  - Added skipif decorators for ensemble tests requiring model files

### Added
- **Temporal Report Display** - NOW vs TOMORROW visualization for ensemble predictions
  - Shows current state (PAT) vs future risk (XGBoost) when using --ensemble
  - Temporal concordance percentage shows agreement between models
  - Pattern interpretation (Stable/Improving/Worsening/Critical)
  - Daily predictions enhanced with temporal context
- Clean architecture report formatter following SOLID principles
  - `ReportFormatterInterface` for extensibility
  - `TemporalAssessmentSection` composable report section
  - Factory pattern for report generation
- Comprehensive integration tests for temporal CLI functionality
- Documentation of all fixes in docs/bugs/v0.5.5-fixes/

### Changed
- Renamed all DLMO fields to clarify they are estimates, not measurements
- Error handling now fails fast with clear messages instead of hiding failures
- Test coverage increased to 90% with new integration tests

## [0.5.4] - 2025-07-29 - 🚨 EMERGENCY FIX

### Critical Bug Fixes
- **Fixed Date Assignment Mismatch** - 99% of sleep data was unfindable (#73, #74)
  - Created `UniversalDateAssignment` as single source of truth
  - Sleep assigned to wake date now findable by feature extractors
  - Fixes midnight-crossing sleep (99% of all sleep patterns)
- **Removed Fake Feature Generation** - No more identical 4.4% predictions (#72, #75)
  - Pipeline now skips days without real sleep data
  - Removed all hardcoded defaults (21:00 sleep, 7:00 wake)
  - System fails explicitly rather than generating fake features
- **Fixed PAT Integration** - Added missing encode() method (#76)
  - `ProductionPATLoader` now implements `PATEncoderInterface`
  - Temporal ensemble orchestrator works correctly
  - Supports both (7, 1440) and (10080,) input shapes
- **Added Data Quality Validation** - Clear warnings for sparse data (#77)
  - `DataQualityValidator` provides honest coverage metrics
  - Refuses predictions with <70% data coverage
  - User-friendly messages explain data requirements

### Added
- `domain/services/date_assignment.py` - Universal date assignment logic
- `application/services/data_quality_validator.py` - Data quality validation
- Comprehensive test suite for all critical bugs
- Demo scripts showing all fixes in action

### Changed
- `AggregationPipeline` now uses `UniversalDateAssignment` for date lookups
- `ClinicalFeatureExtractor` methods updated to find sleep correctly
- All components now skip days without data instead of using defaults
- Confidence scores now reflect actual data availability

### Breaking Changes
- Days without sleep data are now skipped (no fake predictions)
- Minimum 70% data coverage required for reliable predictions
- Default features removed - system returns None/empty for missing data

## [0.5.3] - 2025-07-29

### Added
- **Window Selection Strategies** - Smart data window finding for sparse health records (#67)
  - `WindowSelectionStrategy` interface with three implementations:
    - `MostRecentValidWindowStrategy` - finds most recent window with sufficient data
    - `BestQualityWindowStrategy` - finds window with highest data consistency  
    - `AllValidWindowsStrategy` - finds all valid prediction windows
  - New CLI flags:
    - `--auto-find-window` - automatically find most recent valid data window
    - `--window-strategy [recent|best|all]` - choose window selection approach
  - `DateWindow` value object tracks window quality and metadata
  - Backward compatible - existing behavior unchanged without flags
- **PAT Integration in CLI** - DI container now properly wired for temporal predictions (#68)
  - PAT model now accessible through CLI predictions
  - Temporal ensemble orchestrator created when --ensemble flag used
  - NOW vs TOMORROW separation working in CLI

### Fixed
- **Critical Date Window Bug** - System only checked last 7 days, causing 0 predictions (#67)
  - Previously: hardcoded to analyze 7 days before target_date
  - Now: intelligently finds valid windows in historical data
  - Fixes the "738K records but 0 predictions" issue
- **PAT Not Wired in CLI** - Model loaded but not connected through DI (#68)
  - DI container now passed to MoodPredictionPipeline
  - Temporal orchestrator properly initialized with PAT predictor
  - Clinical reports show temporal assessment when ensemble enabled
- **XML Date Filter Bug** - TypeError when comparing date/datetime objects (#38)
  - FastStreamingXMLParser now properly converts datetime to date for comparison
  - Entity type filtering handles "all" and None correctly
  - Date filtering works efficiently for large XML files
- **Misleading Density Warnings** - "1.5% density" shown for valid dense windows (#69)
  - Density now calculated within analysis window, not entire data span
  - Warnings only shown for actually sparse data within the window being analyzed
  - DataParsingService also updated to use date range for density calculations

## [0.5.2] - 2025-07-28

### Added
- **Temporal Ensemble Integration** - Switched API & CLI to TemporalEnsembleOrchestrator
  - PAT assesses current state (NOW) - "Are you depressed right now?"
  - XGBoost predicts future risk (TOMORROW) - "Will you have an episode tomorrow?"
  - New `/predict/temporal` API endpoint with temporal separation
  - Temporal concordance analysis between current state and future risk
  - Clinical guidance based on temporal patterns
  - Backward compatible - existing endpoints maintain same response format

### Fixed
- **PAT Integration** - PAT model was loaded but never used in predictions
  - Discovered ensemble predictions were just XGBoost results
  - TemporalEnsembleOrchestrator existed but wasn't connected
  - Now properly integrated throughout API and CLI

## [0.5.1] - 2025-07-28

### Changed
- **Baseline Calculation** - Removed BaselineRepository in favor of rolling window normalization
  - XGBoost models now use 30-60 day rolling windows for Z-score calculation
  - Removed 1,139 lines of unused baseline repository code
  - Personal normalization happens automatically in AggregationPipeline
  - No functionality changes - models work exactly as before

### Removed
- **BaselineRepository** - Deleted unused baseline persistence infrastructure
  - `baseline_repository_interface.py`
  - `file_baseline_repository.py`
  - `timescale_baseline_repository.py`
  - `baseline_repository_factory.py`
  - 13 associated test files

### Fixed
- **Model Requirements Understanding** - Clarified that XGBoost models are population-based
  - Models work immediately with 30+ days of sleep data
  - No mood episode labeling required for predictions
  - Resolved Issue #65 with definitive answers

## [0.5.0] - 2025-07-27

### Added
- **Temporal Ensemble Orchestrator** - Proper separation of current state (PAT) vs future risk (XGBoost)
- **XGBoost Feature Name Mapping** - Automatic conversion between internal names and model expectations
- **Git Settings Management** - Added .claude/settings.local.json to .gitignore
- **PAT Inference Smoke Test** - GitHub Actions workflow for model weight validation

### Fixed
- **Sleep Overlap Calculation** - Correctly handles overlapping records from multiple devices
- **XGBoost DMatrix Support** - Tests now properly handle DMatrix objects
- **Feature Name Mismatch** - Fixed "Missing feature: ST_long_MN" errors in tests
- **Mock Predictor Format** - Tests return proper MoodPrediction objects instead of dicts
- **Import Order** - Cleaned up whitespace and import organization

### Changed
- **Test Structure** - Updated all XGBoost tests to use `to_model_dict()` for proper feature mapping
- **DummyBooster** - Enhanced to handle both numpy arrays and DMatrix objects
- **Feature Suffixes** - Standardized to "_MN", "_SD", "_Zscore" across all tests

### Technical Details
- Fixed 10 failing tests related to XGBoost feature naming
- Proper handling of DMatrix shape attributes
- Consistent feature name mapping throughout test suite
- Clean branch management across development → staging → main

## [0.4.0] - 2025-07-24

### Added
- **Pure PyTorch PAT Implementation** - Complete rewrite achieving paper parity
  - PAT-S depression model: 0.56 AUC (matches paper's 0.560)
  - PAT-M depression model: 0.54 AUC (paper: 0.559)
  - PAT-L depression model: Training in progress (target: 0.610)
- **Production-ready training infrastructure**
  - Two-stage training scripts for S/M/L model variants
  - Natural class distribution training with pos_weight
  - MPS (Metal) GPU acceleration support
  - Checkpoint loading and resumption
- **Critical architectural fixes**
  - Non-standard attention (key_dim = embed_dim)
  - Post-norm transformer architecture
  - Concatenated positional embeddings
  - Weight conversion parity (0.000006 max difference)

### Fixed
- **Inverted pos_weight calculation** - was 0.82, now correctly 9.91
- **WeightedRandomSampler neutralizing class imbalance** - added --no-sampler flag
- **Git pre-push hooks** - now properly activate venv
- **Sleep duration calculation** - no longer uses flawed percentage method
- **TensorFlow/PyTorch weight loading** - achieved near-perfect parity

### Changed
- Moved from balanced sampling to natural distribution + pos_weight
- Training strategy: frozen warmup → selective unfreezing
- Reduced batch sizes for larger models (memory optimization)
- All PAT code now pure PyTorch (no TF dependencies)

### Performance
- 976 tests passing, 9 skipped, 7 xfailed
- Full type safety (mypy clean)
- All linting checks pass (ruff clean)
- CI/CD pipeline green

## [0.3.0-alpha] - 2025-07-23

### Added
- **Temporal Ensemble Orchestrator** - Revolutionary separation of NOW vs TOMORROW predictions
  - PAT assesses current mood state based on past 7 days
  - XGBoost predicts future risk based on circadian features
  - No averaging or mixing - clean temporal windows
- PAT depression classification head training infrastructure
  - Training script for NHANES data (`scripts/train_pat_depression_head_simple.py`)
  - Successfully trained proof-of-concept model (AUC 0.64 achieved after 20 epochs)
  - Model weights saved to `model_weights/pat/heads/pat_depression_head.pt`
- Clinical alert generation for high-risk patterns
- Graceful degradation when models fail (returns defaults with 0 confidence)
- CI workflow for PAT training smoke tests

### Fixed
- Discovered and documented that existing "ensemble" was fake (just returned XGBoost predictions)
- Seoul statistical features now correctly provided to XGBoost models
  - Added `aggregate_seoul_features()` method to generate proper 36 features
  - Fixed feature name mismatch (e.g., `sleep_percentage_MN` vs `sleep_duration_hours`)
  - Added `use_seoul_features` config flag to control pipeline behavior
  - XGBoost-only predictions now use correct statistical features

### Changed
- Deprecated `EnsembleOrchestrator` with clear migration warnings
- Test organization: skipped tests converted to xfail with Phase 4 reasons
- `TemporalMoodAssessment` now contains separate `CurrentMoodState` and `FutureMoodRisk`

### Technical Details
- `DailyFeatures` dataclass with all 36 Seoul statistical features
- Comprehensive tests for Seoul feature generation and naming
- `to_xgboost_dict()` method for proper feature name mapping
- All tests passing (976 passed, 12 xfailed)
- Full type safety maintained
- Zero linting issues

## [0.2.4] - 2025-07-23

### Added
- Feature Engineering Orchestrator integration for automatic validation and anomaly detection
- Type annotations throughout the codebase - full mypy compliance
- Adapter pattern for clean orchestrator integration without breaking changes
- Completeness reports showing exactly what data is missing
- Feature importance tracking to understand which biomarkers matter most

### Fixed
- Baseline repository test race conditions with `tmp_path` fixture and `xdist_group` marker
- 15 type errors across orchestrator_adapter, process_health_data_use_case, and main.py
- PATSequence constructor now uses correct parameters
- FastAPI decorator type warnings with proper type: ignore annotations

### Changed
- Moved PERFORMANCE_INVESTIGATION.md to docs/ directory
- Updated documentation to clarify model capabilities and temporal windows
- Feature extraction now includes automatic validation and data quality checks
- DI container properly initializes orchestrator with caching enabled

### Developer Notes
- All 916 tests passing with 90%+ coverage
- No mypy errors (59 source files clean)
- No ruff linting issues
- Parallel test execution now stable

## [0.2.3] - 2025-07-21

### Added
- Optimized aggregation pipeline with pre-indexing for O(n+m) performance
- Configurable DLMO and circadian calculations via AggregationConfig
- Performance tests with pytest markers for large XML files
- XMLDataGenerator utility for creating test data

### Fixed
- XML processing timeouts for 500MB+ files (Issue #29)
  - Aggregation now completes in 17.4s for 365 days (was timeout after 120s)
  - 7x performance improvement by eliminating O(n×m) complexity
- Directory creation race condition in FileBaselineRepository tests
- Parent directory creation in FileBaselineRepository

### Changed
- Made expensive calculations (DLMO, circadian) optional for performance
- Added 'performance' pytest marker to exclude heavy tests from default runs

## [0.2.2] - In Development

### Added
- Progress indication for XML parsing operations (Issue #31)
  - Progress callbacks throughout the pipeline from CLI to XML parser
  - CLI `--progress` flag shows tqdm progress bars
  - Error-resilient progress reporting
  - Integration tests for progress indication functionality
- Test data management with dedicated `tests/_data/` directory
- Coverage configuration for parallel test runs
- Documentation for xfail tests explaining technical debt

### Changed
- Improved error handling for tqdm import in CLI commands

### Fixed
- Progress bar cleanup on error conditions
- Coverage warnings during parallel test execution

### Developer Notes
- All progress indication tests passing (16 unit + integration tests)
- Feature branch ready for merge to development

## [0.2.1] - 2025-07-20

### Added
- Date range filtering for XML processing with `--days-back` and `--date-range` CLI options
- Integration tests for date filtering and memory bounds
- Wire-tap logging in SleepAggregator for debugging sleep date assignment
- Property-based testing with hypothesis for incremental statistics
- Heart rate aggregation in AggregationPipeline
- HR/HRV field support in TimescaleDB baseline repository
- Comprehensive test suite for TimescaleDB HR/HRV functionality
- Test organization: created repositories/ subfolder for repository tests

### Changed
- Implemented Apple Health 3pm cutoff rule for sleep date assignment
- Made HR/HRV fields optional in UserBaseline (no more magic defaults)
- Updated FileBaselineRepository to preserve None values for HR/HRV
- Fixed sleep duration calculation bug (was using sleep_percentage * 24)
- Updated all datetime.utcnow() calls to datetime.now(timezone.utc)
- Improved AdvancedFeatureEngineer to only update baselines with real data

### Fixed
- 848 linting issues resolved with ruff
- 55 type checking errors fixed
- SQLAlchemy 2.0 import compatibility
- Structlog logger initialization order
- Application regression test now uses 3 days of data for statistics
- TimescaleDB repository now handles baseline updates properly
- Sleep duration calculation now caps at 24 hours to handle overlapping records
- Episode deletion in SQLite repository now works correctly
- XGBoost model loading now looks in correct directory (converted/ instead of pretrained/)
- Fixed all deprecated datetime.utcnow() usage to use timezone-aware datetime.now(UTC)
- Fixed deprecated datetime.utcfromtimestamp() to datetime.fromtimestamp(..., UTC)

### Removed
- Magic HR/HRV defaults (70 bpm / 50 ms) that would skew personal baselines
- Deprecated datetime.utcnow() usage throughout codebase

### Technical Debt (Tracked)
- Issue #38: Streaming parser date filtering bug (test: test_memory_bounds.py)
- Issue #39: Baseline persistence tests use legacy entity APIs (test: test_baseline_persistence_pipeline.py)
- Issue #40: XGBoost JSON models lack predict_proba method (test: test_pipeline_with_ensemble)
- All xfail tests have strict=True to alert when fixed
- Nightly CI job added to monitor slow/xfail tests
- Repository pattern redundancy needs review
- SQLite repository now uses unique constraints to prevent duplicate episodes

### Developer Notes
- Run `./scripts/create-tech-debt-issues.sh` to create GitHub issues
- Update issue numbers in xfail markers after creation
- See `issues/` directory for detailed issue descriptions

## [0.1.0] - 2024-01-01

### Added
- Initial release with core functionality
- XGBoost + PAT ensemble models
- CLI with 6 commands
- FastAPI server
- Docker deployment
- Comprehensive test suite (695 tests)