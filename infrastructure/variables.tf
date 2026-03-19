variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name prefix applied to all AWS resources"
  type        = string
  default     = "foodflow"
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair for SSH access (create in AWS Console → EC2 → Key Pairs)"
  type        = string
  default     = "foodflow-key"
}

variable "nemotron_api_key" {
  description = "NVIDIA Nemotron API key (nvapi-...) — Tier 0. Leave blank to use OpenRouter."
  type        = string
  sensitive   = true
  default     = ""
}

variable "openrouter_api_key" {
  description = "OpenRouter API key — Tier 1 fallback for Nemotron-70B"
  type        = string
  sensitive   = true
  default     = ""
}

variable "app_url" {
  description = "Vercel frontend URL — used as HTTP-Referer header for OpenRouter"
  type        = string
  default     = "https://foodflow-ai.vercel.app"
}
