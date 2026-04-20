#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TRUNCATE_ONLY=false
AUTO_YES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --truncate-only) TRUNCATE_ONLY=true; shift ;;
        -y|--yes)        AUTO_YES=true;       shift ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--truncate-only] [-y|--yes]"
            exit 1
            ;;
    esac
done

if [ "$TRUNCATE_ONLY" = true ]; then
    echo -e "${YELLOW}MealTrack Database Cleanup (Truncate Only)${NC}"
else
    echo -e "${YELLOW}MealTrack Database Cleanup (Drop & Recreate)${NC}"
fi
echo "========================================"

# Load DATABASE_URL from .env if not already set
if [ -z "$DATABASE_URL" ]; then
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | grep DATABASE_URL | xargs)
    fi
fi

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}ERROR: DATABASE_URL is not set. Add it to .env${NC}"
    exit 1
fi

# Confirm
if [ "$AUTO_YES" = false ]; then
    if [ "$TRUNCATE_ONLY" = true ]; then
        echo -e "${RED}WARNING: This will DELETE ALL DATA from the Neon database!${NC}"
    else
        echo -e "${RED}WARNING: This will DROP AND RECREATE ALL TABLES in Neon!${NC}"
    fi
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo -e "${RED}Cancelled${NC}"
        exit 0
    fi
fi

echo -e "${YELLOW}Running database cleanup...${NC}"
if [ "$TRUNCATE_ONLY" = true ]; then
    .venv/bin/python scripts/cleanup_db.py --yes --truncate-only
else
    .venv/bin/python scripts/cleanup_db.py --yes
fi

echo -e "${GREEN}Done!${NC}"
