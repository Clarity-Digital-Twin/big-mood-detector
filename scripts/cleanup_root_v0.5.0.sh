#!/bin/bash
# Cleanup root directory for v0.5.0
# Moves analysis/audit files to docs/archive

echo "=== Big Mood Detector v0.5.0 Root Cleanup ==="
echo "Moving analysis and audit files to docs/archive..."

# Create archive directory if it doesn't exist
mkdir -p docs/archive

# Move analysis and audit files
FILES_TO_ARCHIVE=(
    "COMPREHENSIVE_FINDINGS_SUMMARY.md"
    "CRITICAL_FEATURE_IMPLEMENTATION_ANALYSIS.md"
    "CRITICAL_XGBOOST_FEATURE_AUDIT.md"
    "DATA_REQUIREMENTS_ANALYSIS.md"
    "DATA_SELECTION_AND_VALIDATION_ANALYSIS.md"
    "DEEP_AUDIT_FINDINGS.md"
    "EXECUTIVE_SUMMARY_FINAL.md"
    "EXECUTIVE_SUMMARY_PIPELINE_FINDINGS.md"
    "FINAL_ARCHITECTURE_ANALYSIS.md"
    "FINAL_E2E_SUMMARY.md"
    "IMPLEMENTATION_PLAN.md"
    "PIPELINE_DRIFT_ANALYSIS.md"
    "SLEEP_CALCULATION_AUDIT.md"
    "E2E_TEST_RESULTS_2025_07_26.md"
)

for file in "${FILES_TO_ARCHIVE[@]}"; do
    if [ -f "$file" ]; then
        # Add archive header
        echo -e "> **Archived 2025-07-27** – Moved from root to docs/archive during v0.5.0 cleanup\n\n$(cat $file)" > "docs/archive/$file"
        rm "$file"
        echo "✓ Moved $file"
    fi
done

echo ""
echo "=== Files to keep in root ==="
echo "Documentation:"
echo "- README.md (main project readme)"
echo "- CHANGELOG.md (version history)"
echo "- CLAUDE.md (AI assistant guide)"
echo "- CONTRIBUTING.md (contribution guidelines)"
echo "- LICENSE (Apache 2.0)"
echo "- NOTICE (legal notices)"
echo "- ROADMAP_TO_MVP_V1.0.md (current roadmap)"
echo ""
echo "Testing/Status:"
echo "- E2E_TESTING_CHECKLIST.md (active checklist)"
echo "- CHECKPOINT_2025_07_26.md (latest checkpoint)"
echo ""
echo "Config files:"
echo "- pyproject.toml, Makefile, Docker*, etc."
echo ""
echo "=== Cleanup complete! ==="