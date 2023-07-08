#!/bin/sh

set -e

cd $(dirname $0)

( cd global-config && pulumi up -r -s prod )
( cd aws-core && pulumi up -r -s prod )
# Refreshing cloudflare seems not possible.
( cd cloudflare-core && pulumi up -s prod )
( cd nomad-core && pulumi up -r -s prod )

APP_LIST="
bananas
binaries
cdn
docs
dorpsgek
eints
multiplayer
preview
website
wiki
wiki-data
"

IFS="
"

for app in ${APP_LIST}; do
    if [ -e app/${app}/Pulumi.preview.yaml ]; then
        ( cd app/${app} && pulumi up -r -s preview )
    fi

    ( cd app/${app} && pulumi up -r -s prod )
done
