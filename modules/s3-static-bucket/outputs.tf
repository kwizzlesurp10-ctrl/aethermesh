output "bucket_id" {
  value       = aws_s3_bucket.this.id
  description = "ID of the created S3 bucket."
}

output "estMonthlyCostUSD" {
  value       = 4.5
  description = "Estimated monthly cost in USD."
}
