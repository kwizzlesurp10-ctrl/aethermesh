provider "aws" {
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true

  endpoints {
    s3 = "http://localhost:4566"
  }
}

module "site" {
  source      = "../../modules/s3-static-bucket"
  bucket_name = "aethermesh-staging-site"
  environment = "staging"
  owner       = "platform-team"
}
