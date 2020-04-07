#!/usr/bin/env bash
export ZOOM_ACCOUNT_EMAIL=${ZOOM_ACCOUNT_EMAIL:="zoomservice@wipac.wisc.edu"}
export ZOOM_ACCOUNT_PASSWORD=${ZOOM_ACCOUNT_PASSWORD:="hunter2"}  # http://bash.org/?244321
export ZOOM_APP_CLIENT_ID=${ZOOM_APP_CLIENT_ID:=""}
export ZOOM_APP_CLIENT_SECRET=${ZOOM_APP_CLIENT_SECRET:=""}
export ZOOM_TOKEN=${ZOOM_TOKEN:="ey..."}
python -m zml.zml
