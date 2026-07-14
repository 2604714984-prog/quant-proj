from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


binding = load_script("derive_runtime_binding.py")
coverage = load_script("validate_r2_closure_coverage.py")


def _fixture_repo(tmp_path: Path, contract: dict) -> Path:
    root = tmp_path / "repo"
    modules = {
        "usq/cli.py": """
def cmd_data_import_csv():
    from usq.data.csv_importer import CsvImporter
    CsvImporter()
    CsvImporter.from_config()
def cmd_data_provider_qualification():
    from usq.data.provider_qualification import qualify_providers
    from usq.data.data_readiness_gate import run_data_readiness
    qualify_providers()
    run_data_readiness()
def cmd_data_readiness():
    from usq.data.data_readiness_gate import run_data_readiness
    run_data_readiness()
def cmd_research_phase_us2():
    from usq.research.phase_us2_candidate_gate import run_phase_us2_evidence
    run_phase_us2_evidence()
""",
        "usq/data/csv_importer.py": "class CsvImporter: pass\n",
        "usq/data/csv_provider.py": "from usq.data.csv_importer import CsvImporter\nclass CsvImporterProvider: pass\n",
        "usq/data/data_readiness_gate.py": "from usq.data.provider_qualification import qualify_providers\ndef run_data_readiness(): pass\n",
        "usq/data/factory.py": """
from usq.data.csv_provider import CsvImporterProvider
def read_bound_file(): pass
def load_controller_authorization(): pass
def _csv_runtime():
    read_bound_file()
    load_controller_authorization()
    return CsvImporterProvider()
def get_provider(name):
    if name == 'csv':
        return _csv_runtime()
""",
        "usq/data/provider_qualification.py": """
from usq.data.factory import get_provider
from usq.data.csv_importer import CsvImporter
from usq.data.csv_provider import CsvImporterProvider
def validate_runtime(): pass
def _qualify():
    get_provider('csv')
    validate_runtime()
def qualify_providers():
    return _qualify()
""",
        "usq/research/phase_us2_candidate_gate.py": """
from usq.data.factory import get_provider
from usq.data.csv_provider import CsvImporterProvider
from usq.research.phase_us2_evidence_gate import apply_evidence_gate
def validate_runtime(): pass
def subset_panel(): pass
def _load_panel():
    get_provider('csv')
    validate_runtime()
    subset_panel()
def run_phase_us2_evidence():
    _load_panel()
    apply_evidence_gate()
""",
        "usq/research/phase_us2_evidence_gate.py": """
def validate(): pass
def apply_evidence_gate():
    validate()
""",
        "usq/observation/runner.py": "from usq.research.phase_us2_candidate_gate import run_phase_us2_evidence\nfrom usq.research.phase_us2_evidence_gate import apply_evidence_gate\n",
        "usq/research/pipeline.py": "from usq.data.factory import get_provider\n",
    }
    for relative, content in modules.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def test_runtime_binding_derives_exact_active_paths(tmp_path: Path) -> None:
    contract = json.loads(
        (ROOT / "reports/remediation_r2/RUNTIME_BINDING_CONTRACT_20260713.json")
        .read_text(encoding="utf-8")
    )
    source = _fixture_repo(tmp_path, contract)
    derived = binding.validate(source, contract, require_git=False)
    assert derived["cli_sensitive_functions"] == sorted(contract["expected_cli_functions"])


def test_runtime_binding_rejects_adjacent_path_and_missing_edge(tmp_path: Path) -> None:
    contract = json.loads(
        (ROOT / "reports/remediation_r2/RUNTIME_BINDING_CONTRACT_20260713.json")
        .read_text(encoding="utf-8")
    )
    source = _fixture_repo(tmp_path, contract)
    with (source / "usq/cli.py").open("a", encoding="utf-8") as handle:
        handle.write("\ndef cmd_hidden():\n    from usq.data.factory import get_provider\n")
    with pytest.raises(binding.RuntimeBindingError, match="CLI function set"):
        binding.validate(source, contract, require_git=False)
    source = _fixture_repo(tmp_path / "second", contract)
    (source / "usq/data/provider_qualification.py").write_text(
        "def qualify_providers(): pass\n", encoding="utf-8"
    )
    with pytest.raises(binding.RuntimeBindingError, match="edge set differs"):
        binding.validate(source, contract, require_git=False)


def test_runtime_binding_rejects_factory_return_replacement(tmp_path: Path) -> None:
    contract = json.loads(
        (ROOT / "reports/remediation_r2/RUNTIME_BINDING_CONTRACT_20260713.json")
        .read_text(encoding="utf-8")
    )
    source = _fixture_repo(tmp_path, contract)
    factory = source / "usq/data/factory.py"
    factory.write_text(
        factory.read_text(encoding="utf-8").replace(
            "return CsvImporterProvider()", "return AlternateProvider()"
        ) + "\nclass AlternateProvider: pass\n",
        encoding="utf-8",
    )
    with pytest.raises(binding.RuntimeBindingError, match="call missing"):
        binding.validate(source, contract, require_git=False)


def test_closure_coverage_is_exact_and_omission_fails(tmp_path: Path) -> None:
    matrix = json.loads(
        (ROOT / "reports/remediation_r2/R2_FINDING_CLOSURE_MATRIX_20260713.json")
        .read_text(encoding="utf-8")
    )
    contract_path = ROOT / "reports/remediation_r2/RUNTIME_BINDING_CONTRACT_20260713.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    source = _fixture_repo(tmp_path, contract)
    runtime = {
        "schema_version": "runtime-binding-result-v1",
        "source_commit": contract["commit"],
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "derived": binding.evidence_projection(
            binding.validate(source, contract, require_git=False), contract
        ),
        "strategy_candidate_available": False,
    }
    validation_args = {
        "runtime_result": runtime,
        "runtime_contract": contract,
        "runtime_contract_sha256": runtime["contract_sha256"],
    }
    coverage.validate(matrix, **validation_args)
    broken = copy.deepcopy(matrix)
    broken["findings"][4]["active_surfaces"].remove("factory")
    with pytest.raises(coverage.ClosureCoverageError, match="RW-005"):
        coverage.validate(broken, **validation_args)
    broken_runtime = copy.deepcopy(runtime)
    broken_runtime["derived"]["function_calls"][
        "usq.research.phase_us2_candidate_gate._load_panel"
    ].remove("subset_panel")
    with pytest.raises(coverage.ClosureCoverageError, match="function calls"):
        coverage.validate(
            matrix,
            runtime_result=broken_runtime,
            runtime_contract=contract,
            runtime_contract_sha256=runtime["contract_sha256"],
        )
    bad_receipt = copy.deepcopy(matrix)
    bad_receipt["findings"][-1]["receipt_sha256"] = "0" * 64
    with pytest.raises(coverage.ClosureCoverageError, match="receipt bytes"):
        coverage.validate(
            bad_receipt,
            **validation_args,
        )
    for field, replacement, message in (
        ("sensitive_module_edges", [], "sensitive edge"),
        ("return_calls", {}, "return calls"),
        ("conditional_return_calls", {}, "conditional return"),
    ):
        mutated = copy.deepcopy(runtime)
        mutated["derived"][field] = replacement
        with pytest.raises(coverage.ClosureCoverageError, match=message):
            coverage.validate(
                matrix,
                runtime_result=mutated,
                runtime_contract=contract,
                runtime_contract_sha256=runtime["contract_sha256"],
            )
    wrong_source = copy.deepcopy(runtime)
    wrong_source["source_commit"] = "0" * 40
    with pytest.raises(coverage.ClosureCoverageError, match="identity"):
        coverage.validate(
            matrix,
            runtime_result=wrong_source,
            runtime_contract=contract,
            runtime_contract_sha256=runtime["contract_sha256"],
        )
