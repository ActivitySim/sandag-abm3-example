#
# Note use of this exercise script requires the full-scale data archive to be
# downloaded. The archive is not provided in the repository, but can be downloaded
# from the activitysim examples repository. The archive is split into multiple parts,
# each part is a tar.zst archive. The archive is expected to be extracted into the
# `data-full` directory.
#
# This script employs the `wring` package to extract the archive. The `wring` package
# is not provided in the repository, but can be installed from PyPI.
#
#    python -m pip install wring
#

from activitysim.examples.external import download_external_example
from activitysim.cli.create import sha256_checksum
from wring import untarzst
from pathlib import Path
import os
from activitysim.core import workflow


def _exercise_path(dirname) -> Path:
    return Path(os.path.dirname(__file__)).joinpath(dirname)


GET_FULL_DATA = True

full_data_dir = _exercise_path("data-full")

def get_full_data():
    """
    Download the full-scale data archive and extract it.

    This function downloads the full-scale data archive, if not already present,
    and verifies that the data is correct by checking the sha256 checksum of each
    file. If the full scale data is already available, the whole data download
    process can be skipped by setting the global variable GET_FULL_DATA to False.
    """
    archive_sha256 = {
        11: "5b0c7ad009115830fbedaee9dd33981b3bab23b3b7177a7a0a8f3c871decf989",
        10: "c35b7c7f83be21159b20da8185cb5bd78b812378b424c20bdc1f5df51b283921",
        4: "13f04db524324b48b9244e872cc997c97a0a920548ce5d5ef3fe4af7f09e9517",
        3: "a6751f10aee9deec531582862368519f70f6d6f03f344bf82397d099d36537e1",
        2: "ee1cdab914dcba7a0feb01b65822c6160be3f60aba29f797259c7dd0a2a40d3a",
        5: "1663dfaf6eda027850f7c79a783d646bdc58a6a588bc1308fc31ea9cb3f85f2d",
        12: "35b664eedaece82b9ae0167664e618a7daa4079ca99ebf8cc01dd61d7ff4a51b",
        15: "776fed4a3bd01e98caa4aea4f36c99465af252d5ae1a66d66897496271805e35",
        14: "0cce0a90ac662e2d40d89abd28640dd5457e74f0b1a4eabd5f53f747955fe335",
        13: "767cc029fe36e0a67446cf822c4e34525053a0857228efb2f50c17785e88a7a1",
        9: "6e49b3738acfd0778becaf984f570906cfbc600e14f2de0d03c627f95c61afde",
        0: "adeae9915a0402b87937ba19e6732396d29813cec64bb1b1d2c66e336ca349a4",
        7: "3df78f56eb383c4adba4e32ccf78700151e71a8271f3f525317574cdcb61adbb",
        6: "a204166e2875368314cae7070fcd77591603c75565986dfb4b171b1e08400c4f",
        1: "4322559d96c7c1521760f875da7aeb92b9dae7a19824717f5c1ae086623f15a0",
        8: "7dfb447beaf4e5fc2f9656c7e6427a1149f3a0f3c5f6f7c285b508a279d7eab5",
    }

    full_data_sha256 = {
        "persons.parquet": "f41434b49d87aa9bb19296c5ae271c25a07356e3e370659a6230017c82c881b7",
        "transit_skims_PM.omx": "20d9af6f6be2f78ce81f817aca01eb05611a7a1702e9de896db8a918af11421f",
        "maz_maz_walk.parquet": "8759bdae920e6f507120e68eab3ead2e7738e240c22512469bc734cc95bb7c59",
        "traffic_skims_MD.omx": "5cdd041d4324f7898b17b22555af65201ed323cebaf7ba34a0351df981db733c",
        "households.parquet": "c75156d739ae71b01e0d3be7563b04a115b987bd8e8587173d7957aab58f4a89",
        "transit_skims_MD.omx": "535309745b79ad8a71601228b4bb6824e2996632fe177fe9e8cd7b56693eef4d",
        "traffic_skims_PM.omx": "434996674399cdfd1073c4d24cd8b3a5691c541f97386a8d29c4833b9ce85c7f",
        "traffic_skims_EA.omx": "fe097d769c373bd37ab24f57ff102c70213055aae73be9a5a9c3d5d762bf2f0e",
        "traffic_skims_EV.omx": "91c762df3288867a050395691cf1f13b9850f6e8ea55163730f8fceb4f8fca98",
        "transit_skims_AM.omx": "7fc26ce47bfc4c6844a6fcd193d4808dda711bf2a8e02a788b33ba21d000b88f",
        "maz_stop_walk.parquet": "f94fe8690db2342546be3592da4f20088bce7b026749f626a66ce2126555946e",
        "maz_maz_bike.parquet": "9ad9f5108b5dd88d893bc2cb56354400fe29749310d39919bc9e88e9b5ddb036",
        "land_use.parquet": "a2b41246fbfed8250e9fcda0853da1bd33a05cf5d0699f965a93759e39c8071b",
        "transit_skims_EV.omx": "6fcec702b5d4ebc01e88b5dec075fcc9b7ee6c26d32a751dc3b99536e80a336d",
        "transit_skims_EA.omx": "96111a202d4d2630fd2e749f9a3f96dbc6f314d4a3abb4d5cb92f0ff1337d6d0",
        "traffic_skims_AM.omx": "e31e1005897eaf30e3415b12c93696d88fbc42ee6c9b75f35178ad196f0eb80f",
    }

    download_required = False

    for filename, sha256 in full_data_sha256.items():
        f = full_data_dir.joinpath(filename)
        print("checking", f)
        if not f.exists() or sha256 != sha256_checksum(f):
            download_required = True
            break

    if download_required:
        print("downloading full data...")
        download_external_example(
            _exercise_path("."),
            name="sandag-abm3",
            assets={
                f"data-full.tar.zst.part{i:03}": {
                    "url": f"https://github.com/ActivitySim/sandag-abm3-example/releases/download/v0.2.0/data-full.tar.zst.part{i:03}",
                    "sha256": sha256,
                }
                for i, sha256 in archive_sha256.items()
            },
        )
        untarzst(
            _exercise_path("sandag-abm3/data-full.tar.zst.part000"),
            full_data_dir,
        )
        # recheck sha256
        for filename, sha256 in full_data_sha256.items():
            if not full_data_dir.joinpath(filename).exists():
                raise ValueError(f"data missing: {filename}")
            if sha256 != sha256_checksum(full_data_dir.joinpath(filename)):
                raise ValueError(f"data error: {filename}")
    else:
        print("full data ready")


def main(**settings):
    """
    Run the full-scale model exercise.
    """
    out_dir = _exercise_path("exercise-output")
    out_dir.mkdir(exist_ok=True)
    out_dir.joinpath(".gitignore").write_text("**\n")

    state = workflow.State.make_default(
        configs_dir=(
            _exercise_path(r"configs/common"),
            _exercise_path(r"configs/resident"),
        ),
        data_dir=_exercise_path("data-full"),
        output_dir=out_dir,
        settings=settings,
    )
    state.import_extensions("../extensions")
    state.filesystem.persist_sharrow_cache()
    state.run.all()
    return state


if __name__ == "__main__":

    if GET_FULL_DATA or not full_data_dir.exists():
        get_full_data()

    # Modify the settings value here to alter the default settings
    # defined in the various config files.
    state = main(
        cleanup_pipeline_after_run=False,
        treat_warnings_as_errors=False,
        households_sample_size=100_000,
        chunk_size=0,
        use_shadow_pricing=True,
        sharrow="require",
        recode_pipeline_columns=True,
        memory_profile=True,
        chunk_training_mode="explicit",
    )
