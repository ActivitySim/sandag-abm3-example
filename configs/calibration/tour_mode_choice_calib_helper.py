from functools import lru_cache

import pandas as pd
import matplotlib.pyplot as plt
import os

# use the seaborn visual style bundled with matplotlib (no seaborn dependency needed)
try:
    plt.style.use("seaborn-v0_8")
except OSError:
    plt.style.use("seaborn")

TOUR_MODE_TARGETS = os.path.join(os.path.dirname(__file__), "tour_mode_choice_calibration_targets.csv")
TARGET_TRANSIT_MODES = ["WALK-TRANSIT", "PNR-TRANSIT", "KNR-TRANSIT", "TNC-TRANSIT"]

def report_tour_mode_choice(context):
    """Plot regular model tours alongside their scaled calibration targets."""
    _report_tour_mode_choice_by_auto_suff(
        context,
        include_atwork=False,
        file_name="tour_mode_choice_comparison.png",
        title="Tour Mode Choice: Scaled Model vs Target Tours",
    )
    _report_tour_mode_choice_by_purpose(
        context,
        include_atwork=False,
        file_name_prefix="tour_mode_choice_comparison",
        title_prefix="Tour Mode Choice",
    )


def report_atwork_tour_mode_choice(context):
    """Plot at-work subtours alongside their scaled calibration targets."""
    _report_tour_mode_choice_by_auto_suff(
        context,
        include_atwork=True,
        file_name="atwork_tour_mode_choice_comparison.png",
        title="At-work Tour Mode Choice: Scaled Model vs Target Tours",
    )
    _report_tour_mode_choice_by_purpose(
        context,
        include_atwork=True,
        file_name_prefix="atwork_tour_mode_choice_comparison",
        title_prefix="At-work Tour Mode Choice",
    )


def _grouped_barplot(data, x, y, hue, ax=None):
    """Grouped bar chart for pre-aggregated data, replacing sns.barplot."""
    if ax is None:
        ax = plt.gca()
    x_labels = data[x].unique().tolist()
    hue_vals = data[hue].unique().tolist()
    n_hue = len(hue_vals)
    bar_width = 0.8 / n_hue
    offsets = [(i - n_hue / 2 + 0.5) * bar_width for i in range(n_hue)]
    x_pos = list(range(len(x_labels)))
    for j, hue_val in enumerate(hue_vals):
        subset = data[data[hue] == hue_val].set_index(x)[y].reindex(x_labels, fill_value=0)
        ax.bar([p + offsets[j] for p in x_pos], subset.values, width=bar_width, label=hue_val)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels)
    ax.legend(title=hue)
    return ax


def _report_tour_mode_choice_by_auto_suff(context, include_atwork, file_name, title):
    """Plot the requested tour purposes against their scaled targets.

    Produces a 2x2 grid of subplots — one per auto-sufficiency category plus
    one aggregated "All" panel — where each bar shows the percent share of
    tours for each mode.
    """
    targets = get_targets()
    targets = targets[
        (targets.grouped_tour_mode != "All")
        & (targets.auto_suff != "All")
        & (targets.purpose != "Total")
    ]
    if include_atwork:
        targets = targets[targets.purpose == "Work sub-tour"]
    else:
        targets = targets[targets.purpose != "Work sub-tour"]

    auto_suff_values = sorted(targets["auto_suff"].unique().tolist())
    modes = targets["grouped_tour_mode"].unique().tolist()
    purposes = targets["purpose"].unique().tolist()

    # Build a long-form dataframe with columns: tour_mode, auto_suff, source, tours
    rows = []
    for auto_suff in auto_suff_values:
        for mode in modes:
            # sum across all purposes for the given auto_suff/mode combination
            model_val = sum(
                get_model_value(context, mode, auto_suff, purpose)
                for purpose in purposes
            )
            target_val = sum(
                get_target_value(context, mode, auto_suff, purpose)
                for purpose in purposes
            )
            rows.append({"tour_mode": mode, "auto_suff": auto_suff, "source": "Survey", "tours": target_val})
            rows.append({"tour_mode": mode, "auto_suff": auto_suff, "source": "Model", "tours": model_val})

    viz_df = pd.DataFrame(rows)

    # Append an "All" auto-sufficiency group by summing across categories
    all_rows = viz_df.groupby(["tour_mode", "source"])["tours"].sum().reset_index()
    all_rows["auto_suff"] = "All"
    viz_df = pd.concat([viz_df, all_rows], ignore_index=True)

    fig = plt.figure(figsize=(20, 15))
    plot_idx = 221  # 2-row x 2-col grid, starting at subplot 1

    for auto_suff in auto_suff_values:
        plt.subplot(plot_idx)
        data = viz_df[viz_df["auto_suff"] == auto_suff].copy()
        # convert raw counts to percent share within each source
        for source, total in data.groupby("source")["tours"].sum().items():
            data.loc[data["source"] == source, "percent"] = (
                data.loc[data["source"] == source, "tours"] / total * 100
            )
        _grouped_barplot(data, x="tour_mode", y="percent", hue="source")
        plt.title(f"{title}, Auto Sufficiency: {auto_suff}", fontsize=18)
        plt.xticks(rotation=90, fontsize=13)
        plt.yticks(fontsize=16)
        plt.ylabel("Percent", fontsize=16)
        plt.xlabel("Tour Mode", fontsize=16)
        plot_idx += 1

    plt.subplot(plot_idx)
    data = viz_df[viz_df["auto_suff"] == "All"].copy()
    for source, total in data.groupby("source")["tours"].sum().items():
        data.loc[data["source"] == source, "percent"] = (
            data.loc[data["source"] == source, "tours"] / total * 100
        )
    _grouped_barplot(data, x="tour_mode", y="percent", hue="source")
    plt.title(f"{title}, Auto Sufficiency: All", fontsize=18)
    plt.xticks(rotation=90, fontsize=13)
    plt.yticks(fontsize=16)
    plt.ylabel("Percent", fontsize=16)
    plt.xlabel("Tour Mode", fontsize=16)

    plt.tight_layout()
    fig.savefig(os.path.join(context["component_output_dir"], file_name))
    plt.close()


def _report_tour_mode_choice_by_purpose(context, include_atwork, file_name_prefix, title_prefix):
    """Produce 2x2 grid figures of percent mode share, one subplot per purpose."""
    targets = get_targets()
    targets = targets[
        (targets.grouped_tour_mode != "All")
        & (targets.auto_suff != "All")
        & (targets.purpose != "Total")
    ]
    if include_atwork:
        targets = targets[targets.purpose == "Work sub-tour"]
    else:
        targets = targets[targets.purpose != "Work sub-tour"]

    auto_suff_values = sorted(targets["auto_suff"].unique().tolist())
    purposes = targets["purpose"].unique().tolist()

    # pack purposes into 2x2 grids, saving as many figures as needed
    batch_size = 4
    for batch_idx, batch_start in enumerate(range(0, len(purposes), batch_size)):
        batch_purposes = purposes[batch_start : batch_start + batch_size]
        fig, axes = plt.subplots(2, 2, figsize=(20, 15))
        axes_flat = axes.flatten()

        for i, purpose in enumerate(batch_purposes):
            modes = targets.loc[
                targets.purpose == purpose, "grouped_tour_mode"
            ].unique().tolist()

            rows = []
            for mode in modes:
                # sum tours across all auto-sufficiency categories
                model_val = sum(
                    get_model_value(context, mode, auto_suff, purpose)
                    for auto_suff in auto_suff_values
                )
                target_val = sum(
                    get_target_value(context, mode, auto_suff, purpose)
                    for auto_suff in auto_suff_values
                )
                rows.append({"tour_mode": mode, "source": "Survey", "tours": target_val})
                rows.append({"tour_mode": mode, "source": "Model", "tours": model_val})

            viz_df = pd.DataFrame(rows)
            for source, total in viz_df.groupby("source")["tours"].sum().items():
                viz_df.loc[viz_df["source"] == source, "percent"] = (
                    viz_df.loc[viz_df["source"] == source, "tours"] / total * 100
                )

            ax = axes_flat[i]
            _grouped_barplot(viz_df, x="tour_mode", y="percent", hue="source", ax=ax)
            ax.set_title(f"{title_prefix}: {purpose}", fontsize=18)
            ax.tick_params(axis="x", rotation=90, labelsize=13)
            ax.tick_params(axis="y", labelsize=16)
            ax.set_ylabel("Percent", fontsize=16)
            ax.set_xlabel("Tour Mode", fontsize=16)

        # hide any unused subplots in the last figure
        for i in range(len(batch_purposes), batch_size):
            axes_flat[i].set_visible(False)

        plt.tight_layout()
        fig.savefig(
            os.path.join(
                context["component_output_dir"],
                f"{file_name_prefix}_by_purpose_{batch_idx + 1}.png",
            )
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
    # Auto and non-motorized modes already use the target-file names.
    tours["tour_mode_group"] = tours["tour_mode"].copy()
    tours.loc[tours.tour_mode.isin(["WALK_LOC", "WALK_PRM", "WALK_MIX"]), "tour_mode_group"] = "WALK-TRANSIT"
    tours.loc[tours.tour_mode.isin(["PNR_LOC", "PNR_PRM", "PNR_MIX"]), "tour_mode_group"] = "PNR-TRANSIT"
    tours.loc[tours.tour_mode.isin(["KNR_LOC", "KNR_PRM", "KNR_MIX"]), "tour_mode_group"] = "KNR-TRANSIT"
    tours.loc[tours.tour_mode.isin(["TNC_LOC", "TNC_PRM", "TNC_MIX"]), "tour_mode_group"] = "TNC-TRANSIT"
    tours.loc[tours.tour_mode == "TNC_SINGLE", "tour_mode_group"] = "TNC-REG"
    tours.loc[tours.tour_mode == "TNC_SHARED", "tour_mode_group"] = "TNC-SHARED"
    tours.loc[tours.tour_mode == "SCH_BUS", "tour_mode_group"] = "SCHOOLBUS"
    target_modes = set(get_targets()["grouped_tour_mode"].dropna()) - {"All"}
    invalid_mode = tours.tour_mode_group.isna() | ~tours.tour_mode_group.isin(
        target_modes
    )
    if invalid_mode.any():
        invalid_tours = tours.loc[
            invalid_mode, ["tour_id", "person_id", "tour_mode"]
        ]
        raise ValueError(
            "Tour mode group could not be matched to a calibration target for "
            f"some tours:\n{invalid_tours}"
        )

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
    tours = prepare_model_tours(context)
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

    total_target_tours = num_transit_target_tours + num_non_transit_target_tours
    if num_non_transit_target_tours == 0:
        # There is no non-transit target mass available to absorb the difference
        # between model and transit totals. Preserve transit targets when they
        # fit; otherwise scale them down to the model total.
        if num_transit_target_tours > num_model_tours and total_target_tours > 0:
            scale_factor = num_model_tours / total_target_tours
        else:
            scale_factor = 1.0
    else:
        non_transit_scale = (
            num_model_tours - num_transit_target_tours
        ) / num_non_transit_target_tours

        # If transit targets exceed the model total, scaling only non-transit
        # tours would require a negative factor. Scale every mode instead.
        if non_transit_scale < 0:
            scale_factor = (
                num_model_tours / total_target_tours
                if total_target_tours > 0
                else 1.0
            )
        elif mode in TARGET_TRANSIT_MODES:
            # Otherwise preserve the independently derived transit counts.
            scale_factor = 1.0
        else:
            scale_factor = non_transit_scale

    category_target = targets.loc[
        (targets.auto_suff == auto_suff)
        & (targets.purpose == purpose)
        & (targets.grouped_tour_mode == mode),
        "tours",
    ].sum()

    return category_target * scale_factor
