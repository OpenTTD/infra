#!/bin/sh

set -e

cd $(dirname $0)

( cd global-config && pulumi up -r -s OpenTTD/prod )
( cd aws-core && pulumi up -r -s OpenTTD/prod )
# Refreshing cloudflare seems not possible.
( cd cloudflare-core && pulumi up -s OpenTTD/prod )
( cd nomad-core && pulumi up -r -s OpenTTD/prod )

APP_LIST="
bananas
binaries
cdn
dibridge
docs
dorpsgek
eints
multiplayer
preview
redirect
survey-web
symbols
website
wiki
wiki-data
"

IFS="
"

for app in ${APP_LIST}; do
    if [ -e app/${app}/Pulumi.preview.yaml ]; then
        ( cd app/${app} && pulumi up -r -s OpenTTD/preview )
    fi

    ( cd app/${app} && pulumi up -r -s OpenTTD/prod )
done
