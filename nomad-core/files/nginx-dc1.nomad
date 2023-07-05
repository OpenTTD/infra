job "nginx-dc1" {
  datacenters = ["dc1"]

  type = "system"

  group "nginx" {
    network {
      mode = "host"
      port "http" { static = 80 }
    }

    task "nginx" {
      driver = "docker"

      service {
        name = "nginx-dc1"
        port = "http"
        provider = "nomad"

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
        image = "registry.ipv6.docker.com/library/nginx:1.25.0"
        args = [
        ]
        network_mode = "host"

        volumes = [
          "local:/etc/nginx",
        ]
      }

      template {
        data = <<EOT
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

include /etc/nginx/services.conf;

http {
    server {
        listen       80 default_server;
        listen       [::]:80 default_server;
        server_name  _;
        root         /usr/share/nginx/html;

        location /healthz {
            access_log off;
            return 200 "200: OK";
        }

        location / {
            proxy_pass http://www.openttd.org/;
            proxy_set_header Host $http_host;
        }
    }
}
EOT
        destination = "local/nginx.conf"
      }

      template {
        data = <<EOF

{{- define "getPort" -}}
  {{- range . -}}
    {{- if . | regexMatch "port=[0-9]+" -}}
      {{ . | trimPrefix "port=" }}
    {{- end -}}
  {{- end -}}
{{- end -}}

stream {
{{- range nomadServices }}
{{- $port := executeTemplate "getPort" .Tags }}
{{- if $port }}

  upstream {{ .Name | toLower }} {
    hash $remote_addr;

{{- range nomadService .Name }}
  {{- if in .Tags "canary" }}
  {{- else }}
    {{- if in .Address ":" }}
    server [{{ .Address }}]:{{ .Port }};
    {{- else }}
    server {{ .Address }}:{{ .Port }};
    {{- end }}
  {{- end }}
{{- end }}
  }

  server {
    listen {{ $port }} {{- if in .Tags "protocol=udp" }} udp{{ end -}};
    listen [::]:{{ $port }} {{- if in .Tags "protocol=udp" }} udp{{ end -}};

    proxy_pass {{ .Name | toLower }};

  {{- if in .Tags "protocol=udp" }}
    proxy_requests 1;
    proxy_timeout 30s;
  {{- end }}
  }

{{ end }}
{{- end }}
}
EOF

        destination   = "local/services.conf"
        change_mode   = "signal"
        change_signal = "SIGHUP"
      }

      resources {
        cpu = 100
        memory = 32
        memory_max = 64
      }
    }
  }
}
