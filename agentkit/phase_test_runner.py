"""Private Docker runner for separately authorized local test phases.

This module deliberately has no native-host pytest execution path. A run is
reserved before contacting Docker and is never retried after an uncertain
transport outcome.

The in-container supervisor is a separate process from pytest and emits the
host-consumed result frame while the container is live. Collection and per-test
outcomes are still observational reports from mutable test code, not
adversarially authenticated facts; acceptance also depends on independent
review of the selected test diff and gate configuration.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid
from pathlib import Path
from typing import Callable

from .contracts import ContractError
from .phase_test_execution import (
    LocalPhaseTestPolicy,
    PhasePlan,
    authorize_phase,
    verify_phase_freshness,
)
from .test_execution import _safe_source_bytes

_HEX = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID = re.compile(r"^[0-9a-f]{32}$")
_OUTPUT_TAIL = 12_000
_RESULT_MARKER = "AGENTKIT_PHASE_RESULT "
_CONTROL_MEMBER = "__agentkit_phase_control_v1__.json"
_CHILD_MEMBER = "__agentkit_phase_child_v1__.py"
_IMAGE_ENV = {
    "PATH": "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG": "C.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1",
}
# Keep pytest imports and mutable plugin state out of the supervisor process.
# This is a process separation for reliability, not a same-UID adversarial
# security boundary; the resulting report is explicitly labeled observational.
_PYTEST_CHILD = r"""import hashlib,json,os,sys
import pytest
root='/tmp/agentkit-workspace'
if os.path.commonpath([os.path.realpath(pytest.__file__),root])==root: raise SystemExit(93)
sys.path.append(root)
def main():
    with open(os.path.join(root,'__agentkit_phase_control_v1__.json'),encoding='utf-8') as stream:
        control=json.load(stream)
    selected=control['selection']; phase=control['phase']
    os.chdir(root)
    class Recorder:
        items=[]; files=set(); outcomes={}
        def pytest_collection_finish(self,session):
            self.items=sorted(item.nodeid for item in session.items)
        def pytest_collectreport(self,report):
            if report.nodeid.endswith('.py'):
                self.files.add(report.nodeid)
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(self,item,call):
            result=yield
            report=result.get_result()
            if report.when=='call' or report.outcome in ('failed','skipped'):
                wasxfail=getattr(report,'wasxfail',None)
                status='xpassed' if wasxfail and report.passed else ('xfailed' if wasxfail else report.outcome)
                self.outcomes[item.nodeid]={'outcome':status,
                    'exception_type':call.excinfo.type.__name__ if call.excinfo else None,
                    'when':report.when}
    rec=Recorder()
    code=pytest.main(['-q','-c','/dev/null','--rootdir',root,'-p','no:cacheprovider',*selected],plugins=[rec])
    nodeids=rec.items; files=sorted(rec.files | {n.split('::',1)[0] for n in nodeids})
    result={'schema':'agentkit/local-phase-result-v1','phase':phase,'exit_code':int(code),
     'nodeids':nodeids,'nodeids_sha256':hashlib.sha256(json.dumps(nodeids,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),
     'files':files,'files_sha256':hashlib.sha256(json.dumps(files,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),
     'outcomes':rec.outcomes}
    with open('/tmp/agentkit-child-result.json','w',encoding='utf-8') as stream: json.dump(result,stream,sort_keys=True,separators=(',',':'))
    raise SystemExit(int(code))
if __name__=='__main__':
    main()
"""
_WRAPPER = r"""import hashlib,json,os,subprocess,sys,tarfile
root='/tmp/agentkit-workspace'; os.makedirs(root,exist_ok=True)
with tarfile.open('/source.tar','r:') as archive:
    for member in archive.getmembers():
        name=member.name
        if member.isdir() or not member.isfile() or name.startswith('/') or any(p in ('','..','.') for p in name.split('/')):
            raise SystemExit(91)
    for member in archive.getmembers():
        target=os.path.join(root,*member.name.split('/'))
        os.makedirs(os.path.dirname(target),exist_ok=True)
        with archive.extractfile(member) as source, open(target,'xb') as destination:
            destination.write(source.read())
        os.chmod(target,0o444)
sys.path.insert(0,root)
with open(os.path.join(root,'__agentkit_phase_control_v1__.json'),encoding='utf-8') as control_file:
    control=json.load(control_file)
paths=control['snapshot_paths']; phase=control['phase']
for rel,expected in control['input_hashes'].items():
    with open(os.path.join(root,*rel.split('/')),'rb') as stream:
        if hashlib.sha256(stream.read()).hexdigest()!=expected: raise SystemExit(90)
if control['initialize_git']:
    git_env={'PATH':'/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin',
      'LANG':'C.UTF-8','HOME':'/tmp/agentkit-home','GIT_CONFIG_NOSYSTEM':'1',
      'GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0'}
    initialized=subprocess.run(['/usr/bin/git','init','-q',root],cwd=root,env=git_env,
      stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    if initialized.returncode!=0: raise SystemExit(94)
def hashes():
    result={}
    for rel in paths:
        target=os.path.join(root,*rel.split('/'))
        with open(target,'rb') as stream: result[rel]=hashlib.sha256(stream.read()).hexdigest()
    return result
home='/tmp/agentkit-home'; os.makedirs(home,exist_ok=True); os.chmod(home,0o700)
child='/tmp/agentkit-pytest-child.py'
with open(os.path.join(root,'__agentkit_phase_child_v1__.py'),encoding='utf-8') as source, open(child,'w',encoding='utf-8') as destination:
    destination.write(source.read())
os.chmod(child,0o444)
out_path='/tmp/agentkit-pytest.stdout'; err_path='/tmp/agentkit-pytest.stderr'
with open(out_path,'wb') as out, open(err_path,'wb') as err:
    completed=subprocess.run(['/usr/local/bin/python','-I','-B',child],cwd=root,stdout=out,stderr=err,check=False)
limit=control['output_limit']
if os.path.getsize(out_path)+os.path.getsize(err_path)>limit: raise SystemExit(92)
with open('/tmp/agentkit-child-result.json','rb') as result_file:
    raw=result_file.read(limit)
if len(raw)>=limit: raise SystemExit(92)
result=json.loads(raw.decode('utf-8'))
result['exit_code']=int(completed.returncode)
result['post_hashes']=hashes()
with open(out_path,'rb') as out: out_tail=out.read()[-12000:]
with open(err_path,'rb') as err: err_tail=err.read()[-12000:]
for chunk in (out_tail,err_tail):
    if chunk: sys.stdout.buffer.write(chunk+b'\n')
sys.stdout.write('AGENTKIT_PHASE_RESULT '+json.dumps(result,sort_keys=True,separators=(',',':'))+'\n')
raise SystemExit(int(completed.returncode))
"""


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _stage_git_required(policy: LocalPhaseTestPolicy) -> bool:
    """Initialize only a host-declared root .gitignore scratch fixture."""
    return ".gitignore" in policy.snapshot_paths


def _snapshot(
    policy: LocalPhaseTestPolicy,
    workspace: Path,
    freshness: dict[str, object],
    plan: PhasePlan,
    directory: Path,
) -> tuple[Path, str]:
    inputs = freshness.get("input_hashes")
    if type(inputs) is not dict or set(inputs) != set(policy.snapshot_paths):
        raise ContractError(
            "Phase freshness receipt does not match the exact snapshot allowlist."
        )
    archive = directory / "source.tar"
    total = 0
    digest_entries: list[list[str]] = []
    selection = list(plan.nodeids if plan.phase != "full" else plan.test_files)
    reserved_names = {
        _CONTROL_MEMBER,
        _CHILD_MEMBER,
    }
    if reserved_names.intersection(policy.snapshot_paths):
        raise ContractError(
            "Snapshot allowlist collides with the reserved phase-control member."
        )
    control_bytes = _json_bytes(
        {
            "phase": plan.phase,
            "selection": selection,
            "snapshot_paths": list(policy.snapshot_paths),
            "input_hashes": inputs,
            "output_limit": policy.limits["output_bytes"],
            "initialize_git": _stage_git_required(policy),
        }
    )
    if len(control_bytes) > min(policy.limits["output_bytes"] // 4, 500_000):
        raise ContractError(
            "Policy test selection exceeds the bounded phase control size."
        )
    with tarfile.open(archive, "w", format=tarfile.PAX_FORMAT) as tar:
        for relative in policy.snapshot_paths:
            content = _safe_source_bytes(
                workspace, relative, policy.limits["max_file_bytes"]
            )
            total += len(content)
            if total > min(
                policy.limits["max_snapshot_bytes"],
                policy.limits["tmpfs_bytes"] - 1_048_576,
            ):
                raise ContractError(
                    "Phase snapshot exceeds its configured total byte limit."
                )
            digest = hashlib.sha256(content).hexdigest()
            if digest != inputs[relative]:
                raise ContractError(
                    "Workspace changed between freshness verification and staging."
                )
            info = tarfile.TarInfo(relative)
            info.size = len(content)
            info.mode = 0o444
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            tar.addfile(info, io.BytesIO(content))
            digest_entries.append([relative, digest])
        control = tarfile.TarInfo(_CONTROL_MEMBER)
        control.size = len(control_bytes)
        control.mode = 0o444
        control.uid = control.gid = 0
        control.uname = control.gname = ""
        control.mtime = 0
        tar.addfile(control, io.BytesIO(control_bytes))
        child = tarfile.TarInfo(_CHILD_MEMBER)
        child.size = len(_PYTEST_CHILD.encode("utf-8"))
        child.mode = 0o444
        child.uid = child.gid = 0
        child.uname = child.gname = ""
        child.mtime = 0
        tar.addfile(child, io.BytesIO(_PYTEST_CHILD.encode("utf-8")))
    return archive, hashlib.sha256(_json_bytes(digest_entries)).hexdigest()


def _container_program(
    plan: PhasePlan, policy: LocalPhaseTestPolicy
) -> tuple[str, list[str]]:
    environment = [
        "--env=PYTEST_ADDOPTS=",
        "--env=PYTEST_PLUGINS=",
        "--env=PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
        "--env=HOME=/tmp/agentkit-home",
    ]
    environment[:0] = [f"--env={key}={value}" for key, value in _IMAGE_ENV.items()]
    return _WRAPPER, environment


def _limits_string(policy: LocalPhaseTestPolicy) -> dict[str, object]:
    limits = policy.limits
    return {
        "tmpfs": f"rw,noexec,nosuid,nodev,size={limits['tmpfs_bytes']},mode=1777",
        "memory": limits["memory_bytes"],
        "memory_swap": limits["memory_swap_bytes"],
        "nano_cpus": limits["nano_cpus"],
        "pids": limits["pids"],
        "nofile": limits["nofile"],
    }


def _docker_create_args(
    policy: LocalPhaseTestPolicy,
    archive_path: str,
    container_name: str,
    plan: PhasePlan,
    timeout: int,
) -> list[str]:
    wrapper, environment = _container_program(plan, policy)
    limits = _limits_string(policy)
    return [
        "docker",
        "create",
        "--pull=never",
        "--name",
        container_name,
        "--label",
        f"org.agentkit.phase-run={container_name}",
        "--network=none",
        "--read-only",
        "--user=65534:65534",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        f"--memory={limits['memory']}",
        f"--memory-swap={limits['memory_swap']}",
        f"--cpus={policy.limits['nano_cpus'] / 1_000_000_000:g}",
        f"--pids-limit={limits['pids']}",
        f"--ulimit=nofile={limits['nofile']}:{limits['nofile']}",
        f"--tmpfs=/tmp:{limits['tmpfs']}",
        "--mount",
        f"type=bind,source={archive_path},target=/source.tar,readonly",
        *environment,
        "--workdir=/tmp",
        "--entrypoint=/usr/bin/timeout",
        policy.image_ref,
        "--signal=TERM",
        "--kill-after=2",
        str(timeout),
        "/usr/local/bin/python",
        "-I",
        "-B",
        "-c",
        wrapper,
    ]


def _valid_image(output: str, policy: LocalPhaseTestPolicy) -> bool:
    try:
        value = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        return False
    config = value.get("Config") if isinstance(value, dict) else None
    labels = config.get("Labels") if isinstance(config, dict) else None
    environment = config.get("Env") if isinstance(config, dict) else None
    env = _environment_dict(environment)
    return (
        isinstance(value, dict)
        and value.get("Id") == policy.image_id
        and isinstance(labels, dict)
        and labels.get("org.agentkit.test-lock-sha256") == policy.dependency_lock_sha256
        and env == _IMAGE_ENV
    )


def _environment_dict(environment: object) -> dict[str, str] | None:
    if type(environment) is not list or any(
        type(item) is not str for item in environment
    ):
        return None
    result: dict[str, str] = {}
    for entry in environment:
        key, separator, value = entry.partition("=")
        if not separator or not key or key in result:
            return None
        result[key] = value
    return result


def _valid_container(
    output: str, policy: LocalPhaseTestPolicy, name: str, archive: str
) -> bool:
    try:
        value = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(value, dict):
        return False
    config, host = value.get("Config") or {}, value.get("HostConfig") or {}
    mounts = value.get("Mounts") or []
    labels = config.get("Labels") or {}
    limit = _limits_string(policy)
    command = config.get("Cmd", [])
    try:
        command_timeout = int(command[2])
    except (TypeError, ValueError, IndexError):
        return False
    env = _environment_dict(config.get("Env"))
    if env is None:
        return False
    expected_env = {
        **_IMAGE_ENV,
        "PYTEST_ADDOPTS": "",
        "PYTEST_PLUGINS": "",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "HOME": "/tmp/agentkit-home",
    }
    if env != expected_env:
        return False
    return (
        value.get("Name", "").lstrip("/") == name
        and value.get("Image") == policy.image_id
        and config.get("Image") == policy.image_ref
        and config.get("User") == "65534:65534"
        and config.get("Entrypoint") == ["/usr/bin/timeout"]
        and config.get("WorkingDir") == "/tmp"
        and command[0:2] == ["--signal=TERM", "--kill-after=2"]
        and 1 <= command_timeout <= policy.limits["timeout_seconds"]
        and len(config.get("Cmd", [])) == 8
        and config.get("Cmd", [None] * 8)[3:6] == ["/usr/local/bin/python", "-I", "-B"]
        and config.get("Cmd", [None] * 8)[6] == "-c"
        and config.get("Cmd", [None] * 8)[7] == _WRAPPER
        and host.get("NetworkMode") == "none"
        and host.get("ReadonlyRootfs") is True
        and host.get("Privileged") is False
        and host.get("Devices") in (None, [])
        and host.get("DeviceRequests") in (None, [])
        and host.get("CapDrop") == ["ALL"]
        and host.get("CapAdd") in (None, [])
        and host.get("SecurityOpt")
        in (["no-new-privileges"], ["no-new-privileges:true"])
        and host.get("Memory") == limit["memory"]
        and host.get("MemorySwap") == limit["memory_swap"]
        and host.get("NanoCpus") == policy.limits["nano_cpus"]
        and host.get("PidsLimit") == limit["pids"]
        and host.get("Tmpfs") == {"/tmp": limit["tmpfs"]}
        and not host.get("Binds")
        and labels.get("org.agentkit.phase-run") == name
        and len(mounts) == 1
        and mounts[0].get("Destination") == "/source.tar"
        and mounts[0].get("Type") == "bind"
        and mounts[0].get("RW") is False
        and Path(str(mounts[0].get("Source", ""))).resolve() == Path(archive).resolve()
        and any(
            item.get("Name") == "nofile"
            and item.get("Soft") == limit["nofile"]
            and item.get("Hard") == limit["nofile"]
            for item in host.get("Ulimits", [])
            if isinstance(item, dict)
        )
    )


def _valid_result(
    value: object,
    plan: PhasePlan,
    policy: LocalPhaseTestPolicy,
    freshness: dict[str, object],
    container_exit_code: int,
) -> tuple[bool, str, dict[str, object]]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "schema",
            "phase",
            "exit_code",
            "nodeids",
            "nodeids_sha256",
            "files",
            "files_sha256",
            "outcomes",
            "post_hashes",
        }
        or value.get("schema") != "agentkit/local-phase-result-v1"
        or value.get("phase") != plan.phase
    ):
        return False, "phase_result_invalid", {}
    nodeids = value.get("nodeids")
    files = value.get("files")
    outcomes = value.get("outcomes")
    if (
        type(nodeids) is not list
        or type(files) is not list
        or type(outcomes) is not dict
    ):
        return False, "collection_result_invalid", {}
    if any(type(nodeid) is not str for nodeid in nodeids) or nodeids != sorted(
        set(nodeids)
    ):
        return False, "collection_nodeids_invalid", {}
    if any(type(path) is not str for path in files) or files != sorted(set(files)):
        return False, "collection_files_invalid", {}
    expected_selection = list(plan.nodeids if plan.phase != "full" else ())
    if plan.phase != "full" and nodeids != expected_selection:
        return False, "collection_nodeids_mismatch", {}
    expected_files = (
        set(plan.test_files)
        if plan.phase == "full"
        else {item.split("::", 1)[0] for item in plan.nodeids}
    )
    if set(files) != expected_files:
        return False, "collection_files_mismatch", {}
    nodeids_sha = hashlib.sha256(_json_bytes(nodeids)).hexdigest()
    files_sha = hashlib.sha256(_json_bytes(files)).hexdigest()
    if (
        value.get("nodeids_sha256") != nodeids_sha
        or value.get("files_sha256") != files_sha
    ):
        return False, "collection_digest_mismatch", {}
    if plan.phase == "full" and (
        len(nodeids) < (plan.minimum_test_count or 1)
        or len(files) != len(plan.test_files)
    ):
        return False, "full_collection_below_policy", {}
    if set(outcomes) != set(nodeids):
        return False, "per_test_outcomes_incomplete", {}
    if value.get("post_hashes") != freshness.get("input_hashes"):
        return False, "scratch_source_changed", {}
    exit_code = value.get("exit_code")
    if type(exit_code) is not int or exit_code != container_exit_code:
        return False, "exit_code_invalid", {}
    if plan.phase == "red":
        expected_failures = set(plan.expected_failure_nodeids)
        for nodeid in nodeids:
            outcome = outcomes[nodeid]
            if type(outcome) is not dict or set(outcome) != {
                "outcome",
                "exception_type",
                "when",
            }:
                return False, "red_outcome_invalid", {}
            if nodeid in expected_failures:
                if outcome != {
                    "outcome": "failed",
                    "exception_type": "AssertionError",
                    "when": "call",
                }:
                    return False, "red_assertion_not_reproduced", {}
            elif outcome["outcome"] != "passed":
                return False, "unexpected_red_failure", {}
        if exit_code != 1 or not expected_failures:
            return False, "red_exit_or_expectation_mismatch", {}
        status, reason = "passed", "expected_red_reproduced"
    else:
        permitted = (
            {"passed"} if plan.phase == "targeted" else {"passed", "skipped", "xfailed"}
        )
        if exit_code != 0 or any(
            type(outcome) is not dict or outcome.get("outcome") not in permitted
            for outcome in outcomes.values()
        ):
            return False, "tests_failed", {}
        status, reason = "passed", "ok"
    collection = {
        "nodeids_sha256": nodeids_sha,
        "count": len(nodeids),
        "files_sha256": files_sha,
        "files_count": len(files),
    }
    return (
        True,
        reason,
        {
            "status": status,
            "exit_code": exit_code,
            "collection": collection,
            "outcomes": outcomes,
            "scratch_post_hashes": value["post_hashes"],
        },
    )


def _phase_result_from_output(output: str) -> dict[str, object] | None:
    matches = [
        line[len(_RESULT_MARKER) :]
        for line in output.splitlines()
        if line.startswith(_RESULT_MARKER)
    ]
    if len(matches) != 1:
        return None
    try:
        result = json.loads(matches[0])
    except (json.JSONDecodeError, TypeError):
        return None
    return result if type(result) is dict else None


def _classify_container_result(
    container_exit_code: object,
    raw: dict[str, object] | None,
    plan: PhasePlan,
    policy: LocalPhaseTestPolicy,
    freshness: dict[str, object],
) -> tuple[str, str, int | None, dict[str, object]]:
    if type(container_exit_code) is not int or container_exit_code < 0:
        return "unknown", "container_exit_unknown", None, {}
    if container_exit_code in {124, 137, 143}:
        return "unknown", "container_timeout_or_signal_exit", None, {}
    if raw is None:
        return "unknown", "phase_result_unavailable", None, {}
    if raw.get("exit_code") != container_exit_code:
        return "unknown", "container_exit_result_mismatch", None, {}
    valid, reason, execution = _valid_result(
        raw, plan, policy, freshness, container_exit_code
    )
    return ("passed" if valid else "failed"), reason, container_exit_code, execution


def validate_phase_receipt(
    value: object, policy: LocalPhaseTestPolicy, run_id: str
) -> dict[str, object]:
    """Validate a host-created phase receipt before workflow state accepts it."""
    required = {
        "schema",
        "status",
        "run_id",
        "phase",
        "reason",
        "exit_code",
        "outcome_source",
        "policy_sha256",
        "host_runner_sha256",
        "image_ref",
        "image_id",
        "dependency_lock_sha256",
        "snapshot_sha256",
        "workspace_post_snapshot_sha256",
        "input_hashes",
        "collection",
        "outcomes",
        "scratch_post_hashes",
        "cleanup_confirmed",
        "duration_seconds",
        "output",
        "receipt_sha256",
    }
    if (
        type(value) is not dict
        or set(value) != required
        or value.get("schema") != "agentkit/local-phase-receipt-v1"
        or type(policy) is not LocalPhaseTestPolicy
    ):
        raise ContractError("Host phase receipt has an invalid schema.")
    plan = authorize_phase(policy, value.get("phase"))
    if (
        value["run_id"] != run_id
        or value["status"] not in {"passed", "failed", "unknown"}
        or value["outcome_source"] != "pytest_child_report"
        or value["policy_sha256"] != policy.sha256
        or value["host_runner_sha256"] != policy.host_runner_sha256
        or value["image_ref"] != policy.image_ref
        or value["image_id"] != policy.image_id
        or value["dependency_lock_sha256"] != policy.dependency_lock_sha256
    ):
        raise ContractError(
            "Host phase receipt does not match this run's pinned policy."
        )
    digest = value["receipt_sha256"]
    payload = {key: item for key, item in value.items() if key != "receipt_sha256"}
    if (
        type(digest) is not str
        or not _HEX.fullmatch(digest)
        or hashlib.sha256(_json_bytes(payload)).hexdigest() != digest
    ):
        raise ContractError("Host phase receipt digest is invalid.")
    hashes = value["input_hashes"]
    if (
        type(hashes) is not dict
        or set(hashes) != set(policy.snapshot_paths)
        or any(
            type(item) is not str or not _HEX.fullmatch(item)
            for item in hashes.values()
        )
    ):
        raise ContractError("Host phase receipt input bindings are invalid.")
    expected_snapshot = hashlib.sha256(
        _json_bytes([[path, hashes[path]] for path in sorted(hashes)])
    ).hexdigest()
    if value["snapshot_sha256"] != expected_snapshot:
        raise ContractError(
            "Host phase receipt snapshot digest does not match its input hashes."
        )
    if (
        type(value["snapshot_sha256"]) is not str
        or not _HEX.fullmatch(value["snapshot_sha256"])
        or (
            value["workspace_post_snapshot_sha256"]
            and (
                type(value["workspace_post_snapshot_sha256"]) is not str
                or not _HEX.fullmatch(value["workspace_post_snapshot_sha256"])
            )
        )
        or type(value["scratch_post_hashes"]) is not dict
        or any(
            type(item) is not str or not _HEX.fullmatch(item)
            for item in value["scratch_post_hashes"].values()
        )
    ):
        raise ContractError("Host phase receipt contains an invalid content digest.")
    if (
        type(value["cleanup_confirmed"]) is not bool
        or type(value["collection"]) is not dict
        or type(value["outcomes"]) is not dict
        or type(value["scratch_post_hashes"]) is not dict
        or type(value["reason"]) is not str
        or not re.fullmatch(r"[a-z0-9_]{1,100}", value["reason"])
        or type(value["duration_seconds"]) not in {int, float}
        or not 0 <= value["duration_seconds"] <= policy.limits["timeout_seconds"] + 60
        or type(value["output"]) is not str
        or len(value["output"]) > _OUTPUT_TAIL
    ):
        raise ContractError("Host phase receipt has invalid bounded evidence fields.")
    if value["status"] == "unknown":
        if value["reason"] not in {
            "container_create_failed_or_unknown",
            "container_exit_unknown",
            "container_timeout_or_signal_exit",
            "container_exit_result_mismatch",
            "phase_result_unavailable",
            "container_cleanup_unconfirmed",
            "host_workspace_changed_during_phase",
            "transport_timeout",
            "phase_runner_error",
            "runner_error",
        }:
            raise ContractError("Unknown phase receipt reason is invalid.")
        if value["exit_code"] is not None:
            raise ContractError("Unknown phase receipt cannot claim a known exit code.")
        return dict(value)
    if value["cleanup_confirmed"] is not True:
        raise ContractError(
            "Terminal phase receipt lacks independent container cleanup confirmation."
        )
    if value["status"] == "passed":
        if value["workspace_post_snapshot_sha256"] != value["snapshot_sha256"]:
            raise ContractError(
                "Passing phase receipt workspace changed after execution."
            )
        if value["phase"] == "red":
            if value["reason"] != "expected_red_reproduced":
                raise ContractError(
                    "Passing RED receipt does not represent reproduced assertions."
                )
            expected = set(plan.expected_failure_nodeids)
            outcomes = value["outcomes"]
            if type(outcomes) is not dict or set(outcomes) != set(plan.nodeids):
                raise ContractError(
                    "Passing RED receipt lacks expected assertion outcomes."
                )
            if any(
                outcomes[node]
                != {
                    "outcome": "failed",
                    "exception_type": "AssertionError",
                    "when": "call",
                }
                for node in expected
            ):
                raise ContractError(
                    "Passing RED receipt includes a non-assertion expected failure."
                )
            if any(
                outcomes[node].get("outcome") != "passed"
                for node in set(plan.nodeids) - expected
            ):
                raise ContractError(
                    "Passing RED receipt includes an unexpected test failure."
                )
        elif value["reason"] != "ok":
            raise ContractError("Passing regression receipt has an invalid reason.")
        collection = value["collection"]
        if (
            type(collection) is not dict
            or set(collection)
            != {"nodeids_sha256", "count", "files_sha256", "files_count"}
            or any(
                type(collection[key]) is not int or collection[key] < 0
                for key in ("count", "files_count")
            )
            or any(
                type(collection[key]) is not str or not _HEX.fullmatch(collection[key])
                for key in ("nodeids_sha256", "files_sha256")
            )
        ):
            raise ContractError("Passing phase receipt collection binding is invalid.")
        if value["phase"] == "full" and (
            collection["count"] < (plan.minimum_test_count or 1)
            or collection["files_count"] != len(plan.test_files)
        ):
            raise ContractError(
                "Passing full receipt is below the operator-pinned suite scope."
            )
        if collection["count"] != len(value["outcomes"]):
            raise ContractError(
                "Passing phase receipt lacks one outcome per collected nodeid."
            )
        if value["phase"] != "full":
            expected_nodes = list(plan.nodeids)
            expected_files = sorted({node.split("::", 1)[0] for node in expected_nodes})
            if (
                collection["count"] != len(expected_nodes)
                or collection["nodeids_sha256"]
                != hashlib.sha256(_json_bytes(expected_nodes)).hexdigest()
                or collection["files_count"] != len(expected_files)
                or collection["files_sha256"]
                != hashlib.sha256(_json_bytes(expected_files)).hexdigest()
            ):
                raise ContractError(
                    "Passing phase receipt collection differs from host-selected tests."
                )
            if set(value["outcomes"]) != set(expected_nodes):
                raise ContractError(
                    "Passing phase receipt outcomes do not match selected nodeids."
                )
            if value["phase"] == "targeted" and any(
                not isinstance(outcome, dict) or outcome.get("outcome") != "passed"
                for outcome in value["outcomes"].values()
            ):
                raise ContractError(
                    "Passing targeted receipt contains a non-passing test."
                )
        elif any(
            not isinstance(outcome, dict)
            or outcome.get("outcome") not in {"passed", "skipped", "xfailed"}
            for outcome in value["outcomes"].values()
        ):
            raise ContractError(
                "Passing full receipt contains a failed or unexpected test."
            )
        if value["scratch_post_hashes"] != hashes:
            raise ContractError(
                "Passing receipt scratch files differ from its staged snapshot."
            )
    if value["exit_code"] is not None and (
        type(value["exit_code"]) is not int or abs(value["exit_code"]) > 255
    ):
        raise ContractError("Host phase receipt exit code is invalid.")
    return dict(value)


def _write_json_exclusive(path: Path, value: object) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ContractError(
            "This phase snapshot already has an attempt; uncertain runs cannot be replayed."
        ) from exc
    with os.fdopen(fd, "wb") as stream:
        stream.write(_json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def _host_runner_sha256() -> str:
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except OSError as exc:
        raise ContractError(
            "Pinned host phase runner cannot be hashed safely."
        ) from exc


def _reserve_attempt(
    results_dir: Path, run_id: str, phase: str, snapshot_sha: str, policy_sha: str
) -> tuple[Path, Path]:
    prefix = f"{run_id}-"
    for prior in results_dir.glob(prefix + "*.reservation.json"):
        receipt = prior.with_name(
            prior.name.replace(".reservation.json", ".receipt.json")
        )
        if not receipt.is_file():
            raise ContractError(
                "An unresolved phase reservation blocks subsequent phases for this run."
            )
        try:
            previous = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError(
                "A prior phase receipt is unreadable; this run remains blocked."
            ) from exc
        if (
            type(previous) is not dict
            or previous.get("run_id") != run_id
            or previous.get("policy_sha256") != policy_sha
        ):
            raise ContractError(
                "A prior phase reservation belongs to a different run policy."
            )
        previous_digest = previous.get("receipt_sha256")
        previous_payload = {
            key: item for key, item in previous.items() if key != "receipt_sha256"
        }
        if (
            type(previous_digest) is not str
            or not _HEX.fullmatch(previous_digest)
            or hashlib.sha256(_json_bytes(previous_payload)).hexdigest()
            != previous_digest
        ):
            raise ContractError(
                "A prior phase receipt failed its integrity check; this run remains blocked."
            )
        if previous.get("status") == "unknown":
            raise ContractError(
                "An unknown phase outcome blocks subsequent phases for this run."
            )
    stem = f"{run_id}-{phase}-{snapshot_sha}"
    reservation = results_dir / f"{stem}.reservation.json"
    receipt_path = results_dir / f"{stem}.receipt.json"
    _write_json_exclusive(
        reservation,
        {
            "schema": "agentkit/phase-reservation-v1",
            "run_id": run_id,
            "phase": phase,
            "policy_sha256": policy_sha,
            "snapshot_sha256": snapshot_sha,
            "reserved_at": time.time(),
        },
    )
    return reservation, receipt_path


def _wsl_runner(
    config_dir: Path, base_runner: Callable
) -> tuple[Callable, Callable[[], str | None]]:
    clean_env = {
        key: val
        for key, val in os.environ.items()
        if key.upper()
        in {
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "TEMP",
            "TMP",
            "TMPDIR",
        }
    }
    wsl = shutil.which("wsl.exe", path=clean_env.get("PATH")) or shutil.which(
        "wsl", path=clean_env.get("PATH")
    )
    if not wsl:
        raise ContractError(
            "Fixed Ubuntu WSL Docker transport is unavailable; host test fallback is disabled."
        )
    linux_env = [
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME=/tmp/agentkit-test-home",
    ]

    def mapped(path: Path, cwd: Path, timeout: float) -> str:
        command = [
            wsl,
            "--distribution",
            "Ubuntu",
            "--exec",
            "/usr/bin/env",
            "-i",
            *linux_env,
            "wslpath",
            "-a",
            str(path),
        ]
        code, out, _ = base_runner(command, "", cwd, timeout, env=clean_env)
        result = out.strip()
        if (
            code
            or not result.startswith("/mnt/")
            or any(char in result for char in ("\n", ","))
        ):
            raise ContractError(
                "Host staging path could not be mapped to fixed Ubuntu WSL."
            )
        return result

    mapped_config: str | None = None
    mapped_archive: str | None = None

    def invoke(args: list[str], prompt: str, cwd: Path, timeout: float):
        nonlocal mapped_config, mapped_archive
        if mapped_config is None:
            mapped_config = mapped(config_dir.resolve(), cwd, timeout)
        mapped_args = list(args[1:])
        if mapped_args and mapped_args[0] == "create" and "--mount" in mapped_args:
            mount_index = mapped_args.index("--mount") + 1
            descriptor = mapped_args[mount_index]
            marker = "source="
            start = descriptor.index(marker) + len(marker)
            end = descriptor.index(",target=", start)
            source = Path(descriptor[start:end])
            if "," in str(source):
                raise ContractError(
                    "Snapshot path cannot be represented safely in Docker mount syntax."
                )
            linux_source = mapped(source, cwd, timeout)
            mapped_args[mount_index] = (
                descriptor[:start] + linux_source + descriptor[end:]
            )
            mapped_archive = linux_source
        command = [
            wsl,
            "--distribution",
            "Ubuntu",
            "--exec",
            "/usr/bin/env",
            "-i",
            *linux_env,
            "/usr/bin/docker",
            "--config",
            mapped_config,
            *mapped_args,
        ]
        return base_runner(command, "", cwd, timeout, env=clean_env)

    return invoke, lambda: mapped_archive


def run_phase(
    policy: LocalPhaseTestPolicy,
    workspace: Path,
    phase: str,
    *,
    run_id: str,
    timeout: float,
    runner: Callable | None = None,
    results_dir: Path,
) -> dict[str, object]:
    """Run one policy-selected phase once, returning a bound host receipt.

    ``results_dir`` is host-owned durable state and must be outside the workspace.
    A pre-dispatch reservation makes uncertain runs non-replayable.
    """
    if (
        type(policy) is not LocalPhaseTestPolicy
        or not isinstance(run_id, str)
        or not _RUN_ID.fullmatch(run_id)
    ):
        raise ContractError(
            "A loaded phase policy and 32-character run UUID are required."
        )
    if type(timeout) not in {int, float} or timeout <= 0:
        raise ContractError("Phase deadline must be a positive number.")
    if _host_runner_sha256() != policy.host_runner_sha256:
        raise ContractError(
            "Host phase runner differs from the operator-pinned implementation."
        )
    workspace = Path(workspace).resolve(strict=True)
    result_input = Path(results_dir).expanduser().absolute()
    try:
        for candidate in (result_input, *reversed(result_input.parents)):
            if candidate.exists() and (
                candidate.is_symlink()
                or bool(getattr(candidate, "is_junction", lambda: False)())
            ):
                raise ContractError(
                    "Phase receipt directory cannot traverse links or junctions."
                )
    except OSError as exc:
        raise ContractError(
            "Phase receipt directory cannot be inspected safely."
        ) from exc
    results_dir = result_input.resolve()
    if results_dir == workspace or workspace in results_dir.parents:
        raise ContractError("Phase receipts must be stored outside the workspace.")
    plan = authorize_phase(policy, phase)
    timeout = min(float(timeout), float(policy.limits["timeout_seconds"]))
    results_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    freshness: dict[str, object] = {}
    snapshot_sha = ""
    workspace_post_sha = ""
    output = ""
    name = f"agentkit-phase-{phase}-{run_id}-{uuid.uuid4().hex[:16]}"
    created = False
    cleanup = True
    reason = "runner_error"
    status = "unknown"
    execution: dict[str, object] = {}
    exit_code: int | None = None
    base_runner = runner
    transport: Callable | None = None
    receipt_path: Path | None = None
    try:
        if base_runner is None:
            from .backends import _process_result

            base_runner = _process_result
        freshness = verify_phase_freshness(policy, workspace, phase)
        if freshness["policy_sha256"] != policy.sha256:
            raise ContractError(
                "Freshness receipt is not bound to the loaded phase policy."
            )
        with tempfile.TemporaryDirectory(prefix="agentkit-phase-stage-") as stage:
            stage_path = Path(stage)
            archive, snapshot_sha = _snapshot(
                policy, workspace, freshness, plan, stage_path
            )
            _, receipt_path = _reserve_attempt(
                results_dir, run_id, phase, snapshot_sha, policy.sha256
            )
            config_dir = stage_path / "docker-config"
            config_dir.mkdir()
            (config_dir / "config.json").write_text('{"auths":{}}', encoding="utf-8")
            archive_source: Callable[[], str | None]
            if runner is not None:
                transport = runner

                def archive_source() -> str:
                    return str(archive.resolve())
            else:
                transport, archive_source = _wsl_runner(config_dir, base_runner)

            def invoke(args: list[str], limit: float | None = None):
                code, stdout, stderr = transport(
                    args,
                    "",
                    workspace,
                    max(0.01, limit or timeout - (time.monotonic() - started)),
                )
                bounded = len(stdout.encode("utf-8", errors="replace")) + len(
                    stderr.encode("utf-8", errors="replace")
                )
                if bounded > policy.limits["output_bytes"]:
                    raise ContractError(
                        "Phase Docker output exceeded the configured bound."
                    )
                return code, stdout, stderr

            code, image_info, _ = invoke(
                [
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    "{{json .}}",
                    policy.image_ref,
                ]
            )
            if code or not _valid_image(image_info, policy):
                reason = "pinned_image_unavailable_or_mismatch"
                status = "failed"
            else:
                seconds = max(
                    1,
                    min(
                        policy.limits["timeout_seconds"],
                        int(timeout - (time.monotonic() - started)),
                    ),
                )
                create_args = _docker_create_args(
                    policy, str(archive.resolve()), name, plan, seconds
                )
                created = (
                    True  # transport may lose the response after Docker creates it
                )
                cleanup = False
                code, created_id, _ = invoke(create_args)
                created_id = created_id.strip()
                if code or not re.fullmatch(r"[0-9a-f]{12,64}", created_id):
                    reason = "container_create_failed_or_unknown"
                else:
                    code, info, _ = invoke(
                        ["docker", "inspect", "--format", "{{json .}}", created_id]
                    )
                    expected_archive = archive_source()
                    if (
                        code
                        or expected_archive is None
                        or not _valid_container(info, policy, name, expected_archive)
                    ):
                        reason = "container_configuration_mismatch"
                        status = "failed"
                    else:
                        exit_code, stdout, stderr = invoke(
                            ["docker", "start", "--attach", created_id]
                        )
                        raw = _phase_result_from_output(stdout)
                        visible_output = "\n".join(
                            line
                            for line in stdout.splitlines()
                            if not line.startswith(_RESULT_MARKER)
                        )
                        output = (visible_output + "\n" + stderr)[-_OUTPUT_TAIL:]
                        status, reason, exit_code, execution = (
                            _classify_container_result(
                                exit_code, raw, plan, policy, freshness
                            )
                        )
            if created and status != "unknown":
                cleanup = False
    except subprocess.TimeoutExpired:
        status, reason, exit_code = "unknown", "transport_timeout", None
    except Exception:
        if receipt_path is None:
            raise
        # Persist only a code, never raw host diagnostics or exception contents.
        status, reason, exit_code = "unknown", "phase_runner_error", None
    finally:
        if freshness:
            try:
                after = verify_phase_freshness(policy, workspace, phase)
                workspace_post_sha = str(after["snapshot_sha256"])
                if workspace_post_sha != freshness.get("snapshot_sha256"):
                    status, reason, exit_code = (
                        "unknown",
                        "host_workspace_changed_during_phase",
                        None,
                    )
            except Exception:
                status, reason, exit_code = (
                    "unknown",
                    "host_workspace_changed_during_phase",
                    None,
                )
        if created and transport is not None:
            try:
                rm_code, _, _ = transport(
                    ["docker", "rm", "--force", name], "", workspace, 5.0
                )
                inspect_code, remaining, _ = transport(
                    [
                        "docker",
                        "ps",
                        "-a",
                        "--filter",
                        f"name=^/{name}$",
                        "--format",
                        "{{.ID}}",
                    ],
                    "",
                    workspace,
                    5.0,
                )
                cleanup = rm_code == 0 and inspect_code == 0 and not remaining.strip()
            except Exception:
                cleanup = False
            if not cleanup:
                status, reason, exit_code = (
                    "unknown",
                    "container_cleanup_unconfirmed",
                    None,
                )
    receipt: dict[str, object] = {
        "schema": "agentkit/local-phase-receipt-v1",
        "status": status,
        "run_id": run_id,
        "phase": phase,
        "reason": reason,
        "exit_code": exit_code,
        "outcome_source": "pytest_child_report",
        "policy_sha256": policy.sha256,
        "host_runner_sha256": policy.host_runner_sha256,
        "image_ref": policy.image_ref,
        "image_id": policy.image_id,
        "dependency_lock_sha256": policy.dependency_lock_sha256,
        "snapshot_sha256": snapshot_sha,
        "workspace_post_snapshot_sha256": workspace_post_sha,
        "input_hashes": freshness.get("input_hashes", {}),
        "collection": execution.get("collection", {}),
        "outcomes": execution.get("outcomes", {}),
        "scratch_post_hashes": execution.get("scratch_post_hashes", {}),
        "cleanup_confirmed": cleanup,
        "duration_seconds": round(time.monotonic() - started, 3),
        "output": output,
    }
    receipt["receipt_sha256"] = hashlib.sha256(_json_bytes(receipt)).hexdigest()
    if receipt_path is not None:
        _write_json_exclusive(receipt_path, receipt)
    return receipt
