# Skog/Skogskoll – projektbeslut

Detta register innehåller uttryckliga projektledningsbeslut. Tekniska beslut och källspecifika beslut ligger kvar i sina auktoritativa dokument och länkas här vid behov.

| Datum | Beslut | Konsekvens |
|---|---|---|
| 2026-11-18 | AI-projektledaren omfattar hela Skog/Skogskoll, inklusive data, GIS, infrastruktur, rättigheter, kundprodukt och kommersialisering. | Backlogg och roadmap får inte begränsas till kodutveckling. |
| 2026-11-18 | Agentens mandat är att föreslå och planera; användaren godkänner åtgärder. | Ingen automatisk merge, produktionsändring, datainsamling, rättighetsändring eller extern kommunikation. |
| 2026-11-18 | GitHub `main` och aktuell evidens är auktoritativa. | Äldre chattanteckningar och lokala kopior är inte statusbevis. |
| 2026-11-18 | Projektledarens första implementation ska vara read-only och byggas stegvis. | AI-automatisering får inte få skrivmandat till produktionsresurser. |
| 2026-11-18 | Ingen källstatus eller uppgiftsstatus får höjas enbart på grund av teknisk åtkomst, lyckad enstaka körning eller merge. | Kräver verifierad evidens och acceptanskriterier. |

| 2026-11-18 | Agent v1 ska börja med read-only GitHub-inventering och manuell workflow; ingen schedule eller språkmodell/API aktiveras i första steget. | Begränsar behörighet och kostnad tills rapportkvalitet och modellval har beslutats. |

## Beslut som väntar på användaren

Inga ytterligare produktions- eller arkitekturbeslut tas i denna baslinje. Förslag till framtida automatisering, modell/API-val, kostnadsram och körfrekvens ska presenteras separat innan implementation.


| 2026-11-19 | AI-projektledare v2b: användaren valde separat skyddad Git-historikbranch och indefinite retention (bevara tills vidare utan automatisk gallring). Beslutet gäller målbild; persistens är spärrad tills syntetiska tester, branchskydd, separata skrivbehörigheter, checksumma/readback/restore är verifierade och användaren godkänt aktivering separat. | [v2b-beslutsunderlag](PROJECT_MANAGER_AGENT_V2B_STORAGE_DECISION.md) |
