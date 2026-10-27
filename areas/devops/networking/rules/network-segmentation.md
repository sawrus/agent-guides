---
description: Network zones, subnet placement, and access paths for cloud and bare-metal networks defined as code.
paths:
  - "**/network/**"
  - "**/vpc/**"
  - "**/firewall*.tf"
  - "**/security_group*.tf"
  - "**/*network*.tf"
---

# Network segmentation

- Define four zones in the network module: public (load balancers), application (nodes and app servers), data (databases, queues, object storage), management (CI runners, bastion, monitoring).
- Put Kubernetes nodes and application servers in private subnets; never set `associate_public_ip_address = true` on a node.
- Do not add a NAT gateway or any `0.0.0.0/0` egress route to data subnets.
- Allow inbound traffic to the data zone only from application zone security groups on the database or queue port.
- Allow SSH to servers only through a bastion host or VPN with MFA; never open port 22 to `0.0.0.0/0`.
- Use security group IDs (`source_security_group_id`) in rules instead of wide CIDR blocks.
- Limit egress of CI runners and nodes to the registries and APIs they need with an egress `policy` or firewall rule.
- Enable flow logs on every VPC or subnet in production.
- Use mTLS between services when a service mesh (Istio, Linkerd) runs in the cluster; set `PeerAuthentication` to `STRICT`.
