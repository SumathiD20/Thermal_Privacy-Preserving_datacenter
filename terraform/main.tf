provider "aws" {
  region = var.region
}

# Fetch account info for ARNs
data "aws_caller_identity" "current" {}

# 1) Read the Fernet key from SSM Parameter Store
data "aws_ssm_parameter" "fernet" {
  name            = var.ssm_param_name
  with_decryption = true
}

# 2) IAM role for EC2 to assume
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_role" {
  name               = "heat-pipeline-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

# 3) IAM policy allowing SSM read of that parameter
resource "aws_iam_policy" "ssm_access" {
  name        = "heat-pipeline-ssm-access"
  description = "Allow EC2 to fetch Fernet key from SSM"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter", "ssm:GetParameters"]
      Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_param_name}"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "attach_ssm" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ssm_access.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "heat-pipeline-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# 4) Security group: SSH + MQTT-TLS (8883)
resource "aws_security_group" "mqtt_sg" {
  name        = "heat-pipeline-sg"
  description = "Allow SSH & MQTT-TLS from laptop only"

  ingress {
    description = "SSH from laptop"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }
  ingress {
    description = "MQTT over TLS"
    from_port   = 8883
    to_port     = 8883
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 5) EC2 instance for Stream Processor
resource "aws_instance" "stream_processor" {
  ami                    = var.instance_ami
  instance_type          = "t2.micro"
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.mqtt_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = <<-EOF
    #!/bin/bash
    set -e
    apt-get update -y
    apt-get install -y python3-pip awscli mosquitto docker.io docker-compose git
    pip3 install pandas numpy scikit-learn joblib cryptography paho-mqtt psutil

    # Fetch the Fernet key from SSM and save it
    aws ssm get-parameter \
      --name "${var.ssm_param_name}" \
      --with-decryption \
      --query "Parameter.Value" \
      --output text > /home/ubuntu/secret.key

    chown ubuntu:ubuntu /home/ubuntu/secret.key
    chmod 600 /home/ubuntu/secret.key

    # Clone your repo and bring up Docker Compose
    su - ubuntu -c "git clone https://github.com/yourorg/yourrepo.git /home/ubuntu/app"
    su - ubuntu -c "cd /home/ubuntu/app && docker-compose up -d"
  EOF

  tags = {
    Name = "Heat-Pipeline-Processor"
  }
}
