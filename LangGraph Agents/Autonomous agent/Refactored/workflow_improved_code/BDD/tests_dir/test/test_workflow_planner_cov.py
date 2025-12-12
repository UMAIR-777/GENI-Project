# coverage_runner.py

import sys
import os
import coverage
import pytest
import re
from pathlib import Path

def run_step_tests_and_evaluate_coverage(
    production_file: str = "src/workflow_planner.py",
    tests_dir: str = "BDD/tests_dir/test/test_workflow_planner.py",
    report_file: str = "BDD/tests_dir/C_Reports/workflow_planner_coverage_report.json"
) -> dict:
    """
    Execute the BDD step tests and evaluate both code coverage and functional coverage
    of the specified production code.
    """
    # Get absolute paths - fix path resolution
    project_root = Path(__file__).parent.parent.parent.parent  # Go up to main project root
    src_path = project_root / "src"
    
    # Verify source file exists
    production_path = project_root / production_file
    if not production_path.exists():
        raise FileNotFoundError(f"Source file not found: {production_path}")

    # Configure coverage with correct paths
    cov = coverage.Coverage(
        source=[str(src_path)],
        omit=["*/tests/*", "*/__pycache__/*"],
        branch=True,
        data_file='.coverage'  # Specify coverage data file
    )
    
    try:
        cov.erase()
        cov.start()

        # Add source directory to Python path
        sys.path.insert(0, str(project_root))
        
        # Run tests with coverage
        test_file = project_root / tests_dir
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")
            
        exit_code = pytest.main([
            str(test_file),
            "--disable-warnings",
            "-v",
            f"--rootdir={project_root}"
        ])
        
        # Stop coverage collection before checking results
        cov.stop()
        cov.save()

        if exit_code != 0:
            raise RuntimeError("Tests failed; aborting coverage evaluation.")

        # Get coverage data with proper path resolution and analyze coverage data with error handling
        try:
            filename, executed, missing, _ = cov.analysis(str(project_root / production_file))
        except coverage.exceptions.NoSource as e:
            raise FileNotFoundError(f"Could not analyze source file: {e}")
        except coverage.exceptions.CoverageException as e:
            raise RuntimeError(f"Coverage analysis failed: {e}")
        
        # Filter out comments and docstrings from missing lines
        with open(str(project_root / production_file), "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not analyze source file: {e}")
    except coverage.exceptions.CoverageException as e:
        raise RuntimeError(f"Coverage analysis error: {e}")
    
    actual_missing = []
    for line_num in missing:
        line = lines[line_num-1].strip()
        if not (line.startswith('#') or line.startswith('"""') or line.startswith("'''")):
            actual_missing.append(line_num)

    total = len(executed) + len(actual_missing)
    coverage_pct = (len(executed) / total * 100) if total else 0.0

    warnings = []
    if actual_missing:
        warnings.append(
            f"Unexecuted lines in {production_file}: {actual_missing}"
        )
    if coverage_pct < 100.0:
        warnings.append(
            f"Code coverage is below 100%: {coverage_pct:.2f}%"
        )

    # Functional coverage analysis
    feature_lines = []
    for idx, line in enumerate(lines, start=1):
        if "@Feature:" in line or "@Scenario:" in line:
            feature_lines.append(idx)

    covered_features = [ln for ln in feature_lines if ln in executed]
    total_features = len(feature_lines)

    if total_features and len(covered_features) < total_features:
        warnings.append(
            f"Only {len(covered_features)}/{total_features} feature markers were covered."
        )

    report = {
        "code_coverage": coverage_pct,
        "total_lines": total,
        "executed_lines": len(executed),
        "missing_lines": actual_missing,
        "total_features": total_features,
        "covered_features": len(covered_features),
        "warnings": warnings,
    }

    # Print summary
    print("\n=== Coverage & Functional Verification Report ===")
    print(f"Production module: {production_file}")
    print(f"Total lines       : {total}")
    print(f"Executed lines    : {len(executed)}")
    print(f"Coverage          : {coverage_pct:.2f}%")
    if actual_missing:
        print(f"Missing lines     : {actual_missing}")
    print(f"Feature markers   : {total_features}")
    print(f"Covered features  : {len(covered_features)}")
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(" -", w)
    else:
        print("All lines and features are fully exercised.")

    # Write JSON report
    try:
        import json
        with open(report_file, "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2)
    except Exception as e:
        print(f"Warning: Could not write report file: {e}")

    return report

if __name__ == "__main__":
    run_step_tests_and_evaluate_coverage()
