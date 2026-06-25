# Production Environment Deployment

provider "aws" {
  region = "us-east-1"
}

# Production Kubernetes Workload
module "production_kubernetes" {
  source             = "../../modules/kubernetes"
  cluster_name       = "eks-prod-cluster-1"
  node_instance_type = "m5.2xlarge"
}

# Production Serverless Payment service
module "production_serverless" {
  source        = "../../modules/serverless"
  function_name = "lambda-payment-processor"
  memory_size   = 2048 # Overprovisioned memory
}

# Production Monolith Compute Instance
module "production_compute" {
  source        = "../../modules/compute"
  instance_name = "ec2-monolith-legacy"
  instance_type = "t3.xlarge" # Overprovisioned type
  volume_type   = "gp2"       # gp2 to gp3 upgrade target
}
