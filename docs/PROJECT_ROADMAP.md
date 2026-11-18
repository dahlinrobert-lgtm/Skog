# Skog/Skogskoll – föreslagen roadmap

**Baslinje:** 2026-11-18  
**Roadmapen är ett planeringsförslag.** Tidsperioder fastställs först när beroenden och kapacitet har kontrollerats.

## Fas 0 – Projektledarens grund (påbörjad)

- [x] Fastställ omfattning: hela Skog/Skogskoll.
- [x] Fastställ mandat: föreslå och planera; användaren godkänner åtgärder.
- [x] Skapa projektledarregler och första status/backlogg/roadmap.
- [x] Bygg första read-only GitHub-inventering (PR under granskning; CI/livekörning återstår).
- [ ] Lägg till LLM-baserad analys och rapportutkast efter separat modell-/kostnadsbeslut.
- [ ] Lägg till tester för statusklassning och skydd mot falska slutsatser.

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
