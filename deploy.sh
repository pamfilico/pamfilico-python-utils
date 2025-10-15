#!/bin/bash
# deploy.sh - Automated deployment script for pamfilico-python-utils
#
# Usage:
#   ./deploy.sh [OPTIONS]
#
# Options:
#   -m, --message <msg>    Commit message (required if changes exist)
#   -i, --increment <type> Version increment type: patch|minor|major (default: patch)
#   -s, --skip-commit      Skip git commit (only bump version and push)
#   -d, --dry-run          Show what would be done without executing
#   -h, --help             Show this help message
#
# Examples:
#   ./deploy.sh -m "fix: bug fix"                    # Patch bump with message
#   ./deploy.sh -m "feat: new feature" -i minor      # Minor bump with message
#   ./deploy.sh -m "feat!: breaking change" -i major # Major bump with message
#   ./deploy.sh -s -i minor                          # Skip commit, just bump & push
#   ./deploy.sh -d -m "test"                         # Dry run to preview

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
INCREMENT="patch"
COMMIT_MESSAGE=""
SKIP_COMMIT=false
DRY_RUN=false

# Functions
print_usage() {
    cat << EOF
Usage: ./deploy.sh [OPTIONS]

Automated deployment script for pamfilico-python-utils package.
Handles: git commit → version bump → tag → push

Options:
  -m, --message <msg>    Commit message (required if changes exist)
  -i, --increment <type> Version increment: patch|minor|major (default: patch)
  -s, --skip-commit      Skip git commit (only bump version and push)
  -d, --dry-run          Show what would be done without executing
  -h, --help             Show this help message

Examples:
  ./deploy.sh -m "fix: bug fix"
  ./deploy.sh -m "feat: new feature" -i minor
  ./deploy.sh -m "feat!: breaking change" -i major
  ./deploy.sh -s -i minor

Version Increment Types:
  patch - Bug fixes, small changes (0.1.0 → 0.1.1)
  minor - New features, backwards compatible (0.1.0 → 0.2.0)
  major - Breaking changes (0.1.0 → 1.0.0)

EOF
}

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

execute() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN]${NC} $1"
    else
        log_info "Executing: $1"
        eval "$1"
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--message)
            COMMIT_MESSAGE="$2"
            shift 2
            ;;
        -i|--increment)
            INCREMENT="$2"
            if [[ ! "$INCREMENT" =~ ^(patch|minor|major)$ ]]; then
                log_error "Invalid increment type: $INCREMENT. Must be patch, minor, or major."
                exit 1
            fi
            shift 2
            ;;
        -s|--skip-commit)
            SKIP_COMMIT=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Banner
echo "=================================="
echo "  Pamfilico Python Utils Deploy"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    log_error "pyproject.toml not found. Run this script from the package root."
    exit 1
fi

if [ ! -e ".git" ]; then
    log_error "Not a git repository. Initialize git first."
    exit 1
fi

# Check for uncommitted changes
if [ "$SKIP_COMMIT" = false ]; then
    if ! git diff-index --quiet HEAD --; then
        if [ -z "$COMMIT_MESSAGE" ]; then
            log_error "You have uncommitted changes but no commit message provided."
            echo ""
            log_info "Either provide a message with -m or use -s to skip commit:"
            echo "  ./deploy.sh -m \"your commit message\""
            echo "  ./deploy.sh -s  # skip commit, just bump and push"
            exit 1
        fi

        log_info "Uncommitted changes detected:"
        git status --short
        echo ""

        # Stage all changes
        execute "git add -A"

        # Commit with message
        execute "git commit -m \"$COMMIT_MESSAGE\""
        log_success "Changes committed"
    else
        log_info "No uncommitted changes found"
    fi
elif [ "$SKIP_COMMIT" = true ]; then
    log_warning "Skipping commit step as requested"
fi

# Get current version
CURRENT_VERSION=$(grep -m 1 '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
log_info "Current version: $CURRENT_VERSION"

# Bump version using commitizen
log_info "Bumping version ($INCREMENT)..."
if [ "$DRY_RUN" = true ]; then
    log_warning "[DRY RUN] Would run: poetry run cz bump --increment $INCREMENT --yes"
    NEW_VERSION="$CURRENT_VERSION"
else
    poetry run cz bump --increment $INCREMENT --yes
    NEW_VERSION=$(grep -m 1 '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
fi
log_success "Version bumped: $CURRENT_VERSION → $NEW_VERSION"

# Push to remote with tags
log_info "Pushing to remote..."
execute "git push origin master --tags"
log_success "Pushed to GitHub with tags"

# Show final summary
echo ""
echo "=================================="
log_success "Deployment complete!"
echo "=================================="
echo ""
log_info "Summary:"
echo "  • Version: $CURRENT_VERSION → $NEW_VERSION"
echo "  • Tag: v$NEW_VERSION"
echo "  • Branch: master"
echo ""
log_info "To update in backend, run:"
echo "  cd ../backend_carfast"
echo "  poetry update pamfilico-python-utils"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_warning "This was a DRY RUN. No changes were made."
fi
