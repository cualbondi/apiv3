#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset


celery -A v3.taskapp worker -l INFO
