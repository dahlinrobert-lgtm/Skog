# Viltdata – första nationella differensanalys

**Granskad:** 2026-11-25  
**Källa:** Viltdata.se publika StatisticsApi, report type `kill`  
**Metod:** `scripts/viltdata_kill_statistics_diff.py` – observationer nycklas på scope, art-ID och år. `null` hålls åtskilt från numeriskt noll.

## Underlag

| Roll | Snapshot | GitHub Actions |
|---|---|---|
| Baslinje | `20261118T204420Z` | [#44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179) |
| Senare observation | `20261118T220720Z` | [#44408345762](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44408345762) |

Båda manifest är `status=complete`, `complete=true`, 49 arter, 21 län och 550/550 lyckade statistikförfrågningar. Båda innehåller 552 manifestregistrerade råfiler. SHA-256 och byteantal verifierades för samtliga 552 filer i respektive artifact. Observationerna har samma rapporttyp, artinventering, scope-uppsättning och nyckeltäckning.

## Resultat

| Mått | Resultat |
|---|---:|
| Observationer per snapshot | 73 255 |
| Jämförbara nycklar | 73 255 |
| Oförändrade observationer | 73 252 |
| Ändrade observationer | 3 |
| Nya värden | 0 |
| Nya nollvärden | 0 |
| Värden som blivit saknade | 0 |
| Nycklar som saknas i någon snapshot | 0 |

De tre förändringarna gäller rapporterad älgavskjutning för år 2026:

| Scope | Art | År | Baslinje | Senare | Förändring |
|---|---|---:|---:|---:|---:|
| Nationellt | Älg | 2026 | 18 158 | 18 163 | +5 |
| Län 7 | Älg | 2026 | 1 025 | 1 026 | +1 |
| Län 17 | Älg | 2026 | 2 014 | 2 018 | +4 |

Förändringarna är konsistenta: län 7 och län 17 ökar tillsammans med 5, vilket motsvarar den nationella ökningen. Detta är en kontroll av summeringskonsistens för just dessa två län, inte ett påstående om att övriga län är oförändrade i alla möjliga dimensioner.

Antal null-värden var 3 364 och explicita nollvärden 24 950 i båda snapshots. De har inte slagits ihop eller omtolkats.

## Tolkning och begränsningar

- Detta är en tekniskt jämförbar första differens mellan två kompletta uttag med cirka en timmes mellanrum den 18 november 2026.
- De tre ändringarna visar att källans värden för pågående rapporteringsår kan revideras. De ska inte tolkas som nya individuella fälthändelser eller som fälldatum.
- Första kompletta snapshoten används som tyst baslinje. Inga historiska larm skapas av baslinjen eller denna första jämförelse.
- Ingen ofullständig körning har använts.
- Resultatet ändrar inte originalsnapshots eller deras artifacts.
- GitHub Actions-artifacts har 30 dagars retention och är inte permanent historik eller backup.
- Rätt till permanent historisk lagring, bearbetning, kommersiell användning, kundvisning och vidare distribution är fortsatt separat och inte godkänd genom denna tekniska kontroll.

## Reproducerbarhet

Hämta båda artifacts från respektive Actions-körning, packa upp dem så att varje snapshotkatalog innehåller `manifest.json` och `raw/`, och kör:

```bash
python scripts/viltdata_kill_statistics_diff.py \
  <path-to-20261118T204420Z> \
  <path-to-20261118T220720Z> \
  --output <separate-output-directory>
```

Skriptet avvisar ofullständiga manifest, ofullständig art-/scope-täckning och snapshots med olika observationsnycklar. Resultatet skrivs separat som `summary.json` och `changes.json`.

## Nästa steg

1. Behåll de två original-artifactsen oförändrade tills de löper ut; de är fortfarande kortlivade granskningsunderlag.
2. Fortsätt med nästa manuella kompletta snapshot när det är lämpligt och jämför endast efter fullständighets-, integritets- och täckningskontroll.
3. Invänta skriftligt besked om rättigheter för exakt statistikprodukt innan permanent arkivering eller kundexponering.
