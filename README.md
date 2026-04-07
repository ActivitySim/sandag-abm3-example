# sandag-abm3-example

This example demonstrates the SANDAG ABM3 model.  This is ActivitySim's 
"prototypical" example of a two-zone model.

A full-scale exercise of the model is available via the `exercise.py` script,
which will download (large) data files to run the full-scale tests.

You can also run a smaller sized example set using the data files included
in this repository, using this command:

```
activitysim run -c configs/common -c configs/resident -d data -o output -s settings_mp.yaml --ext extensions
```

# Git diff with the ABM3 production model

The current guideline is that this example model _should_ be consistent with the [production model](https://github.com/SANDAG/ABM).

You can run the `diff_production_configs.py` script in this repo to automatically diff the example model configs with the production model configs.

## Usage
Basic exmaple - diff resident configs:
```
# Diff the resident configs of the latest release of production and the main branch of example
uv run python diff_production_configs.py -d resident
```

Specify release or branch of the production model with `-p`, branch of the example model with `-e`, and the subdirectory with `-d`:
```
# Diff specific release of production, branch of example, and subdirectory
uv run python diff_production_configs.py -p v15.3.1 -e main -d common

# Diff specific branch of production, branch of example, and subdirectory
uv run python diff_production_configs.py -p main -e sharrow-test -d common
```

Show full diff output, not just file names:
```
# with full output
uv run python diff_production_configs.py -p v15.3.1 -e main -d common --full
```