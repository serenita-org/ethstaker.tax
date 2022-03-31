#!/bin/sh

echo "Prepping multiprocessing metrics dir"
# Make sure the directory for the multiprocessing metrics exists
mkdir -p /tmp/prometheus_multiproc_dir

# Remove metrics left-over from previous runs with possibly
# conflicting PIDs
rm -f /tmp/prometheus_multiproc_dir/*

# Run the API
uvicorn src.api.app:app --host api --port 8000 --log-config etc/logging.yml
