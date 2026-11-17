import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { writeFileSync, unlinkSync } from "node:fs";

const html = readFileSync(new URL("../docs/bevakning-test.html", import.meta.url), "utf8");
const productionHtml = readFileSync(new URL("../docs/bevakning.html", import.meta.url), "utf8");

test("scrollprototypen är separat och behåller befintliga datakomponenter", () => {
  for (const id of ["storyLayout", "storyProgress", "storyProgressFill", "feed", "activityMap", "casePreview", "monthFilter", "forestFilter", "animalFilter"]) {
    assert.match(html, new RegExp('id="' + id + '"'));
  }
  assert.match(html, /bevakning-core\.mjs/);
  assert.match(html, /algdata-bevakning\.mjs/);
  assert.match(html, /data-kind="samrad"[^>]*>Samråd/);
  assert.match(html, /data-animal="collisions"[^>]*>Viltolyckor/);
  assert.match(html, /data-animal="hunting"[^>]*>Jakt/);
  assert.match(html, /id="forestFilterGroup"[^>]*aria-labelledby="forestFilterHeading"/);
  assert.match(html, /id="forestFilterHeading"[^>]*>[\s\S]*?Skog[\s\S]*?<svg/);
  assert.match(html, /id="animalFilterGroup"[^>]*aria-labelledby="animalFilterHeading"/);
  assert.match(html, /id="animalFilterHeading"[^>]*>[\s\S]*?Djur[\s\S]*?<svg/);
  assert.match(html, /\.filter-group-heading\{height:37px/);
  assert.match(html, /html\[data-theme="dark"\] \.filter-group-heading/);
  assert.match(html, /getElementById\("forestFilterGroup"\)\.hidden=isElk\|\|isNvr/);
  assert.match(html, /GeodataportalVisaSamrad\/MapServer\/0\/query/);
  assert.match(html, /GeodataportalVisaSamrad\/MapServer\/1\/query/);
  assert.match(html, /GeodataportalVisaSamrad\/MapServer\/2\/query/);
  assert.doesNotMatch(html, /<option value="elk">Älg/);
  assert.match(html, /NVR-arkiv ej publicerat/);
  assert.match(html, /matchingAreas\.flatMap\(area=>\(area\.snapshots\|\|\[\]\)/);
  assert.match(html, /Number\(snapshot\.delta\)!==0/);
  assert.match(html, /delta>0\?"elkdata-positive":"elkdata-negative"/);
  assert.match(html, /Rapporterad förändring observerad/);
  assert.match(html, /En minskning kan bero på rättelse/);
  assert.match(html, /html\[data-theme="dark"\] \.elkdata-caveat/);
  assert.match(html, /html\[data-theme="dark"\] \.elkdata-negative/);
  assert.doesNotMatch(html, /<th>Första observerade<\/th>/);
  assert.doesNotMatch(html, /<th>Senaste uttag<\/th>/);
  assert.match(html, /colspan="6" class="elkdata-empty"/);
  assert.match(html, /Till ordinarie sida/);
});

test("produktionssidan använder den godkända prototypen utan testmarkering", () => {
  for (const id of ["storyLayout", "forestFilterGroup", "animalFilterGroup", "basemapImagery", "basemapStandard", "imageryDate", "activityMap", "casePreview"]) {
    assert.match(productionHtml, new RegExp('id="' + id + '"'));
  }
  assert.match(productionHtml, /<title>Skogsbevakning – Nordmaling<\/title>/);
  assert.doesNotMatch(productionHtml, /class="prototype-banner"|DESIGNTEST|Scrollprototyp ·/);
  assert.match(productionHtml, /function setBasemap\(mode\)/);
  assert.match(productionHtml, /standardColors=\{planned:"#d88a32",done:"#3e8b59",samrad:"#3e8b59"\}/);
  assert.match(productionHtml, /imageryColors=\{planned:"#ff6238",done:"#00d5ef",samrad:"#f1e64b"\}/);
  assert.match(productionHtml, /data-basemap="imagery"/);
  assert.match(productionHtml, /data-basemap="standard"/);
  assert.doesNotMatch(productionHtml, /getElementById\("forestFilterGroup"\)\.hidden=isElk\|\|isNvr/);
  assert.match(productionHtml, /getElementById\("forestFilterGroup"\)\.hidden=false/);
  assert.match(productionHtml, /let activeFilterCategory="forest"/);
  assert.match(productionHtml, /forestFilterGroup"\)\.classList\.toggle\("is-active",activeFilterCategory==="forest"\)/);
  assert.match(productionHtml, /animalFilterGroup"\)\.classList\.toggle\("is-active",activeFilterCategory==="animal"\)/);
  assert.match(productionHtml, /activeFilterCategory="forest"/);
  assert.match(productionHtml, /activeFilterCategory="animal"/);
  assert.match(productionHtml, /activeFilterCategory="forest";[\s\S]*?animalMode/);
  assert.match(productionHtml, /activeFilterCategory="animal";[\s\S]*?const mode=button\.dataset\.animal/);
  assert.match(productionHtml, /\.filter-group\.is-active \.filter-group-heading\{/);
  assert.match(productionHtml, /html\[data-theme="dark"\] \.filter-group\.is-active \.filter-group-heading/);
  assert.match(productionHtml, /if\(baseMapMode!=="imagery"\|\|!activityMap\|\|!label\)return/);
  assert.match(productionHtml, /imageryDateRequest\+\+;label\.hidden=true/);
  assert.match(productionHtml, /Älgförvaltningsområden – hela Sverige/);
  assert.match(productionHtml, /lst_jaktadm_visning\/MapServer\/1\/query/);
  assert.match(productionHtml, /returnIdsOnly/);
  assert.match(productionHtml, /objectIds/);
  assert.match(productionHtml, /outSR.*4326/);
  assert.match(productionHtml, /async function fetchAfoBoundaryData\(\)/);
  assert.match(productionHtml, /function setAfoLayerVisible\(visible\)/);
  assert.match(productionHtml, /L\.geoJSON\(data/);
  assert.doesNotMatch(productionHtml, /tileLayer\.wms/);
  assert.doesNotMatch(productionHtml, /elkAfoMap/);
  assert.match(productionHtml, /setAfoLayerVisible\(true\)/);
  assert.match(productionHtml, /setAfoLayerVisible\(false\)/);
  assert.match(productionHtml, /document\.querySelector\("\.map-card"\)\.hidden=false/);
  assert.match(productionHtml, /map-card\.is-animal-map/);
  assert.match(productionHtml, /map-legend\[hidden\]/);
  assert.match(productionHtml, /Regional avskjutningsstatistik/);
  assert.match(productionHtml, /inte geografiskt kopplad till ÄFO-polygonerna/);
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

test("kartan använder flyg-/satellitbilder och visar platsbaserat bilddatum", () => {
  assert.ok(html.includes("World_Imagery/MapServer/tile/"));
  assert.ok(html.includes("World_Imagery/MapServer/0/query"));
  assert.match(html, /SRC_DATE,SRC_DATE2,NICE_NAME,NICE_DESC,SRC_RES/);
  assert.match(html, /id="imageryDate" aria-live="polite"/);
  assert.match(html, /#imageryDate\{min-height:2\.8em;line-height:1\.4;\}/);
  assert.match(html, /activityMap\.on\("moveend",\(\)=>\{if\(baseMapMode==="imagery"\)scheduleImageryDateUpdate\(\);\}\)/);
  assert.match(html, /Flyg-\/satellitbild tagen /);
  assert.doesNotMatch(html, /\(kartans mittpunkt\)/);
  assert.match(html, /Bilddatum saknas för kartans mitt/);
  assert.doesNotMatch(html, /Kartan ger geografisk kontext till det valda bevakningsflödet/);
});

test("prototype and production inline module scripts pass Node syntax validation", () => {
  for (const [label, source] of [["prototype", html], ["production", productionHtml]]) {
    const match = source.match(/<script type="module">([\s\S]*?)<\/script>/);
    assert.ok(match, label + " module script should exist");
    const temp = join(tmpdir(), "skog-bevakning-" + label + "-check-" + process.pid + ".mjs");
    try {
      writeFileSync(temp, match[1].replace(/^import .*bevakning-core\.mjs";\s*/m, ""));
      const result = spawnSync(process.execPath, ["--check", temp], { encoding: "utf8" });
      assert.equal(result.status, 0, result.stderr || result.stdout);
    } finally {
      try { unlinkSync(temp); } catch {}
    }
  }
});
