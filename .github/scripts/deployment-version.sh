#!/bin/bash

# Deployment Version Manager
# Handles version generation and storage for deployments

set -e

# Function to generate version
generate_version() {
    local run_number="${1:-0}"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    echo "${run_number}-${timestamp}"
}

# Function to create deployment record
create_deployment_record() {
    local environment="$1"
    local version="$2"
    local image_tag="$3"
    local commit_sha="$4"
    local deployed_by="$5"
    local deployment_type="${6:-manual}"
    local workflow_run_id="${7:-unknown}"
    local workflow_run_number="${8:-0}"

    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local dir=".deployments"

    # Create directory if it doesn't exist
    mkdir -p "$dir"

    # Create deployment JSON
    cat > "${dir}/${environment}-${version}.json" << EOF
{
  "version": "${version}",
  "environment": "${environment}",
  "image_tag": "${image_tag}",
  "commit_sha": "${commit_sha}",
  "deployed_by": "${deployed_by}",
  "deployed_at": "${timestamp}",
  "deployment_type": "${deployment_type}",
  "workflow_run_id": "${workflow_run_id}",
  "workflow_run_number": "${workflow_run_number}"
}
EOF

    # Update latest
    cp "${dir}/${environment}-${version}.json" "${dir}/${environment}-latest.json"

    echo "✅ Deployment record created: ${version}"
}

# Function to get latest deployment
get_latest_deployment() {
    local environment="$1"
    local file=".deployments/${environment}-latest.json"

    if [ -f "$file" ]; then
        cat "$file"
    else
        echo "{}"
    fi
}

# Function to list recent deployments
list_deployments() {
    local environment="$1"
    local limit="${2:-5}"

    echo "Recent deployments for ${environment}:"
    ls -lt .deployments/${environment}-*.json 2>/dev/null | head -n $((limit + 1)) | grep -v latest || echo "No deployments found"
}

# Main execution
ACTION="${1:-generate}"

case $ACTION in
    generate)
        generate_version "$2"
        ;;
    create)
        shift
        create_deployment_record "$@"
        ;;
    latest)
        get_latest_deployment "$2"
        ;;
    list)
        list_deployments "$2" "$3"
        ;;
    *)
        echo "Usage: $0 {generate|create|latest|list} [args...]"
        echo ""
        echo "Commands:"
        echo "  generate [run_number]     - Generate a version string"
        echo "  create [args...]          - Create deployment record"
        echo "  latest [environment]      - Get latest deployment info"
        echo "  list [environment] [limit] - List recent deployments"
        exit 1
        ;;
esac