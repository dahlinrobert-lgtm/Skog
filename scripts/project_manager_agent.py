#!/usr/bin/env python3
"""Read-only GitHub inventory and project-manager report for Skog/Skogskoll."""
from __future__ import annotations
import argparse, json, os, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_ROOT = "https://api.github.com"
DEFAULT_DOCS = (
    "docs/AI_HANDOVER.md", "docs/SKOGSKOLL_SOURCE_STATUS.md",
    "docs/SKOGSKOLL_DATA_OVERVIEW.md", "docs/PROJECT_MANAGER_RULES.md",
    "docs/PROJECT_STATUS.md", "docs/PROJECT_BACKLOG.md",
    "docs/PROJECT_ROADMAP.md", "docs/PROJECT_DECISIONS.md",
    "docs/PROJECT_DEPENDENCIES.md",
)
class GitHubAPIError(RuntimeError): pass

class GitHubClient:
    def __init__(self, token: str, repository: str, opener=None):
        if "/" not in repository: raise ValueError("repository must use owner/name format")
        self.owner, self.name = repository.split("/", 1)
        self.repository, self.token = repository, token
        self.opener = opener or urllib.request.urlopen

    def get_json(self, path: str) -> Any:
        url = path if path.startswith("https://") else f"{API_ROOT}{path}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "skogskoll-project-manager/0.1",
        })
        try:
            with self.opener(req, timeout=30) as response:
                import json
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise GitHubAPIError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubAPIError(f"GitHub API connection failed: {exc.reason}") from exc

    def paged(self, endpoint: str, max_pages: int = 3) -> list[dict[str, Any]]:
        rows = []
        for page in range(1, max_pages + 1):
            sep = "&" if "?" in endpoint else "?"
            batch = self.get_json(f"{endpoint}{sep}per_page=100&page={page}")
            if not isinstance(batch, list): raise GitHubAPIError(f"Expected a list from {endpoint}")
            rows.extend(x for x in batch if isinstance(x, dict))
            if len(batch) < 100: break
        return rows

    def file_metadata(self, path: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(path, safe="/")
        item = self.get_json(f"/repos/{self.repository}/contents/{encoded}?ref=main")
        if not isinstance(item, dict) or item.get("type") != "file":
            raise GitHubAPIError(f"Expected file metadata for {path}")
        return {"path": path, "sha": item.get("sha"), "size": item.get("size"), "exists": True}

def _issue_summary(item):
    return {"number": item.get("number"), "title": item.get("title", ""),
        "state": item.get("state"), "state_reason": item.get("state_reason"),
        "updated_at": item.get("updated_at"), "created_at": item.get("created_at"),
        "url": item.get("html_url"),
        "labels": [x.get("name") for x in item.get("labels", []) if isinstance(x, dict)]}

def _pull_summary(item):
    return {"number": item.get("number"), "title": item.get("title", ""),
        "state": item.get("state"), "draft": bool(item.get("draft")),
        "merged_at": item.get("merged_at"), "updated_at": item.get("updated_at"),
        "created_at": item.get("created_at"), "url": item.get("html_url"),
        "base": (item.get("base") or {}).get("ref"), "head": (item.get("head") or {}).get("ref")}

def collect_inventory(client: GitHubClient, generated_at: str | None = None) -> dict[str, Any]:
    repo = client.get_json(f"/repos/{client.repository}")
    raw_issues = client.paged(f"/repos/{client.repository}/issues?state=all&sort=updated&direction=desc")
    issues = [_issue_summary(x) for x in raw_issues if "pull_request" not in x]
    raw_pulls = client.paged(f"/repos/{client.repository}/pulls?state=all&sort=updated&direction=desc")
    pulls = [_pull_summary(x) for x in raw_pulls]
    wf_payload = client.get_json(f"/repos/{client.repository}/actions/workflows?per_page=100")
    workflows = wf_payload.get("workflows", []) if isinstance(wf_payload, dict) else []
    run_payload = client.get_json(f"/repos/{client.repository}/actions/runs?per_page=50")
    runs = run_payload.get("workflow_runs", []) if isinstance(run_payload, dict) else []
    commits = client.paged(f"/repos/{client.repository}/commits", max_pages=1)
    docs = []
    for path in DEFAULT_DOCS:
        try: docs.append(client.file_metadata(path))
        except GitHubAPIError as exc: docs.append({"path": path, "exists": False, "error": str(exc)})
    return {
        "schema_version": 1,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "repository": {"full_name": repo.get("full_name", client.repository),
            "default_branch": repo.get("default_branch"), "html_url": repo.get("html_url"),
            "private": repo.get("private"), "archived": repo.get("archived")},
        "collection_limits": {"issues_pages": 3, "pull_request_pages": 3,
            "recent_commits": 100, "workflow_runs": 50,
            "note": "Lists are bounded; inspect pagination and totals before treating them as exhaustive."},
        "issues": issues, "pull_requests": pulls,
        "workflows": [{"id": w.get("id"), "name": w.get("name"), "path": w.get("path"),
            "state": w.get("state"), "url": w.get("html_url")} for w in workflows],
        "workflow_runs": [{"id": r.get("id"), "name": r.get("name"), "workflow_id": r.get("workflow_id"),
            "event": r.get("event"), "status": r.get("status"), "conclusion": r.get("conclusion"),
            "head_branch": r.get("head_branch"), "head_sha": r.get("head_sha"),
            "created_at": r.get("created_at"), "updated_at": r.get("updated_at"),
            "url": r.get("html_url")} for r in runs],
        "recent_commits": [{"sha": c.get("sha"),
            "message": ((c.get("commit") or {}).get("message") or "").splitlines()[0],
            "url": c.get("html_url"), "date": ((c.get("commit") or {}).get("committer") or {}).get("date")}
            for c in commits],
        "documents": docs,
    }

def build_report(data: dict[str, Any]) -> str:
    issues, prs, runs, workflows, docs = (data[k] for k in
        ("issues", "pull_requests", "workflow_runs", "workflows", "documents"))
    open_issues = [x for x in issues if x.get("state") == "open"]
    open_prs = [x for x in prs if x.get("state") == "open"]
    merged = [x for x in prs if x.get("merged_at")]
    failed = [x for x in runs if x.get("status") == "completed" and
        x.get("conclusion") not in ("success", "neutral", "skipped")]
    missing = [x for x in docs if not x.get("exists")]
    lines = ["# Skogskoll – projektledarrapport", "",
        f"- Skapad: {data['generated_at']}",
        f"- Repository: [{data['repository']['full_name']}]({data['repository'].get('html_url', '')})",
        f"- Default branch: `{data['repository'].get('default_branch')}`",
        "- Körläge: read-only inventering; inga GitHub-ändringar eller AI/API-anrop utförs.", "",
        "## Överblick", "",
        f"- Issues i insamlingsfönstret: {len(issues)} (öppna: {len(open_issues)})",
        f"- Pull requests: {len(prs)} (öppna: {len(open_prs)}, mergade: {len(merged)})",
        f"- Workflows: {len(workflows)}",
        f"- Senaste workflow-körningar insamlade: {len(runs)}",
        f"- Misslyckade/avbrutna senaste körningar: {len(failed)}",
        f"- Projektledardokument som saknas: {len(missing)}", "", "## Kräver uppmärksamhet", ""]
    if failed:
        lines.extend(f"- **{x.get('name')}** – `{x.get('conclusion')}` / `{x.get('status')}` ({x.get('updated_at')}); [körning]({x.get('url')})" for x in failed[:20])
    else: lines.append("- Inga misslyckade/avbrutna körningar identifierades bland de 50 senaste returnerade körningarna.")
    if missing: lines.extend(["", "Saknade dokument:"] + [f"- `{x['path']}`" for x in missing])
    lines.extend(["", "## Öppna issues", ""])
    lines.extend([f"- [#{x['number']} – {x['title']}]({x.get('url')}) (uppdaterad {x.get('updated_at')})" for x in open_issues[:50]] or ["- Inga öppna issues i insamlingsfönstret."])
    lines.extend(["", "## Öppna pull requests", ""])
    lines.extend([f"- [#{x['number']} – {x['title']}]({x.get('url')}) (`{x.get('head')}` → `{x.get('base')}`)" for x in open_prs[:50]] or ["- Inga öppna pull requests i insamlingsfönstret."])
    lines.extend(["", "## Projektledardokument", ""])
    lines.extend(f"- `{x['path']}`: {'finns' if x.get('exists') else 'SAKNAS'}" +
        (f" (blob `{x.get('sha')}`)" if x.get("sha") else "") for x in docs)
    lines.extend(["", "## Begränsningar", "",
        "- GitHub-listorna är begränsade till högst tre sidor per issues-/PR-lista och 50 workflow-körningar. Rapporten får inte beskrivas som fullständig om fler sidor finns.",
        "- En misslyckad workflow är en granskningssignal, inte automatiskt bevis för att en datakälla eller produktfunktion är trasig.",
        "- Agenten gör ingen juridisk bedömning och ändrar inte källstatus, backlogg, issues, PR, kod eller produktionsflöden.",
        "- Ingen språkmodell används i denna första version. AI-syntes kräver separat beslut om modell, API-secret och kostnadsgräns.", ""])
    return "\n".join(lines)

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Skogskoll project manager inventory")
    parser.add_argument("--output-dir", default="project-manager-output")
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY", "dahlinrobert-lgtm/Skog")
    if not token: parser.error("Set GITHUB_TOKEN (or GH_TOKEN) with read-only repository permissions.")
    try: data = collect_inventory(GitHubClient(token, repository))
    except (GitHubAPIError, ValueError) as exc:
        print(f"Project inventory failed: {exc}", file=sys.stderr); return 2
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "report.md").write_text(build_report(data), encoding="utf-8")
    print(f"Created read-only project report in {out}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
