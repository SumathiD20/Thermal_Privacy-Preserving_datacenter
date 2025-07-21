output "processor_public_ip" {
  description = "Public IP of the Stream Processor EC2"
  value       = aws_instance.stream_processor.public_ip
}
