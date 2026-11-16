variable "bucket_name" {
  type        = string
  description = "Name of the S3 static bucket."
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g., staging, production)."
}

variable "owner" {
  type        = string
  description = "Owning team or service."
}

variable "kms_key_arn" {
  type        = string
  default     = null
  description = "Optional KMS key ARN; defaults to AES256 (SSE-S3) when null."
}
