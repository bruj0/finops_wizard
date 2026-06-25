# Kubernetes Module containing EKS cluster definitions

variable "cluster_name" {
  type        = string
  description = "Name of the Kubernetes cluster"
}

variable "node_instance_type" {
  type        = string
  default     = "t3.medium"
  description = "Instance type for EKS node groups"
}

# Overprovisioned EKS Cluster resource
resource "aws_eks_cluster" "eks-prod-cluster-1" {
  name     = var.cluster_name
  role_arn = "arn:aws:iam::123456789012:role/eks-service-role"

  vpc_config {
    subnet_ids = ["subnet-12345", "subnet-67890"]
  }
}

resource "aws_eks_node_group" "eks-nodes" {
  cluster_name    = aws_eks_cluster.eks-prod-cluster-1.name
  node_group_name = "eks-node-group"
  node_role_arn   = "arn:aws:iam::123456789012:role/eks-node-role"
  subnet_ids      = ["subnet-12345", "subnet-67890"]

  scaling_config {
    desired_size = 8
    max_size     = 12
    min_size     = 2
  }

  instance_types = [var.node_instance_type]
}
