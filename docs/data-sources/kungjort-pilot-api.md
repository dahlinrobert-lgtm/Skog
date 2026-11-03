# Kungjort pilot API – första verifiering

Detta manuella GitHub Actions-flöde verifierar pilotnyckeln och läser API:ets täckningsöversikt samt en sida från dokumentlistan. Det hämtar inte fulltext, originalfiler eller hela dokumentbeståndet och skriver inget till databasen.

## GitHub Secret

Obligatoriskt:
- `KUNGJORT_API_KEY`: API-nyckeln från kundportalen.

`KUNGJORT_API_ID` ingår inte i den publicerade OpenAPI-specifikationens autentisering. API:et dokumenterar Bearer-autentisering med nyckeln, så ID:t används inte i denna första probe.

## Körning

1. Öppna Actions → Probe Kungjort pilot API.
2. Välj Run workflow.
3. Öppna artefakten `kungjort-api-probe`.

Rapporten visar:
- vilka kommuner som faktiskt finns i pilotens täckningsdata,
- antal dokument per kommun, organ, dokumenttyp och år,
- rapporterade fel och datumintervall,
- om dokumentlistan och ändringscursor går att läsa,
- ett begränsat urval dokumentmetadata för att verifiera formatet.

Täckningen är enligt API:et observerat bestånd, inte en garanti för fullständighet. Ingen API-nyckel, inget lösenord och ingen fulltext skrivs ut i loggen eller artefakten.

## Nästa steg

Efter verifierad åtkomst bygger vi den återupptagningsbara historiska exporten och därefter daglig ändringssynkronisering. Den första exporten ska spara `changes_cursor` från första sidan och spela upp ändringar efter exporten är klar.
