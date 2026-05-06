resource "aws_dynamodb_table" "users" {
  name         = "${local.name_prefix}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "account_id"
    type = "S"
  }

  global_secondary_index {
    name            = "account_id-index"
    hash_key        = "account_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    System = local.name_prefix
  }
}

resource "aws_dynamodb_table" "active_resources" {
  name         = "${local.name_prefix}-active-resources"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "resource_id"

  attribute {
    name = "resource_id"
    type = "S"
  }

  attribute {
    name = "account_id"
    type = "S"
  }

  global_secondary_index {
    name            = "account_id-index"
    hash_key        = "account_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    System = local.name_prefix
  }
}

resource "aws_dynamodb_table" "usage_log" {
  name         = "${local.name_prefix}-usage-log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl_epoch"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    System = local.name_prefix
  }
}

resource "aws_dynamodb_table" "price_cache" {
  name         = "${local.name_prefix}-price-cache"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "price_key"

  attribute {
    name = "price_key"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    System = local.name_prefix
  }
}

resource "aws_dynamodb_table" "notification_locks" {
  name         = "${local.name_prefix}-notification-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "lock_id"

  attribute {
    name = "lock_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    System = local.name_prefix
  }
}
