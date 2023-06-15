job "nomad-proxy" {
  datacenters = ["dc1"]
  type = "system"

  group "nomad-proxy" {
    task "app" {
      driver = "exec"

      config {
        command = "local/nomad-proxy.py"
      }

      template {
        destination = "local/nomad-proxy.py"
        perms = "755"
        left_delimiter = "@@"
        right_delimiter = "@@"

        data =<<EOT
[[ content ]]
EOT
      }

      resources {
        cpu = 100
        memory = 32
        memory_max = 64
      }
    }
  }
}
