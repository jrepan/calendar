output "instance_ip" {
  description = "External IP of the created VM"
  value       = google_compute_instance.vm.network_interface[0].access_config[0].nat_ip
}
