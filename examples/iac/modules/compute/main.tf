# Compute Module containing VMs and block storage definitions

variable "instance_name" {
  type        = string
  description = "Name of the compute instance"
}

variable "instance_type" {
  type        = string
  default     = "t3.xlarge"
  description = "Size of the VM instance"
}

variable "volume_type" {
  type        = string
  default     = "gp2"
  description = "EBS Volume storage class"
}

# Idle Virtual Machine resource
resource "aws_instance" "ec2-monolith-legacy" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = var.instance_type

  tags = {
    Name        = var.instance_name
    Environment = "staging"
  }
}

# Unattached/Orphan storage resource
resource "aws_ebs_volume" "ebs-unused-temp" {
  availability_zone = "us-east-1a"
  size              = 1000
  type              = var.volume_type

  tags = {
    Name        = "ebs-unused-temp"
    Environment = "staging"
  }
}
