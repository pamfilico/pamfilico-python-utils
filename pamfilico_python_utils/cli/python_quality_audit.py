#!/usr/bin/env python3
"""
Python Code Quality Audit - CLI Entry Point

Runs comprehensive quality analysis on Python files and saves markdown reports
to audit/ directories next to the analyzed files.

Tools integrated:
- Radon: Cyclomatic complexity, Maintainability Index, Halstead metrics
- Xenon: Complexity threshold checker (fails if thresholds exceeded)
- Cohesion: LCOM (Lack of Cohesion of Methods) for classes
- Bandit: Security vulnerabilities
- Pylint: Code quality and style
- Vulture: Dead code detection

Usage:
    poetry run python_quality_audit <file_or_pattern>
    poetry run python_quality_audit src/app.py --xenon-threshold A
    poetry run python_quality_audit --pattern "src/**/*.py" --dry-run
"""

import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime
import argparse
from typing import Optional, Dict, Any

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli  # Python 3.11+
    except ImportError:
        tomli = None


def run_command(cmd: list[str], timeout: int = 120) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, returncode."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", f"Tool not found: {cmd[0]}", -1
    except subprocess.TimeoutExpired:
        return "", "Command timed out", -1


def section(title: str) -> str:
    return f"\n## {title}\n"


def analyze_radon_cc(target: str) -> str:
    """Cyclomatic complexity analysis."""
    stdout, stderr, rc = run_command(["radon", "cc", target, "-s", "-a"])
    if rc == -1:
        return f"Error: {stderr}\n"
    return stdout if stdout.strip() else "No functions analyzed.\n"


def analyze_radon_mi(target: str) -> str:
    """Maintainability index analysis."""
    stdout, stderr, rc = run_command(["radon", "mi", target, "-s"])
    if rc == -1:
        return f"Error: {stderr}\n"
    return stdout if stdout.strip() else "No files analyzed.\n"


def analyze_radon_hal(target: str) -> str:
    """Halstead metrics analysis."""
    stdout, stderr, rc = run_command(["radon", "hal", target])
    if rc == -1:
        return f"Error: {stderr}\n"
    return stdout if stdout.strip() else "No functions analyzed.\n"


def analyze_xenon(target: str, threshold: str = "B") -> str:
    """Xenon threshold check."""
    stdout, stderr, rc = run_command([
        "xenon", target,
        "--max-absolute", threshold,
        "--max-modules", threshold,
        "--max-average", "A"
    ])
    
    if rc == -1:
        return f"Error: {stderr}\n"
    
    if rc == 0:
        return f"PASSED - All code is below threshold '{threshold}'\n"
    else:
        output = f"FAILED - Code exceeds threshold '{threshold}'\n\n"
        if stdout:
            output += stdout
        if stderr:
            output += stderr
        return output


def analyze_cohesion(target: str) -> str:
    """LCOM cohesion analysis for classes."""
    stdout, stderr, rc = run_command(["cohesion", "-f", target])
    if rc == -1:
        return f"Error: {stderr}\n"
    
    if not stdout.strip():
        return "No classes found to analyze.\n"
    
    return stdout


def analyze_bandit(target: str) -> str:
    """Security vulnerability analysis."""
    stdout, stderr, rc = run_command(["bandit", "-r", target, "-f", "txt", "-q"])
    if rc == -1:
        return f"Error: {stderr}\n"
    
    if not stdout.strip() or "No issues identified" in stdout:
        return "No security issues found.\n"
    
    return stdout


def analyze_pylint(target: str) -> str:
    """Pylint code quality analysis."""
    stdout, stderr, rc = run_command([
        "pylint", target,
        "--output-format=text",
        "--reports=y",
        "--score=y",
        "--exit-zero"
    ])
    if rc == -1:
        return f"Error: {stderr}\n"
    return stdout if stdout.strip() else "No issues found.\n"


def is_flask_route_function(file_path: str, function_name: str, line_number: int) -> bool:
    """Check if a function is a Flask route by examining decorators above it."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Look backwards from the function line for decorators
        start_idx = max(0, line_number - 10)  # Check up to 10 lines before
        end_idx = min(len(lines), line_number + 2)  # And a bit after
        
        function_block = ''.join(lines[start_idx:end_idx])
        
        # Flask route decorators patterns
        flask_decorators = [
            '@api.route', '@app.route', '@blueprint.route', '@bp.route',
            '@api_bp.route', '@main.route', '@views.route'
        ]
        
        # Check if any Flask decorator appears before the function
        return any(decorator in function_block for decorator in flask_decorators)
        
    except Exception:
        return False


def analyze_vulture(target: str) -> str:
    """Dead code detection with Flask route awareness."""
    stdout, stderr, rc = run_command(["vulture", target])
    if rc == -1:
        return f"Error: {stderr}\n"
    
    if not stdout.strip():
        return "No dead code detected.\n"
    
    # Filter out Flask route functions from vulture output
    lines = stdout.strip().split('\n')
    filtered_lines = []
    flask_routes_ignored = []
    
    for line in lines:
        if 'unused function' in line:
            # Parse vulture output: "path:line: unused function 'name' (confidence%)"
            try:
                parts = line.split(':')
                if len(parts) >= 3:
                    file_path = parts[0]
                    line_number = int(parts[1]) - 1  # Convert to 0-based index
                    
                    # Extract function name from the message
                    match = re.search(r"unused function '([^']+)'", line)
                    if match:
                        function_name = match.group(1)
                        
                        # Check if this is a Flask route function
                        if is_flask_route_function(file_path, function_name, line_number):
                            flask_routes_ignored.append(function_name)
                            continue  # Skip this line (don't add to filtered_lines)
            except (ValueError, IndexError):
                pass  # If parsing fails, keep the original line
        
        # Add non-Flask route lines to output
        filtered_lines.append(line)
    
    # Build the final output
    result = []
    if filtered_lines:
        result.extend(filtered_lines)
        result.append("")  # Empty line separator
    
    if flask_routes_ignored:
        result.append("# Flask routes ignored (not actually unused):")
        for route in flask_routes_ignored:
            result.append(f"# - {route}()")
        result.append("")
    
    if not filtered_lines and not flask_routes_ignored:
        return "No dead code detected.\n"
    elif not filtered_lines:
        return "No dead code detected (Flask routes ignored).\n"
    
    return '\n'.join(result)


def generate_report(target: str, xenon_threshold: str = "B") -> str:
    """Generate the full markdown report."""
    target_path = Path(target).resolve()
    
    report = []
    report.append("# Python Code Quality Report")
    report.append("")
    report.append(f"**Target:** `{target_path}`")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("---")
    
    # Cyclomatic Complexity
    report.append(section("Cyclomatic Complexity (McCabe)"))
    report.append("Measures the number of independent paths through code.")
    report.append("Grades: A (1-5), B (6-10), C (11-20), D (21-30), E (31-40), F (40+)")
    report.append("")
    report.append("```")
    report.append(analyze_radon_cc(str(target_path)).rstrip())
    report.append("```")
    
    # Xenon Threshold Check
    report.append(section("Complexity Threshold Check (Xenon)"))
    report.append(f"Threshold set to: **{xenon_threshold}**")
    report.append("")
    report.append("```")
    report.append(analyze_xenon(str(target_path), xenon_threshold).rstrip())
    report.append("```")
    
    # Maintainability Index
    report.append(section("Maintainability Index (Oman-Hagemeister)"))
    report.append("Combines Halstead Volume, Cyclomatic Complexity, and LOC.")
    report.append("Grades: A (20-100 high), B (10-19 medium), C (0-9 low)")
    report.append("")
    report.append("```")
    report.append(analyze_radon_mi(str(target_path)).rstrip())
    report.append("```")
    
    # Halstead Metrics
    report.append(section("Halstead Metrics"))
    report.append("Measures: h1 (unique operators), h2 (unique operands), N1 (total operators), N2 (total operands)")
    report.append("Derived: vocabulary, length, volume, difficulty, effort, time, bugs")
    report.append("")
    report.append("```")
    report.append(analyze_radon_hal(str(target_path)).rstrip())
    report.append("```")
    
    # Cohesion (LCOM)
    report.append(section("Class Cohesion (LCOM)"))
    report.append("Lack of Cohesion of Methods - measures how related methods are within a class.")
    report.append("Lower percentage = better cohesion. High LCOM suggests class should be split.")
    report.append("")
    report.append("```")
    report.append(analyze_cohesion(str(target_path)).rstrip())
    report.append("```")
    
    # Security
    report.append(section("Security Issues (Bandit)"))
    report.append("Scans for common security vulnerabilities and bad practices.")
    report.append("")
    report.append("```")
    report.append(analyze_bandit(str(target_path)).rstrip())
    report.append("```")
    
    # Pylint
    report.append(section("Code Quality (Pylint)"))
    report.append("Style, errors, refactoring suggestions, and overall score.")
    report.append("")
    report.append("```")
    report.append(analyze_pylint(str(target_path)).rstrip())
    report.append("```")
    
    # Dead Code
    report.append(section("Dead Code (Vulture)"))
    report.append("Detects unused functions, variables, classes, and imports.")
    report.append("Note: Flask route functions are automatically excluded from unused function reports.")
    report.append("")
    report.append("```")
    report.append(analyze_vulture(str(target_path)).rstrip())
    report.append("```")
    
    # References
    report.append(section("References"))
    report.append("- McCabe (1976) 'A Complexity Measure' IEEE TSE")
    report.append("- Halstead (1977) 'Elements of Software Science' Elsevier")
    report.append("- Oman & Hagemeister (1992) 'Metrics for Assessing Maintainability' IEEE ICSM")
    report.append("- Chidamber & Kemerer (1994) 'A Metrics Suite for OO Design' IEEE TSE (LCOM)")
    report.append("")
    
    return "\n".join(report)


def save_audit_report(file_path: Path, report: str) -> Path:
    """Save the audit report next to the analyzed file in audit/ directory."""
    # Create audit directory in the same location as the file
    audit_dir = file_path.parent / "audit"
    audit_dir.mkdir(exist_ok=True)
    
    # Generate report filename based on the original file
    report_name = f"{file_path.stem}.md"
    report_path = audit_dir / report_name
    
    # Write the report
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return report_path


def check_tools() -> list[str]:
    """Check which tools are available and return list of missing ones."""
    tools = ["radon", "xenon", "cohesion", "bandit", "pylint", "vulture"]
    missing = []
    
    for tool in tools:
        _, _, rc = run_command([tool, "--help"])
        if rc == -1:
            missing.append(tool)
    
    return missing


def load_config_from_pyproject() -> Optional[Dict[str, Any]]:
    """Load configuration from pyproject.toml if it exists"""
    if tomli is None:
        return None

    # Look for pyproject.toml in current directory or parent directories
    cwd = Path.cwd()
    for path in [cwd] + list(cwd.parents):
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomli.load(f)
                    # Try specific config first
                    config = data.get("tool", {}).get("python_quality_audit", {})
                    if config:
                        print(f"📋 Loaded config from: {pyproject_path}")
                        return config
            except Exception as e:
                print(f"Warning: Could not load {pyproject_path}: {e}")
                continue

    return None


def parse_arguments():
    """Parse command line arguments with pyproject.toml config support"""
    # Load config from pyproject.toml
    config = load_config_from_pyproject()

    # Set defaults from config or sensible defaults
    default_threshold = config.get("xenon_threshold", "B") if config else "B"
    default_pattern = config.get("pattern", "**/*.py") if config else "**/*.py"

    parser = argparse.ArgumentParser(
        description="Python Code Quality Audit - Comprehensive analysis with multiple tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single file
  poetry run python_quality_audit src/app.py
  
  # Analyze with strict threshold
  poetry run python_quality_audit src/app.py --xenon-threshold A
  
  # Analyze multiple files with pattern
  poetry run python_quality_audit --pattern "src/**/*.py"
  
  # Preview what would be analyzed
  poetry run python_quality_audit --pattern "src/**/*.py" --dry-run

Configuration in pyproject.toml:
  [tool.python_quality_audit]
  xenon_threshold = "A"
  pattern = "src/**/*.py"
        """,
    )

    parser.add_argument(
        'target',
        nargs='?',
        help='Python file to analyze (or use --pattern for multiple files)'
    )
    
    parser.add_argument(
        '--pattern',
        type=str,
        default=default_pattern,
        help=f'File pattern to match for multiple files (default: {default_pattern})'
    )
    
    parser.add_argument(
        '--xenon-threshold',
        '-x',
        type=str,
        default=default_threshold,
        choices=["A", "B", "C", "D", "E", "F"],
        help=f'Xenon complexity threshold (default: {default_threshold})'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what files would be analyzed without running analysis'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    # Check if target or pattern is provided
    if not args.target and not hasattr(args, 'pattern'):
        print("❌ Error: Must specify either a target file or use --pattern")
        sys.exit(1)

    # Check tools availability
    missing_tools = check_tools()
    if missing_tools:
        print(f"⚠️  Missing tools: {', '.join(missing_tools)}")
        print(f"📦 Install with: pip install {' '.join(missing_tools)}")
        print("")

    # Determine files to analyze
    if args.target:
        # Single file mode
        target_path = Path(args.target)
        if not target_path.exists():
            print(f"❌ Error: {target_path} does not exist")
            sys.exit(1)
        
        if not target_path.suffix == '.py':
            print(f"❌ Error: {target_path} is not a Python file")
            sys.exit(1)
            
        files_to_analyze = [target_path]
    else:
        # Pattern mode
        cwd = Path.cwd()
        files_to_analyze = list(cwd.glob(args.pattern))
        files_to_analyze = [f for f in files_to_analyze if f.suffix == '.py' and f.is_file()]
        
        if not files_to_analyze:
            print(f"❌ No Python files found matching pattern: {args.pattern}")
            sys.exit(1)

    print(f"🔍 Found {len(files_to_analyze)} Python file(s) to analyze")
    
    if args.dry_run:
        print("🔍 DRY RUN - Files that would be analyzed:")
        for file_path in files_to_analyze:
            audit_dir = file_path.parent / "audit"
            report_name = f"{file_path.stem}.md"
            try:
                file_rel = file_path.relative_to(Path.cwd())
                audit_rel = audit_dir.relative_to(Path.cwd())
            except ValueError:
                # If file is not relative to cwd, use absolute paths
                file_rel = file_path
                audit_rel = audit_dir
            print(f"  📝 {file_rel} -> {audit_rel}/{report_name}")
        return

    # Analyze files
    total_files = len(files_to_analyze)
    for i, file_path in enumerate(files_to_analyze, 1):
        try:
            file_rel = file_path.relative_to(Path.cwd())
        except ValueError:
            file_rel = file_path
            
        print(f"\n📊 Analyzing ({i}/{total_files}): {file_rel}")
        
        if missing_tools:
            print(f"  ⚠️  Some tools unavailable, report will be incomplete")
        
        # Generate report
        report = generate_report(str(file_path), args.xenon_threshold)
        
        # Save report
        report_path = save_audit_report(file_path, report)
        try:
            report_rel = report_path.relative_to(Path.cwd())
        except ValueError:
            report_rel = report_path
        print(f"  ✅ Report saved: {report_rel}")

    print(f"\n✨ Analysis complete! Generated {total_files} audit report(s)")


if __name__ == '__main__':
    main()