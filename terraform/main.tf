terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project
  region  = "us-east1"
  zone    = "us-east1-b"
}

resource "google_compute_network" "vpc" {
  name                    = "calendar-vpc"
  auto_create_subnetworks = true
}

resource "google_compute_firewall" "allow_http" {
  name    = "allow-http"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
      auth_password_sha1 = var.auth_password_sha1
      startup-script = <<-EOF
  }

  source_ranges = ["0.0.0.0/0"]
}
        # Fetch auth_password_sha1 from instance metadata and write to env file
        if METAPW=$(curl -fs -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/auth_password_sha1 2>/dev/null); then
          echo "AUTH_PASSWORD_SHA1=\"${METAPW}\"" > /etc/default/calendar_env
          chmod 600 /etc/default/calendar_env
        fi

resource "google_compute_instance" "vm" {
  name         = "calendar-vm"
  machine_type = "e2-micro"
  zone         = "us-east1-b"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 20
    }
  }

  network_interface {
    network = google_compute_network.vpc.id
    access_config {}
  }

  service_account {
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata = {
  EnvironmentFile=/etc/default/calendar_env
  Environment=FLASK_APP=app.py
  ExecStart=/opt/app/venv/bin/gunicorn --bind 0.0.0.0:8080 app:app
      set -e
      apt-get update
      apt-get install -y python3 python3-venv python3-pip git
      mkdir -p /opt/app
      cd /opt
      if [ ! -d /opt/app/.git ]; then
        git clone https://github.com/jrepan/codespaces-flask.git app || true
      else
        cd /opt/app && git pull || true
      fi
      cd /opt/app || exit 0
      python3 -m venv venv
      . venv/bin/activate
      pip install --upgrade pip
      if [ -f requirements.txt ]; then
        pip install -r requirements.txt || true
      fi
      pip install gunicorn || true
      cat > /etc/systemd/system/calendar.service <<'SERVICE'
[Unit]
Description=Calendar Flask App
After=network.target

[Service]
User=root
WorkingDirectory=/opt/app
Environment=FLASK_APP=app.py
ExecStart=/opt/app/venv/bin/gunicorn --bind 0.0.0.0:8080 app:app
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE
      systemctl daemon-reload
      systemctl enable calendar
      systemctl start calendar || true
    EOF
  }

  tags = ["http-server"]
}

output "instance_ip" {
  value = google_compute_instance.vm.network_interface[0].access_config[0].nat_ip
}
