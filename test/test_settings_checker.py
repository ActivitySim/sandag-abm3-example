"""Exercise configuration preflight without running a simulation or loading skims."""

import ast
import importlib
from pathlib import Path

import pytest
import yaml

from activitysim.abm.models import settings_checker
from activitysim.core import workflow
from activitysim.core.exceptions import ModelConfigurationError


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_FILES = ("settings.yaml", "settings_mp.yaml", "settings_mp_sharrow.yaml")


def _extension_settings_files():
    """Discover declared settings independently of the registry under test."""
    settings_files = {}
    for source in (ROOT / "extensions").glob("*.py"):
        for node in ast.parse(source.read_text()).body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for arg, default in zip(
                node.args.args[-len(node.args.defaults) :], node.args.defaults
            ):
                if arg.arg == "model_settings_file_name":
                    settings_files[node.name] = ast.literal_eval(default)
    return settings_files


EXTENSION_SETTINGS_FILES = _extension_settings_files()
RESIDENT_MODELS = yaml.safe_load((ROOT / "configs/resident/settings.yaml").read_text())[
    "models"
]
ACTIVE_EXTENSIONS = sorted(set(RESIDENT_MODELS) & EXTENSION_SETTINGS_FILES.keys())


@pytest.fixture
def checker_state(tmp_path):
    """Keep checker output, global mappings, and file handlers isolated per test."""
    original_handlers = set(settings_checker.file_logger.handlers)

    def make_state(settings_file="settings.yaml", models=None, overlay=None):
        configs = [ROOT / "configs/common", ROOT / "configs/resident"]
        if overlay is not None:
            configs.insert(0, overlay)
        overrides = {}
        if models is not None:
            overrides.update(models=models, use_shadow_pricing=False)
        state = workflow.State.make_default(
            configs_dir=configs,
            data_dir=tmp_path,
            output_dir=tmp_path,
            working_dir=ROOT,
            settings_file_name=settings_file,
            settings=overrides,
        )
        state.import_extensions("extensions")
        # Discover the registry through the same imported-extension list as the CLI.
        registry = {}
        for extension in state.get_injectable("imported_extensions"):
            module = importlib.import_module(extension + ".settings_checker")
            registry.update(module.EXTENSION_CHECKER_SETTINGS)
        return state, registry

    yield make_state

    # The core checker adds a handler on each invocation and mutates its mapping.
    # _check supplies a copy; close the handlers so temporary files can be removed.
    for handler in set(settings_checker.file_logger.handlers) - original_handlers:
        settings_checker.file_logger.removeHandler(handler)
        handler.close()


def _check(state, registry):
    """Run preflight explicitly; running workflow steps does not invoke it."""
    settings_checker.check_model_settings(
        state,
        checker_settings=settings_checker.CHECKER_SETTINGS.copy(),
        extension_settings=registry,
    )


@pytest.mark.parametrize("settings_file", SETTINGS_FILES)
def test_resident_settings_preflight(checker_state, settings_file):
    state, registry = checker_state(settings_file)
    assert state.settings.check_model_settings
    _check(state, registry)


@pytest.mark.parametrize("settings_file", SETTINGS_FILES)
def test_active_extension_settings_are_registered(checker_state, settings_file):
    state, registry = checker_state(settings_file)
    active = set(state.settings.models) & EXTENSION_SETTINGS_FILES.keys()
    assert active
    assert (
        active <= registry.keys()
    ), f"Missing checker mappings: {active - registry.keys()}"
    for model in active:
        assert registry[model]["settings_file"] == EXTENSION_SETTINGS_FILES[model]


@pytest.mark.parametrize("model", ACTIVE_EXTENSIONS)
@pytest.mark.parametrize("broken_field", ("schema", "SPEC", "COEFFICIENTS"))
def test_invalid_extension_settings_fail(checker_state, tmp_path, model, broken_field):
    """Prove each active extension is validated, including its referenced files."""
    filename = EXTENSION_SETTINGS_FILES[model]
    baseline, _ = checker_state(models=[model])
    # Resolve include_settings before applying the one intentional defect.
    config = baseline.filesystem.read_model_settings(filename, mandatory=True)
    if broken_field == "schema":
        config["SPEC"] = ["invalid type: SPEC must be a filename"]
    else:
        config[broken_field] = "missing_checker_test_file.csv"
    overlay = tmp_path / "configs"
    overlay.mkdir()
    (overlay / filename).write_text(yaml.safe_dump(config))
    state, registry = checker_state(models=[model], overlay=overlay)
    with pytest.raises(ModelConfigurationError):
        _check(state, registry)
    log = (tmp_path / "settings_checker.log").read_text()
    if broken_field == "schema":
        assert f"Error checking settings for {model}" in log
        assert "SPEC" in log
    else:
        assert "missing_checker_test_file.csv" in log


def test_inactive_extensions_need_no_settings_files(checker_state, monkeypatch):
    """Keep airport/student code without requiring unused configuration files."""
    state, registry = checker_state()
    inactive = {
        "airport_returns",
        "external_student_identification",
        "external_school_location",
    }
    assert inactive <= registry.keys()
    assert inactive.isdisjoint(state.settings.models)
    assert not list(
        (ROOT / "configs").rglob(registry["airport_returns"]["settings_file"])
    )
    attempted_models = set()
    original = settings_checker.try_load_model_settings

    def record_load(*args, **kwargs):
        assert kwargs["model_name"] not in inactive
        attempted_models.add(kwargs["model_name"])
        return original(*args, **kwargs)

    monkeypatch.setattr(settings_checker, "try_load_model_settings", record_load)
    _check(state, registry)
    assert inactive.isdisjoint(attempted_models)
    assert set(ACTIVE_EXTENSIONS) <= attempted_models
