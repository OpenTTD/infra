job "nginx" {
  datacenters = ["dc1"]

  type = "system"

  group "nginx" {
    network {
      mode = "host"
    }

    task "nginx" {
      driver = "docker"

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
  upstream {{ .Name | toLower }} {
    hash $remote_addr;

{{- range nomadService .Name }}
  {{- if in .Tags "canary" }}
  {{- else }}
    server [{{ .Address }}]:{{ .Port }};
  {{- end }}
{{- end }}
  }

{{- $port := executeTemplate "getPort" .Tags }}

  server {
    listen {{ $port }} {{- if in .Tags "protocol=udp" -}}udp{{- end -}};
    listen [::]:{{ $port }} {{- if in .Tags "protocol=udp" -}}udp{{- end -}};

    proxy_pass {{ .Name | toLower }};

    {{- if in .Tags "proxy-protocol" }}
      proxy_protocol on;
    {{- end }}

    {{- if in .Tags "protocol=udp" }}
      proxy_requests 1;
      proxy_timeout 30s;
    {{- end }}
  }

{{- end }}
}
EOF

        destination   = "local/services.conf"
        change_mode   = "signal"
        change_signal = "SIGHUP"
      }

      resources {
        cpu = 100
        memory = 64
      }
    }
  }
}
