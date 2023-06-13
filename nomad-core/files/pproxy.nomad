job "pproxy" {
  datacenters = ["public"]

  type = "system"

  group "pproxy" {
    network {
      mode = "host"
    }

    task "app" {
      driver = "exec"

      config {
        command = "/usr/local/bin/pproxy"
        args = [
          "-l", "socks5://0.0.0.0:8080",
          "-ul", "socks5://0.0.0.0:8080",
        ]
      }

      resources {
        cpu = 100
        memory = 64
      }
    }
  }
}
