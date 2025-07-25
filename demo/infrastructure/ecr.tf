# ECR repository for AgentCore container images
resource "aws_ecr_repository" "agentcore_agents" {
  name                 = "bedrock-agentcore-agents"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = var.tags
}

# ECR lifecycle policy to manage image retention
resource "aws_ecr_lifecycle_policy" "agentcore_agents" {
  repository = aws_ecr_repository.agentcore_agents.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}