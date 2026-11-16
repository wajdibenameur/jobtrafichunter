"""CLI privacy and filesystem contract, with explicitly synthetic local data."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.modules.matching import calibration_cli as cli
from app.modules.matching.tests.test_calibration import synthetic_corpus, synthetic_scores


def fixture_file(tmp_path: Path) -> Path:
    path = tmp_path / "SYNTHETIC_PRIVATE_PATH.json"
    path.write_text(synthetic_corpus().model_dump_json(), encoding="utf-8")
    return path


def test_cli_runs_without_configuration_database_or_network(tmp_path: Path) -> None:
    source = fixture_file(tmp_path)
    env = os.environ.copy()
    env.update(DATABASE_URL="deliberately-invalid-offline", JWT_SECRET="", CV_ENCRYPTION_KEY="")
    result = subprocess.run(
        [sys.executable, "-m", "app.modules.matching.calibration_cli", "--input", str(source)],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )
    assert result.returncode == 0 and not result.stderr
    report = json.loads(result.stdout)
    assert report["calibration_status"] == "UNVALIDATED"
    assert report["cohorts"][0]["baseline"]["target_status"] == "INCOMPLETE"
    assert "SYNTHETIC_PRIVATE" not in result.stdout


def test_validate_only_does_not_call_scorer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Format validation must not score")

    monkeypatch.setattr(cli, "evaluate", forbidden)
    assert cli.main(["--input", str(fixture_file(tmp_path)), "--validate-only"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "format_valid": True,
        "calibration_status": "UNVALIDATED",
        "case_count": 4,
        "snapshot_count": 1,
    }


def test_incomplete_target_check_exits_three_and_comparison_is_explicit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = fixture_file(tmp_path)
    policy = tmp_path / "policy.json"
    policy.write_text('{"mandatory_cap":50}', encoding="utf-8")
    assert (
        cli.main(["--input", str(source), "--alternative-policy", str(policy), "--check-targets"])
        == 3
    )
    report = json.loads(capsys.readouterr().out)
    assert report["cohorts"][0]["alternative"]["policy"]["mandatory_cap"] == 50
    assert report["cohorts"][0]["comparison"]["unchanged"] == 4


def test_empty_template_never_passes_targets(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--input", "../calibration/template.json", "--check-targets"]) == 3
    assert not json.loads(capsys.readouterr().out)["cohorts"]


@pytest.mark.parametrize(
    "mode",
    [
        "invalid_json",
        "invalid_model",
        "invalid_policy",
        "invalid_argument",
        "missing_input",
        "remote_input",
        "unc_input",
    ],
)
def test_errors_do_not_echo_private_arguments_or_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str
) -> None:
    source = fixture_file(tmp_path)
    args = ["--input", str(source)]
    if mode == "invalid_json":
        source.write_text('{"SYNTHETIC_PRIVATE_DATA":', encoding="utf-8")
    elif mode == "invalid_model":
        source.write_text('{"schema_version":"SYNTHETIC_PRIVATE_DATA"}', encoding="utf-8")
    elif mode == "invalid_policy":
        policy = tmp_path / "SYNTHETIC_PRIVATE_POLICY.json"
        policy.write_text('{"SYNTHETIC_PRIVATE_DATA":42}', encoding="utf-8")
        args += ["--alternative-policy", str(policy)]
    elif mode == "invalid_argument":
        args += ["--SYNTHETIC_PRIVATE_ARGUMENT"]
    elif mode == "missing_input":
        args = ["--input", str(tmp_path / "SYNTHETIC_PRIVATE_MISSING")]
    elif mode == "remote_input":
        args = ["--input", "https://SYNTHETIC_PRIVATE_HOST/data"]
    else:
        args = ["--input", r"\\SYNTHETIC_PRIVATE_SERVER\data\corpus.json"]
    assert cli.main(args) == 2
    captured = capsys.readouterr()
    assert not captured.out and "SYNTHETIC_PRIVATE" not in captured.err
    assert "Traceback" not in captured.err and "CALIBRATION_" in captured.err


def test_atomic_report_refuses_overwrite_and_input_clobber(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = fixture_file(tmp_path)
    target = tmp_path / "report.json"
    args = ["--input", str(source), "--output", str(target)]
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert json.loads(target.read_text(encoding="utf-8")) == json.loads(captured.out)
    target.write_text("existing report", encoding="utf-8")
    assert cli.main(args) == 2 and target.read_text(encoding="utf-8") == "existing report"
    assert cli.main(args + ["--overwrite"]) == 0
    capsys.readouterr()
    before = source.read_bytes()
    assert cli.main(["--input", str(source), "--output", str(source), "--overwrite"]) == 2
    assert source.read_bytes() == before
    assert not list(tmp_path.glob(".calibration-*.tmp"))


def test_failed_atomic_publish_leaves_no_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def failing_link(*args: object, **kwargs: object) -> None:
        raise OSError("SYNTHETIC_PRIVATE_FAILURE")

    source = fixture_file(tmp_path)
    target = tmp_path / "output.json"
    monkeypatch.setattr(os, "link", failing_link)
    assert cli.main(["--input", str(source), "--output", str(target)]) == 2
    assert not target.exists() and not list(tmp_path.glob(".calibration-*.tmp"))
    assert "SYNTHETIC_PRIVATE" not in capsys.readouterr().err


def test_unexpected_scoring_error_is_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def failed(*args: object, **kwargs: object) -> None:
        raise RuntimeError("SYNTHETIC_PRIVATE_FACTS")

    monkeypatch.setattr(cli, "evaluate", failed)
    assert cli.main(["--input", str(fixture_file(tmp_path))]) == 2
    captured = capsys.readouterr()
    assert not captured.out and "SYNTHETIC_PRIVATE" not in captured.err
    assert "CALIBRATION_PROCESSING_FAILED" in captured.err


def test_evaluation_makes_no_socket_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Offline evaluation must not connect to a database/provider")

    source = fixture_file(tmp_path)
    monkeypatch.setattr(socket, "socket", forbidden)
    assert cli.main(["--input", str(source)]) == 0


def test_publish_race_does_not_overwrite_existing_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = fixture_file(tmp_path)
    target = tmp_path / "report.json"
    original = os.link

    def racing_link(source: str, destination: Path) -> None:
        target.write_text("concurrent report", encoding="utf-8")
        original(source, destination)

    monkeypatch.setattr(os, "link", racing_link)
    assert cli.main(["--input", str(source), "--output", str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "concurrent report"
    assert "CALIBRATION_OUTPUT_EXISTS" in capsys.readouterr().err
    assert not list(tmp_path.glob(".calibration-*.tmp"))


def test_numerical_target_success_still_requires_human_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from app.modules.matching import calibration

    corpus = synthetic_corpus(50, purpose="VALIDATION")
    corpus.owner_reviewed = True
    source = tmp_path / "synthetic-gate-mechanics-only.json"
    source.write_text(corpus.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(calibration, "_scores", synthetic_scores)
    assert cli.main(["--input", str(source), "--check-targets"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["cohorts"][0]["baseline"]["target_status"] == "TARGETS_MET"
    assert report["calibration_status"] == "UNVALIDATED" and report["human_validation_required"]
