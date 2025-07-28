#!/usr/bin/env python3
"""
Find all BaselineRepository usage and dependencies.
This helps us safely remove dead code without breaking anything.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Root directory
ROOT = Path(__file__).parent
SRC = ROOT / "src" / "big_mood_detector"

# What we're looking for
BASELINE_PATTERNS = [
    r"baseline_repository",
    r"BaselineRepository",
    r"UserBaseline",
    r"persist_baseline",
    r"load_baseline",
    r"update_baseline",
]

def find_imports(file_path):
    """Find all baseline-related imports in a file."""
    imports = []
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Find import statements
        for pattern in BASELINE_PATTERNS:
            # Check imports
            import_pattern = rf"(from .* import .*{pattern}.*|import .*{pattern}.*)"
            matches = re.findall(import_pattern, content, re.IGNORECASE)
            if matches:
                imports.extend(matches)
                
            # Check usage (not in comments)
            usage_pattern = rf"(?<!#.*){pattern}"
            if re.search(usage_pattern, content):
                # Count non-import, non-comment usages
                usage_count = len(re.findall(usage_pattern, content)) - len(matches)
                if usage_count > 0:
                    imports.append(f"USES: {pattern} ({usage_count} times)")
                    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return imports

def analyze_file_dependencies():
    """Analyze all Python files for baseline dependencies."""
    dependencies = defaultdict(list)
    
    # Scan all Python files
    for py_file in SRC.rglob("*.py"):
        imports = find_imports(py_file)
        if imports:
            rel_path = py_file.relative_to(ROOT)
            dependencies[str(rel_path)] = imports
    
    return dependencies

def categorize_files(dependencies):
    """Categorize files by their role."""
    categories = {
        "Core Baseline Files": [],
        "Infrastructure Using Baseline": [],
        "Application Using Baseline": [],
        "Tests": [],
        "Other": []
    }
    
    for file_path, imports in dependencies.items():
        if "baseline_repository_interface.py" in file_path:
            categories["Core Baseline Files"].append(file_path)
        elif "repositories" in file_path and "baseline" in file_path:
            categories["Core Baseline Files"].append(file_path)
        elif "test" in file_path:
            categories["Tests"].append(file_path)
        elif "infrastructure" in file_path:
            categories["Infrastructure Using Baseline"].append(file_path)
        elif "application" in file_path:
            categories["Application Using Baseline"].append(file_path)
        else:
            categories["Other"].append(file_path)
    
    return categories

def check_critical_paths():
    """Check if critical paths use baseline."""
    critical_files = [
        "application/pipelines/xgboost_pipeline.py",
        "application/services/aggregation_pipeline.py",
        "infrastructure/ml_models/xgboost_models.py",
        "interfaces/cli/commands/predict.py",
        "interfaces/api/routes/predictions.py",
    ]
    
    print("\n=== Critical Path Analysis ===")
    all_clear = True
    
    for file in critical_files:
        file_path = SRC / file
        if file_path.exists():
            imports = find_imports(file_path)
            if imports:
                print(f"⚠️  {file}: USES BASELINE")
                for imp in imports:
                    print(f"    - {imp}")
                all_clear = False
            else:
                print(f"✓ {file}: Clean")
        else:
            print(f"? {file}: Not found")
    
    return all_clear

def main():
    print("=== Baseline Repository Usage Analysis ===\n")
    
    # Find all dependencies
    dependencies = analyze_file_dependencies()
    
    # Categorize files
    categories = categorize_files(dependencies)
    
    # Print results by category
    for category, files in categories.items():
        if files:
            print(f"\n{category} ({len(files)} files):")
            for file in sorted(files):
                print(f"  - {file}")
                if file in dependencies:
                    for imp in dependencies[file][:3]:  # Show first 3
                        print(f"      {imp}")
                    if len(dependencies[file]) > 3:
                        print(f"      ... and {len(dependencies[file]) - 3} more")
    
    # Check critical paths
    critical_clear = check_critical_paths()
    
    # Summary
    print("\n=== Summary ===")
    total_files = sum(len(files) for files in categories.values())
    print(f"Total files with baseline dependencies: {total_files}")
    print(f"Critical paths clear: {'YES' if critical_clear else 'NO'}")
    
    # Removal order recommendation
    print("\n=== Recommended Removal Order ===")
    print("1. Remove test files first (they won't break production)")
    print("2. Check if infrastructure files are actually used")
    print("3. Update application files to remove baseline parameters")
    print("4. Finally remove core baseline files")
    
    # Next steps
    print("\n=== Next Steps ===")
    print("1. Run: python find_dead_baseline_code.py > baseline_deps_before.txt")
    print("2. Create git branch: git checkout -b remove-baseline-repository")
    print("3. Start removing files in recommended order")
    print("4. Run tests after each removal")
    print("5. Run this script again to verify progress")

if __name__ == "__main__":
    main()