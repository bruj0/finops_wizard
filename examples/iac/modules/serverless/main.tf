# Serverless Module containing Lambda and API Gateway definitions

variable "function_name" {
  type        = string
  description = "Name of the Lambda function"
}

variable "memory_size" {
  type        = number
  default     = 2048
  description = "Configured memory size in MB"
}

# Overprovisioned Serverless Lambda function
resource "aws_lambda_function" "lambda-payment-processor" {
  function_name = var.function_name
  role          = "arn:aws:iam::123456789012:role/lambda-execution-role"
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  memory_size   = var.memory_size

  filename         = "lambda.zip"
  source_code_hash = "hash12345"
}

# API Gateway in front of Serverless functions
resource "aws_apigatewayv2_api" "http-api" {
  name          = "http-payment-gateway"
  protocol_type = "HTTP"
}
