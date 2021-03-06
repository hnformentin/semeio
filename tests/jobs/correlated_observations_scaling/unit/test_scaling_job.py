import numpy as np
import pandas as pd
import pytest
import os
from ert_data import measured
from semeio.jobs.correlated_observations_scaling.job import ScalingJob
from semeio.jobs.correlated_observations_scaling.exceptions import ValidationError
from semeio.communication.reporter import FileReporter


def test_filter_on_column_index():
    matrix = np.random.rand(10, 10)

    index_lists = [[0, 1], [1, 2, 3], [1, 2, 3, 4, 5]]
    for index_list in index_lists:
        result = measured.MeasuredData._filter_on_column_index(
            pd.DataFrame(matrix), index_list
        )
        assert result.shape == (10, len(index_list))

    with pytest.raises(IndexError):
        measured.MeasuredData._filter_on_column_index(pd.DataFrame(matrix), [11])


@pytest.mark.parametrize(
    "calc_key,app_key,obs_keys,obs_with_data,scaling_job_content",
    [
        (
            "KEY_1",
            "KEY_1",
            ["KEY_1"],
            ["KEY_1"],
            {"get_index_lists": [None], "get_calc_keys": ["KEY_1"]},
        ),
        (
            "KEY_1",
            "KEY_1",
            ["KEY_1", "KEY_2"],
            ["KEY_1"],
            {"get_index_lists": [None], "get_calc_keys": ["KEY_1"]},
        ),
    ],
)
@pytest.mark.usefixtures("setup_tmpdir")
def test_valid_job(
    calc_key,
    app_key,
    obs_keys,
    obs_with_data,
    scaling_job_content,
):
    user_config_dict = {
        "CALCULATE_KEYS": {"keys": [{"key": calc_key}]},
        "UPDATE_KEYS": {"keys": [{"key": app_key}]},
    }
    default_vals = {
        "CALCULATE_KEYS": {"std_cutoff": 1.0e-6, "alpha": 3},
        "UPDATE_KEYS": {},
    }
    reporter = FileReporter(os.path.realpath(os.getcwd()))
    job = ScalingJob(
        obs_keys, [], obs_with_data, user_config_dict, reporter, default_vals
    )
    assert job.get_index_lists() == scaling_job_content["get_index_lists"]
    assert job.get_calc_keys() == scaling_job_content["get_calc_keys"]


@pytest.mark.parametrize("input_key", ["alpha", "std_cutoff"])
def test_config_value_overwrites_default(input_key):
    user_config_dict = {
        "CALCULATE_KEYS": {"keys": [{"key": "a_key"}], "alpha": 2, "std_cutoff": 0.01},
    }
    default_vals = {
        "CALCULATE_KEYS": {"std_cutoff": 1.0e-6, "alpha": 3},
        "UPDATE_KEYS": {},
    }
    reporter = FileReporter(os.path.realpath(os.getcwd()))
    job = ScalingJob(["a_key"], [], ["a_key"], user_config_dict, reporter, default_vals)

    # Check that the value equals the config value
    assert (
        getattr(job._config.snapshot.CALCULATE_KEYS, input_key)
        == user_config_dict["CALCULATE_KEYS"][input_key]
    )
    # Check that different from default value
    assert (
        getattr(job._config.snapshot.CALCULATE_KEYS, input_key)
        != default_vals["CALCULATE_KEYS"][input_key]
    )


@pytest.mark.parametrize("alpha", [True, False])
@pytest.mark.parametrize(
    "calc_key,app_key,obs_keys,obs_with_data,errors",
    [
        (
            "KEY_1",
            "KEY_1",
            ["KEY_1", "KEY_2"],
            ["KEY_2"],
            ["Key: KEY_1 has no data"],
        ),
        (
            "not_in_list",
            "KEY_1",
            ["KEY_1"],
            ["KEY_1"],
            [
                "Update key: KEY_1 missing from calculate keys: ['not_in_list']",
                "Key: not_in_list has no observations",
                "Key: not_in_list has no data",
            ],
        ),
        (
            "KEY_1",
            "not_in_list",
            ["KEY_1"],
            ["KEY_1"],
            ["Update key: not_in_list missing from calculate keys: ['KEY_1']"],
        ),
        (
            "KEY_1",
            "KEY_1",
            [],
            ["KEY_1"],
            ["Key: KEY_1 has no observations"],
        ),
        ("KEY_1", "KEY_1", ["KEY_1"], [], ["Key: KEY_1 has no data"]),
    ],
)
@pytest.mark.usefixtures("setup_tmpdir")
def test_invalid_job(
    calc_key,
    app_key,
    obs_keys,
    obs_with_data,
    errors,
    alpha,
):
    user_config_dict = {
        "CALCULATE_KEYS": {"keys": [{"key": calc_key}], "std_cutoff": 0.001},
        "UPDATE_KEYS": {"keys": [{"key": app_key}]},
    }

    if alpha:
        user_config_dict["CALCULATE_KEYS"]["alpha"] = 3
    else:
        errors.insert(
            0,
            "MissingKeyError(msg=Missing key: alpha, "
            "key_path=('CALCULATE_KEYS',), layer=None)",
        )

    reporter = FileReporter(os.path.realpath(os.getcwd()))

    with pytest.raises(ValidationError) as exc_info:
        ScalingJob(obs_keys, [], obs_with_data, user_config_dict, reporter)
    assert [str(elem) for elem in exc_info.value.errors] == errors
