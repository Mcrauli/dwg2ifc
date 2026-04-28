"""Plan E Task 11: build.yml triggers a Windows PyInstaller build + uploads artifact."""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "build.yml"


def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_build_workflow_file_exists():
    assert WORKFLOW_PATH.is_file(), f"missing workflow: {WORKFLOW_PATH}"


def test_build_workflow_triggers_on_push_master_and_pull_request():
    data = _load_workflow()
    # `on` is parsed as Python bool True due to YAML 1.1 quirks; tolerate both keys.
    triggers = data.get("on") or data.get(True)
    assert triggers is not None
    push = triggers.get("push") or {}
    assert "master" in (push.get("branches") or [])
    assert "pull_request" in triggers


def test_build_workflow_runs_on_windows_runner():
    data = _load_workflow()
    jobs = data["jobs"]
    runner_strings: list[str] = []
    for job in jobs.values():
        runs_on = job.get("runs-on", "")
        if isinstance(runs_on, str):
            runner_strings.append(runs_on)
        strategy = (job.get("strategy") or {}).get("matrix") or {}
        for value in strategy.values():
            if isinstance(value, list):
                runner_strings.extend(str(v) for v in value)
    assert any("windows" in s.lower() for s in runner_strings)


def test_build_workflow_invokes_build_exe_script():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "scripts/build_exe.ps1" in text or "scripts\\build_exe.ps1" in text


def test_build_workflow_uploads_dxf2ifc_windows_artifact():
    data = _load_workflow()
    upload_steps: list[dict] = []
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses", "")
            if uses.startswith("actions/upload-artifact"):
                upload_steps.append(step)
    names = [step.get("with", {}).get("name", "") for step in upload_steps]
    assert any("dxf2ifc-windows" in name for name in names), names


def test_build_workflow_includes_ubuntu_smoke_job():
    data = _load_workflow()
    runner_strings: list[str] = []
    for job in data["jobs"].values():
        runs_on = job.get("runs-on", "")
        if isinstance(runs_on, str):
            runner_strings.append(runs_on)
        strategy = (job.get("strategy") or {}).get("matrix") or {}
        for value in strategy.values():
            if isinstance(value, list):
                runner_strings.extend(str(v) for v in value)
    assert any("ubuntu" in s.lower() for s in runner_strings)


def test_build_workflow_invokes_build_exe_sh_on_linux():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "scripts/build_exe.sh" in text


def test_build_workflow_runs_version_smoke_before_upload():
    data = _load_workflow()
    windows_job = next(
        job for job in data["jobs"].values() if "windows" in str(job.get("runs-on", "")).lower()
    )
    steps = windows_job["steps"]
    smoke_index = None
    upload_index = None
    for index, step in enumerate(steps):
        run = step.get("run", "")
        if "--version" in run and ".exe" in run:
            smoke_index = index
        if step.get("uses", "").startswith("actions/upload-artifact"):
            upload_index = index
    assert smoke_index is not None, "Windows job has no --version smoke step"
    assert upload_index is not None
    assert smoke_index < upload_index, "smoke step must run before artifact upload"
