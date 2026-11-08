import re
from pathlib import Path


def publishes_image(step: str) -> bool:
    return bool(
        (
            re.search(r"uses:\s*docker/build-push-action@", step)
            and re.search(r"(?m)^\s+push:\s*true\s*$", step)
        )
        or re.search(r"\bdocker\s+(?:image\s+)?push\b", step)
    )


def test_image_publishing_workflow_supports_main_pushes_and_manual_runs(
    repo_root: Path,
) -> None:
    workflows = repo_root / ".github" / "workflows"
    candidates = list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml"))
    publish_workflows = [
        path.read_text(encoding="utf-8")
        for path in candidates
        if "ghcr.io" in path.read_text(encoding="utf-8").lower()
    ]
    assert publish_workflows, "a GHCR image publishing workflow is required"
    assert any(
        re.search(r"\bpush\s*:", workflow)
        and re.search(r"\bmain\b", workflow)
        and re.search(r"\bworkflow_dispatch\s*:", workflow)
        for workflow in publish_workflows
    ), "a publishing workflow must support pushes to main and manual runs"


def test_image_publishing_workflow_uses_commit_based_versions(repo_root: Path) -> None:
    workflows = repo_root / ".github" / "workflows"
    candidates = list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml"))
    contents = [path.read_text(encoding="utf-8") for path in candidates]
    assert any(
        "ghcr.io" in workflow.lower()
        and re.search(r"github\.sha|GITHUB_SHA", workflow, re.IGNORECASE)
        for workflow in contents
    ), "GHCR image versions must incorporate the triggering commit SHA"


def test_image_tags_include_latest_only_on_main(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    steps = re.split(r"(?m)^\s{6}-\s+(?=name:|uses:)", workflow)
    publish_steps = [
        step for step in steps
        if publishes_image(step)
    ]
    assert publish_steps, "workflow must publish images"
    sha = "a" * 40
    for ref, latest in (("refs/heads/main", True), ("refs/heads/feature/test", False)):
        tags: dict[str, set[str]] = {"backend": set(), "frontend": set()}
        for step in publish_steps:
            condition = re.search(r"(?m)^\s*if:\s*(.*?)\s*$", step)
            if condition:
                expression = condition.group(1).removeprefix("${{").removesuffix("}}").strip()
                assert re.fullmatch(
                    r"github\.ref\s*==\s*['\"]refs/heads/main['\"]", expression
                ), f"unsupported publish condition: {expression}"
                if ref != "refs/heads/main":
                    continue
            for component, tag in re.findall(
                r"print-job-manager-(backend|frontend):"
                r"(latest|\$\{\{\s*github\.sha\s*\}\})", step
            ):
                tags[component].add(sha if tag != "latest" else tag)
        for component in ("backend", "frontend"):
            expected = {sha}
            if latest:
                expected.add("latest")
            assert tags[component] == expected, f"{component} tags for {ref}"


def test_both_image_checks_gate_publication(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    job_parts = re.split(r"(?m)^  ([\w-]+):\s*$", workflow.partition("\njobs:\n")[2])
    jobs = dict(zip(job_parts[1::2], job_parts[2::2], strict=True))
    required = {
        "backend/tests/test_production_image.py",
        "backend/tests/test_frontend_production_image.py",
    }

    def checks_before_publish(job_name: str, seen: set[str]) -> set[str]:
        assert job_name not in seen, "job dependencies must not contain cycles"
        assert job_name in jobs, f"unknown job dependency: {job_name}"
        job = jobs[job_name]
        seen = seen | {job_name}
        checked: set[str] = set()
        needs = re.search(r"(?m)^    needs:\s*(.+?)\s*$", job)
        if needs:
            dependencies = needs.group(1).strip("[]").split(",")
            for dependency in dependencies:
                checked.update(checks_before_publish(dependency.strip(), seen))
        assert not re.search(r"(?m)^    if:.*\b(always|failure)\s*\(", job), (
            "dependent publishing must not bypass failed checks"
        )
        assert not re.search(r"(?m)^    continue-on-error:\s*true\s*$", job), (
            "check failures must fail their job"
        )
        steps = re.split(r"(?m)^\s{6}-\s+(?=name:|uses:)", job)
        for step in steps:
            if publishes_image(step):
                break
            if re.search(r"\bpytest\b", step) and not re.search(
                r"(?m)^\s*(if|continue-on-error):", step
            ):
                checked.update(test_file for test_file in required if test_file in step)
        return checked

    publish_jobs = 0
    for job_name, job in jobs.items():
        steps = re.split(r"(?m)^\s{6}-\s+(?=name:|uses:)", job)
        first_push = next(
            (
                index for index, step in enumerate(steps)
                if publishes_image(step)
            ),
            None,
        )
        if first_push is None:
            continue
        publish_jobs += 1
        assert checks_before_publish(job_name, set()) == required, (
            "both image check suites must run successfully before any image is published"
        )
        for step in steps[first_push:]:
            if publishes_image(step):
                assert not re.search(r"\b(always|failure)\s*\(", step), (
                    "publishing must not bypass failed checks"
                )
                assert not re.search(r"(?m)^\s*continue-on-error:\s*true\s*$", step), (
                    "publication failures must fail the workflow"
                )
    assert publish_jobs, "workflow must publish images"


def test_publication_does_not_rebuild_images_after_checks(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    steps = re.split(r"(?m)^\s{6}-\s+(?=name:|uses:)", workflow)
    publishing_steps = [step for step in steps if publishes_image(step)]
    assert publishing_steps, "workflow must publish images"
    assert all(
        not re.search(r"uses:\s*docker/build-push-action@", step)
        for step in publishing_steps
    ), "publishing must reuse the tested image artifacts instead of rebuilding them"


def test_latest_ordering_does_not_cancel_sha_publication(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    workflow_concurrency = re.search(
        r"(?m)^concurrency:\s*\n((?:  [^\n]*\n)+)", workflow
    )
    if workflow_concurrency:
        settings = workflow_concurrency.group(1)
        assert re.search(r"(?m)^  queue:\s*max\s*$", settings), (
            "workflow-level concurrency must queue SHA publication runs"
        )
        assert not re.search(r"(?m)^  cancel-in-progress:\s*true\s*$", settings), (
            "workflow-level concurrency must not cancel SHA publication runs"
        )
    jobs = re.split(r"(?m)^  [\w-]+:\s*$", workflow.partition("\njobs:\n")[2])
    sha_jobs = [job for job in jobs if re.search(r"docker push[^\n]*github\.sha", job)]
    latest_jobs = [job for job in jobs if re.search(r"docker push[^\n]*:latest\b", job)]
    assert sha_jobs and latest_jobs, "both SHA and latest publications are required"
    assert not any(job in latest_jobs for job in sha_jobs), (
        "latest ordering must not cancel or queue the SHA publication job"
    )
    for job in latest_jobs:
        assert re.search(r"(?m)^    concurrency:\s*$", job), (
            "latest publication jobs must share concurrency control"
        )
        assert re.search(r"(?m)^\s+group:\s*\S", job), "latest concurrency needs a group"
        assert re.search(r"git\s+ls-remote\b[^\n]*refs/heads/main", job), (
            "latest publication must check the current main commit"
        )


def test_sha_publication_warns_about_partial_failure_and_recovery(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    steps = re.split(r"(?m)^\s{6}-\s+(?=name:|uses:)", workflow)
    sha_steps = [step for step in steps if re.search(r"docker push[^\n]*github\.sha", step)]
    assert sha_steps, "workflow must publish SHA-tagged images"
    for step in sha_steps:
        assert re.search(r"(?i)(?:warning|error).*\b(?:partial|one|only|incomplete)\b", step), (
            "SHA publication must warn that a failure can leave a partial image pair"
        )
        assert re.search(r"(?i)\b(?:rerun|retry)\b", step), (
            "SHA publication must describe how to recover from partial publication"
        )


def test_same_sha_publication_is_serialized_without_canceling_pending_runs(
    repo_root: Path,
) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    jobs = re.split(r"(?m)^  [\w-]+:\s*$", workflow.partition("\njobs:\n")[2])
    sha_jobs = [job for job in jobs if re.search(r"docker push[^\n]*github\.sha", job)]
    assert sha_jobs, "workflow must publish SHA-tagged images"
    workflow_concurrency = re.search(
        r"(?m)^concurrency:\s*\n((?:  [^\n]*\n)+)", workflow
    )
    if workflow_concurrency:
        settings = workflow_concurrency.group(1)
        assert re.search(r"(?m)^  group:.*github\.sha", settings)
        assert not re.search(r"(?m)^  group:.*github\.ref", settings)
        assert re.search(r"(?m)^  queue:\s*max\s*$", settings)
        assert not re.search(r"(?m)^  cancel-in-progress:\s*true\s*$", settings)
        return
    for job in sha_jobs:
        concurrency = re.search(
            r"(?m)^    concurrency:\s*\n((?:      [^\n]*\n)+)", job
        )
        assert concurrency, "same-SHA publication jobs must be serialized"
        settings = concurrency.group(1)
        assert re.search(r"(?m)^      group:.*github\.sha", settings), (
            "same commit must use the same publication concurrency group"
        )
        assert not re.search(r"(?m)^      group:.*github\.ref", settings), (
            "same-SHA runs from different refs must share a group"
        )
        assert re.search(r"(?m)^      queue:\s*max\s*$", settings), (
            "queue same-SHA runs instead of replacing pending publication jobs"
        )
        assert not re.search(r"(?m)^      cancel-in-progress:\s*true\s*$", settings), (
            "same-SHA publication must not cancel in-progress jobs"
        )


def test_latest_publication_queues_pending_runs(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    jobs = re.split(r"(?m)^  [\w-]+:\s*$", workflow.partition("\njobs:\n")[2])
    latest_jobs = [job for job in jobs if re.search(r"docker push[^\n]*:latest\b", job)]
    assert latest_jobs, "workflow must publish latest images"
    for job in latest_jobs:
        concurrency = re.search(
            r"(?m)^    concurrency:\s*\n((?:      [^\n]*\n)+)", job
        )
        assert concurrency, "latest publication must have concurrency control"
        assert re.search(r"(?m)^      queue:\s*max\s*$", concurrency.group(1)), (
            "latest publication must queue pending runs instead of replacing them"
        )


def test_same_sha_lock_covers_publication_and_latest_promotion(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    concurrency = re.search(r"(?m)^concurrency:\s*\n((?:  [^\n]*\n)+)", workflow)
    assert concurrency, "same-SHA coordination must cover the entire workflow through promotion"
    settings = concurrency.group(1)
    assert re.search(r"(?m)^  group:.*github\.sha", settings), (
        "same-SHA runs must use the same workflow concurrency group"
    )
    assert not re.search(r"(?m)^  group:.*github\.ref", settings), (
        "same-SHA runs from different refs must share the workflow lock"
    )
    assert re.search(r"(?m)^  queue:\s*max\s*$", settings), (
        "same-SHA workflow runs must queue rather than replace pending runs"
    )
    assert not re.search(r"(?m)^  cancel-in-progress:\s*true\s*$", settings), (
        "same-SHA workflow runs must not cancel in-progress publication"
    )
