# NVDB – nationell egenskapsanalys av vägkandidater

**Status:** första fristående feature-extraktor under utveckling i PR.  
**Syfte:** hitta återkommande egenskaper och kombinationer i nationella vägkandidatresultat utan att manuellt granska varje händelse.

## Indata och utdata

Skriptet `scripts/build_nvdb_candidate_features.py` läser CSV-utdata från `scripts/match_points_to_nvdb_roads.py` och skapar:

- händelsenivå: koordinater, sökstatus, antal kandidater, närmaste och näst närmaste avstånd, avståndsgap, avståndskvot, källproveniens och sökfel;
- kandidatnivå: rangordning, avstånd, avstånd från närmaste kandidat, vägnummer, vägroll, NVDB-element-ID och källfil;
- JSON-sammanfattning: statusfördelning och kandidatantal per vägroll/vägnummer.

Ingen korrekthetsklass eller automatisk bekräftelse skapas. Saknade eller felaktiga kandidatlistor blir tomma kandidatlistor; statusen från matcharen bevaras.

## Körning

```powershell
python scripts/build_nvdb_candidate_features.py `
  --input path\to\nvdb-road-match.csv `
  --events-output path\to\nvdb-event-features.csv `
  --candidates-output path\to\nvdb-candidate-features.csv `
  --summary-output path\to\nvdb-feature-summary.json
```

Ange `--event-id-field` när en stabil händelseidentitet finns i indatan. Radnummer är annars endast körningslokalt.

## Analysidé

Jämför kombinationer av:
- närmaste avstånd och skillnaden till näst närmaste kandidat;
- avståndskvot mellan första och andra kandidat;
- vägnummer och vägroll;
- kandidatantal och geografisk källproveniens;
- sökstatus och antal lästa/felande källor.

Dessa variabler kan användas för stratifiering, klustring och senare modellering. De är inte etiketter för rätt/fel. För att uppskatta faktisk träffsäkerhet krävs oberoende utfallsetiketter; utan sådana kan analysen endast hitta struktur och samvariation.

## Begränsningar

- Endast kandidater som finns kvar i matchnings-CSV:n analyseras; matcharens maxgräns begränsar synliga alternativ.
- Källfilernas proveniens visar inte geografisk täckning.
- `partial_source_read` får inte användas som negativ evidens.
- Inga temporala fält, kandidater, poäng, statusar eller `geographic_match_used` ändras.
- Resultaten är analysunderlag, inte kundvisning eller juridisk bekräftelse av olycksplats.

## Nästa steg

1. Kör extraktorn mot åttahändelsepiloten för schema-/funktionskontroll.
2. Kör därefter den befintliga matcharen mot ett större historiskt nationellt urval och alla 21 kompatibilitetskontrollerade länsarkiv.
3. Mät körtid, minne, antal händelser/kandidater och partiella källfel.
4. Analysera egenskapsfördelningar och kluster separat per sökstatus och geografiskt område.
5. Bygg först därefter en separat, versionsstyrd poängmodell; ändra inte temporal matchning.
