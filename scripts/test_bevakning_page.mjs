import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";

const html = readFileSync(new URL("../docs/bevakning.html", import.meta.url), "utf8");

test("bevakningssidan contains the activity map, preview and quick filters", () => {
  for (const id of ["activityMap", "casePreview", "mapSummary", "periodComparison", "monthFilter"]) {
    assert.match(html, new RegExp('id="' + id + '"'));
  }
  assert.match(html, /data-kind="planned"/);
  assert.match(html, /data-kind="done"/);
  assert.match(html, /bevakning-core\.mjs/);
});

test("inline module script passes Node syntax validation", () => {
  const match = html.match(/<script type="module">([\s\S]*?)<\/script>/);
  assert.ok(match, "module script should exist");
  const temp = join(tmpdir(), "skog-bevakning-page-check-" + process.pid + ".mjs");
  try {
    writeFileSync(temp, match[1].replace(/^import .*bevakning-core\.mjs";\s*/m, ""));
    const result = spawnSync(process.execPath, ["--check", temp], { encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr || result.stdout);
  } finally {
    try { unlinkSync(temp); } catch {}
  }
});
