data_dir = "/opt/nomad/data"
bind_addr = "0.0.0.0"
disable_update_check = true

datacenter = "public"

server {
  enabled = false
}

client {
  enabled = true
  server_join {
    retry_join = ["provider=aws endpoint=ec2.eu-west-1.api.aws addr_type=private_v4 region=eu-west-1 tag_key=AutoJoin tag_value=nomad"]
  }
}

plugin "docker" {
  config {
    allow_privileged = true
  }
}
