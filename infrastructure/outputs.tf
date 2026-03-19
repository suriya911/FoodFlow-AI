output "backend_public_ip" {
  description = "Static public IP of the backend EC2 instance"
  value       = aws_eip.backend.public_ip
}

output "backend_api_url" {
  description = "REST API base URL — set as NEXT_PUBLIC_API_URL in Vercel"
  value       = "http://${aws_eip.backend.public_ip}"
}

output "backend_ws_url" {
  description = "WebSocket base URL — set as NEXT_PUBLIC_WS_URL in Vercel"
  value       = "ws://${aws_eip.backend.public_ip}"
}

output "ecr_repository_url" {
  description = "ECR repo URL — use for docker build/push"
  value       = aws_ecr_repository.backend.repository_url
}

output "ssh_command" {
  description = "SSH into the backend instance to check logs"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_eip.backend.public_ip}"
}
