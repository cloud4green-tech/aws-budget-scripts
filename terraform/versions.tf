terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.60"
    }

    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }

    random = {
      source  = "hashicorp/random"
      version = ">= 3.6"
    }
  }
}

provider "aws" {
  region = var.management_region
}

data "aws_caller_identity" "current" {}
data "aws_organizations_organization" "current" {}
data "aws_partition" "current" {}

resource "random_id" "suffix" {
  byte_length = 4
}
