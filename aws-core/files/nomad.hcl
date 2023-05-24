data_dir = "/opt/nomad/data"
bind_addr = "0.0.0.0"
disable_update_check = true

server {
  enabled = true
  bootstrap_expect = 1
#  server_join {
#    "retry_join": ["provider=aws region=eu-central-1 tag_key=AutoJoin tag_value=production"]
#  }
}

client {
  enabled = true
  servers = ["127.0.0.1"]
}

plugin "docker" {
  config {
    allow_privileged = true
  }
}
