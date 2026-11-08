# Gräsmyr-monitorering – verifierad uppdatering 2026-11-08

## Sammanfattning

Gräsmyr-monitoreringens workflow rapporterades som **completed successfully** i körning **#422** den 8 november 2026. Efter körningen uppdaterades monitoreringens datafiler i committen [Update Gräsmyr monitoring snapshot](https://github.com/dahlinrobert-lgtm/Skog/commit/829b2368f11a4d533fbe1b34f56541b1d2d95568).

Den här anteckningen dokumenterar vad som kan utläsas ur den sparade snapshot-uppdateringen. Körningsstatusen #422 bygger på den rapporterade GitHub-statusen; committen och dataändringarna har kontrollerats separat.

## Datakontroller

| Kontroll | Resultat |
|---|---:|
| Planerade avverkningsnotiser – historiska snapshots lästa | 281 |
| Oläsbara planerade snapshots | 0 |
| Historiska snapshots jämförda i notishistoriken | 281 |
| Registrerade notisärenden i historiken | 433 |
| Snapshots av utförda avverkningar | 278 |
| Jämförbara par av snapshots för utförda avverkningar | 267 |

Jämfört med föregående publicerade analys ökade antalet lästa planerade snapshots från 279 till 281. För utförda avverkningar ökade antalet snapshots från 276 till 278 och antalet jämförbara par från 265 till 267.

## Tidsstämplar och arkiv

- Planerade avverkningar senast kontrollerade: **2026-11-08 14:45:49 UTC**.
- Utförda avverkningar senast kontrollerade: **2026-11-08 14:46:08 UTC**.
- Ny planerad snapshot: `data/snapshots/20261108T144549Z.json`.
- Nytt komprimerat arkiv för utförda avverkningar: `data/snapshots/completed_20261108T144608Z.geojson.gz`.
- Analysrapporten `data/change_analysis.json` och notishistoriken uppdaterades också.

## Tolkning och begränsningar

- En lyckad körning och nya snapshots visar att datainsamlingen och historikuppdateringen har fortlöpt. Det är inte i sig bevis för att en viss planerad avverkning har genomförts.
- Antalet 433 avser ärenden i den härledda notishistoriken, inte 433 nya eller aktiva avverkningsanmälningar.
- Antalet jämförbara snapshot-par är ett mått på historiskt jämförelseunderlag, inte antalet avverkningshändelser.
- Matchningar mellan planerade och utförda polygoner är fortsatt diagnostiska indikationer. Överlappning eller tidsmässig närhet ska inte ensamt tolkas som bekräftelse på att ett specifikt ärende har verkställts.
- Fortsatt uppföljning behövs för att se hur jämförelserna utvecklas mellan efterföljande körningar.

## Rekommenderad fortsatt kontroll

1. Säkerställ att kommande körningar fortsätter att spara nya planerade snapshots och arkiv för utförda avverkningar.
2. Följ förändringar i notisernas status och geometri över tid, särskilt när objekt försvinner ur en sökning.
3. Fortsätt jämföra planerade och utförda polygoner med geometriunion/deduplicering så att överlappande utförda polygoner inte dubbelräknas.
4. Dra inga slutsatser om enskilda avverkningar utan ytterligare stöd från källmetadata eller oberoende verifiering.

## Referenser

- [Gräsmyr monitoring – GitHub Actions](https://github.com/dahlinrobert-lgtm/Skog/actions/workflows/monitor.yml)
- [Snapshot-uppdatering 2026-11-08](https://github.com/dahlinrobert-lgtm/Skog/commit/829b2368f11a4d533fbe1b34f56541b1d2d95568)
