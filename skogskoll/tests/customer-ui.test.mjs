import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const nav = html.match(/<nav class="skog-global-nav"[\\s\\S]*?<\\/nav>/)?.[0] ?? "";
test("customer navigation contains only Skogskoll destinations", () => {
  assert.match(nav, /Skogskoll/);
  for (const href of ["#flow", "#map-preview", "#watch-areas", "#history", "#account"]) {
    assert.ok(nav.includes('href="' + href + '"'), "missing customer destination " + href);
    assert.match(html, new RegExp('id="' + href.slice(1) + '"' ));
  }
  assert.doesNotMatch(nav, /\\.\\.\\/|docs\\/|bevakning\\.html|karta\\.html|historik\\.html/);
});
test("customer page does not link to internal Skog pages", () => {
  assert.doesNotMatch(html, /href=["\'][^"\']*(?:\\.\\.\\/|\\/docs\\/karta\\.html|\\/Skog\\/karta\\.html)/);
});
test("daily change feed is primary and clearly marks disconnected data", () => {
  assert.match(html, /id="flow"/);
  assert.match(html, /Förändringar – dag för dag/);
  assert.match(html, /id="flowDate"/);
  assert.match(html, /Inga verifierade snapshots är anslutna ännu/);
  assert.match(html, /kompletta, jämförbara snapshots/);
});
test("map preview never opens the internal Skog map", () => {
  const mapArea = html.match(/function mapArea\\(area\\)\\{[\\s\\S]*?\\n\\}/)?.[0] ?? "";
  assert.ok(mapArea);
  assert.doesNotMatch(mapArea, /window\\.open|docs\\/karta\\.html/);
  assert.match(mapArea, /Kundkartan är ännu inte ansluten/);
});
