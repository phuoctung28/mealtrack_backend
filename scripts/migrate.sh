#!/bin/bash
#
# Helper script for database migrations
# Run this after making changes to your SQLAlchemy models
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_ALEMBIC="$PROJECT_ROOT/.venv/bin/alembic"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

function print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Change to project root
cd "$PROJECT_ROOT"

case "${1:-}" in
    "check")
        print_header "Checking Migration Status"
        
        # Check current migration
        echo -e "${BLUE}Current database revision:${NC}"
        $VENV_ALEMBIC current
        
        echo ""
        echo -e "${BLUE}Latest available revision:${NC}"
        $VENV_ALEMBIC heads
        
        # Check if migrations are needed
        echo ""
        echo -e "${BLUE}Checking for model changes:${NC}"
        $VENV_ALEMBIC check 2>/dev/null && echo "✅ No changes needed" || echo "⚠️  Model changes detected - generate a migration"
        ;;
        
    "generate")
        print_header "Generating New Migration"
        
        # Get migration message
        if [ -z "${2:-}" ]; then
            read -p "Enter migration description: " message
        else
            message="$2"
        fi
        
        if [ -z "$message" ]; then
            print_error "Migration message is required!"
            exit 1
        fi
        
        # Generate migration
        print_info "Generating migration: $message"
        $VENV_ALEMBIC revision --autogenerate -m "$message"
        
        if [ $? -eq 0 ]; then
            print_success "Migration generated successfully!"
            
            # Find the latest migration file
            latest_migration=$(ls -t migrations/versions/*.py | head -n 1)
            
            echo ""
            print_warning "Please review the generated migration:"
            echo "   $latest_migration"
            echo ""
            print_info "Next steps:"
            echo "   1. Review the migration file for correctness"
            echo "   2. Test locally: ./scripts/migrate.sh upgrade"
            echo "   3. Commit both model changes and migration"
        else
            print_error "Failed to generate migration"
            exit 1
        fi
        ;;
        
    "upgrade")
        print_header "Applying Migrations"
        
        # Apply migrations to head
        print_info "Upgrading database to latest revision..."
        $VENV_ALEMBIC upgrade head
        
        if [ $? -eq 0 ]; then
            print_success "Database upgraded successfully!"
            $VENV_ALEMBIC current
        else
            print_error "Failed to upgrade database"
            exit 1
        fi
        ;;
        
    "downgrade")
        print_header "Downgrading Database"
        
        target="${2:--1}"
        print_warning "Downgrading database to: $target"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            $VENV_ALEMBIC downgrade "$target"
            
            if [ $? -eq 0 ]; then
                print_success "Database downgraded successfully!"
                $VENV_ALEMBIC current
            else
                print_error "Failed to downgrade database"
                exit 1
            fi
        else
            print_info "Downgrade cancelled"
        fi
        ;;
        
    "history")
        print_header "Migration History"
        $VENV_ALEMBIC history --verbose
        ;;
        
    *)
        print_header "Database Migration Helper"
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  check                    Check current migration status and model changes"
        echo "  generate <message>       Generate a new migration with the given message"
        echo "  upgrade                  Apply all pending migrations"
        echo "  downgrade [target]       Downgrade to a specific revision (default: -1)"
        echo "  history                  Show migration history"
        echo ""
        echo "Examples:"
        echo "  $0 check"
        echo "  $0 generate \"Add user preferences table\""
        echo "  $0 upgrade"
        echo "  $0 downgrade -1"
        echo ""
        echo "Workflow:"
        echo "  1. Make changes to your SQLAlchemy models"
        echo "  2. Run: $0 check"
        echo "  3. Run: $0 generate \"describe your changes\""
        echo "  4. Review the generated migration file"
        echo "  5. Run: $0 upgrade (to test locally)"
        echo "  6. Commit both model changes and migration file"
        ;;
esac