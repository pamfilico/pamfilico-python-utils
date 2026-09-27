## v0.4.0 (2026-09-27)

### Feat

- improve complexity threshold defaults and interface
- enhance vulture analysis with Flask route awareness
- add python_quality_audit CLI tool for comprehensive code analysis
- add move_imports_to_top CLI tool for organizing Python imports
- add axios instance call detection to fix zero matching issue
- detect wrapper function API calls (get/post/put/delete)

### Fix

- properly handle multi-line imports in insertion logic
- prevent extracting continuation lines of top-level multi-line imports
- finalize multi-line import extraction logic
- improve multi-line import handling with line tracking
- handle multi-line imports in move_imports_to_top tool
- improve pattern matching debug output in move_imports_to_top tool
- add_usage_comments tool now uses flask_route_usage config
- remove hardcoded backend paths from add_usage_comments tool
- handle baseURL prefix mismatch in route matching logic
- remove hardcoded paths from flask_route_usage_report CLI tool
- relax python-jose version constraint for compatibility
- relax python-dotenv version constraint to resolve dependency conflicts

## v0.3.2 (2025-10-15)

### Fix

- replace escaped newlines with actual newlines in markdown report

## v0.3.1 (2025-10-15)

### Fix

- handle axios calls with newline before dot operator

## v0.3.0 (2025-10-15)

### Feat

- add update_route_usage_comments CLI to chain all three tools

## v0.2.2 (2025-10-15)

## v0.2.1 (2025-10-15)

### Fix

- simplify comment placement logic to match root version

## v0.2.0 (2025-10-15)

### Feat

- add remove_route_usage_comments CLI tool

## v0.1.8 (2025-10-15)

### Fix

- ensure comments are ALWAYS placed BEFORE decorators

## v0.1.7 (2025-10-15)

### Feat

- migrate to descriptive ROUTE USAGES TOOL markers and clean all duplicates

## v0.1.6 (2025-10-15)

### Fix

- properly detect and replace existing USAGES TOOL comment blocks

## v0.1.5 (2025-10-15)

### Fix

- ensure empty usage lists generate 'No Usages' message

## v0.1.4 (2025-10-15)

### Fix

- correct comment placement and empty comment block issues

## v0.1.3 (2025-10-15)

## v0.1.2 (2025-10-15)

### Feat

- add automated deployment script

## v0.1.1 (2025-10-15)

### Feat

- add add_usage_comments CLI tool with pyproject.toml config
- add pyproject.toml config support for flask_route_usage_report
- **flask**: add pagination decorator, storage client, and CLI tools
