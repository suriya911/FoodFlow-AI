output "alb_dns_name" {
  description = "ALB public DNS — use as NEXT_PUBLIC_API_URL (http://)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "alb_websocket_url" {
  description = "WebSocket URL — use as NEXT_PUBLIC_WS_URL"
  value       = "ws://${aws_lb.main.dns_name}"
}

output "ecr_repository_url" {
  description = "ECR repo URL for docker push"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.backend.name
}
