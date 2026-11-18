# Stage 3 of 3: the ROSA cluster with hosted control plane. CPU workers only.
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "= 6.66.0" }
    rhcs   = { source = "terraform-redhat/rhcs", version = "= 1.7.9" }
    random = { source = "hashicorp/random", version = "= 3.9.1" }
  }
  backend "s3" {
    key          = "rosa/terraform.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}
variable "expected_account_id" { type = string }
variable "region" { type = string }
variable "project" { type = string }
variable "openshift_version" {
  type        = string
  description = "ROSA HCP version, for example 4.22.3. Check with: rosa list versions --hosted-cp"
}
variable "worker_replicas" {
  type    = number
  default = 3
}
variable "worker_machine_type" {
  type    = string
  default = "m6i.2xlarge"
}
provider "aws" {
  region              = var.region
  allowed_account_ids = [var.expected_account_id]
  default_tags {
    tags = { Project = var.project, ManagedBy = "terraform" }
  }
}
provider "rhcs" {}
data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "${var.project}-tfstate-${var.expected_account_id}"
    key    = "foundation/terraform.tfstate"
    region = var.region
  }
}
resource "random_password" "admin" {
  length           = 24
  special          = true
  override_special = "-_"
}
module "hcp" {
  source                              = "terraform-redhat/rosa-hcp/rhcs"
  version                             = "1.7.5"
  cluster_name                        = var.project
  openshift_version                   = var.openshift_version
  machine_cidr                        = data.terraform_remote_state.foundation.outputs.network.vpc_cidr
  aws_subnet_ids                      = concat(data.terraform_remote_state.foundation.outputs.network.public_subnet_ids, data.terraform_remote_state.foundation.outputs.network.private_subnet_ids)
  aws_availability_zones              = [data.terraform_remote_state.foundation.outputs.network.availability_zone]
  replicas                            = var.worker_replicas
  cluster_autoscaler_enabled          = false
  compute_machine_type                = var.worker_machine_type
  aws_billing_account_id              = var.expected_account_id
  tags                                = { Project = var.project, ManagedBy = "terraform" }
  create_account_roles                = true
  account_role_prefix                 = "${var.project}-account"
  create_oidc                         = true
  create_operator_roles               = true
  operator_role_prefix                = "${var.project}-operator"
  admin_credentials_username          = "cluster-admin"
  admin_credentials_password          = random_password.admin.result
  wait_for_create_complete            = true
  wait_for_std_compute_nodes_complete = true
}
# There is deliberately no GPU machine pool.
output "cluster_id" { value = module.hcp.cluster_id }
output "api_url" { value = module.hcp.cluster_api_url }
output "console_url" { value = module.hcp.cluster_console_url }
output "admin_password" {
  value     = random_password.admin.result
  sensitive = true
}
