#!/usr/bin/env python3
"""Move Imports to Top - CLI Entry Point

Command-line interface for moving all inline imports from inside functions 
to the top of Python files. This is particularly useful for Flask route files
that have imports scattered throughout the functions.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli  # Python 3.11+
    except ImportError:
        tomli = None


def extract_inline_imports(file_content: str) -> tuple[List[str], str]:
    """
    Extract all inline imports from file content and return them along with cleaned content.
    
    Args:
        file_content: The content of the Python file
        
    Returns:
        Tuple of (list_of_imports, content_without_inline_imports)
    """
    lines = file_content.split('\n')
    imports = []
    cleaned_lines = []
    
    # Track indentation to identify imports inside functions/classes
    for i, line in enumerate(lines):
        # Check if line is an import statement with indentation (inline import)
        stripped = line.strip()
        if (line.startswith('    ') or line.startswith('\t')) and (
            stripped.startswith('import ') or stripped.startswith('from ')
        ):
            # This is an inline import - extract it
            # Remove leading whitespace to normalize
            import_statement = stripped
            if import_statement not in imports:
                imports.append(import_statement)
            # Skip this line (remove it from content)
            continue
        else:
            # Keep this line
            cleaned_lines.append(line)
    
    return imports, '\n'.join(cleaned_lines)


def insert_imports_at_top(file_content: str, new_imports: List[str]) -> str:
    """
    Insert new imports at the top of the file, after existing imports.
    
    Args:
        file_content: The content of the Python file
        new_imports: List of import statements to add
        
    Returns:
        Modified file content with imports added
    """
    if not new_imports:
        return file_content
        
    lines = file_content.split('\n')
    
    # Find the insertion point (after existing imports)
    insertion_point = 0
    last_import_line = -1
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines and comments at the beginning
        if not stripped or stripped.startswith('#'):
            continue
            
        # Check if this is an import line (at top level - no indentation)
        if (not line.startswith(' ') and not line.startswith('\t') and 
            (stripped.startswith('import ') or stripped.startswith('from '))):
            last_import_line = i
            continue
            
        # Check for docstrings (triple quotes)
        if stripped.startswith('"""') or stripped.startswith("'''"):
            # Skip docstring
            quote_type = stripped[:3]
            if stripped.count(quote_type) >= 2:
                # Single line docstring
                continue
            else:
                # Multi-line docstring - find end
                for j in range(i + 1, len(lines)):
                    if quote_type in lines[j]:
                        i = j
                        break
                continue
        
        # If we hit non-import, non-comment, non-docstring code, stop
        if stripped and not stripped.startswith('#'):
            break
    
    # Insert point is after last import line, or at beginning if no imports
    insertion_point = last_import_line + 1 if last_import_line >= 0 else 0
    
    # Insert new imports
    for import_stmt in new_imports:
        lines.insert(insertion_point, import_stmt)
        insertion_point += 1
    
    return '\n'.join(lines)


def process_file(file_path: Path, dry_run: bool = True) -> tuple[bool, int]:
    """
    Process a single Python file to move imports to top.
    
    Args:
        file_path: Path to the Python file
        dry_run: If True, don't actually modify files
        
    Returns:
        Tuple of (was_modified, number_of_imports_moved)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Extract inline imports
        inline_imports, cleaned_content = extract_inline_imports(original_content)
        
        if not inline_imports:
            return False, 0
        
        # Insert imports at top
        final_content = insert_imports_at_top(cleaned_content, inline_imports)
        
        if dry_run:
            print(f"  🔍 DRY RUN: Would move {len(inline_imports)} imports")
            for imp in inline_imports[:5]:  # Show first 5
                print(f"    - {imp}")
            if len(inline_imports) > 5:
                print(f"    ... and {len(inline_imports) - 5} more")
        else:
            # Write the modified content back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            print(f"  ✅ Moved {len(inline_imports)} imports to top")
        
        return True, len(inline_imports)
        
    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False, 0


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
                    config = data.get("tool", {}).get("move_imports_to_top", {})
                    if config:
                        print(f"📋 Loaded config from: {pyproject_path}")
                        return config
                    
                    # Fall back to flask_route_usage config for backend path
                    flask_config = data.get("tool", {}).get("flask_route_usage", {})
                    if flask_config:
                        mapped_config = {
                            "backend_path": flask_config.get("backend", "./"),
                        }
                        print(f"📋 Loaded config from: {pyproject_path} (flask_route_usage)")
                        return mapped_config
            except Exception as e:
                print(f"Warning: Could not load {pyproject_path}: {e}")
                continue

    return None


def parse_arguments():
    """Parse command line arguments with pyproject.toml config support"""
    # Load config from pyproject.toml
    config = load_config_from_pyproject()

    # Set defaults from config or sensible defaults
    default_backend = config.get("backend_path", "./") if config else "./"

    parser = argparse.ArgumentParser(
        description="Move all inline imports from inside functions to the top of Python files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run on current directory
  poetry run move_imports_to_top --dry-run

  # Process specific backend directory
  poetry run move_imports_to_top --backend-path ./backend

  # Live mode (actually modify files)
  poetry run move_imports_to_top

Configuration:
  Settings can be defined in pyproject.toml:

  [tool.move_imports_to_top]
  backend_path = "./backend"
        """,
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )

    parser.add_argument(
        '--backend-path',
        type=str,
        default=default_backend,
        help=f'Path to backend directory (default: {default_backend})'
    )

    parser.add_argument(
        '--pattern',
        type=str,
        default='**/*.py',
        help='File pattern to match (default: **/*.py)'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    # Base paths
    cwd = Path.cwd()
    backend_base = cwd / args.backend_path

    if not backend_base.exists():
        print(f"❌ Backend directory not found: {backend_base}")
        sys.exit(1)

    print(f"🔍 Scanning for Python files in: {backend_base}")
    print(f"🔍 Using pattern: {args.pattern}")
    print(f"🔍 Full search path: {backend_base / args.pattern}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")
    else:
        print("⚠️  LIVE MODE - Files will be modified\n")

    # Find all Python files using the pattern relative to backend_base
    try:
        python_files = list(backend_base.glob(args.pattern))
        print(f"🔍 Found {len(python_files)} files matching pattern")
        
        # Debug: show first few matches
        for i, f in enumerate(python_files[:3]):
            print(f"  🎯 Match {i+1}: {f.relative_to(cwd) if f.is_relative_to(cwd) else f}")
        if len(python_files) > 3:
            print(f"  ... and {len(python_files) - 3} more")
        
    except Exception as e:
        print(f"❌ Error applying glob pattern: {e}")
        python_files = []
    
    if not python_files:
        print(f"❌ No Python files found matching pattern: {args.pattern}")
        print(f"   Search base: {backend_base}")
        print(f"   Full pattern: {backend_base / args.pattern}")
        
        # Try to help debug
        print(f"\n🔍 Debug: Checking if pattern path exists...")
        pattern_dir = backend_base / Path(args.pattern).parent
        if pattern_dir.exists():
            print(f"   ✅ Directory exists: {pattern_dir}")
            files_in_dir = list(pattern_dir.glob("*.py"))
            print(f"   📁 Python files in directory: {len(files_in_dir)}")
            for f in files_in_dir[:3]:
                print(f"      - {f.name}")
        else:
            print(f"   ❌ Directory does not exist: {pattern_dir}")
        return

    total_files_modified = 0
    total_imports_moved = 0

    for py_file in python_files:
        relative_path = py_file.relative_to(backend_base)
        print(f"📝 Processing: {relative_path}")
        
        was_modified, imports_count = process_file(py_file, args.dry_run)
        
        if was_modified:
            total_files_modified += 1
            total_imports_moved += imports_count
        else:
            print(f"  ✅ No inline imports found")

    print(f"\n✨ Done!")
    print(f"📊 Summary:")
    print(f"  - Files processed: {len(python_files)}")
    print(f"  - Files with inline imports: {total_files_modified}")
    print(f"  - Total imports moved: {total_imports_moved}")
    
    if args.dry_run and total_files_modified > 0:
        print(f"\n💡 Run without --dry-run to apply changes")


if __name__ == '__main__':
    main()