#!/usr/bin/env bash

# exit on error, undefined variable, and fail on pipe errors
set -euxo pipefail

# set the directory to the location of this script
cd "$(dirname "$0")/.."

# set output directory to name of script without .sh extension
OUTPUT_DIR="output-$(basename "$0" .sh)"

# run activitysim with multiprocessing settings
uv run --project .. activitysim run \
  -c configs/common \
  -c configs/resident \
  -d data-full \
  -o scripts/${OUTPUT_DIR} \
  -s settings_mp.yaml \
  --ext extensions \
  --multiprocess 8 \
  --persist-sharrow-cache \
  --households_sample_size 500000

