import json
from pathlib import Path

import pytest

from tools.coverage_gate import Coverage, coverage_by_scope, dashboard_coverage, main, violations


def summary(covered: int, total: int) -> dict[str, dict[str, int]]:
    return {"summary": {"covered_lines": covered, "num_statements": total, "covered_branches": 0, "num_branches": 0}}


def test_coverage_of_nothing_is_complete() -> None:
    assert Coverage(0, 0).percent == 100.0


def test_branches_count_together_with_lines() -> None:
    report = {
        "files": {
            "src/autotrading/domain/a.py": {
                "summary": {"covered_lines": 8, "num_statements": 10, "covered_branches": 1, "num_branches": 2}
            }
        }
    }

    assert coverage_by_scope(report)["domain"] == Coverage(9, 12)


def test_files_are_grouped_by_layer_whatever_the_separator() -> None:
    report = {
        "files": {
            "src\\autotrading\\domain\\a.py": summary(9, 10),
            "src/autotrading/application/b.py": summary(5, 10),
            "src/autotrading/bootstrap.py": summary(10, 10),
        }
    }

    scopes = coverage_by_scope(report)

    assert scopes["domain"] == Coverage(9, 10)
    assert scopes["application"] == Coverage(5, 10)
    assert scopes["totale"] == Coverage(24, 30)


def test_violations_name_scope_and_threshold() -> None:
    scopes = {"domain": Coverage(89, 100), "application": Coverage(90, 100), "totale": Coverage(80, 100)}

    assert violations(scopes) == ["copertura domain 89.00% sotto la soglia 90%"]


def test_main_reports_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"files": {"src/autotrading/application/b.py": summary(1, 2)}}), encoding="utf-8")

    assert main([str(report)]) == 1
    assert "application" in capsys.readouterr().err


def test_main_accepts_full_coverage(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"files": {"src/autotrading/domain/a.py": summary(2, 2)}}), encoding="utf-8")

    assert main([str(report)]) == 0


def test_pipeline_tools_stay_out_of_the_service_scopes() -> None:
    report = {
        "files": {
            "src/autotrading/bootstrap.py": summary(10, 10),
            "tools/release_version.py": summary(0, 10),
            "tools/domain/x.py": summary(0, 10),
        }
    }

    scopes = coverage_by_scope(report)

    assert scopes["totale"] == Coverage(10, 10)
    assert scopes["domain"] == Coverage(0, 0)


def dashboard_summary(lines: tuple[int, int], branches: tuple[int, int]) -> dict[str, object]:
    return {
        "total": {
            "lines": {"covered": lines[0], "total": lines[1]},
            "branches": {"covered": branches[0], "total": branches[1]},
        }
    }


def test_dashboard_coverage_counts_branches_together_with_lines() -> None:
    assert dashboard_coverage(dashboard_summary((90, 100), (5, 10))) == Coverage(95, 110)


def test_dashboard_below_its_threshold_is_a_violation() -> None:
    scopes = {
        "domain": Coverage(1, 1),
        "application": Coverage(1, 1),
        "totale": Coverage(1, 1),
        "dashboard": Coverage(89, 100),
    }

    assert violations(scopes) == ["copertura dashboard 89.00% sotto la soglia 90%"]


def test_main_reads_the_coverage_of_the_dashboard_beside_the_service(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"files": {"src/autotrading/domain/a.py": summary(2, 2)}}), encoding="utf-8")
    dashboard = tmp_path / "coverage-summary.json"
    dashboard.write_text(json.dumps(dashboard_summary((50, 100), (0, 0))), encoding="utf-8")

    assert main([str(report), str(dashboard)]) == 1
    assert "dashboard 50.00%" in capsys.readouterr().err


def test_main_accepts_a_fully_covered_dashboard(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"files": {"src/autotrading/domain/a.py": summary(2, 2)}}), encoding="utf-8")
    dashboard = tmp_path / "coverage-summary.json"
    dashboard.write_text(json.dumps(dashboard_summary((10, 10), (4, 4))), encoding="utf-8")

    assert main([str(report), str(dashboard)]) == 0
