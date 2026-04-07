#!/usr/bin/env -S uv run --script --locked --no-project
#
# /// script
# requires-python = ">=3.10,<3.12"
# dependencies = [
#   "activitysim >=1.5,<2.0",
#   "sharrow >=2.15",
#   "wring >=0.0.6",
# ]
# [tool.uv]
# exclude-newer = "2025-11-01T00:00:00Z"
# ///

"""
Run the sandag-abm3 example model with sharrow enabled, on the full-scale sample.

The metadata in the header above allows this script to be run with `uv` without
needing to set up a separate virtual environment or install dependencies manually.

Use of this script requires the full-scale data archive to be downloaded. This data
is not provided in the repository itself due to its large size, but can be downloaded
and this script will do so as needed. The archive is split into multiple parts,
each part is a tar.zst archive. The archive is expected to be extracted into the
`data-full` directory.
"""

# Some tests by SANDAG are reporting crashes that seem to happen after an
# OpenBLAS warning that the precompiled NUM_THREADS was exceeded.
# see: https://github.com/ActivitySim/sandag-abm3-example/pull/39#issuecomment-3603510160
#
# The following environment variables limit the number of threads used by
# various numerical libraries to 1, which should hopefully prevent these problems.
# This may slow down the model run for single-process runs, but should improve
# stability and not seriously impact multiprocessing runs.

import os
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMBA_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
from pathlib import Path
from activitysim.core import workflow
import activitysim.abm  # register components # noqa: F401


def main():
    working_dir = Path(__file__).parents[1]
    out_dir = Path(str(__file__).replace(".py", "-output"))
    out_dir.mkdir(exist_ok=True)
    out_dir.joinpath(".gitignore").write_text("**\n")

    data_dir = "data-full"

    sys.path.insert(0, str(Path(__file__).parent))
    from fulldata import get_full_data

    # get full data if needed
    get_full_data(working_dir.joinpath(data_dir))

    settings = dict(
        cleanup_pipeline_after_run=False,
        treat_warnings_as_errors=False,
        households_sample_size=100_000,
        chunk_size=0,
        use_shadow_pricing=True,
        sharrow="require",
        recode_pipeline_columns=True,
        memory_profile=False,
    )

    state = workflow.State.make_default(
        working_dir=working_dir,
        configs_dir=(
            "configs/common",
            "configs/resident",
        ),
        data_dir=data_dir,
        output_dir=out_dir,
        settings=settings,
    )
    state.import_extensions("extensions")
    state.filesystem.persist_sharrow_cache()
    state.run.all()


if __name__ == "__main__":
    main()
