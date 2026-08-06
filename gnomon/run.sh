#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

bashio::log.info "Starting Gnomon..."
exec python3 /app/app.py
