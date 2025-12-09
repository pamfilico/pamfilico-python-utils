"""Flask Route Usage Analyzer - Core Logic

This module provides the core functionality for analyzing Flask routes
and finding their usage across frontend applications.
"""

import re
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass
from collections import defaultdict


@dataclass(frozen=True)
class RouteInfo:
    """Information about a Flask route"""

    method: str
    path: str
    file_path: str
    line_number: int
    function_name: str
    blueprint_prefix: str = ""

    @property
    def full_path(self) -> str:
        """Get the full route path including blueprint prefix"""
        return f"{self.blueprint_prefix}{self.path}"


@dataclass
class UsageInfo:
    """Information about a route usage in frontend"""

    file_path: str
    line_number: int
    line_content: str


class FlaskRouteAnalyzer:
    """Analyzes Flask routes and their frontend usage"""

    # Regex patterns for route extraction
    ROUTE_PATTERN = re.compile(
        r'@(?P<blueprint>\w+)\.route\(["\'](?P<path>[^"\']+)["\'](?:,\s*methods=\[(?P<methods>[^\]]+)\])?'
    )
    FUNCTION_PATTERN = re.compile(r"def\s+(\w+)\s*\(")

    # Regex patterns for frontend API calls
    AXIOS_PATTERN = re.compile(
        r'axios\.(?P<method>get|post|put|delete|patch)\s*\(\s*[`"\'](?P<url>[^`"\']+)[`"\']'
    )
    FETCH_PATTERN = re.compile(r'fetch\s*\(\s*[`"\'](?P<url>[^`"\']+)[`"\']')

    # Regex patterns for wrapper function calls (from @/actions/*)
    # Matches: get<Type>('/api/...', ...) or get('/api/...', ...)
    WRAPPER_GET_PATTERN = re.compile(
        r'\bget\s*(?:<[^>]+>)?\s*\(\s*[`"\'](?P<url>[^`"\']+)[`"\']'
    )
    WRAPPER_POST_PATTERN = re.compile(
        r'\bpost\s*(?:<[^>]+>)?\s*\(\s*[`"\'](?P<url>[^`"\']+)[`"\']'
    )
    WRAPPER_PUT_PATTERN = re.compile(
        r'\bput\s*(?:<[^>]+>)?\s*\(\s*[`"\'](?P<url>[^`"\']+)[`"\']'
    )
    WRAPPER_DELETE_PATTERN = re.compile(
        r'\bdelete\s*(?:<[^>]+>)?\s*\(\s*[`"\'](?P<url>[^`"\']+)[`"\']'
    )

    # Regex patterns for axios instance calls (e.g., apiClient.get(), client.post())
    # Matches: someIdentifier.get('/api/...', ...) or someIdentifier.post('/api/...', ...)
    AXIOS_INSTANCE_PATTERN = re.compile(
        r'\b\w+\.(?P<method>get|post|put|delete|patch)\s*(?:<[^>]+>)?\s*\(\s*[`"\'](?P<url>[^`"\']+)[`"\']'
    )

    TEMPLATE_VAR_PATTERN = re.compile(r"\$\{[^}]+\}")

    # Known blueprint prefixes
    BLUEPRINT_PREFIXES = {
        "api": "/api/v1",
        "aade_bp": "/api/v1/aade",  # AADE blueprint prefix
    }

    def __init__(
        self,
        backend_root: str,
        frontend_roots: List[str],
        api_subpath: str = "app/api/v1",
        frontend_src_subpath: str = "src",
        verbose: bool = False,
    ):
        self.backend_root = Path(backend_root)
        self.frontend_roots = [Path(root) for root in frontend_roots]
        self.api_subpath = api_subpath
        self.frontend_src_subpath = frontend_src_subpath
        self.verbose = verbose
        self.routes: List[RouteInfo] = []
        self.usages: Dict[str, List[UsageInfo]] = defaultdict(list)

    def extract_routes(self) -> None:
        """Extract all Flask routes from backend API files"""
        api_path = self.backend_root / self.api_subpath

        if not api_path.exists():
            print(f"Warning: API path not found: {api_path}")
            return

        # Process all Python files in API directory
        for py_file in api_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            self._extract_routes_from_file(py_file)

        print(f"Found {len(self.routes)} routes in backend")
        
        if self.verbose and self.routes:
            self._debug_show_sample_routes()

    def _extract_routes_from_file(self, file_path: Path) -> None:
        """Extract routes from a single Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            i = 0
            while i < len(lines):
                line = lines[i]

                # Look for route decorator start - find the FIRST route decorator for a function
                if "@api.route(" in line or "@aade_bp.route(" in line:
                    # Track the line where decorators start (for comment placement)
                    first_decorator_line = i
                    all_routes = []  # Collect all route decorators for this function

                    # Process all consecutive route decorators
                    j = i
                    while j < len(lines):
                        current_line = lines[j]

                        # Check if this is a route decorator
                        if "@api.route(" in current_line or "@aade_bp.route(" in current_line:
                            # Collect the full decorator (might span multiple lines)
                            decorator_lines = [current_line]
                            k = j + 1

                            # If the line doesn't end with a closing paren, collect continuation lines
                            if ")" not in current_line or current_line.rstrip().endswith("("):
                                while k < len(lines):
                                    decorator_lines.append(lines[k])
                                    if ")" in lines[k]:
                                        k += 1
                                        break
                                    k += 1

                            # Join all decorator lines into a single string for regex matching
                            full_decorator = " ".join(l.strip() for l in decorator_lines)

                            # Try to match the full decorator
                            route_match = self.ROUTE_PATTERN.search(full_decorator)
                            if route_match:
                                all_routes.append((route_match, len(decorator_lines)))

                            # Move past this decorator
                            j = k if k > j + 1 else j + 1
                        elif current_line.strip().startswith("@"):
                            # Other decorator (not a route), skip it
                            j += 1
                        else:
                            # Not a decorator - must be the function definition
                            break

                    # Find the function name
                    function_name = "unknown"
                    func_match = self.FUNCTION_PATTERN.search(lines[j] if j < len(lines) else "")
                    if func_match:
                        function_name = func_match.group(1)

                    # Create route info for all routes found
                    for route_match, _ in all_routes:
                        blueprint = route_match.group("blueprint")
                        path = route_match.group("path")
                        methods_str = route_match.group("methods")

                        # Parse methods
                        methods = ["GET"]  # Default method
                        if methods_str:
                            methods = [m.strip(" \"'") for m in methods_str.split(",")]

                        # Get blueprint prefix
                        blueprint_prefix = self.BLUEPRINT_PREFIXES.get(blueprint, "/api/v1")

                        # Create route info for each method - ALL use the FIRST decorator line number
                        for method in methods:
                            route_info = RouteInfo(
                                method=method,
                                path=path,
                                file_path=str(file_path.relative_to(self.backend_root)),
                                line_number=first_decorator_line + 1,  # All routes use first line
                                function_name=function_name,
                                blueprint_prefix=blueprint_prefix,
                            )
                            self.routes.append(route_info)

                    # Skip past this entire function definition (all decorators + function line)
                    i = j + 1
                    continue

                i += 1

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def extract_frontend_usages(self) -> None:
        """Extract API calls from frontend files"""
        for frontend_root in self.frontend_roots:
            if not frontend_root.exists():
                print(f"Warning: Frontend path not found: {frontend_root}")
                continue

            src_path = frontend_root / self.frontend_src_subpath
            if not src_path.exists():
                print(f"Warning: Source path not found: {src_path}")
                continue

            # Process TypeScript/JavaScript files
            for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
                for file_path in src_path.rglob(ext):
                    self._extract_usages_from_file(file_path, frontend_root)

        print(f"Found {sum(len(v) for v in self.usages.values())} frontend API calls")
        
        if self.verbose and self.usages:
            self._debug_show_sample_usages()

    def _extract_usages_from_file(self, file_path: Path, frontend_root: Path) -> None:
        """Extract API calls from a single frontend file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # Try to find multi-line axios/fetch calls
            # Pattern for axios.method( followed by URL on next lines
            # Handles: axios.get(), axios\n.get(), axios.get(\nurl), axios\n.get(\nurl)
            multiline_axios_pattern = re.compile(
                r'axios\s*\n?\s*\.(?P<method>get|post|put|delete|patch)\s*\(\s*\n?\s*[`"\'](?P<url>[^`"\']+)[`"\']',
                re.MULTILINE,
            )
            multiline_fetch_pattern = re.compile(
                r'fetch\s*\(\s*\n?\s*[`"\'](?P<url>[^`"\']+)[`"\']', re.MULTILINE
            )

            # Find all multi-line axios matches
            for match in multiline_axios_pattern.finditer(content):
                url = match.group("url")
                method = match.group("method").upper()

                # Find line number
                line_num = content[: match.start()].count("\n") + 1

                usage = UsageInfo(
                    file_path=str(file_path.relative_to(frontend_root.parent)),
                    line_number=line_num,
                    line_content=(
                        lines[line_num - 1].strip() if line_num <= len(lines) else ""
                    ),
                )

                key = f"{method} {url}"
                self.usages[key].append(usage)

            # Find all multi-line fetch matches
            for match in multiline_fetch_pattern.finditer(content):
                url = match.group("url")

                # Find line number
                line_num = content[: match.start()].count("\n") + 1

                # Try to determine method (look for method: in nearby content)
                method = "GET"
                context_start = max(0, match.start() - 200)
                context_end = min(len(content), match.end() + 200)
                context = content[context_start:context_end]

                if re.search(r'method\s*:\s*["\']POST["\']', context, re.IGNORECASE):
                    method = "POST"
                elif re.search(r'method\s*:\s*["\']PUT["\']', context, re.IGNORECASE):
                    method = "PUT"
                elif re.search(
                    r'method\s*:\s*["\']DELETE["\']', context, re.IGNORECASE
                ):
                    method = "DELETE"
                elif re.search(r'method\s*:\s*["\']PATCH["\']', context, re.IGNORECASE):
                    method = "PATCH"

                usage = UsageInfo(
                    file_path=str(file_path.relative_to(frontend_root.parent)),
                    line_number=line_num,
                    line_content=(
                        lines[line_num - 1].strip() if line_num <= len(lines) else ""
                    ),
                )

                key = f"{method} {url}"
                self.usages[key].append(usage)

            # Find wrapper function calls (get, post, put, delete from @/actions/*)
            # These are TypeScript wrapper functions that internally call axios
            wrapper_patterns = [
                (self.WRAPPER_GET_PATTERN, "GET"),
                (self.WRAPPER_POST_PATTERN, "POST"),
                (self.WRAPPER_PUT_PATTERN, "PUT"),
                (self.WRAPPER_DELETE_PATTERN, "DELETE"),
            ]

            for pattern, method in wrapper_patterns:
                for match in pattern.finditer(content):
                    url = match.group("url")

                    # Find line number
                    line_num = content[: match.start()].count("\n") + 1

                    usage = UsageInfo(
                        file_path=str(file_path.relative_to(frontend_root.parent)),
                        line_number=line_num,
                        line_content=(
                            lines[line_num - 1].strip() if line_num <= len(lines) else ""
                        ),
                    )

                    key = f"{method} {url}"
                    self.usages[key].append(usage)

            # Find axios instance calls (e.g., apiClient.get(), aiServiceClient.post())
            # These are axios instance method calls that are very common in modern projects
            for match in self.AXIOS_INSTANCE_PATTERN.finditer(content):
                url = match.group("url")
                method = match.group("method").upper()

                # Find line number
                line_num = content[: match.start()].count("\n") + 1

                usage = UsageInfo(
                    file_path=str(file_path.relative_to(frontend_root.parent)),
                    line_number=line_num,
                    line_content=(
                        lines[line_num - 1].strip() if line_num <= len(lines) else ""
                    ),
                )

                key = f"{method} {url}"
                self.usages[key].append(usage)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def match_routes_to_usages(self) -> Dict[RouteInfo, List[UsageInfo]]:
        """Match Flask routes to their frontend usages"""
        matched: Dict[RouteInfo, List[UsageInfo]] = {}

        for route in self.routes:
            route_usages = []
            route_key = f"{route.method} {route.full_path}"

            # Try exact match first
            if route_key in self.usages:
                route_usages.extend(self.usages[route_key])

            # Try fuzzy matching for dynamic routes
            for usage_key, usages in self.usages.items():
                if self._routes_match(route, usage_key):
                    # Avoid duplicates
                    for usage in usages:
                        if usage not in route_usages:
                            route_usages.append(usage)

            matched[route] = route_usages

        return matched

    def _routes_match(self, route: RouteInfo, usage_key: str) -> bool:
        """Check if a route matches a usage key using fuzzy matching"""
        # Parse usage key
        parts = usage_key.split(" ", 1)
        if len(parts) != 2:
            return False

        usage_method, usage_path = parts

        # Check method
        if route.method != usage_method:
            return False

        # Exact match
        if route.full_path == usage_path:
            return True

        # Remove BACKEND_DOMAIN/BACKEND_URL variables from usage path
        usage_path_clean = re.sub(r"\$\{BACKEND[^}]*\}/?", "", usage_path)
        usage_path_clean = re.sub(r"\$\{[^}]*DOMAIN[^}]*\}/?", "", usage_path_clean)
        usage_path_clean = re.sub(r"\$\{[^}]*URL[^}]*\}/?", "", usage_path_clean)

        # Check if cleaned path matches route
        if route.full_path == usage_path_clean:
            return True

        # Segment-by-segment matching with dynamic parameters
        route_segments = [s for s in route.full_path.split("/") if s]
        usage_segments = [s for s in usage_path_clean.split("/") if s]

        if len(route_segments) != len(usage_segments):
            return False

        for route_seg, usage_seg in zip(route_segments, usage_segments):
            # Flask dynamic parameter pattern: <type:name> or <name>
            if route_seg.startswith("<") and route_seg.endswith(">"):
                # Dynamic segment - check if usage has template variable or dynamic content
                if "${" in usage_seg or "{" in usage_seg:
                    # Has template variable, counts as match
                    continue
                # Allow any non-empty segment as dynamic match (literal values)
                if usage_seg:
                    continue
                return False
            else:
                # Static segment - must match exactly
                if route_seg != usage_seg:
                    return False

        return True

    def _debug_show_sample_routes(self) -> None:
        """Show sample routes found for debugging"""
        print("\n📋 Debug: Sample backend routes found:")
        # Group by method and show a few examples
        by_method = defaultdict(list)
        for route in self.routes:
            by_method[route.method].append(route)
        
        for method in sorted(by_method.keys()):
            routes = by_method[method][:3]  # Show first 3 of each method
            print(f"   {method}: {len(by_method[method])} routes")
            for route in routes:
                print(f"     {route.full_path} ({route.file_path}:{route.line_number})")
            if len(by_method[method]) > 3:
                print(f"     ... and {len(by_method[method]) - 3} more")

    def _debug_show_sample_usages(self) -> None:
        """Show sample frontend usages found for debugging"""
        print("\n📋 Debug: Sample frontend API calls found:")
        # Show first few usage keys
        usage_keys = list(self.usages.keys())[:10]  # Show first 10
        for key in usage_keys:
            usages = self.usages[key]
            print(f"   {key} ({len(usages)} call{'s' if len(usages) != 1 else ''})")
            for usage in usages[:2]:  # Show first 2 locations
                print(f"     {usage.file_path}:{usage.line_number}")
            if len(usages) > 2:
                print(f"     ... and {len(usages) - 2} more")
        
        if len(self.usages) > 10:
            print(f"   ... and {len(self.usages) - 10} more unique API calls")

    def generate_split_reports(self) -> None:
        """Generate two separate markdown reports: routes with usage and routes without usage"""
        matched = self.match_routes_to_usages()

        # Separate routes into used and unused
        routes_with_usage_list = [
            (r, usages) for r, usages in matched.items() if usages
        ]
        routes_without_usage_list = [
            (r, usages) for r, usages in matched.items() if not usages
        ]

        # Generate report for routes WITH usage
        self._generate_used_routes_report(routes_with_usage_list, matched)

        # Generate report for routes WITHOUT usage
        self._generate_unused_routes_report(routes_without_usage_list)

        # Print summary
        print(f"\n✅ Reports generated:")
        print(f"   📄 flask_routes_with_usage.md")
        print(f"      - {len(routes_with_usage_list)} routes with usage")
        print(
            f"      - {sum(len(usages) for _, usages in routes_with_usage_list)} total frontend calls"
        )
        print(f"\n   📄 flask_routes_without_usage.md")
        print(f"      - {len(routes_without_usage_list)} routes without usage")

    def _generate_used_routes_report(
        self,
        routes_with_usage: List[tuple],
        all_matched: Dict,
    ) -> None:
        """Generate report for routes that have frontend usage"""
        output_file = "flask_routes_with_usage.md"

        # Sort routes by method and path
        sorted_routes = sorted(
            routes_with_usage, key=lambda x: (x[0].method, x[0].full_path)
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Flask Routes WITH Frontend Usage\n\n")
            f.write(f"**Total Routes with Usage:** {len(routes_with_usage)}\n\n")
            f.write(
                f"**Total Frontend Calls:** {sum(len(usages) for _, usages in routes_with_usage)}\n\n"
            )
            f.write("---\n\n")

            # Group by method for easier navigation
            by_method = defaultdict(list)
            for route, usages in sorted_routes:
                by_method[route.method].append((route, usages))

            # Table of contents
            f.write("## Table of Contents\n\n")
            for method in sorted(by_method.keys()):
                count = len(by_method[method])
                f.write(f"- [{method} Routes ({count})](#-{method.lower()}-routes-)\n")
            f.write("\n---\n\n")

            # Routes by method
            for method in sorted(by_method.keys()):
                f.write(f"## {method} Routes\n\n")

                routes_list = by_method[method]
                for route, usages in routes_list:
                    f.write(f"### {method} `{route.full_path}`\n\n")
                    f.write(
                        f"**Backend Location:** `{route.file_path}:{route.line_number}`\n\n"
                    )
                    f.write(f"**Function:** `{route.function_name}()`\n\n")
                    f.write(
                        f"**Frontend Usage:** ({len(usages)} location{'s' if len(usages) != 1 else ''})\n\n"
                    )

                    for usage in usages:
                        f.write(f"- `{usage.file_path}:{usage.line_number}`\n")
                        # Show a snippet of the line
                        snippet = usage.line_content[:100]
                        if len(usage.line_content) > 100:
                            snippet += "..."
                        f.write(f"  ```typescript\n  {snippet}\n  ```\n")

                    f.write("\n---\n\n")

            f.write("*Report generated by pamfilico-python-utils flask_route_usage_report*\n")

    def _generate_unused_routes_report(
        self, routes_without_usage: List[tuple]
    ) -> None:
        """Generate report for routes that have no frontend usage"""
        output_file = "flask_routes_without_usage.md"

        # Sort routes by method and path
        sorted_routes = sorted(
            routes_without_usage, key=lambda x: (x[0].method, x[0].full_path)
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Flask Routes WITHOUT Frontend Usage\n\n")
            f.write(f"**Total Unused Routes:** {len(routes_without_usage)}\n\n")
            f.write("Routes that have no detected frontend usage. These may be:\n")
            f.write("- Dead code that can be removed\n")
            f.write("- Internal/admin endpoints not used in these frontends\n")
            f.write("- Routes used by external clients (mobile apps, integrations)\n")
            f.write("- Future/upcoming features not yet implemented\n\n")
            f.write("---\n\n")

            # Group by method
            by_method = defaultdict(list)
            for route, _ in sorted_routes:
                by_method[route.method].append(route)

            # Table of contents
            f.write("## Table of Contents\n\n")
            for method in sorted(by_method.keys()):
                count = len(by_method[method])
                f.write(f"- [{method} Routes ({count})](#-{method.lower()}-routes-)\n")
            f.write("\n---\n\n")

            # Routes by method
            for method in sorted(by_method.keys()):
                f.write(f"## {method} Routes\n\n")

                routes_list = by_method[method]
                for route in routes_list:
                    f.write(f"### {method} `{route.full_path}`\n\n")
                    f.write(
                        f"**Backend Location:** `{route.file_path}:{route.line_number}`\n\n"
                    )
                    f.write(f"**Function:** `{route.function_name}()`\n\n")
                    f.write("---\n\n")

            f.write("*Report generated by pamfilico-python-utils flask_route_usage_report*\n")
