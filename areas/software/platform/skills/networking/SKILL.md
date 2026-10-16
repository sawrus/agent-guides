---
name: networking
description: "Guides cloud networking with three-tier VPC design, default-deny security group rules, and network cost optimization; use when designing VPC topology, configuring security groups, setting up NAT, or reviewing network architecture."
---

# Skill: Cloud Networking

## When to load

When designing VPC topology, configuring security groups, setting up NAT, or reviewing network architecture.

## VPC Design (3-tier)

```
VPC (10.0.0.0/16)
├── Public subnets   (10.0.1.0/24, 10.0.2.0/24) ← ALB, NAT Gateway
├── Private subnets  (10.0.10.0/24, 10.0.11.0/24) ← App servers, K8s nodes
└── Isolated subnets (10.0.20.0/24, 10.0.21.0/24) ← RDS, ElastiCache
```

## Security Group Rules (Default-Deny)

```hcl
# App tier: only accepts traffic from ALB security group
resource "aws_security_group_rule" "app_from_alb" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.app.id
}

# DB tier: only accepts traffic from app security group
resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.app.id
  security_group_id        = aws_security_group.db.id
}
```

## Cost Optimization

- Use VPC Endpoints for S3/DynamoDB to avoid NAT Gateway costs
- NAT Gateway: one per AZ in production (not one shared)
- Transit Gateway for multi-VPC connectivity (cheaper than VPC peering at scale)
