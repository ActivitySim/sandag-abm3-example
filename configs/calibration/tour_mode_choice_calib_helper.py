import pandas as pd
import matplotlib.pyplot as plt
import os

SURVEY_DATA_FOLDER = "activitysim/examples/example_estimation/data_sf/survey_data"


def report_tour_mode_choice(context):
    model_tours = context["tours"]
    survey_tours = None
    survey_tours = pd.read_csv(os.path.join(SURVEY_DATA_FOLDER, "override_tours.csv"))

    model_summary = (
        model_tours.tour_mode.value_counts(normalize=True).sort_index().fillna(0)
    )
    if "tour_weight" in survey_tours.columns:
        survey_summary = survey_tours.groupby("tour_mode").tour_weight.sum()
        survey_summary = survey_summary / survey_tours.tour_weight.sum()
    else:
        survey_summary = survey_tours.groupby("tour_mode").size()

    summary_df = (
        pd.DataFrame({"model": model_summary, "survey": survey_summary})
        .reset_index()
        .rename(columns={"index": "tour_mode"})
    )

    # plot comparing model and survey distributions
    summary_df.plot(x="tour_mode", y=["model", "survey"], kind="bar")
    plt.title("Tour Mode Choice Distribution: Model vs Survey")
    plt.xlabel("Tour Mode")
    plt.ylabel("Proportion of Tours")
    plt.legend(title="Data Source")
    plt.savefig(
        os.path.join(context["component_output_dir"], "tour_mode_choice_comparison.png")
    )
    plt.close()


def get_tour_group(tour_df: pd.DataFrame, person_df: pd.DataFrame = None) -> pd.Series:
    ret_series = pd.Series(index=tour_df.index, dtype=str)
    ret_series.loc[tour_df.tour_type == "othmaint"] = "maint"
    ret_series.loc[tour_df.tour_type == "othdiscr"] = "disc"
    ret_series.loc[
        tour_df.tour_type.isin(["shopping", "escort"])
    ] = "maint"
    ret_series.loc[tour_df.tour_type.isin(["work", "atwork"])] = tour_df.loc[
        tour_df.tour_type.isin(["work", "atwork"])
    ].tour_type
    ret_series.loc[tour_df.tour_type.isin(["eatout", "social"])] = "disc"
    ret_series.loc[tour_df.tour_type == "univ"] = "univ"
    ret_series.loc[tour_df.tour_type == "school"] = "school"

    assert (
        not ret_series.isna().any()
    ), f"Tour group could not be determined for some tours:\n{tour_df.loc[ret_series.isna(),['tour_id','person_id','tour_type']]}"

    return ret_series
