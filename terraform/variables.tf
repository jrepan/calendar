variable "project" {
  description = "GCP project ID"
  type        = string
}

variable "auth_password_sha1" {
  description = "SHA1 hash of the app password to inject into the VM via metadata (optional)"
  type        = string
  default     = ""
}

