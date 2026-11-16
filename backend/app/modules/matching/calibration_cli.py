"""Explicit local calibration tooling; no settings, database or provider connection."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

from app.modules.matching.calibration import (
    CalibrationCorpus,
    CalibrationError,
    evaluate,
    load_model,
    local_path,
)
from app.modules.matching.schemas import ScoringPolicy


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse's default error echoes user arguments and potentially private paths.
        raise CalibrationError("CALIBRATION_ARGUMENTS_INVALID")


def write_report(path: Path, payload: str, *, overwrite: bool) -> None:
    """Publish a complete file atomically, without clobbering an existing file by default."""
    pending: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".calibration-",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            pending = stream.name
            stream.write(payload + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(pending, path)
            pending = None
        else:
            os.link(pending, path)
    except FileExistsError:
        raise CalibrationError("CALIBRATION_OUTPUT_EXISTS") from None
    except OSError:
        raise CalibrationError("CALIBRATION_OUTPUT_UNAVAILABLE") from None
    finally:
        if pending is not None:
            Path(pending).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    try:
        parser = Parser(
            description="Offline matching evaluation; never promotes application scores."
        )
        parser.add_argument("--input", required=True, help="Local anonymized corpus JSON")
        parser.add_argument("--alternative-policy", help="Local ScoringPolicy JSON")
        parser.add_argument("--output", help="Explicit aggregate report path (parent must exist)")
        parser.add_argument(
            "--overwrite", action="store_true", help="Allow replacing an existing report"
        )
        parser.add_argument(
            "--validate-only", action="store_true", help="Check format without scoring"
        )
        parser.add_argument(
            "--check-targets", action="store_true", help="Exit 3 for incomplete/unmet targets"
        )
        options = parser.parse_args(argv)
        if options.validate_only and (options.alternative_policy or options.check_targets):
            raise CalibrationError("CALIBRATION_ARGUMENTS_INVALID")
        if options.overwrite and not options.output:
            raise CalibrationError("CALIBRATION_ARGUMENTS_INVALID")
        source = local_path(options.input)
        alternate = local_path(options.alternative_policy) if options.alternative_policy else None
        target = local_path(options.output) if options.output else None
        if target is not None:
            resolved = target.resolve()
            if resolved == source.resolve() or (
                alternate is not None and resolved == alternate.resolve()
            ):
                raise CalibrationError("CALIBRATION_OUTPUT_IS_INPUT")
            if target.exists() and not options.overwrite:
                raise CalibrationError("CALIBRATION_OUTPUT_EXISTS")
        corpus = load_model(source, CalibrationCorpus)
        exit_code = 0
        if options.validate_only:
            payload = json.dumps(
                {
                    "format_valid": True,
                    "calibration_status": "UNVALIDATED",
                    "case_count": len(corpus.cases),
                    "snapshot_count": len(corpus.snapshots),
                },
                sort_keys=True,
            )
        else:
            policy = load_model(alternate, ScoringPolicy) if alternate is not None else None
            report = evaluate(corpus, policy)
            payload = json.dumps(
                report.model_dump(mode="json"), ensure_ascii=True, sort_keys=True, allow_nan=False
            )
            if options.check_targets:
                checks = [
                    row.alternative if policy is not None else row.baseline
                    for row in report.cohorts
                ]
                if not checks or any(
                    row is None or row.target_status != "TARGETS_MET" for row in checks
                ):
                    exit_code = 3
        if target is not None:
            write_report(target, payload, overwrite=options.overwrite)
        print(payload)
        return exit_code
    except CalibrationError as error:
        print(json.dumps({"error": {"code": error.code}}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('{"error":{"code":"CALIBRATION_INTERRUPTED"}}', file=sys.stderr)
        return 130
    except Exception:
        # Includes unexpected scorer failures: never print objects/traceback with private facts.
        print('{"error":{"code":"CALIBRATION_PROCESSING_FAILED"}}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
