# Stage 1 of 3: the private bucket that holds the Terraform state of the other stages.
# Its own state stays local (local/bootstrap.tfstate). Keep this bucket when you tear down.
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.66.0" }
  }
  backend "local" {}
}
variable "expected_account_id" { type = string }
variable "region" { type = string }
variable "project" { type = string }
provider "aws" {
  region              = var.region
  allowed_account_ids = [var.expected_account_id]
  default_tags {
    tags = { Project = var.project, ManagedBy = "terraform" }
  }
}
resource "aws_s3_bucket" "state" {
  bucket        = "${var.project}-tfstate-${var.expected_account_id}"
  force_destroy = false
}
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
output "state_bucket" { value = aws_s3_bucket.state.id }
