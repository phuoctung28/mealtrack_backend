#!/bin/bash

# CI Linting Script
# Runs code quality checks (ruff, black, isort, mypy)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[LINT]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Track overall status
LINT_FAILED=0

# Install linting tools
install_tools() {
    log_info "Installing linting tools..."
    python -m pip install --upgrade pip
    pip install ruff black isort mypy
    log_success "Linting tools installed"
}

# Run ruff
run_ruff() {
    log_info "Running ruff..."
    if ruff check src tests; then
        log_success "Ruff: No issues found"
    else
        log_warn "Ruff: Issues detected"
        LINT_FAILED=1
    fi
}

# Run black
run_black() {
    log_info "Running black formatter check..."
    if black --check src tests; then
        log_success "Black: Code is properly formatted"
    else
        log_warn "Black: Code needs formatting"
        log_info "  Run 'black src tests' to fix"
        LINT_FAILED=1
    fi
}

# Run isort
run_isort() {
    log_info "Running isort import checker..."
    if isort --check-only src tests; then
        log_success "Isort: Imports are properly sorted"
    else
        log_warn "Isort: Imports need sorting"
        log_info "  Run 'isort src tests' to fix"
        LINT_FAILED=1
    fi
}

# Run mypy
run_mypy() {
    log_info "Running mypy type checker..."
    if mypy src --ignore-missing-imports; then
        log_success "Mypy: No type issues found"
    else
        log_warn "Mypy: Type issues detected"
        LINT_FAILED=1
    fi
}

# Generate lint report
generate_report() {
    log_info "Generating lint report..."

    {
        echo "## 🔍 Code Quality Report"
        echo ""
        echo "### Tools Run:"
        echo "- ✅ Ruff (linter)"
        echo "- ✅ Black (formatter)"
        echo "- ✅ Isort (import sorter)"
        echo "- ✅ Mypy (type checker)"
        echo ""

        if [ $LINT_FAILED -eq 0 ]; then
            echo "### Result: ✅ All checks passed"
        else
            echo "### Result: ⚠️ Some checks failed (non-blocking)"
            echo ""
            echo "Run these commands to fix:"
            echo '```bash'
            echo "black src tests"
            echo "isort src tests"
            echo '```'
        fi
    } > lint_report.md

    log_info "Lint report saved to lint_report.md"
}

# Main execution
main() {
    ACTION="${1:-all}"

    case "$ACTION" in
        install)
            install_tools
            ;;
        ruff)
            run_ruff
            ;;
        black)
            run_black
            ;;
        isort)
            run_isort
            ;;
        mypy)
            run_mypy
            ;;
        all)
            install_tools
            echo ""
            run_ruff
            echo ""
            run_black
            echo ""
            run_isort
            echo ""
            run_mypy
            echo ""
            generate_report

            if [ $LINT_FAILED -eq 0 ]; then
                log_success "🎉 All linting checks passed!"
            else
                log_warn "⚠️ Some linting checks failed (non-blocking)"
            fi
            ;;
        *)
            echo "Usage: $0 {install|ruff|black|isort|mypy|all}"
            exit 1
            ;;
    esac

    # Return non-zero if any check failed (for CI)
    exit $LINT_FAILED
}

main "$@"