# FoodFlow AI — Deployment Guide

**Stack:** AWS EC2 t2.micro (Terraform) + Vercel (GitHub import)
**Cost:** $0 for 12 months (AWS free tier) → ~$9/month after · Vercel always free

---

## What Terraform provisions

```
AWS EC2 t2.micro ── Elastic IP (static) ── nginx (port 80)
       │                                        │
  IAM role                               reverse proxy
  (ECR pull)                             WebSocket passthrough
       │
  ECR repository ── Docker image (python:3.11-slim)
```

No load balancer. No ECS. Just a single well-configured VM — right-sized for a portfolio project.

---

## Prerequisites (install once)

```powershell
# AWS CLI
winget install Amazon.AWSCLI
aws --version   # aws-cli/2.x ✓

# Terraform
winget install Hashicorp.Terraform
terraform -version   # >= 1.6 ✓

# Docker Desktop — for building the image
# https://www.docker.com/products/docker-desktop/
docker info   # must not say "not running" ✓
```

---

## Phase 1 — Push to GitHub

```powershell
cd D:\FoodFlow-AI

git init
git add .
git commit -m "feat: FoodFlow AI — multi-agent surplus food + SafeRide dispatch"

# Replace YOUR_USERNAME
git remote add origin https://github.com/YOUR_USERNAME/foodflow-ai.git
git branch -M main
git push -u origin main
```

**Check:** `https://github.com/YOUR_USERNAME/foodflow-ai` shows `backend/` `frontend/` `infrastructure/` folders.

---

## Phase 2 — AWS credentials

```powershell
aws configure
# AWS Access Key ID:     <IAM → Security credentials → Create access key>
# AWS Secret Access Key: <same>
# Default region:        us-east-1
# Output format:         json

# Verify:
aws sts get-caller-identity
# { "Account": "123456789", "Arn": "arn:aws:iam::..." }
```

---

## Phase 3 — Create EC2 key pair (for SSH access)

```powershell
# Create key pair in AWS, save the .pem file
aws ec2 create-key-pair `
  --key-name foodflow-key `
  --query "KeyMaterial" `
  --output text `
  --region us-east-1 > "$HOME\.ssh\foodflow-key.pem"

# Restrict permissions (required for SSH)
icacls "$HOME\.ssh\foodflow-key.pem" /inheritance:r /grant:r "$($env:USERNAME):(R)"
```

**Check:** File exists at `~/.ssh/foodflow-key.pem`

---

## Phase 4 — Build and push Docker image

```powershell
# Get your AWS account ID
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ECR_URL    = "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com"

# Create ECR repo (Terraform also creates it, but we need it now for the push)
aws ecr create-repository --repository-name foodflow-backend --region us-east-1

# Login to ECR
aws ecr get-login-password --region us-east-1 `
  | docker login --username AWS --password-stdin $ECR_URL

# Build
cd D:\FoodFlow-AI\backend
docker build -t foodflow-backend .

# Tag + push
docker tag  foodflow-backend:latest "$ECR_URL/foodflow-backend:latest"
docker push "$ECR_URL/foodflow-backend:latest"
```

**Check:** Output ends with `latest: digest: sha256:... size: ...`

---

## Phase 5 — Terraform: provision EC2

```powershell
cd D:\FoodFlow-AI\infrastructure

# Copy and fill in secrets
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region         = "us-east-1"
project            = "foodflow"
key_pair_name      = "foodflow-key"
openrouter_api_key = "sk-or-v1-YOUR_KEY"
nemotron_api_key   = ""
app_url            = "https://foodflow-ai.vercel.app"
```

```powershell
terraform init
# ✓ "Terraform has been successfully initialized!"

terraform plan
# ✓ "Plan: X to add, 0 to change, 0 to destroy." — no errors

terraform apply
# Type: yes
# ⏳ ~3 minutes to provision

# ✓ "Apply complete!"
# Outputs:
#   backend_public_ip  = "1.2.3.4"
#   backend_api_url    = "http://1.2.3.4"
#   backend_ws_url     = "ws://1.2.3.4"
#   ecr_repository_url = "123456789.dkr.ecr...."
#   ssh_command        = "ssh -i ~/.ssh/foodflow-key.pem ec2-user@1.2.3.4"
```

Save the `backend_public_ip` — you need it for Vercel.

---

## Phase 6 — Verify backend is running

```powershell
# Wait ~2 minutes for the EC2 user_data script to finish
$IP = terraform output -raw backend_public_ip

# Health check
curl http://$IP/health
# ✓ {"status":"ok","entities":18}

# Check logs via SSH
ssh -i "$HOME\.ssh\foodflow-key.pem" ec2-user@$IP
# Inside the EC2 instance:
docker logs foodflow-backend --tail 50
# ✓ INFO  🌱 World seeded — 18 entities ready
```

---

## Phase 7 — Deploy frontend to Vercel

### Option A — Vercel dashboard (recommended)

1. Go to **https://vercel.com/new**
2. Click **Import Git Repository** → connect GitHub → select `foodflow-ai`
3. Set **Root Directory** to `frontend`
4. Under **Environment Variables** add:

| Name | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `http://YOUR_EC2_IP` |
| `NEXT_PUBLIC_WS_URL` | `ws://YOUR_EC2_IP` |

5. Click **Deploy** → wait ~90 seconds

**Check:** Vercel gives you `https://foodflow-ai-xxx.vercel.app` — open it, header shows green **● live** dot.

### Option B — Vercel CLI

```powershell
cd D:\FoodFlow-AI\frontend
npm install -g vercel
vercel login   # follow prompts

vercel   # first deploy

# Set env vars
vercel env add NEXT_PUBLIC_API_URL production
# paste: http://YOUR_EC2_IP

vercel env add NEXT_PUBLIC_WS_URL production
# paste: ws://YOUR_EC2_IP

vercel --prod   # redeploy with env vars
```

---

## Phase 8 — End-to-end smoke test

```
✓ Open Vercel URL
✓ Green "● live" dot in header
✓ Click [▶ Start Sim] — signals appear in left panel
✓ Click [⚡ Force Food] — food signal fires immediately
✓ Click [🚖 Force Ride] — ride signal fires immediately
✓ Click [Agents] tab — see LangGraph trace with 6 nodes
✓ Model Status table shows Tier 1 (Nemotron-70B) active + green

SSH into EC2 and confirm:
  docker logs foodflow-backend --tail 20
  ✓ "▶ Calling nvidia/llama-3.1-nemotron-70b-instruct via https://openrouter.ai..."
  ✓ "✅ Model call OK: Nemotron-70B (OpenRouter) (1400 ms)"
```

---

## Redeploy after code changes

```powershell
# 1. Rebuild + push new image
cd D:\FoodFlow-AI\backend
docker build -t foodflow-backend .
docker tag  foodflow-backend:latest "$ECR_URL/foodflow-backend:latest"
docker push "$ECR_URL/foodflow-backend:latest"

# 2. Pull new image on EC2
$IP = (cd infrastructure && terraform output -raw backend_public_ip)
ssh -i "$HOME\.ssh\foodflow-key.pem" ec2-user@$IP "sudo /usr/local/bin/foodflow-redeploy.sh"

# Frontend redeploys automatically on every git push to main (Vercel CI)
```

---

## Teardown

```powershell
cd D:\FoodFlow-AI\infrastructure
terraform destroy   # type "yes" — removes EC2, ECR, VPC, Elastic IP, IAM roles

# Delete ECR images first if destroy fails:
aws ecr batch-delete-image \
  --repository-name foodflow-backend \
  --image-ids imageTag=latest \
  --region us-east-1
```

---

## Cost breakdown

| Resource | Free period | After free tier |
|---|---|---|
| EC2 t2.micro | 750 hrs/month × 12 months | ~$9/month |
| EC2 storage (20 GB gp3) | 30 GB free × 12 months | ~$1.60/month |
| Elastic IP | Free when attached | Free |
| ECR (Docker registry) | 500 MB free forever | ~$0.10/GB |
| CloudWatch logs | 5 GB free | ~$0 |
| Vercel (frontend) | Free forever (Hobby) | Free |
| OpenRouter Nemotron-70B | Pay-per-use | < $1/month (demo usage) |
| **Total year 1** | | **< $1/month** |
| **Total year 2+** | | **~$11/month** |
