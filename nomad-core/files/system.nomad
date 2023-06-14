job "system" {
  datacenters = ["public", "dc1"]

  type = "system"

  group "system" {
    network {
      mode = "host"
    }

    task "empty" {
      driver = "exec"

      config {
        command = "sleep"
        args = [
          "3650d"
        ]
      }

      resources {
        cpu = 100
        memory = 384
      }
    }
  }
}
