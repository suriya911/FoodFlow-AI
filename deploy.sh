#!/usr/bin/env bash
# ── FoodFlow AI — Full deploy script ────────────────────────────────────────
# Usage: bash deploy.sh
# Prerequisites: aws CLI configured, docker running, terraform installed, vercel CLI installed
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
PROJECT="${PROJECT:-foodflow}"

echo "=== [1/5] Terraform apply — provision AWS infrastructure ==="
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
echo ">>> Edit infrastructure/terraform.tfvars with your API keys, then press Enter"
read -r

terraform init -upgrade
terraform apply -auto-approve

ECR_URL=$(terraform output -raw ecr_repository_url)
ALB_URL=$(terraform output -raw alb_dns_name)
WS_URL=$(terraform output -raw alb_websocket_url)
echo "ECR: $ECR_URL"
echo "ALB: $ALB_URL"
cd ..

echo ""
echo "=== [2/5] Docker build & push backend to ECR ==="
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "${ECR_URL%%/*}"

docker build -t "${PROJECT}-backend" ./backend
docker tag "${PROJECT}-backend:latest" "${ECR_URL}:latest"
docker push "${ECR_URL}:latest"

echo ""
echo "=== [3/5] Force ECS redeployment ==="
CLUSTER="${PROJECT}-cluster"
SERVICE="${PROJECT}-backend"
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --region "$REGION" \
  --output text > /dev/null
echo "ECS redeployment triggered — backend will be live in ~2 min"

echo ""
echo "=== [4/5] Frontend — deploy to Vercel ==="
cd frontend
# Write env vars
cat > .env.production <<EOF
NEXT_PUBLIC_API_URL=${ALB_URL}
NEXT_PUBLIC_WS_URL=${WS_URL/http/ws}
EOF

vercel --prod --yes

cd ..

echo ""
echo "=== [5/5] Done! ==="
echo "Backend : $ALB_URL"
echo "WebSocket: ${WS_URL/http/ws}/ws/live"
echo "Frontend : Check Vercel output above for your deployment URL"
