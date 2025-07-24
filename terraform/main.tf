provider "aws" {
  region = var.region
}

# Get AWS account details
data "aws_caller_identity" "current" {}

# Fetch the Fernet key securely from SSM Parameter Store
data "aws_ssm_parameter" "fernet" {
  name            = var.ssm_param_name
  with_decryption = true
}

# Reference existing IAM role instead of creating it
data "aws_iam_role" "ec2_role" {
  name = "heat-pipeline-ec2-role"
}

# IAM policy to allow reading from SSM
resource "aws_iam_policy" "ssm_read" {
  name        = "heat-pipeline-ssm-read"
  description = "Allow EC2 instance to read the Fernet key from SSM"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["ssm:GetParameter", "ssm:GetParameters"],
        Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_param_name}"
      }
    ]
  })
}

# Attach the policy to the existing IAM role
resource "aws_iam_role_policy_attachment" "attach_ssm_read" {
  role       = data.aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ssm_read.arn
}

# Create an instance profile using the existing role
data "aws_iam_instance_profile" "ec2_profile" {
  name = "heat-pipeline-ec2-profile"
}

# Security group allowing SSH and MQTT from your IP only
resource "aws_security_group" "sg" {
  name        = "heat-pipeline-sg"
  description = "Allow SSH and MQTT plaintext from laptop IP"

  ingress {
    description = "SSH from laptop"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  ingress {
    description = "MQTT (port 1883) from laptop"
    from_port   = 1883
    to_port     = 1883
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

# EC2 instance to host broker and stream processor
resource "aws_instance" "processor" {
  ami                    = var.instance_ami
  instance_type          = "t2.micro"
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.sg.id]
  iam_instance_profile = data.aws_iam_instance_profile.ec2_profile.name

  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Install dependencies
    apt-get update -y
    apt-get install -y mosquitto mosquitto-clients python3-pip awscli
    pip3 install pandas numpy scikit-learn joblib cryptography paho-mqtt

    # Fetch Fernet key from SSM
    mkdir -p /home/ubuntu/model
    aws ssm get-parameter \
      --name "${var.ssm_param_name}" \
      --with-decryption \
      --query "Parameter.Value" \
      --output text > /home/ubuntu/secret.key

    chown ubuntu:ubuntu /home/ubuntu/secret.key
    chmod 600 /home/ubuntu/secret.key

    chown -R ubuntu:ubuntu /home/ubuntu/model
    chmod 700 /home/ubuntu/model

    # Enable and start Mosquitto
    systemctl enable --now mosquitto

    # Manual steps required after launch:
    # - scp stream_processor.py and iforest.joblib
    # - run: python3 stream_processor.py
  EOF

  tags = {
    Name = "Heat-Pipeline-Processor"
  }
}
