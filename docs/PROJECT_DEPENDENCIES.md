# Skog/Skogskoll – beroenden och blockerare

**Baslinje:** 2026-11-18. Uppdateras när evidens eller beroenden ändras.

| Beroende | Berör | Status | Vad krävs | Konsekvens om olöst |
|---|---|---|---|---|
| Lantmäteriets beslut och exakta produktvillkor | Fastighetssökning, geometri, kommersiell produkt | Blockerande | Hämta/granska besluten för LM2026/171963 och LM2026/171968. | Fastighetsfunktion och kundvisning kan inte godkännas. |
| Skogsstyrelsens fullständiga och jämförbara avverkningsanmälningar | Historik och nya händelser | Ej verifierat | Full paginering, checkpoint/retry, två kompletta jämförbara körningar. | Frånvaro/nyhet kan inte användas säkert som larm. |
| Samrådslagrens separata fullständighet | Historik och matchning | Ej verifierat | Kontrollera punkt, linje och polygon separat. | Täckningsluckor kan misstolkas. |
| SIS metadata-/rasterflöde | Skoglig analys | Fel behöver felsökas | Kontrollera misslyckade körningar 13–14 november och rastervillkor. | Ingen tillförlitlig uppdaterad SIS-serie. |
| NVR 30-dagars observationsperiod | Viltolyckor/historik | Pågående | Kontrollera kompletta dagskörningar, manifest och jämförbarhet. | Historisk frånvaro får inte tolkas som borttagning. |
| Rovbase koordinatsystem och kvalitetsavvikelser | Rovbase geografisk analys | Öppet | Bekräfta RT90-variant med källägaren; kör korrigerad full kontroll och granska avvikelser. | Ingen säker normalisering/produktionsimport. |
| Viltdata historisk lagring och användningsvillkor | Azure-arkiv och statistikprodukt | Blockerad | Skriftligt besked för exakt statistikprodukt och användning. | Inga riktiga snapshots till Azure eller kundvisning. |
| Oberoende facit och nationell täckning för NVDB-matchning | Vägmatchning av viltolyckor | Ej verifierat | Manuellt bedömda positiva, negativa och tvetydiga fall; benchmark och täckningskontroll. | Resultat förblir review-only. |
| Produktionsprojekt för Supabase/PostGIS och liveverifiering | Kundprodukt | Ej verifierat | Separat testprojekt, auth/RLS, transaktioner, backup/restore och ingestion. | Ingen kunddrift eller avisering. |
| GitHub read-only inventeringsagent | AI-projektledare | v1 och v2a mergade/CI- och liveverifierade; v2b-beslutsunderlag framtaget | Välj lagringsmodell, retention och separat skrivgräns enligt `PROJECT_MANAGER_AGENT_V2B_STORAGE_DECISION.md`. | Ingen beständig baslinje eller jämförelse införs innan användarens beslut och verifierad persistens. |
| LLM/API och eventuell schedule | AI-syntes och återkommande rapport | Väntar på beslut | Välj modell, API-secret, datahantering, kostnadstak och frekvens; håll skrivmandat avstängt. | Agenten förblir deterministisk och manuell tills godkännande. |

## Hanteringsregler

- En blockerare måste ha ägare, evidens, nästa kontroll och konsekvens.
- Externa svar eller beslut ska länkas och registreras; projektledaren får inte dra juridiska slutsatser utifrån tystnad.
- Blockerade uppgifter ska inte ingå i veckans genomförandeplan som om de vore fria att starta.
- Om en blockerare försvinner ska berörda uppgifter återbedömas, inte automatiskt startas.
