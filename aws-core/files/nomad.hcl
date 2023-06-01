data_dir = "/opt/nomad/data"
bind_addr = "0.0.0.0"
disable_update_check = true

server {
  enabled = true
  bootstrap_expect = 3
  server_join {
    retry_join = ["provider=aws endpoint=ec2.eu-west-1.api.aws addr_type=private_v4 region=eu-west-1 tag_key=AutoJoin tag_value=nomad"]
  }
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
