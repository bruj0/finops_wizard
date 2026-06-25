# Staging Environment Deployment

provider "aws" {
  region = "us-east-1"
}

# Staging Kubernetes Workload
module "staging_kubernetes" {
  source             = "../../modules/kubernetes"
  cluster_name       = "eks-staging-cluster"
  node_instance_type = "t3.medium"
}

# Staging Serverless Payment service
module "staging_serverless" {
  source        = "../../modules/serverless"
  function_name = "lambda-payment-staging"
  memory_size   = 1024
}

# Staging Monolith Compute Instance
module "staging_compute" {
  source        = "../../modules/compute"
  instance_name = "ec2-monolith-staging"
  instance_type = "t3.medium"
  volume_type   = "gp2"
}
