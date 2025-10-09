#!/bin/bash
set -e

# ECS Deployment Script using ECR Images
# Deploys containers from ECR to ECS with Fargate Spot

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
ECS_CLUSTER="${ECS_CLUSTER:-mealtrack-cluster}"
ECS_SERVICE="${ECS_SERVICE:-mealtrack-api}"
ECS_TASK_FAMILY="${ECS_TASK_FAMILY:-mealtrack-backend}"
ECR_REPOSITORY="${ECR_REPOSITORY:-mealtrack-backend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
USE_SPOT="${USE_FARGATE_SPOT:-true}"

# Load configuration if exists
if [ -f "aws-resources.json" ]; then
    print_info "Loading AWS resources configuration..."
    VPC_ID=$(jq -r '.vpc.vpc_id' aws-resources.json)
    PUBLIC_SUBNET_1=$(jq -r '.vpc.public_subnet_1' aws-resources.json)
    PUBLIC_SUBNET_2=$(jq -r '.vpc.public_subnet_2' aws-resources.json)
    ECS_SG=$(jq -r '.security_groups.ecs_sg' aws-resources.json)
    RDS_ENDPOINT=$(jq -r '.rds.endpoint' aws-resources.json)
    RDS_USERNAME=$(jq -r '.rds.username' aws-resources.json)
    RDS_DB_NAME=$(jq -r '.rds.database' aws-resources.json)
    RDS_PASSWORD_SECRET=$(jq -r '.rds.password_secret' aws-resources.json)
    EXECUTION_ROLE=$(jq -r '.ecs.execution_role' aws-resources.json)
fi

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

    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi

    if [ -z "$AWS_ACCOUNT_ID" ]; then
        print_error "AWS credentials not configured"
        exit 1
    fi

    # Check if image exists in ECR
    if ! aws ecr describe-images \
        --repository-name $ECR_REPOSITORY \
        --image-ids imageTag=$IMAGE_TAG \
        --region $AWS_REGION &>/dev/null; then
        print_error "Image not found in ECR: ${ECR_URI}:${IMAGE_TAG}"
        print_info "Please build and push the image first using ecr-push.sh"
        exit 1
    fi

    print_status "✅ Prerequisites checked"
}

# Register task definition
register_task_definition() {
    print_status "Registering ECS task definition..."

    # Get RDS password from Secrets Manager
    RDS_SECRET_ARN="arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:${RDS_PASSWORD_SECRET}"

    # Create task definition
    cat > /tmp/task-definition.json <<EOF
{
  "family": "${ECS_TASK_FAMILY}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "${EXECUTION_ROLE:-arn:aws:iam::${AWS_ACCOUNT_ID}:role/mealtrack-ecs-execution-role}",
  "containerDefinitions": [
    {
      "name": "mealtrack-api",
      "image": "${ECR_URI}:${IMAGE_TAG}",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "PORT",
          "value": "8000"
        },
        {
          "name": "DB_HOST",
          "value": "${RDS_ENDPOINT}"
        },
        {
          "name": "DB_PORT",
          "value": "5432"
        },
        {
          "name": "DB_NAME",
          "value": "${RDS_DB_NAME}"
        },
        {
          "name": "DB_USER",
          "value": "${RDS_USERNAME}"
        },
        {
          "name": "DEPLOYMENT_VERSION",
          "value": "${IMAGE_TAG}"
        },
        {
          "name": "DEPLOYED_AT",
          "value": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")"
        }
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "${RDS_SECRET_ARN}"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mealtrack",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

    # Register the task definition
    TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
        --cli-input-json file:///tmp/task-definition.json \
        --region $AWS_REGION \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)

    print_status "✅ Task definition registered"
}

# Create or update ECS service
deploy_service() {
    print_status "Deploying ECS service..."

    # Check if service exists
    if aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --region $AWS_REGION 2>/dev/null | grep -q ACTIVE; then

        print_status "Updating existing service..."
        aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --task-definition $ECS_TASK_FAMILY \
            --force-new-deployment \
            --region $AWS_REGION \
            --output json > /dev/null

        print_status "✅ Service updated"

    else
        print_status "Creating new service..."

        # Create service configuration
        cat > /tmp/create-service.json <<EOF
{
  "cluster": "${ECS_CLUSTER}",
  "serviceName": "${ECS_SERVICE}",
  "taskDefinition": "${ECS_TASK_FAMILY}",
  "desiredCount": 1,
  "launchType": "FARGATE",
  "capacityProviderStrategy": [
    {
      "capacityProvider": "$([ "$USE_SPOT" = "true" ] && echo "FARGATE_SPOT" || echo "FARGATE")",
      "weight": 100,
      "base": 0
    }
  ],
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["${PUBLIC_SUBNET_1}", "${PUBLIC_SUBNET_2}"],
      "securityGroups": ["${ECS_SG}"],
      "assignPublicIp": "ENABLED"
    }
  },
  "healthCheckGracePeriodSeconds": 60,
  "enableECSManagedTags": true,
  "propagateTags": "TASK_DEFINITION"
}
EOF

        aws ecs create-service \
            --cli-input-json file:///tmp/create-service.json \
            --region $AWS_REGION \
            --output json > /dev/null

        print_status "✅ Service created"
    fi
}

# Setup auto-scaling
setup_autoscaling() {
    print_status "Setting up auto-scaling..."

    # Register scalable target
    aws application-autoscaling register-scalable-target \
        --service-namespace ecs \
        --resource-id "service/${ECS_CLUSTER}/${ECS_SERVICE}" \
        --scalable-dimension ecs:service:DesiredCount \
        --min-capacity 0 \
        --max-capacity 3 \
        --region $AWS_REGION 2>/dev/null || true

    # Create CPU-based scaling policy
    aws application-autoscaling put-scaling-policy \
        --policy-name cpu-scaling \
        --service-namespace ecs \
        --resource-id "service/${ECS_CLUSTER}/${ECS_SERVICE}" \
        --scalable-dimension ecs:service:DesiredCount \
        --policy-type TargetTrackingScaling \
        --target-tracking-scaling-policy-configuration '{
            "targetValue": 60.0,
            "predefinedMetricSpecification": {
                "predefinedMetricType": "ECSServiceAverageCPUUtilization"
            },
            "scaleInCooldown": 300,
            "scaleOutCooldown": 60
        }' \
        --region $AWS_REGION 2>/dev/null || true

    # Create memory-based scaling policy
    aws application-autoscaling put-scaling-policy \
        --policy-name memory-scaling \
        --service-namespace ecs \
        --resource-id "service/${ECS_CLUSTER}/${ECS_SERVICE}" \
        --scalable-dimension ecs:service:DesiredCount \
        --policy-type TargetTrackingScaling \
        --target-tracking-scaling-policy-configuration '{
            "targetValue": 70.0,
            "predefinedMetricSpecification": {
                "predefinedMetricType": "ECSServiceAverageMemoryUtilization"
            },
            "scaleInCooldown": 300,
            "scaleOutCooldown": 60
        }' \
        --region $AWS_REGION 2>/dev/null || true

    print_status "✅ Auto-scaling configured"
}

# Wait for deployment
wait_for_deployment() {
    print_status "Waiting for deployment to stabilize..."

    aws ecs wait services-stable \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --region $AWS_REGION

    print_status "✅ Deployment stabilized"
}

# Get service details
get_service_details() {
    print_status "Getting service details..."

    # Get task ARN
    TASK_ARN=$(aws ecs list-tasks \
        --cluster $ECS_CLUSTER \
        --service-name $ECS_SERVICE \
        --region $AWS_REGION \
        --query 'taskArns[0]' \
        --output text)

    if [ "$TASK_ARN" != "None" ] && [ ! -z "$TASK_ARN" ]; then
        # Get task details
        TASK_DETAILS=$(aws ecs describe-tasks \
            --cluster $ECS_CLUSTER \
            --tasks $TASK_ARN \
            --region $AWS_REGION)

        # Extract public IP
        ENI_ID=$(echo $TASK_DETAILS | jq -r '.tasks[0].attachments[0].details[] | select(.name=="networkInterfaceId") | .value')

        if [ ! -z "$ENI_ID" ] && [ "$ENI_ID" != "null" ]; then
            PUBLIC_IP=$(aws ec2 describe-network-interfaces \
                --network-interface-ids $ENI_ID \
                --region $AWS_REGION \
                --query 'NetworkInterfaces[0].Association.PublicIp' \
                --output text)

            if [ ! -z "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "None" ]; then
                print_status "✅ Service URL: http://${PUBLIC_IP}:8000"
                echo "SERVICE_URL=http://${PUBLIC_IP}:8000" >> $GITHUB_OUTPUT 2>/dev/null || true
            fi
        fi
    fi
}

# Show deployment summary
show_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 ECS Deployment Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Cluster: $ECS_CLUSTER"
    echo "Service: $ECS_SERVICE"
    echo "Image: ${ECR_URI}:${IMAGE_TAG}"
    echo ""

    if [ "$USE_SPOT" = "true" ]; then
        echo "💰 Cost Optimization:"
        echo "  • Using Fargate Spot (70% discount)"
        echo "  • Estimated cost: ~$0.0027/hour"
        echo "  • Auto-scaling: 0-3 tasks"
    else
        echo "💰 Pricing:"
        echo "  • Using Fargate On-Demand"
        echo "  • Estimated cost: ~$0.009/hour"
    fi

    echo ""
    echo "📊 Resources:"
    echo "  • CPU: 0.25 vCPU (256 units)"
    echo "  • Memory: 512 MB"
    echo "  • Auto-scaling: Enabled (CPU & Memory based)"
    echo ""
    echo "🔍 Monitoring:"
    echo "  • CloudWatch Logs: /ecs/mealtrack"
    echo "  • View logs: aws logs tail /ecs/mealtrack --follow"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    print_status "🚀 Starting ECS deployment from ECR"

    check_prerequisites
    register_task_definition
    deploy_service
    setup_autoscaling
    wait_for_deployment
    get_service_details
    show_summary

    print_status "🎉 Deployment completed successfully!"
}

# Run main function
main