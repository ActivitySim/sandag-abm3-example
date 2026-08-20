import matplotlib.pyplot as plt
import pandas as pd
import os


def report_auto_ownership(context):
    model_hhs = context["households"]

    # Read target shares from the calibration spec.
    spec_path = context["state"].filesystem.get_config_file_path(
        context["component_settings"].calibration_spec
    )
    spec = pd.read_csv(spec_path)
    # extract integer ownership level from description, e.g. "0 auto ownership share" -> 0
    spec["auto_ownership"] = spec["description"].str.extract(r"^(\d+)").astype(int)
    # 1-auto share is the remainder not explicitly targeted in the spec
    one_auto = max(0.0, 1.0 - spec["target_value"].sum())
    spec = pd.concat(
        [spec, pd.DataFrame({"auto_ownership": [1], "target_value": [one_auto]})],
        ignore_index=True,
    ).sort_values("auto_ownership")
    survey_summary = spec.set_index("auto_ownership")["target_value"]

    # To compare against an external survey file instead, replace above with:
    #   survey_hhs = pd.read_csv(os.path.join("path/to", "survey_households.csv"))
    #   survey_summary = survey_hhs.auto_ownership.value_counts(normalize=True).sort_index().fillna(0)
    # for an example of how to build targets directly from an external source, 
    # take a look at the `tour_mode_choice_calib_helper.py` file in the `configs/calibration` directory.

    model_summary = (
        model_hhs.auto_ownership.value_counts(normalize=True).sort_index().fillna(0)
    )
    summary_df = (
        pd.DataFrame({"model": model_summary, "survey": survey_summary})
        .reset_index()
        .rename(columns={"index": "num_autos"})
    )

    # plot comparing model and survey distributions
    summary_df.plot(x="auto_ownership", y=["model", "survey"], kind="bar")
    plt.title("Auto Ownership Distribution: Model vs Survey")
    plt.xlabel("Number of Autos")
    plt.ylabel("Proportion of Households")
    plt.legend(title="Data Source")
    plt.savefig(
        os.path.join(context["component_output_dir"], "auto_ownership_comparison.png")
    )
    plt.close()
