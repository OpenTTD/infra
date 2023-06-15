job "nlb-dns-update" {
  datacenters = ["public"]
  type = "service"

  group "nlb-dns-update" {
    count = 1

    network {
      mode = "host"
    }

    task "app" {
      driver = "exec"

      config {
        command = "local/nlb-dns-update.py"
      }

      template {
        destination = "local/nlb-dns-update.py"
        perms = "755"
        left_delimiter = "@@"
        right_delimiter = "@@"

        data =<<EOT
[[ content ]]
EOT
      }

      template {
        destination = "local/nlb.json"
        change_mode = "signal"
        change_signal = "SIGHUP"

        data =<<EOT
[
{{- range nomadService "nginx-public" }}
    "{{ .Address }}",
{{- end }}
    ""
]
EOT
      }

      resources {
        cpu = 100
        memory = 32
        memory_max = 128
      }
    }
  }
}
