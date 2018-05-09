#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o xtrace


celery -A v3.taskapp worker -l INFO
