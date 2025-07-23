provider "aws" { region = var.region }
data "aws_caller_identity" "me" {}

# Read key from SSM
data "aws_ssm_parameter" "fernet" {
  name            = var.ssm_param_name
  with_decryption = true
}

# IAM role for EC2 to fetch SSM
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

  }
}

resource "aws_iam_role" "ec2" {
  name               = "heat-pipeline-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_policy" "ssm_access" {
  name = "ssm-access"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["ssm:GetParameter", "ssm:GetParameters"],
      Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter${var.ssm_param_name}"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "att" {
  role       = aws_iam_role.ec2.name
  policy_arn = aws_iam_policy.ssm_access.arn
}

resource "aws_iam_instance_profile" "profile" {
  role = aws_iam_role.ec2.name
  name = "heat-pipeline-profile"
}

# Security Group
resource "aws_security_group" "sg" {
  name = "heat-pipeline-sg"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }
  ingress {
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

# EC2 Instance
resource "aws_instance" "processor" {
  ami                    = var.instance_ami
  instance_type          = "t2.micro"
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.sg.id]
  iam_instance_profile   = aws_iam_instance_profile.profile.name

  user_data = <<-EOF
    #!/bin/bash
    set -e
    # Install prerequisites
    apt-get update -y
    apt-get install -y docker.io docker-compose awscli
    systemctl start docker

    # Fetch key
    aws ssm get-parameter \
      --name "${var.ssm_param_name}" \
      --with-decryption \
      --query "Parameter.Value" \
      --output text > /home/ubuntu/secret.key
    chown ubuntu:ubuntu /home/ubuntu/secret.key
    chmod 600 /home/ubuntu/secret.key

    # Copy model from user (we’ll scp this later)
    mkdir /home/ubuntu/model
    chown ubuntu:ubuntu /home/ubuntu/model

    # Pull your repo & start broker+processor
    su - ubuntu -c "git clone https://github.com/yourorg/heat-pipeline-demo.git app"
    cat << 'EOC' > /home/ubuntu/app/docker-compose-ec2.yml
    version: "3.8"
    services:
      broker:
        image: eclipse-mosquitto:latest
        ports: ["1883:1883"]
      processor:
        build:
          context: /home/ubuntu/app/docker/processor
        volumes:
          - /home/ubuntu/secret.key:/app/secret.key:ro
          - /home/ubuntu/model/iforest.joblib:/app/iforest.joblib:ro
    EOC
    su - ubuntu -c "cd /home/ubuntu/app && docker-compose -f docker-compose-ec2.yml up -d"
  EOF

  tags = { Name = "Heat-Pipeline-Processor" }
}
