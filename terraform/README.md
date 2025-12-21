# Terraform deploy for codespaces-flask

This folder contains Terraform files to provision a small Google Compute VM and firewall to run the `codespaces-flask` app.

Quick start

1. Install prerequisites:

```bash
# Install gcloud and authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Install Terraform (https://learn.hashicorp.com/terraform)
```

2. Set your project (option A - env):

```bash
export TF_VAR_project=your-gcp-project-id
```

Or pass `-var "project=..."` to `terraform apply`.

3. Initialize and apply:

```bash
cd terraform
terraform init
terraform apply
```

4. After apply completes, Terraform prints `instance_ip`. The app listens on port `8080` — open `http://INSTANCE_IP:8080`.

Destroy resources

```bash
terraform destroy
```

Notes and caveats
- The VM is `e2-micro` (free-tier friendly in many regions) and the Terraform default zone is `us-east1-b`.
- The startup script clones `https://github.com/jrepan/codespaces-flask` and runs it via `gunicorn` on port 8080.
- If the repository is private, update the startup script to pull from a private source or use an image/CI pipeline.
- The firewall created allows `0.0.0.0/0` to ports 80 and 8080 — tighten as needed.
- Set the `AUTH_PASSWORD_SHA1` and `SECRET_KEY` environment variables in the VM or modify the startup script/systemd unit to inject them if you need persistent secure credentials.
- Running resources in GCP may incur charges; verify your free-tier eligibility.

Alternatives
- For a simpler, lower-maintenance deployment consider Cloud Run or App Engine (I can add Terraform for those if you prefer).
