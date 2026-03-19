# FoodFlow AI — AWS Elastic Beanstalk Deploy Script (Windows PowerShell)
# Run: .\deploy-aws.ps1
# Prerequisites: AWS CLI installed + configured (aws configure)

param(
    [string]$AppName   = "foodflow-ai",
    [string]$EnvName   = "foodflow-ai-prod",
    [string]$Region    = "us-east-1",
    [string]$Platform  = "64bit Amazon Linux 2023 v4.3.0 running Docker"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== FoodFlow AI — AWS EB Deploy ===" -ForegroundColor Cyan

# ── 1. Zip the backend source ───────────────────────────────────────────────
Write-Host "`n[1/5] Packaging backend..." -ForegroundColor Yellow

$ZipPath = "$PSScriptRoot\foodflow-backend.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath }

# Zip backend directory (exclude venv, pycache, .env)
Compress-Archive -Path "$PSScriptRoot\backend\*" `
    -DestinationPath $ZipPath `
    -Force

# Remove junk from zip (venv is large — warn user)
Write-Host "  Created: $ZipPath"
Write-Host "  NOTE: Make sure backend/.venv is NOT in the zip (gitignored)"

# ── 2. Create EB application (idempotent) ──────────────────────────────────
Write-Host "`n[2/5] Ensuring EB application exists..." -ForegroundColor Yellow

$apps = aws elasticbeanstalk describe-applications --region $Region 2>&1
if ($apps -notmatch $AppName) {
    aws elasticbeanstalk create-application `
        --application-name $AppName `
        --description "FoodFlow AI — surplus food + SafeRide dispatch" `
        --region $Region
    Write-Host "  Created application: $AppName"
} else {
    Write-Host "  Application already exists: $AppName"
}

# ── 3. Upload source bundle to S3 ──────────────────────────────────────────
Write-Host "`n[3/5] Uploading source bundle to S3..." -ForegroundColor Yellow

$Bucket  = "elasticbeanstalk-$Region-$(aws sts get-caller-identity --query Account --output text)"
$Key     = "$AppName/foodflow-backend-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"

# Create bucket if it doesn't exist
aws s3 mb "s3://$Bucket" --region $Region 2>$null
aws s3 cp $ZipPath "s3://$Bucket/$Key" --region $Region
Write-Host "  Uploaded: s3://$Bucket/$Key"

# ── 4. Create application version ──────────────────────────────────────────
$VersionLabel = "v-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

aws elasticbeanstalk create-application-version `
    --application-name $AppName `
    --version-label $VersionLabel `
    --source-bundle "S3Bucket=$Bucket,S3Key=$Key" `
    --region $Region

Write-Host "`n[4/5] Created version: $VersionLabel"

# ── 5. Create or update environment ────────────────────────────────────────
Write-Host "`n[5/5] Deploying environment..." -ForegroundColor Yellow

$envs = aws elasticbeanstalk describe-environments `
    --application-name $AppName `
    --environment-names $EnvName `
    --region $Region 2>&1

if ($envs -match '"Status"') {
    # Update existing environment
    aws elasticbeanstalk update-environment `
        --application-name $AppName `
        --environment-name $EnvName `
        --version-label $VersionLabel `
        --region $Region
    Write-Host "  Updated environment: $EnvName"
} else {
    # Create new environment
    aws elasticbeanstalk create-environment `
        --application-name $AppName `
        --environment-name $EnvName `
        --version-label $VersionLabel `
        --platform-arn $Platform `
        --option-settings `
            "Namespace=aws:elasticbeanstalk:application:environment,OptionName=OPENROUTER_API_KEY,Value=$env:OPENROUTER_API_KEY" `
            "Namespace=aws:elasticbeanstalk:application:environment,OptionName=NEMOTRON_API_KEY,Value=$env:NEMOTRON_API_KEY" `
            "Namespace=aws:elasticbeanstalk:application:environment,OptionName=APP_URL,Value=https://foodflow-ai.vercel.app" `
        --region $Region
    Write-Host "  Created environment: $EnvName"
}

# ── Done ────────────────────────────────────────────────────────────────────
Write-Host "`n=== Deploy initiated ===" -ForegroundColor Green
Write-Host "Monitor: https://console.aws.amazon.com/elasticbeanstalk/home?region=$Region"
Write-Host ""
Write-Host "Once green, get your URL with:"
Write-Host "  aws elasticbeanstalk describe-environments --environment-names $EnvName --region $Region --query 'Environments[0].CNAME' --output text"
Write-Host ""
Write-Host "Then update frontend .env.local:"
Write-Host "  NEXT_PUBLIC_API_URL=http://<your-eb-url>"
Write-Host "  NEXT_PUBLIC_WS_URL=ws://<your-eb-url>"
