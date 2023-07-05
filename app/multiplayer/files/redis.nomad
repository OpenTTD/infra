job "redis-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  group "redis" {
    count = 1

    network {
      mode = "host"
      port "redis" { to = 6379 }
    }

    task "app" {
      driver = "docker"

      service {
        name = "redis-[[ stack ]]"
        port = "redis"
        provider = "nomad"

        check {
          type = "tcp"
          name = "app_health"
          interval = "20s"
          timeout = "5s"

          check_restart {
            limit = 3
            grace = "90s"
            ignore_warnings = false
          }
        }
      }

      config {
        image = "registry.ipv6.docker.com/library/redis:7.0.11"
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["redis"]
      }

      resources {
        cpu = 100
        memory = 128
        memory_max = 256
      }
    }
  }
}
