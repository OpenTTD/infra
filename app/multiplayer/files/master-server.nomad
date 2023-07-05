job "master-server-[[ stack ]]" {
  datacenters = ["dc1"]
  type = "service"

  spread {
    attribute = "${node.unique.id}"
  }

  group "master-server" {
    count = [[ count ]]

    network {
      mode = "host"
      port "http" { to = 80 }
      port "master" { to = 3978 }
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
        name = "master-server-[[ stack ]]"
        port = "master"
        provider = "nomad"

        tags = [
          "port=[[ master_port ]]",
          "public=[[ master_public_port ]]",
          "protocol=udp",
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
        image = "ghcr-proxy.openttd.org/openttd/master-server[[ version ]]"
        args = [
          "--app", "master_server",
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--db", "redis",
          "--proxy-protocol",
          "--socks-proxy", "socks5://nlb-internal.[[ domain ]]:8080",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http", "master"]
      }

      env {
        MASTER_SERVER_SENTRY_DSN = "[[ sentry_dsn ]]"
        MASTER_SERVER_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"
      }

      template {
        data = <<-EOT
          {{- range nomadService "redis-[[ stack ]]" }}
          MASTER_SERVER_REDIS_URL="redis://[{{ .Address }}]:{{ .Port }}/1"
          {{end}}
        EOT

        destination = "local/vars.env"
        env = true
      }

      resources {
        cpu = 100
        memory = [[ master_memory ]]
        memory_max = [[ master_memory_max ]]
      }
    }
  }

  group "api" {
    count = [[ count ]]

    network {
      mode = "host"
      port "http" { to = 80 }
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
        name = "master-server-api-[[ stack ]]"
        port = "http"
        provider = "nomad"

        tags = [
          "port=[[ api_port ]]",
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
        image = "ghcr-proxy.openttd.org/openttd/master-server[[ version ]]"
        args = [
          "--app", "web_api",
          "--bind", "::",
          "--bind", "0.0.0.0",
          "--db", "redis",
        ]
        network_mode = "bridge"
        advertise_ipv6_address = true
        ports = ["http"]
      }

      env {
        MASTER_SERVER_SENTRY_DSN = "[[ sentry_dsn ]]"
        MASTER_SERVER_SENTRY_ENVIRONMENT = "[[ sentry_environment ]]"
      }

      template {
        data = <<-EOT
          {{- range nomadService "redis-[[ stack ]]" }}
          MASTER_SERVER_REDIS_URL="redis://[{{ .Address }}]:{{ .Port }}/1"
          {{end}}
        EOT

        destination = "local/vars.env"
        env = true
      }

      resources {
        cpu = 100
        memory = [[ api_memory ]]
        memory_max = [[ api_memory_max ]]
      }
    }
  }
}
