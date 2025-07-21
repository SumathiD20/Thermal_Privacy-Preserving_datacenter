variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH"
  type        = string
}

variable "allowed_ip" {
  description = "Your laptop’s public IP in CIDR format (e.g. 1.2.3.4/32)"
  type        = string
}

variable "ssm_param_name" {
  description = "SSM SecureString parameter holding the Fernet key"
  type        = string
  default     = "/heat-pipeline/fernet_key"
}

variable "instance_ami" {
  description = "AMI ID for Ubuntu 22.04 LTS"
  type        = string
  default     = "ami-0a7d80731ae1b2435"
}
