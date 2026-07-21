import json
from pathlib import Path
import shutil

from core.controlling import ControllingComputeTool


ROOT = Path(__file__).parents[1]
DEMO = ROOT / "presets" / "kmu-controlling" / "pilot" / "demo"


def test_packaged_kmu_demo_reproduces_approved_reference_results(tmp_path):
    instance = tmp_path / "demo-kmu" / "controlling"
    actuals = instance / "inbox" / "actuals"
    pilot = instance / "project" / "pilot"
    actuals.mkdir(parents=True)
    pilot.mkdir(parents=True)
    shutil.copyfile(
        DEMO / "Saldenliste_Muster_Juni2026.xlsx",
        actuals / "Saldenliste_Muster_Juni2026.xlsx",
    )
    shutil.copyfile(DEMO / "account-mapping.json", pilot / "account-mapping.json")

    report = json.loads(
        ControllingComputeTool(instance).safe_run(
            '{"operation":"kmu_report","source":"auto"}'
        )
    )
    expected = json.loads(
        (DEMO / "expected-results.json").read_text(encoding="utf-8")
    )

    assert report["source"] == expected["source"]
    assert report["report_metadata"] == expected["report_metadata"]
    assert report["groups"]["revenue"]["month"] == expected["metrics"][
        "revenue_month"
    ]
    assert report["groups"]["material"]["month"] == expected["metrics"][
        "material_month"
    ]
    assert report["groups"]["personnel"]["month"] == expected["metrics"][
        "personnel_month"
    ]
    assert report["metrics"]["ebitda"]["month"] == expected["metrics"][
        "ebitda_month"
    ]
    assert report["metrics"]["egt"]["month"] == expected["metrics"]["egt_month"]
    assert report["metrics"]["egt"]["prior"] == expected["metrics"]["egt_prior"]
    assert report["metrics"]["egt"]["ytd"] == expected["metrics"]["egt_ytd"]
    assert report["metrics"]["egt"]["ytd_prior"] == expected["metrics"][
        "egt_ytd_prior"
    ]
    assert report["metrics"]["receivables"]["month"] == expected["metrics"][
        "receivables_month"
    ]
    assert report["metrics"]["liquidity"]["month"] == expected["metrics"][
        "liquidity_month"
    ]
    assert report["metrics"]["payables"]["month"] == expected["metrics"][
        "payables_month"
    ]
    for name, value in expected["reconciliation"].items():
        assert report["reconciliation"][name] == value
