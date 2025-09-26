from .av_ownership import AVOwnershipSettings
from .external_identification import ExternalIdentificationSettings
from .transponder_ownership import TransponderOwnershipSettings

from activitysim.core.configuration.base import PydanticReadable
from activitysim.core.configuration.logit import (
    TourLocationComponentSettings,
    TourModeComponentSettings,
)
from activitysim.core.workflow import State



### SETTINGS FORMAT ###
### {"<model_name>": {"settings_cls": <PydanticSettings Object>, "settings_file": "<name of YAML file"}}
### If a specific Pydantic data model is not defined, map to PydanticReadable to expose .read_settings_file() method
### If required, an alternate set of spec/coefficients to resolve together can be defined for a model using
###    "spec_coefficient_keys": [{"spec": "OUTBOUND_SPEC", "coefs": "OUTBOUND_COEFFICIENTS"}, ...]
EXTENSION_CHECKER_SETTINGS = {
    "airport_returns": {
        "settings_cls": PydanticReadable,
        "settings_file": "airport_returns.yaml"
    },
    "av_ownership": {
        "settings_cls": AVOwnershipSettings,
        "settings_file": "av_ownership.yaml"
    },
    "external_student_identification": {
        "settings_cls": ExternalIdentificationSettings,
        "settings_file": "external_student_identification.yaml"
    },
    "external_non_mandatory_tour_identification": {
        "settings_cls": ExternalIdentificationSettings,
        "settings_file": "external_non_mandatory_identification.yaml"
    },
    "external_joint_tour_identification": {
        "settings_cls": ExternalIdentificationSettings,
        "settings_file": "external_joint_tour_identification.yaml"
    },
    "external_school_location": {
        "settings_cls": TourLocationComponentSettings,
        "settings_file": "external_school_location.yaml"
    },
    "external_workplace_location": {
        "settings_cls": TourLocationComponentSettings,
        "settings_file": "external_workplace_location.yaml"
    },
    "external_non_mandatory_destination": {
        "settings_cls": TourLocationComponentSettings,
        "settings_file": "external_non_mandatory_destination.yaml"
    },
    "external_joint_tour_destination": {
        "settings_cls": TourLocationComponentSettings,
        "settings_file": "external_joint_tour_destination.yaml"
    },
    "transponder_ownership": {
        "settings_cls": TransponderOwnershipSettings,
        "settings_file": "transponder_ownership.yaml"
    },
}