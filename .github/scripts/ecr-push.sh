#!/bin/bash
set -e

# ECR Docker Build and Push Script
# Builds Docker image and pushes directly to AWS ECR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
ECR_REPOSITORY="${ECR_REPOSITORY:-mealtrack-backend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"
BUILD_CONTEXT="${BUILD_CONTEXT:-.}"

# Additional tags
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
VERSION_TAG="${VERSION_TAG:-$GIT_COMMIT}"

# ECR URI
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

print_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi

    # Check AWS credentials
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        print_error "AWS credentials not configured. Please run: aws configure"
        exit 1
    fi

    print_status "✅ Prerequisites checked"
    print_info "AWS Account: $AWS_ACCOUNT_ID"
    print_info "Region: $AWS_REGION"
    print_info "ECR Repository: $ECR_REPOSITORY"
}

# Create ECR repository if it doesn't exist
create_ecr_repository() {
    print_status "Checking ECR repository..."

    if aws ecr describe-repositories \
        --repository-names $ECR_REPOSITORY \
        --region $AWS_REGION &>/dev/null; then
        print_status "ECR repository exists"
    else
        print_status "Creating ECR repository..."
        aws ecr create-repository \
            --repository-name $ECR_REPOSITORY \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true \
            --image-tag-mutability MUTABLE

        # Set lifecycle policy
        cat > /tmp/lifecycle-policy.json <<EOF
{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Keep last 10 images",
            "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 10
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
EOF
        aws ecr put-lifecycle-policy \
            --repository-name $ECR_REPOSITORY \
            --lifecycle-policy-text file:///tmp/lifecycle-policy.json \
            --region $AWS_REGION

        print_status "✅ ECR repository created"
    fi
}

# Login to ECR
ecr_login() {
    print_status "Logging in to ECR..."

    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $ECR_URI

    if [ $? -eq 0 ]; then
        print_status "✅ Successfully logged in to ECR"
    else
        print_error "Failed to login to ECR"
        exit 1
    fi
}

# Build Docker image
build_image() {
    print_status "Building Docker image..."
    print_info "Dockerfile: $DOCKERFILE"
    print_info "Context: $BUILD_CONTEXT"

    # Build with multiple tags
    docker build \
        -f $DOCKERFILE \
        -t ${ECR_URI}:${IMAGE_TAG} \
        -t ${ECR_URI}:${VERSION_TAG} \
        -t ${ECR_URI}:${TIMESTAMP} \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VERSION="${VERSION_TAG}" \
        --build-arg VCS_REF="${GIT_COMMIT}" \
        $BUILD_CONTEXT

    if [ $? -eq 0 ]; then
        print_status "✅ Docker image built successfully"

        # Show image size
        IMAGE_SIZE=$(docker image inspect ${ECR_URI}:${IMAGE_TAG} --format='{{.Size}}' | numfmt --to=iec-i)
        print_info "Image size: $IMAGE_SIZE"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Push image to ECR
push_image() {
    print_status "Pushing image to ECR..."

    # Push all tags
    for TAG in ${IMAGE_TAG} ${VERSION_TAG} ${TIMESTAMP}; do
        print_info "Pushing tag: $TAG"
        docker push ${ECR_URI}:${TAG}

        if [ $? -ne 0 ]; then
            print_error "Failed to push image with tag: $TAG"
            exit 1
        fi
    done

    print_status "✅ Image pushed successfully to ECR"
}

# Scan image for vulnerabilities
scan_image() {
    print_status "Initiating vulnerability scan..."

    aws ecr start-image-scan \
        --repository-name $ECR_REPOSITORY \
        --image-id imageTag=${IMAGE_TAG} \
        --region $AWS_REGION

    print_status "✅ Vulnerability scan initiated"
    print_info "Check scan results with:"
    print_info "aws ecr describe-image-scan-findings --repository-name $ECR_REPOSITORY --image-id imageTag=${IMAGE_TAG}"
}

# Clean up local images
cleanup() {
    print_status "Cleaning up local images..."

    docker rmi ${ECR_URI}:${IMAGE_TAG} 2>/dev/null || true
    docker rmi ${ECR_URI}:${VERSION_TAG} 2>/dev/null || true
    docker rmi ${ECR_URI}:${TIMESTAMP} 2>/dev/null || true

    print_status "✅ Cleanup complete"
}

# Output summary
show_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 ECR Push Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Repository: ${ECR_URI}"
    echo "Tags pushed:"
    echo "  • ${IMAGE_TAG}"
    echo "  • ${VERSION_TAG}"
    echo "  • ${TIMESTAMP}"
    echo ""
    echo "Pull commands:"
    echo "  docker pull ${ECR_URI}:${IMAGE_TAG}"
    echo "  docker pull ${ECR_URI}:${VERSION_TAG}"
    echo "  docker pull ${ECR_URI}:${TIMESTAMP}"
    echo ""
    echo "Use in ECS task definition:"
    echo "  \"image\": \"${ECR_URI}:${IMAGE_TAG}\""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Output for GitHub Actions
    if [ -n "$GITHUB_OUTPUT" ]; then
        echo "ecr_uri=${ECR_URI}" >> $GITHUB_OUTPUT
        echo "image_tag=${IMAGE_TAG}" >> $GITHUB_OUTPUT
        echo "version_tag=${VERSION_TAG}" >> $GITHUB_OUTPUT
        echo "timestamp_tag=${TIMESTAMP}" >> $GITHUB_OUTPUT
    fi
}

# Main execution
main() {
    print_status "🚀 Starting ECR build and push process"

    check_prerequisites
    create_ecr_repository
    ecr_login
    build_image
    push_image
    scan_image
    cleanup
    show_summary

    print_status "🎉 ECR push completed successfully!"
}

# Run main function
main