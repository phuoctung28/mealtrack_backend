#!/bin/bash

# CI Security Scanner
# Runs security checks with bandit and safety

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${PURPLE}[SECURITY]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Track security issues
SECURITY_ISSUES=0

# Install security tools
install_tools() {
    log_info "Installing security tools..."
    python -m pip install --upgrade pip
    pip install bandit safety
    log_success "Security tools installed"
}

# Run bandit security scan
run_bandit() {
    log_info "Running bandit security scan..."

    # Run bandit and capture result
    if bandit -r src -f json -o bandit-report.json; then
        log_success "Bandit: No security issues found"
    else
        log_warn "Bandit: Security issues detected"
        SECURITY_ISSUES=1

        # Parse and display critical issues
        if command -v jq &> /dev/null; then
            echo ""
            jq -r '.results[] | select(.issue_severity == "HIGH") | "  ⚠️ \(.issue_text) in \(.filename):\(.line_number)"' bandit-report.json 2>/dev/null || true
        fi
    fi

    # Also generate text report for viewing
    bandit -r src -f txt -o bandit-report.txt 2>/dev/null || true
}

# Check for vulnerable dependencies
run_safety() {
    log_info "Checking for known vulnerabilities in dependencies..."

    # Run safety check
    if safety check --json > safety-report.json 2>&1; then
        log_success "Safety: No known vulnerabilities found"
    else
        log_warn "Safety: Vulnerable dependencies detected"
        SECURITY_ISSUES=1

        # Display vulnerabilities
        safety check || true
    fi
}

# Generate security report
generate_report() {
    log_info "Generating security report..."

    {
        echo "## 🔒 Security Scan Report"
        echo ""
        echo "### Scans Performed:"
        echo "- **Bandit**: Static security analysis"
        echo "- **Safety**: Dependency vulnerability check"
        echo ""

        if [ $SECURITY_ISSUES -eq 0 ]; then
            echo "### Result: ✅ No security issues found"
        else
            echo "### Result: ⚠️ Security issues detected"
            echo ""
            echo "Please review:"
            echo "- \`bandit-report.json\` for code security issues"
            echo "- \`safety-report.json\` for dependency vulnerabilities"
        fi

        echo ""
        echo "### Recommendations:"
        echo "1. Review and fix any HIGH severity issues immediately"
        echo "2. Update vulnerable dependencies when possible"
        echo "3. Add security exceptions only when necessary with proper justification"
    } > security_report.md

    log_info "Security report saved to security_report.md"
}

# Main execution
main() {
    ACTION="${1:-all}"

    case "$ACTION" in
        install)
            install_tools
            ;;
        bandit)
            run_bandit
            ;;
        safety)
            run_safety
            ;;
        report)
            generate_report
            ;;
        all)
            install_tools
            echo ""
            run_bandit
            echo ""
            run_safety
            echo ""
            generate_report

            if [ $SECURITY_ISSUES -eq 0 ]; then
                log_success "🔒 All security checks passed!"
            else
                log_warn "⚠️ Security issues found (review required)"
            fi
            ;;
        *)
            echo "Usage: $0 {install|bandit|safety|report|all}"
            exit 1
            ;;
    esac

    # Always exit 0 for non-blocking security checks
    exit 0
}

main "$@"