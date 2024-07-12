data_dir = "/opt/nomad/data"
bind_addr = "0.0.0.0"
disable_update_check = true

datacenter = "dc1"

leave_on_terminate = true

limits {
  http_max_conns_per_client = 1000
  rpc_max_conns_per_client = 1000
}

server {
  enabled = true
  bootstrap_expect = 3
  server_join {
    retry_join = ["exec=oci-list-pool-ips.sh private nomad" ]
  }
}

client {
  enabled = true
  max_kill_timeout = "24h"
  servers = ["127.0.0.1"]
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
