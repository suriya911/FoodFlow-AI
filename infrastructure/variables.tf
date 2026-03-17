variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "foodflow"
}

variable "backend_desired_count" {
  description = "Number of backend ECS tasks to run"
  type        = number
  default     = 1
}

variable "nemotron_api_key" {
  description = "NVIDIA Nemotron API key (nvapi-...)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openrouter_api_key" {
  description = "OpenRouter API key for backup Nemotron tier"
  type        = string
  sensitive   = true
  default     = ""
}
