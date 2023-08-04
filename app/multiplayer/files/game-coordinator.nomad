job "game-coordinator-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  spread {
    attribute = "${node.unique.id}"
  }

  group "game-coordinator" {
    count = [[ count ]]

    network {
      mode = "host"
      port "http" { to = 80 }
      port "coordinator" { to = 3976 }
    }

    update {
      max_parallel = 1
      health_check = "checks"
      auto_promote = true
      canary = 1
    }

    task "app" {
      driver = "docker"

      service {
        name = "coordinator-[[ stack ]]-web"
        port = "http"
        provider = "nomad"

        tags = [
          "metrics",
        ]
        canary_tags = [
          "canary",
        ]

        check {
          type = "http"
          name = "app_health"
          path = "/healthz"
          interval = "20s"
          timeout = "5s"

          check_restart {
            limit = 3
            grace = "90s"
            ignore_warnings = false
          }
        }
      }

      service {
        name = "coordinator-[[ stack ]]"
        port = "coordinator"
        provider = "nomad"

        tags = [
          "port=[[ coordinator_port ]]",
          "public=[[ coordinator_public_port ]]",
        ]
        canary_tags = [
          "canary",
        ]

        check {
          type = "http"
          port = "http"
          name = "app_health"
          path = "/healthz"
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
        image = "ghcr-proxy.openttd.org/openttd/game-coordinator[[ version ]]"
        args = [
          "--app", "coordinator",
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--db", "redis",
          "--proxy-protocol",
          "--socks-proxy", "socks5://nlb-internal.[[ domain ]]:8080",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http", "coordinator"]
      }

      env {
        GAME_COORDINATOR_SENTRY_DSN = "[[ sentry_dsn ]]"
        GAME_COORDINATOR_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"
        GAME_COORDINATOR_SHARED_SECRET = "[[ shared_secret ]]"
      }

      template {
        data = <<-EOT
          {{- range nomadService "redis-[[ stack ]]" }}
          GAME_COORDINATOR_REDIS_URL="redis://[{{ .Address }}]:{{ .Port }}/1"
          {{end}}
        EOT

        destination = "local/vars.env"
        env = true
      }

      resources {
        cpu = 100
        memory = [[ coordinator_memory ]]
        memory_max = [[ coordinator_memory_max ]]
      }
    }
  }

  group "stun" {
    count = [[ count ]]

    network {
      mode = "host"
      port "http" { to = 80 }
      port "stun" { to = 3975 }
    }

    update {
      max_parallel = 1
      health_check = "checks"
      auto_promote = true
      canary = 1
    }

    task "app" {
      driver = "docker"

      service {
        name = "stun-[[ stack ]]-web"
        port = "http"
        provider = "nomad"

        tags = [
          "metrics",
        ]
        canary_tags = [
          "canary",
        ]

        check {
          type = "http"
          name = "app_health"
          path = "/healthz"
          interval = "20s"
          timeout = "5s"

          check_restart {
            limit = 3
            grace = "90s"
            ignore_warnings = false
          }
        }
      }

      service {
        name = "stun-[[ stack ]]"
        port = "stun"
        provider = "nomad"

        tags = [
          "port=[[ stun_port ]]",
          "public=[[ stun_public_port ]]",
        ]
        canary_tags = [
          "canary",
        ]

        check {
          type = "http"
          port = "http"
          name = "app_health"
          path = "/healthz"
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
        image = "ghcr-proxy.openttd.org/openttd/game-coordinator[[ version ]]"
        args = [
          "--app", "stun",
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--db", "redis",
          "--proxy-protocol",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http", "stun"]
      }

      env {
        GAME_COORDINATOR_SENTRY_DSN = "[[ sentry_dsn ]]"
        GAME_COORDINATOR_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"
      }

      template {
        data = <<-EOT
          {{- range nomadService "redis-[[ stack ]]" }}
          GAME_COORDINATOR_REDIS_URL="redis://[{{ .Address }}]:{{ .Port }}/1"
          {{end}}
        EOT

        destination = "local/vars.env"
        env = true
      }

      resources {
        cpu = 100
        memory = [[ stun_memory ]]
        memory_max = [[ stun_memory_max ]]
      }
    }
  }

  group "turn-1" {
    count = 1

    network {
      mode = "host"
      port "http" { to = 80 }
      port "turn" { to = 3974 }

      # Both turn-1 and turn-2 use the same static port, forcing Nomad to schedule them on different nodes.
      port "affinity" {
        static = [[ affinity_port ]]
      }
    }

    task "app" {
      driver = "docker"

      service {
        name = "turn-1-[[ stack ]]-web"
        port = "http"
        provider = "nomad"

        tags = [
          "metrics",
        ]
        canary_tags = [
          "canary",
        ]

        check {
          type = "http"
          name = "app_health"
          path = "/healthz"
          interval = "20s"
          timeout = "5s"

          check_restart {
            limit = 3
            grace = "90s"
            ignore_warnings = false
          }
        }
      }

      service {
        name = "turn-1-[[ stack ]]"
        port = "turn"
        provider = "nomad"

        tags = [
          "port=[[ turn_1_port ]]",
          "public=[[ turn_1_public_port ]]",
        ]

        check {
          type = "http"
          port = "http"
          name = "app_health"
          path = "/healthz"
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
        image = "ghcr-proxy.openttd.org/openttd/game-coordinator[[ version ]]"
        args = [
          "--app", "turn",
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--db", "redis",
          "--proxy-protocol",
          "--turn-address", "[[ turn_hostname ]]-1.[[ domain ]]:[[ turn_1_public_port ]]",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http", "turn"]
      }

      env {
        GAME_COORDINATOR_SENTRY_DSN = "[[ sentry_dsn ]]"
        GAME_COORDINATOR_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"
      }

      template {
        data = <<-EOT
          {{- range nomadService "redis-[[ stack ]]" }}
          GAME_COORDINATOR_REDIS_URL="redis://[{{ .Address }}]:{{ .Port }}/1"
          {{end}}
        EOT

        destination = "local/vars.env"
        env = true
      }

      resources {
        cpu = 100
        memory = [[ turn_memory ]]
        memory_max = [[ turn_memory_max ]]
      }
    }
  }

  group "turn-2" {
    count = 1

    network {
      mode = "host"
      port "http" { to = 80 }
      port "turn" { to = 3974 }

      # Both turn-1 and turn-2 use the same static port, forcing Nomad to schedule them on different nodes.
      port "affinity" {
        static = [[ affinity_port ]]
      }
    }

    task "app" {
      driver = "docker"

      service {
        name = "turn-2-[[ stack ]]-web"
        port = "http"
        provider = "nomad"

        tags = [
          "metrics",
        ]
        canary_tags = [
          "canary",
        ]

        check {
          type = "http"
          name = "app_health"
          path = "/healthz"
          interval = "20s"
          timeout = "5s"

          check_restart {
            limit = 3
            grace = "90s"
            ignore_warnings = false
          }
        }
      }

      service {
        name = "turn-2-[[ stack ]]"
        port = "turn"
        provider = "nomad"

        tags = [
          "port=[[ turn_2_port ]]",
          "public=[[ turn_2_public_port ]]",
        ]

        check {
          type = "http"
          port = "http"
          name = "app_health"
          path = "/healthz"
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
        image = "ghcr-proxy.openttd.org/openttd/game-coordinator[[ version ]]"
        args = [
          "--app", "turn",
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--db", "redis",
          "--proxy-protocol",
          "--turn-address", "[[ turn_hostname ]]-2.[[ domain ]]:[[ turn_2_public_port ]]",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http", "turn"]
      }

      env {
        GAME_COORDINATOR_SENTRY_DSN = "[[ sentry_dsn ]]"
        GAME_COORDINATOR_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"
      }

      template {
        data = <<-EOT
          {{- range nomadService "redis-[[ stack ]]" }}
          GAME_COORDINATOR_REDIS_URL="redis://[{{ .Address }}]:{{ .Port }}/1"
          {{end}}
        EOT

        destination = "local/vars.env"
        env = true
      }

      resources {
        cpu = 100
        memory = [[ turn_memory ]]
        memory_max = [[ turn_memory_max ]]
      }
    }
  }
}
