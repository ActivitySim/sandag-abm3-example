from functools import lru_cache

import pandas as pd
import matplotlib.pyplot as plt
import os

TOUR_MODE_TARGETS = os.path.join(os.path.dirname(__file__), "tour_mode_choice_calibration_targets.csv")
TARGET_TRANSIT_MODES = ["WALK-TRANSIT", "PNR-TRANSIT", "KNR-TRANSIT", "TNC-TRANSIT"]

def report_tour_mode_choice(context):
    """Plot scaled model tours alongside their scaled calibration targets."""
    targets = get_targets()
    targets = targets[
        (targets.grouped_tour_mode != "All")
        & (targets.auto_suff != "All")
        & (targets.purpose != "Total")
    ]

    comparison_rows = []
    for target in targets.itertuples(index=False):
        comparison_rows.append(
            {
                "category": f"{target.purpose} | auto sufficiency {target.auto_suff} | {target.grouped_tour_mode}",
                "model": get_model_value(
                    context,
                    target.grouped_tour_mode,
                    target.auto_suff,
                    target.purpose,
                ),
                "target": get_target_value(
                    context,
                    target.grouped_tour_mode,
                    target.auto_suff,
                    target.purpose,
                ),
            }
        )

    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df.plot(x="category", y=["model", "target"], kind="bar")
    plt.title("Tour Mode Choice: Scaled Model vs Target Tours")
    plt.xlabel("Purpose, Auto Sufficiency, and Tour Mode")
    plt.ylabel("Tours")
    plt.legend(title="Data Source")
    plt.tight_layout()
    plt.savefig(
        os.path.join(context["component_output_dir"], "tour_mode_choice_comparison.png")
    )
    plt.close()

def _sample_rate(context):
    """
    Returns the sample rate for the model tours, based on the household sample
    rate. Assumes that all households have the same sample rate.
    """
    households = context["households"]
    if "sample_rate" in households.columns:
        return households.sample_rate.iloc[0]
    else:
        return 1.0


@lru_cache()
def get_targets() -> pd.DataFrame:
    """
    Loads and returns the survey-based tour mode choice calibration targets.

    Cached (no arguments) since the target data is static for the duration of
    a Python process.
    """
    targets = pd.read_csv(TOUR_MODE_TARGETS)
    return targets

@lru_cache()
def prepare_model_tours(context) -> pd.DataFrame:
    """
    Adds a ``tour_purp_group`` column to the model tours dataframe, grouping
    ActivitySim tour purposes into the categories used by the calibration
    targets (e.g. "Work", "Ind-Maintenance", "Joint-Discretionary", ...).

    Parameters
    ----------
    tours : pd.DataFrame
        The model tours dataframe
    """
    cached_tours = context.get("_prepared_model_tours")
    if cached_tours is not None:
        return cached_tours

    tours = context["tours"].copy()  # make a copy so we don't modify the original dataframe

    # determine the tour purposes groupings you want to calibrate to
    tours['tour_purp_group'] = pd.NA
    tours.loc[tours.tour_type == "work", "tour_purp_group"] = "Work"
    tours.loc[tours.tour_type == "school", "tour_purp_group"] = "School"
    tours.loc[tours.tour_type == "univ", "tour_purp_group"] = "University"
    tours.loc[tours.tour_type.isin(["shopping", "escort", "othmaint"]) & (tours.tour_category != "joint"), "tour_purp_group"] = "Ind-Maintenance"
    tours.loc[tours.tour_type.isin(["eatout", "social", "othdiscr"]) & (tours.tour_category != "joint"), "tour_purp_group"] = "Ind-Discretionary"
    tours.loc[tours.tour_type.isin(["shopping", "escort", "othmaint"]) & (tours.tour_category == "joint"), "tour_purp_group"] = "Joint-Maintenance"
    tours.loc[tours.tour_type.isin(["eatout", "social", "othdiscr"]) & (tours.tour_category == "joint"), "tour_purp_group"] = "Joint-Discretionary"
    tours.loc[tours.tour_category == "atwork", "tour_purp_group"] = "Work sub-tour"
    assert (
        tours.tour_purp_group.isna().sum() == 0
    ), f"Tour purpose group could not be determined for some tours:\n{tours.loc[tours.tour_purp_group.isna(),['tour_id','person_id','tour_type','tour_category']]}"


    # code the tour mode groupings that are defined in the targets file
    tours['tour_mode_group'] = tours["tour_mode"].copy()  # auto and non-motorized modes have same coding in targets
    tours.loc[tours.tour_mode.isin(["WALK_LOC", "WALK_PRM", "WLK_MIX"]), "tour_mode_group"] = "WALK-TRANSIT"
    tours.loc[tours.tour_mode.isin(["PNR_LOC", "PNR_PRM", "PNR_MIX"]), "tour_mode_group"] = "PNR-TRANSIT"
    tours.loc[tours.tour_mode.isin(["KNR_LOC", "KNR_PRM", "KNR_MIX"]), "tour_mode_group"] = "KNR-TRANSIT"
    tours.loc[tours.tour_mode.isin(["TNC_LOC", "TNC_PRM", "TNC_MIX"]), "tour_mode_group"] = "TNC-TRANSIT"
    tours.loc[tours.tour_mode == "TNC_SINGLE", "tour_mode_group"] = "TNC-REG"
    tours.loc[tours.tour_mode == "TNC_SHARED", "tour_mode_group"] = "TNC-SHARED"
    tours.loc[tours.tour_mode == "SCH_BUS", "tour_mode_group"] = "SCHOOLBUS"
    assert (
        tours.tour_mode_group.isna().sum() == 0
    ), f"Tour mode group could not be determined for some tours:\n{tours.loc[tours.tour_mode_group.isna(),['tour_id','person_id','tour_mode']]}"

    # code auto sufficiency category for each tour based on the household's auto ownership and number of adults
    tours = tours.merge(
        context["households"][["auto_ownership", "num_adults", "sample_rate"]],
        left_on="household_id",
        right_index=True,
        how="left",
    )
    tours['auto_suff'] = pd.NA
    tours.loc[tours.auto_ownership == 0, "auto_suff"] = "0"
    tours.loc[
        (tours.auto_ownership > 0) & (tours.auto_ownership < tours.num_adults), "auto_suff"
    ] = "1"
    tours.loc[
        (tours.auto_ownership > 0) & (tours.auto_ownership >= tours.num_adults), "auto_suff"
    ] = "2"
    assert (
        tours.auto_suff.isna().sum() == 0
    ), f"Auto sufficiency category could not be determined for some tours:\n{tours.loc[tours.auto_suff.isna(),['tour_id','person_id','household_id','auto_ownership','num_adults']]}"

    # save in the cache so we don't have to recalculate every time
    context["_prepared_model_tours"] = tours
    
    return tours


def get_model_value(context, mode, auto_suff, purpose):
    """
    Returns the full-scale (population-level) number of model tours for a
    given mode, auto sufficiency, and purpose. The raw (sample) tour count is
    expanded to full scale by dividing by the household sample rate.

    Parameters
    ----------
    context : dict
        The calibration evaluation context, containing at least "tours" and
        "households" dataframes.
    mode : str
        The mode of transportation (name to match title in spec), or "All"
        to include all modes.
    auto_suff : str
        The auto sufficiency category ("zero-auto", "auto-deficient", "auto-sufficient")
    purpose : str
        The tour purpose group (e.g. "Work", "Ind-Maintenance", "Joint-Discretionary")
    """
    tours = prepare_model_tours(context)

    mask = (tours.tour_mode_group == mode) & (tours.auto_suff == auto_suff) & (tours.tour_purp_group == purpose)

    model_count = tours.loc[mask].shape[0]

    return model_count / _sample_rate(context)


def get_target_value(context, mode, auto_suff, purpose):
    """
    Returns the survey-based target number of tours for a given mode, auto
    sufficiency, and purpose, scaled to match the model's total number of tours
    in that auto sufficiency/purpose category.

    The survey mode share (mode tours / total tours for the auto_suff/purpose
    category) is multiplied by the model's full-scale total tours for that same
    category, so that survey and model totals agree per category while
    preserving the survey's relative mode split.  Transit tours are not scaled,
    under the assumption that the survey targets were derived independently from
    on-board survey data and the model output should match the actual number,
    not the share.

    Parameters
    ----------
    context : dict
        The calibration evaluation context, containing at least "tours" and
        "households" dataframes.
    mode : str
        The mode of transportation (name to match title in spec)
    auto_suff : str
        The auto sufficiency category ("zero-auto", "auto-deficient",
        "auto-sufficient")
    purpose : str
        The tour purpose group (e.g. "Work", "Ind-Maintenance",
        "Joint-Discretionary")
    """
    tours = prepare_model_tours(context, context["tours"])
    targets = get_targets()

    num_model_tours = (
        tours.loc[
            (tours.auto_suff == auto_suff) & (tours.tour_purp_group == purpose)
        ].shape[0]
        / _sample_rate(context)
    )

    num_transit_target_tours = targets.loc[
        (targets.auto_suff == auto_suff) 
        & (targets.purpose == purpose) 
        & (targets.grouped_tour_mode.isin(TARGET_TRANSIT_MODES))
    ]["tours"].sum()
    num_non_transit_target_tours = targets.loc[
        (targets.auto_suff == auto_suff) 
        & (targets.purpose == purpose) 
        & (targets.grouped_tour_mode != "All")
        & (~targets.grouped_tour_mode.isin(TARGET_TRANSIT_MODES))
    ]["tours"].sum()

    scale_factor = (num_model_tours - num_transit_target_tours) / num_non_transit_target_tours

    # do not scale transit tours under the assumption we want the exact number
    # of transit tours to match the target.  This is under the assumption that
    # transit targets were derived independently from on-board survey data and
    # the model output should match the actual number, not the share.
    if mode in TARGET_TRANSIT_MODES and scale_factor > 0:
        scale_factor = 1.0

    # if number of transit target tours exceeds the total number of model tours,
    # we can't scale the non-transit target tours to match the model total while
    # keeping transit constant.  In this case, we will scale the transit tours
    # too such that the share across the modes is preserved, but the total
    # number of tours matches the model total.
    if scale_factor < 0:
        scale_factor = num_model_tours / (num_transit_target_tours + num_non_transit_target_tours)

    category_target = targets.loc[
        (targets.auto_suff == auto_suff)
        & (targets.purpose == purpose)
        & (targets.grouped_tour_mode == mode),
        "tours",
    ].sum()

    return category_target * scale_factor
