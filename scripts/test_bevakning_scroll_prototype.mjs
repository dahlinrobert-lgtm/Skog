import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { writeFileSync, unlinkSync } from "node:fs";

const html = readFileSync(new URL("../docs/bevakning-test.html", import.meta.url), "utf8");

test("scrollprototypen är separat och behåller befintliga datakomponenter", () => {
  for (const id of ["storyLayout", "storyProgress", "storyProgressFill", "feed", "activityMap", "casePreview", "monthFilter"]) {
    assert.match(html, new RegExp('id="' + id + '"'));
  }
  assert.match(html, /bevakning-core\.mjs/);
  assert.match(html, /algdata-bevakning\.mjs/);
  assert.match(html, /Till ordinarie sida/);
});

test("scrollupplevelsen har fördröjd kartförhandsvisning och klickbar händelseruta", () => {
  assert.match(html, /IntersectionObserver/);
  assert.match(html, /prefers-reduced-motion:\s*reduce/);
  assert.match(html, /aria-valuenow/);
  assert.match(html, /setupScrollExperience\(list\)/);
  assert.match(html, /STORY_PREVIEW_DELAY=250/);
  assert.match(html, /scheduleStoryPreview\(activeStoryCard\(cards\),list,cards\)/);
  assert.match(html, /window\.clearTimeout\(storyPreviewTimer\)/);
  assert.match(html, /stillActive\.dataset\.key!==key/);
  assert.match(html, /tabindex="0" aria-label="Visa /);
  assert.match(html, /event\.target\.closest\("a"\)/);
  assert.match(html, /event\.key==="Enter"\|\|event\.key===" "/);
  assert.doesNotMatch(html, /Förhandsvisa ärende/);
  assert.doesNotMatch(html, /data-select=/);
});

test("inline module script passes Node syntax validation", () => {
  const match = html.match(/<script type="module">([\s\S]*?)<\/script>/);
  assert.ok(match, "module script should exist");
  const temp = join(tmpdir(), "skog-bevakning-scroll-check-" + process.pid + ".mjs");
  try {
    writeFileSync(temp, match[1].replace(/^import .*bevakning-core\.mjs";\s*/m, ""));
    const result = spawnSync(process.execPath, ["--check", temp], { encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr || result.stdout);
  } finally {
    try { unlinkSync(temp); } catch {}
  }
});
