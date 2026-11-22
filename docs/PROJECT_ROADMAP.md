# Skog/Skogskoll – föreslagen roadmap

**Baslinje:** 2026-11-18  
**Roadmapen är ett planeringsförslag.** Tidsperioder fastställs först när beroenden och kapacitet har kontrollerats.

## Fas 0 – Projektledarens grund (påbörjad)

- [x] Fastställ omfattning: hela Skog/Skogskoll.
- [x] Fastställ mandat: föreslå och planera; användaren godkänner åtgärder.
- [x] Skapa projektledarregler och första status/backlogg/roadmap.
- [x] Bygg första read-only GitHub-inventering (PR #432 mergad; Actions #44413951767 verifierad med test- och inventory-jobb success samt artifact).
- [ ] Lägg till LLM-baserad analys och rapportutkast efter separat modell-/kostnadsbeslut.
- [x] Genomför v2a pagination och täckningsmetadata; PR #436 mergad, CI och manuell liveinventering verifierade 2026-11-19. Se [v2-planen](PROJECT_MANAGER_AGENT_V2.md).\n- [ ] Besluta separat om append-only-baslinjelagring innan historisk jämförelse implementeras.

## Fas 1 – Stabil dataplattform

- Slutför verifiering av avverkningsanmälningar och samråd.
- Felsök SIS metadata/rasterflöde och etablera jämförbara snapshots.
- Följ NVR:s 30-dagars test och dokumentera fullständighet.
- Slutför Rovbase kvalitetsgranskning och rättighetsbedömning.
- Kontrollera Viltdata rättigheter före arkivering av riktiga snapshots.
- Verifiera backup/restore och historik där produktionsflöden kräver det.

## Fas 2 – Rättigheter och produktionsförutsättningar

- Hämta och granska Lantmäteriets faktiska beslut/villkor.
- Bedöm exakt produkt/lager för kommersiell användning, historisk lagring, bearbetning, kundvisning och distribution.
- Håll källstatus och rättighetsstatus evidensbaserade.
- Upprätta separata godkännandepunkter per datakälla.

## Fas 3 – Gemensam historisk dataplattform

- Standardisera käll-/dataset-ID, manifest och snapshots.
- Verifiera beständig databas, transaktionella commits, scan sessions och PostGIS.
- Säkerställ återställningstester, observability och felhantering.
- Bevara original och gör alla ofullständiga körningar fail-closed.

## Fas 4 – Skogskoll kundprodukt

- Produktionssätt autentisering, RLS och PostGIS.
- Implementera säker serverbaserad ingestion.
- Implementera fastighetssökning först efter rättighetsbesked.
- Bygg matchning, historik och tydlig proveniens.
- Aktivera e-post/push först efter verifierad baslinje och uttryckligt användarval.

## Fas 5 – Utökning och kommersialisering

- Prioritera nya datakällor efter kundnytta, kvalitet, kostnad och rättigheter.
- Bygg abonnemangs-/behörighetsmodell och support-/driftprocess.
- Mät kvalitet, täckning, aktualitet och användarnytta.
- Undvik att sälja rådata där rättigheterna endast medger analys eller intern användning.

## Planeringsprincip

Projektledaren ska föreslå en realistisk veckoplan med högst 3–5 aktiva huvuduppgifter. Blockerade uppgifter ska inte presenteras som om de vore genomförbara. Om en ny blockerare uppstår ska ordningsföljden revideras och beslut som krävs från användaren lyftas separat.


- [x] Besluta v2b-lagring: separat skyddad Git-branch och indefinite retention (2026-11-19).
- [x] Dokumentera teknisk design och testmatris för v2b (PR under arbete).
- [ ] Implementera ren Python-modul och syntetiska tester för manifest, SHA-256, append-only, idempotens, coverage-gate och restore. Ingen GitHub-skrivning eller workflow i detta steg.
- [x] Genomför read-only API-granskning: inga repository rulesets returnerades; klassiskt main-skydd kunde inte läsas (403); historikbranch finns inte. Se `PROJECT_MANAGER_AGENT_V2B_SECURITY_AUDIT.md`.
- [x] Verifiera `main`-skydd via GitHub Rulesets API: `Protect main` aktivt, target default branch, tom bypass-lista, PR krävs, deletion och force-push blockeras (2026-11-19).
- [ ] Utforma och verifiera separat ruleset för historikbranchen; skrividentitetens scope och skydd mot force-push/radering måste vara tydliga.
- [ ] Utred om branchskydd och tokenmodell kan garantera att separat persistence-jobb inte kan skriva till `main`; annars ompröva Git-lagringsalternativet.
- [ ] Genomför syntetisk livepilot först efter verifiering och separat uttryckligt godkännande.
- [ ] v2c historisk jämförelse först efter minst två verifierade kompletta arkivkörningar.


- [x] Ta fram design för separat GitHub App-identitet med minsta permissions och hotmodell (dokumentations-PR under granskning).
- [ ] Besluta om repository-scoped Contents write med verifierat main-ruleset är tillräckligt; annars välj separat repo/lagring med snävare scope.
- [ ] Syntetisk implementation och negativa tester utan GitHub-skrivning.
- [ ] Först efter separat godkännande: skapa App/secret, historikbranch och ruleset samt verifiera negativa GitHub-operationer.

- [x] Syntetiskt lokalt Git-append-test mergat via PR #445 och CI verifierad (project-manager tests success; Snapshot storage full unittest success).
- [ ] Utforma och verifiera historikbranchens ruleset och negativa operationer; skilj lokal Git-simulering från faktisk GitHub-säkerhetsverifiering.
- [ ] Fortsätt hålla GitHub App, secret, contents: write och persistensworkflow avstängda tills verifiering och separat godkännande.

- [x] Verifiera att `Protect main` är enda ruleset i Skog (read-only listning 2026-11-20); inget ruleset för `project-manager-history` finns.
- [ ] Förbered separat ruleset för exakt `project-manager-history` enligt testmatrisen; administrativ konfiguration och negativtest återstår.
- [ ] Verifiera att dedikerad identitet kan append:a syntetisk körning men nekas direktuppdatering av main, force push och branch deletion.
- [ ] Om repository-scoped Contents-write inte ger tillräcklig isolering, välj separat repo/lagring innan App eller secret skapas.

- [x] Avväg Git-historikbranch i Skog mot separat privat repo; välj separat privat repo `skogskoll-project-manager-history` för sekretess och credential-isolering.
- [ ] Skapa privat historikrepo efter separat uttryckligt godkännande.
- [ ] Sätt ruleset, App-identitet och syntetiska negativa tester i det separata repot; ingen persistens före verifiering och separat godkännande.


## AI-projektledare v2b – privat historikrepo (uppdaterat 2026-11-20)

- [x] Besluta separat privat Git-repository i stället för historikbranch i publika Skog (PR #458).
- [x] Skapa `skogskoll-project-manager-history` som privat repo; verifiera visibility och default branch.
- [x] Lägga till README, historikformat och säkerhets-/driftdokumentation.
- [ ] Konfigurera och verifiera aktivt ruleset på `main`: blockera deletion och non-fast-forward/force push; ingen bypass för framtida App-identitet.
- [ ] Genomföra extern backup och återställningstest.
- [ ] Köra syntetiska positiva och negativa GitHub-tester utan produktionsdata.
- [ ] Först efter separat godkännande: skapa skrividentitet/secret och separat persistensflöde.
- [ ] Först efter ytterligare uttryckligt godkännande och samtliga säkerhetsgrindar: aktivera historikpersistens.

Verifierad status 2026-11-20: repository rulesets API returnerar `[]`. Klassisk branch protection för `main` kunde inte läsas av integrationen (403), därför är effektivt branchskydd ännu inte verifierat. Ingen App, secret, skrivbehörighet, workflow eller produktionshistorik finns.


### Uppdatering 2026-11-20 – ruleset för privat historikrepo

- [x] Skapa och aktivera `Protect history main` (ID 27761134).
- [x] Verifiera via GitHub Rulesets API: target exakt `refs/heads/main`; deletion och non_fast_forward blockerade; bypass-lista tom; `current_user_can_bypass: never`.
- [ ] Extern backup med manifest/checksummor.
- [ ] Restore-test till ny tom katalog och verifiera samtliga SHA-256.
- [ ] Syntetiska positiva/negativa tester av append-only-logiken och Git-skyddet.
- [ ] Separat godkännande innan App, credentials, writer workflow eller persistens skapas.

Konfigurationen är verifierad; faktisk negativ push-/delete-testning är ännu inte utförd. Ingen produktionshistorik är skriven.


# Samordnad målroadmap – från dataplattform till kundprodukt (2026-11-22)

## Slutmål

Skogskoll ska vara en driftsäker och kommersiellt hållbar bevakningstjänst för privata skogsägare. Kunden ska kunna registrera en fastighet eller ett eget bevakningsområde, få relevanta och kvalitetssäkrade skogshändelser matchade mot området, se när förändringen upptäcktes och vilken källa den bygger på samt välja e-post/pushaviseringar.

Skog fortsätter vara den bredare dataplattformen. Alla källor i Skog behöver inte ingå i Skogskolls första produktversion.

## Leveranssteg och grindar

### M1 – Tillförlitlig kärnbevakning
- Nationell insamling är övergripande mål för varje relevant datakälla och separat produkt/lager, där källans täckning, teknik och rättigheter medger det. Gräsmyr är pilot, inte slutlig geografisk omfattning.
- Nationell täckning ska bevisas med dokumenterat scope, fullständighetskontroller, stabila ID:n, manifest och återkommande jämförbara observationer. En nationell karta eller lyckad regional pilot räcker inte.
- Fullständig, paginerad och auditerbar insamling av planerade avverkningsanmälningar.
- Separat fullständighetskontroll för Samråds punkt-, linje- och polygonlager.
- Bevara utförda avverkningar och unionera geometrier före arealberäkning.
- Minst två kompletta och jämförbara observationer innan frånvaro eller nyhet tolkas som förändring.
- Gräsmyr-piloten ska verifieras operativt innan geografisk uppskalning.

**Godkänd när:** schemalagda körningar lyckas, manifest/täckning kan granskas, historik bevaras och ofullständiga körningar inte kan skapa falska borttagningar.

### M2 – Gemensam historik- och dataplattform
- Gemensamma käll-ID:n, snapshot-envelope, manifest, körnings-ID och kontrollsummor.
- Idempotent och transaktionell ingestion med scan sessions och checkpoints.
- Append-only observationshistorik, proveniens, felhantering och restore-test.
- Standardiserade statusar för åtkomst, fullständighet, historik, rättigheter och kundvisning.

**Godkänd när:** minst ett prioriterat produktflöde kan återställas och reproduceras från bevarat original/snapshot med verifierade checksummor.

### M3 – Skogskoll runtime
- Separat testmiljö med liveverifierad Postgres/Supabase och PostGIS.
- Autentisering och RLS testas positivt och negativt.
- Säker serverbaserad ingestion med hemligheter endast på serversidan.
- Matchning mellan bevakningsområden och observationer via PostGIS.
- Fastighetsidentifiering/-sökning först när Lantmäteriets exakta villkor är klarlagda.

**Godkänd när:** en testanvändare kan skapa och läsa endast sina egna bevakningar och se korrekta matchningar från en verifierad datakälla.

### M4 – Kundupplevelse och avisering
- Kundens karta, händelselista och spårbara historik.
- Tydlig skillnad mellan verifierad händelse, planeringsunderlag och risk-/indikatorlager.
- Aviseringspreferenser, opt-in, deduplicering och transactional outbox.
- Tyst första baslinje; inga historiska poster ska generera larm.

**Godkänd när:** end-to-end-test visar att en verkligt ny, verifierad och relevant händelse kan visas och aviseras en gång till rätt användare – och att partial/duplicat/baslinje inte ger larm.

### M5 – Kommersiell drift
- Källspecifika beslut om lagring, bearbetning, kommersiell användning, kundvisning och vidare distribution.
- Abonnemang/behörighetsmodell, support, incidenthantering, backup och återställning.
- Mätning av täckning, aktualitet, precision, falska positiva och användarnytta.
- Gradvis geografisk uppskalning efter verifierad pilot.

**Godkänd när:** produktens kundflöde, rättigheter, säkerhet, drift och support är granskade och dokumenterade.

## Aktiv arbetsprioritering

Högst fyra huvudspår ska vara aktiva samtidigt:
1. Kärnbevakning och schemalagd drift.
2. Gemensam snapshot-/historikplattform.
3. Liveverifiering av Skogskoll runtime i separat testmiljö.
4. Rättighetsbesked för de källor som behövs i första kundflödet.

Nya datakällor och sidoprojekt prioriteras efter direkt kundnytta, blockerande effekt, evidens, kostnad och rättigheter. En tekniskt lyckad insamling är inte i sig ett kundklart resultat.

## Övergripande stoppregler

- Ingen frånvaroklassning från ofullständig eller ojämförbar körning.
- Ingen historisk baslinjeavisering.
- Ingen kundvisning eller kommersiell användning utan källspecifikt stöd.
- Ingen produktionsaktivering innan auth/RLS, ingestion, historik, backup och återställning är verifierade.
- Geografisk uppskalning först efter stabil och reproducerbar pilot.

## Övergripande mål för nationell insamling per datakälla (fastställt 2026-11-22)

Skog ska utvecklas till en dataplattform med verifierad nationell insamling för varje relevant datakälla, separat per produkt/lager. Målet gäller i den omfattning källan faktiskt tillhandahåller och tillåter. Det innebär inte att alla källor måste ingå i Skogskolls första kundprodukt.

### Gemensam nationell acceptansgrind
- Avgränsa och dokumentera källans nationella geografi, objektmängd, tidsomfång, filter och kända begränsningar.
- Verifiera komplett uttagsmetod/paginering, stabila ID:n, unika objekt och avstämning mot källans inventering eller annan oberoende kontroll.
- Bevara rådata/snapshots och manifest med körnings-ID, tidpunkt, scope, status, antal och checksummor.
- Fail closed: partial/failed får aldrig ersätta senaste kompletta observation eller skapa falska borttagningar.
- Kräva minst två kompletta och jämförbara observationer före förändringsklassning.
- Verifiera schemalagd drift, felhantering, återhämtning och återställning.
- Bedöma teknisk åtkomst, lagring, bearbetning, kommersiell användning, kundvisning och distribution separat.

### Genomförandeordning
1. Skogsstyrelsens planerade avverkningsanmälningar: slutför två kompletta jämförbara Gräsmyr-observationer och bygg därefter nationell uttagsdesign.
2. Skogsstyrelsens Samråd: verifiera nationell täckning och fullständighet separat för punkt-, linje- och polygonlager.
3. Övriga prioriterade källor: nationell täckningsinventering och stegvis insamling enligt kundnytta, datakvalitet, teknisk möjlighet, kostnad och rättighetsläge.
4. Källor med regional täckning, oklar omfattning eller begränsade villkor ska redovisas med faktisk täckning och blockerare – inte som nationella.

### Första konkreta bevispunkt
Den kompletta Gräsmyr 10 km-snapshoten för planerade avverkningsanmälningar från 2026-11-22 är arkiverad genom PR #524. Manifestet visar 165/165 ID:n/geometrier, stabil ID-inventering och complete_scan=true. Detta är en komplett pilotobservation, inte nationell täckning eller en jämförbar tidsserie. Nästa steg är observation nummer två.