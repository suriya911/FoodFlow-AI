#!/bin/bash
# FoodFlow AI — EC2 Bootstrap Script
# Runs once on first boot via cloud-init
set -euxo pipefail

# ── 1. System update + Docker ──────────────────────────────────────────────────
dnf update -y
dnf install -y docker nginx
systemctl enable docker
systemctl start docker

# ── 2. nginx reverse proxy (port 80 → 8000, WebSocket support) ────────────────
cat > /etc/nginx/conf.d/foodflow.conf <<'NGINX'
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80 default_server;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # WebSocket
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        $connection_upgrade;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Keep WebSocket alive for 1 hour (live simulation)
        proxy_read_timeout  3600s;
        proxy_send_timeout  3600s;
    }
}
NGINX

# Remove default nginx config
rm -f /etc/nginx/conf.d/default.conf
systemctl enable nginx
systemctl start nginx

# ── 3. ECR login + pull latest image ──────────────────────────────────────────
AWS_REGION="${aws_region}"
ECR_URL="${ecr_url}"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_URL"

docker pull "$ECR_URL:latest"

# ── 4. Run FoodFlow backend container ─────────────────────────────────────────
docker run -d \
  --restart unless-stopped \
  --name foodflow-backend \
  -p 8000:8000 \
  -e OPENROUTER_API_KEY="${openrouter_api_key}" \
  -e NEMOTRON_API_KEY="${nemotron_api_key}" \
  -e APP_URL="${app_url}" \
  "$ECR_URL:latest"

# ── 5. Create redeploy helper script (for future pushes) ──────────────────────
cat > /usr/local/bin/foodflow-redeploy.sh <<REDEPLOY
#!/bin/bash
set -euxo pipefail
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ECR_URL
docker pull $ECR_URL:latest
docker stop foodflow-backend 2>/dev/null || true
docker rm   foodflow-backend 2>/dev/null || true
docker run -d \\
  --restart unless-stopped \\
  --name foodflow-backend \\
  -p 8000:8000 \\
  -e OPENROUTER_API_KEY="${openrouter_api_key}" \\
  -e NEMOTRON_API_KEY="${nemotron_api_key}" \\
  -e APP_URL="${app_url}" \\
  $ECR_URL:latest
echo "✅ FoodFlow backend redeployed"
REDEPLOY

chmod +x /usr/local/bin/foodflow-redeploy.sh

echo "✅ FoodFlow AI bootstrap complete"
