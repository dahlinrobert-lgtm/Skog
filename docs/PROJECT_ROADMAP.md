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
