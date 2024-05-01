from __future__ import annotations

import logging

from activitysim.core import chunk, workflow
from activitysim.abm.models.initialize import InitializeTableSettings, annotate_tables

logger = logging.getLogger(__name__)


@workflow.step
def initialize_landuse_taz(
    state: workflow.State,
    model_settings: InitializeTableSettings | None = None,
    model_settings_file_name: str = "initialize_landuse_taz.yaml",
    trace_label: str = "initialize_landuse_taz",
) -> None:
    """
    Initialize the land use table.

    Parameters
    ----------
    state : State
    """
    if model_settings is None:
        model_settings = InitializeTableSettings.read_settings_file(
            state.filesystem,
            model_settings_file_name,
            mandatory=True,
        )
    with chunk.chunk_log(state, trace_label, base=True) as chunk_sizer:
        annotate_tables(state, model_settings, trace_label, chunk_sizer)
