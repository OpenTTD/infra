data_dir = "/opt/nomad/data"
bind_addr = "0.0.0.0"
disable_update_check = true

datacenter = "public"

server {
  enabled = false
}

client {
  enabled = true
  max_kill_timeout = "24h"
  server_join {
    retry_join = ["exec=oci-list-pool-ips.sh private nomad" ]
  }
}

telemetry {
  collection_interval = "1s"
  disable_hostname = true
  prometheus_metrics = true
  publish_allocation_metrics = true
  publish_node_metrics = true
}

plugin "docker" {
  config {
    allow_privileged = true
  }
}
