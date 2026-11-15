# NVR – offentlig information och källhänvisning

**Dokumenterad:** 2026-11-15  
**Underlag:** mejlsvar från Polismyndigheten, återgivet av projektägaren 2026-11-15. Originalmeddelandets fullständiga header, avsändaradress och datum har inte verifierats i denna dokumentationsändring.

## Polisens besked (ordagrant utdrag från projektägaren)

> Bara för att dubbelkolla CSV-uttaget omfattar samtliga tillgängliga djurposter från 2015 och framåt, och  
> Ja, Detta är allt vi har.
>
> att det går bra att hämta och arkivera dessa återkommande för egen geografisk analys och statistik, men med tydlig källa dvs: Nationella viltolycksrådet.
>
> Ja, detta är offentlig information. Ange källan så är allt lugnt.

## Projektets tolkning

Beskedet stödjer återkommande hämtning, arkivering av CSV-uttaget och egen geografisk analys/statistik. Källhänvisningen ska anges som **Nationella viltolycksrådet (NVR)**. Polisen bekräftar också att CSV-uttaget omfattar samtliga djurposter som myndigheten har tillgång till från 2015 och framåt.

Beskedet ska inte övertolkas som ett uttryckligt godkännande av vidare distribution av rådata eller försäljning av en fristående rådatatjänst. Det är inte heller ett undantag från separat kontroll av personuppgifter, sekretess, fältsemantik, koordinatkvalitet eller datakompletthet.

## Implementeringskrav

1. Bevara originalexporter och snapshots oförändrade med hämtningstid, körnings-ID, status, täckning och kontrollsumma.
2. Ofullständiga exporter får aldrig ge falska borttagningar. Importen 2026-11-09 hade status `partial`.
3. Håll DjurID och OlycksID åtskilda och var tydlig med om en post avser ett djur eller en olycka.
4. Visa synligt: **Källa: Nationella viltolycksrådet (NVR)**.
5. Innan GitHub Pages visar händelserna ska en kontrollerad, skrivskyddad publiceringsendpoint etableras. Publicera inte det privata OneDrive-arkivet eller autentiseringsuppgifter direkt.
6. Håll NVR:s individuella händelser åtskilda från Trafikverkets aggregerade olycksfrekvenser per vägsegment.

## Kvarstående verifiering

- Hämta originalmejlets fullständiga header om det behövs för framtida granskning.
- Verifiera vilka NVR-fält som innehåller koordinater och datum samt koordinaternas lämplighet för kartvisning.
- Kontrollera att varje publicerad export är komplett enligt manifest innan den görs tillgänglig.
