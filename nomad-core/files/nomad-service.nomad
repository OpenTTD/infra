job "nomad-service" {
  datacenters = ["public"]
  type = "system"

  group "nomad-service" {
    count = 1

    network {
      mode = "host"
      port "http" {}
    }

    task "app" {
      driver = "exec"

      service {
        name = "nomad-service-web"
        port = "http"
        provider = "nomad"

        tags = [
          "port=10000"
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

      config {
        command = "local/nomad-service.py"
        args = [
          "${NOMAD_PORT_http}"
        ]
      }

      template {
        destination = "local/nomad-service.py"
        perms = "755"
        left_delimiter = "@@"
        right_delimiter = "@@"

        data =<<EOT
[[ content ]]
EOT
      }

      template {
        destination = "local/service-keys.json"
        change_mode = "signal"
        change_signal = "SIGHUP"

        data =<<EOT
{
{{ range nomadVarList "deploy-keys" }}
  "{{ .Path | trimPrefix "deploy-keys/" }}": {
    {{ with nomadVar .Path }}
      "key": "{{ .key }}"
    {{ end }}
  },
{{ end }}
  "fake": {}
}
EOT
      }

      resources {
        cpu = 100
        memory = 128
      }
    }
  }
}
