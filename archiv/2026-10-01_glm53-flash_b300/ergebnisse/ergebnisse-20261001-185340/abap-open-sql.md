# ABAP: open-sql

## Aufgabe

Formuliere ein modernes ABAP-SQL-Statement (7.50+), das je Kunde (KNA1) die Anzahl der Aufträge und den Gesamtnettowert aus VBAK für das laufende Jahr ermittelt, nur Kunden mit mehr als 5 Aufträgen, sortiert nach Wert absteigend. Nutze Host-Variablen mit @, INTO TABLE @DATA(...) und erkläre jede Klausel kurz.

## Antwort



---

<details><summary>Denkprozess (28478 Zeichen)</summary>

The user is asking in German for a modern ABAP SQL statement (7.50+) that:
- Per customer (KNA1) counts orders and sums net value from VBAK
- For the current year
- Only customers with more than 5 orders
- Sorted by value descending
- Using host variables with @, INTO TABLE @DATA(...)
- Explain each clause briefly

This is a technical ABAP question. I should respond in German since the question is in German. Let me write the modern Open SQL / ABAP SQL statement.

Key elements for ABAP 7.50+:
- `SELECT ... FROM vbak` with @ escaping for host variables
- `INTO TABLE @DATA(lt_result)`
- Aggregate functions: COUNT( * ) or COUNT( DISTINCT ... ), SUM( netwr )
- GROUP BY
- HAVING with aggregate condition
- ORDER BY with aggregate alias
- JOIN to KNA1 (the requirement says "je Kunde (KNA1)" - per customer from KNA1). Actually the orders are in VBAK (sales document header). KNA1 is customer master. The requirement: "je Kunde (KNA1) die Anzahl der Aufträge und den Gesamtnettowert aus VBAK" - so we need to join KNA1 with VBAK on KUNNR, group by customer, count orders, sum NETWR.

Note: VBAK has fields: VBELN (order number), ERDAT (creation date), NETWR (net value), WAERK (currency), KUNNR (sold-to party, actually KUNNR in VBAK is the sold-to customer... in VBAK the field is KUNNR - Sold-to party). Yes, VBAK-KUNNR exists.

For "laufendes Jahr" - current year: we can use ERDAT in VBAK. ERDAT is CHAR8 (YYYYMMDD). We could compare ERDAT >= concat of year... In ABAP SQL 7.50, we can use string functions like CONCAT, or better: use `WHERE erdat BETWEEN @lv_start AND @lv_end` with host variables computed before. Or use the built-in function to extract year: In 7.50, there's no YEAR() function until... Actually ABAP SQL has date functions from 7.40 SP08+: e.g., `LEFT( erdat, 4 )`? String functions in ABAP SQL: LOWER, UPPER, LENGTH, LPAD, RPAD, LTRIM, RTRIM, REPLACE, SUBSTRING, CONCAT... SUBSTRING is available. So `SUBSTRING( erdat, 1, 4 ) = @lv_year` could work but ERDAT is CHAR8 so substring works.

Better approach: compute host variables in ABAP:
```abap
DATA(lv_year) = |{ sy-datum(4) }| .
DATA(lv_date_from) = |{ lv_year }0101|.
DATA(lv_date_to) = |{ lv_year }1231|.
```
Then use `WHERE vbak~erdat BETWEEN @lv_date_from AND @lv_date_to`.

Alternatively use `WHERE YEAR( erdat ) = ...` — the YEAR function doesn't exist in ABAP SQL; there's no YEAR function. There are date functions in 7.51+? Actually ABAP SQL date functions: DATS_IS_VALID, DATS_DAYS_BETWEEN, DATS_ADD_DAYS, DATS_ADD_MONTHS (7.40 SP08+). No YEAR extraction. So SUBSTRING or host variables.

Cleanest: host variables for date range.

Also currency: NETWR is CURR field; summing is fine. Might mention WAERK grouping if multiple currencies — but keep it simple, maybe mention as a note.

HAVING COUNT( * ) > 5 — note: in ABAP SQL, HAVING with aggregate: `HAVING COUNT( * ) > 5`. Host variable not needed for literal. Actually you can write `> @lv_min` too. Use literal 5 or host variable. The user asked "mehr als 5 Aufträgen" — so `> 5`.

ORDER BY: In ABAP SQL, ORDER BY can reference aliases of aggregates: `ORDER BY sum_netwr DESCENDING`. Since 7.50, ORDER BY with aggregate expressions is allowed? In 7.40 SP08+, ORDER BY can only use columns of the result set — aliases allowed. Yes, ORDER BY sum_netwr DESCENDING works because it's in the SELECT list.

Also GROUP BY: `GROUP BY vbak~kunnr, kna1~name1` — in 7.50, when using comma-separated column list after SELECT, GROUP BY must also use comma-separated list. If we select kna1~name1, we must group by it too.

Let me draft:

```abap
" Host-Variablen für das laufende Jahr
DATA(lv_year)  = |{ sy-datum(4) }|.
DATA(lv_first) = |{ lv_year }0101|.
DATA(lv_last)  = |{ lv_year }1231|.

SELECT k~kunnr,
       k~name1,
       COUNT( * )            AS anzahl_auftraege,
       SUM( v~netwr )        AS gesamt_netwr,
       v~waerk               AS waehrung   " optional
  FROM kna1 AS k
  INNER JOIN vbak AS v
          ON v~kunnr = k~kunnr
  WHERE v~erdat BETWEEN @lv_first AND @lv_last
    AND v~auart ... (optional: nur Aufträge, z.B. TA)
  GROUP BY k~kunnr, k~name1, v~waerk
  HAVING COUNT( * ) > 5
  ORDER BY gesamt_netwr DESCENDING
  INTO TABLE @DATA(lt_kunden_umsatz).
```

Wait — ORDER BY with alias of aggregate: allowed since 7.40 SP08? The rule: "ORDER BY" can specify columns after INTO? Actually in modern Open SQL, ORDER BY must come before INTO? No — in ABAP SQL the clause order is: SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... INTO/APPENDING ... UP TO n ROWS. Hmm, actually the standard order: SELECT, FROM, FIELDS, WHERE, GROUP BY, HAVING, ORDER BY, then INTO, then UP TO, OFFSET. Wait let me recall.

In modern ABAP SQL (7.50+), the recommended order is:

```
SELECT ... FROM ... FIELDS ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... INTO TABLE @DATA(...) ...
```

Actually the INTO clause can be placed at the end (traditional) or right after SELECT (strict mode recommended). The official syntax diagram: SELECT [DISTINCT] select_list FROM source ... INTO target ... where clauses... Hmm.

The ABAP keyword documentation: The mainquery clauses can be specified in the order: FROM, FIELDS, WHERE, GROUP BY, HAVING, ORDER BY, UP TO, OFFSET — and INTO can be specified either after the select list (i.e., after SELECT ... INTO ... FROM ...) or at the end. Both are allowed. The "strict mode" of the syntax check requires FROM before... Actually strict mode 7.50 requires: SELECT ... FROM ... FIELDS ... etc. with INTO at the end being allowed.

Common modern style:

```abap
SELECT FROM kna1 AS k
       INNER JOIN vbak AS v ON v~kunnr = k~kunnr
       FIELDS k~kunnr,
              k~name1,
              COUNT( * ) AS anzahl,
              SUM( v~netwr ) AS netwr_sum
       WHERE ...
       GROUP BY ...
       HAVING ...
       ORDER BY netwr_sum DESCENDING
       INTO TABLE @DATA(lt_result).
```

That's the fully modern "strict" style with FIELDS. Both styles are valid in 7.50. I'll present the modern one with FROM ... FIELDS ... INTO at the end, since the user asked for "modernes ABAP-SQL-Statement (7.50+)". Or the classic order with INTO at the end is also fine and widely used. I'll use the modern order and mention that INTO can also be at the end.

Hmm, one caveat: ORDER BY with aggregate alias — is that allowed? Yes: "ORDER BY" can use the alias names of the SELECT list. From docs: "The columns of the result set can be specified either by their name ... or alias ... Aggregate expressions can be referenced by their alias names." Actually let me recall precisely: In ORDER BY, you can specify columns of the result set: for aggregate expressions, the alias must be used. Yes, that's correct — ORDER BY col_alias works if the alias is defined in the SELECT list.

Also note: ORDER BY in combination with INTO TABLE is fine.

Another caveat: SUM over CURR field — NETWR is CURR (domain NETWR, CURR 15,2). SUM is allowed for numeric types including CURR/QUAN? In ABAP SQL, SUM works for numeric fields; CURR is treated as DEC. Yes, SUM( netwr ) is fine. The result type: for SUM, the result is the same type as the field (DEC 15,2) — might overflow risk but fine.

Also: grouping by WAERK is advisable because you can't meaningfully sum different currencies. I'll include it and explain, or mention it as a note. Including it makes the statement more correct. But the requirement says "je Kunde" — grouping by currency adds rows per currency. I could include WAERK in GROUP BY and mention why; or omit and note the caveat. I think including it with a comment is better practice, but it changes the grouping. Let me include it and explain briefly — or mention as optional. I'll include it, since summing NETWR across currencies is technically wrong; and note that if only EUR (or one currency) is relevant, one can filter with WHERE v~waerk = 'EUR' instead.

Also "Aufträge" — technically VBAK contains all sales document types (TA = standard order). Could add `v~auart = 'TA'` as optional filter. Mention briefly.

Also KNA1 join: strictly, you don't need KNA1 to aggregate VBAK; but the user explicitly says "je Kunde (KNA1)", so join KNA1 to get the name. Use INNER JOIN (only customers with orders appear). Could mention LEFT OUTER JOIN alternative if all customers should appear (but then HAVING > 5 filters them out anyway, so INNER JOIN is fine).

Host variables: @lv_first, @lv_last. Also could use @sy-datum? You can use @sy-datum? Actually sy-datum can be used as host variable: `WHERE erdat >= @sy-datum`? Hmm, sy fields can be used with @? I believe you can reference sy-datum as a host variable in modern Open SQL: `WHERE erdat = @sy-datum` — yes, sy is a structure and @sy-datum works. But computing year boundaries needs ABAP code anyway.

Alternative: compute first day of year via ABAP:

```abap
DATA(lv_first_day) = CONV d( |{ sy-datum(4) }0101| ).
DATA(lv_last_day)  = CONV d( |{ sy-datum(4) }1231| ).
```

ERDAT is CHAR8, comparing with D type host variable — types must be compatible; char8 vs d — in Open SQL, comparison rules: d and c(8) are comparable? For host variables, the value is converted. Safe approach: make them CHAR8: `DATA(lv_first) = |{ sy-datum(4) }0101|` produces string; better `CONV char8`? Hmm. Let's do:

```abap
DATA lv_jahr TYPE n LENGTH 4.
lv_jahr = sy-datum(4).
DATA(lv_von) = |{ lv_jahr }0101|.
DATA(lv_bis) = |{ lv_jahr }1231|.
```

Or simply:

```abap
DATA(lv_von) = CONV d( sy-datum(4) && '0101' ).
```

String templates: `|{ sy-datum(4) }0101|` — sy-datum(4) substring works on sy-datum since it's c8. Result is string type; passing string host variable comparing to CHAR8 column — Open SQL handles conversion (string to char comparison is fine, loses trailing blanks; '20250101' is 8 chars, fine).

Alternatively, avoid host variables for dates and use SQL: `WHERE v~erdat >= CONCAT...` — no. Or use SUBSTRING: `WHERE SUBSTRING( v~erdat, 1, 4 ) = @lv_year` — but that prevents index usage; range condition is better. I'll use the range with host variables and briefly mention the alternative.

Also could mention: since ERDAT is the creation date of the document — "laufendes Jahr" interpreted as ERDAT year.

Now the explanation of each clause, briefly, in German:

- SELECT list: columns + aggregates with aliases AS.
- FROM with JOIN: KNA1 master data joined to VBAK on KUNNR; aliases k, v.
- WHERE: restrict to current year via host variables @lv_von/@lv_bis (ERDAT = Erstdatum des Belegs).
- GROUP BY: one row per customer (+ currency).
- HAVING: filter on aggregated groups — COUNT(*) > 5. Difference to WHERE: WHERE filters rows before aggregation, HAVING after.
- ORDER BY: sort by alias of the aggregate descending.
- INTO TABLE @DATA(...): inline declaration of internal table; @ marks host variables (mandatory in 7.40 SP08+ / 7.50 for host variables in Open SQL).

Also mention: comma-separated lists require all host variables escaped with @; aggregates COUNT(*), SUM; aliases needed for ORDER BY and for later access.

Let me also double check: In GROUP BY with comma-separated list after SELECT comma list — yes, GROUP BY must use commas too when SELECT list uses commas (strict mode). `GROUP BY k~kunnr, k~name1, v~waerk`.

HAVING COUNT( * ) > 5: In ABAP SQL, HAVING can contain aggregate expressions. Correct syntax: `HAVING COUNT( * ) > 5`. Yes.

ORDER BY: `ORDER BY gesamt_netwr DESCENDING` — alias without @. Correct. Alternatively `ORDER BY SUM( v~netwr ) DESCENDING`? Not allowed I think — ORDER BY cannot contain aggregate expressions directly in older releases; since 7.51? Actually ABAP SQL allows aggregate expressions in ORDER BY? The docs: "ORDER BY ... can be specified as columns of the result set ... An aggregate expression cannot be specified directly" — hmm. In 7.40 SP08+, ORDER BY allows: columns, aliases... I recall that aggregate expressions in ORDER BY are not allowed; you must use the alias. Let me be safe and use the alias. That definitely works.

Also: When using INTO TABLE @DATA(lt_...), the internal table types are derived: kunnr (KUNNR type), name1, anzahl (INT4? COUNT(*) returns INT4... actually COUNT(*) returns type INT4? The result type of COUNT is INT4? Docs: COUNT( * ) result type is INT4? I believe it's INT4 (i). SUM(netwr) returns NETWR's type CURR -> decfloat? No: SUM result type = type of the argument (for CURR, DEC). Fine.)

Also note: NETWR is currency field tied to WAERK; summing per currency is consistent.

Let me also think about whether to use `COUNT( DISTINCT v~vbeln )` — since join is 1:1 per order row, COUNT(*) suffices. Keep COUNT(*).

Potential addition: `UP TO 100 ROWS` — not requested. Skip.

Now write the answer in German, with code block and concise clause-by-clause explanation. Format: A short intro sentence, the ABAP code block (including the two DATA declarations for the date range), then a compact explanation list (bulleted) per clause, plus a couple of notes (currency caveat, auart filter, INNER vs LEFT JOIN, alternative with SUBSTRING or DATS functions). Keep it reasonably concise but complete. Use headers maybe. The user asked "erkläre jede Klausel kurz" — so a list mapping clause → explanation.

Code:

```abap
" Zeitraum: laufendes Jahr
DATA(lv_von) = CONV erdat( |{ sy-datum(4) }0101| ).
DATA(lv_bis) = CONV erdat( |{ sy-datum(4) }1231| ).
```

Hmm, ERDAT is data element CHAR8 (domain CHAR8). CONV char8? Using `CONV d` might be cleaner: d is comparable with c(8)? In Open SQL comparisons, host variable of type d vs column c8 — the comparison rules for host variables: the column type determines; d is converted to c? I think it's safe: d is treated like c(8) in comparisons (n, d, t are character-like). Yes, d is character-like, so comparing c8 column with d host variable works. But to be explicit and safe, use `CONV char8`? char8 is a data element? There's domain CHAR8; type char8 exists? There's built-in type `c LENGTH 8`. Simpler: 

```abap
DATA lv_jahr TYPE c LENGTH 4.
lv_jahr = sy-datum(4).
DATA(lv_von) = |{ lv_jahr }0101|.
DATA(lv_bis) = |{ lv_jahr }1231|.
```

Or one-liners:

```abap
DATA(lv_von) = |{ sy-datum(4) }0101|.  " z.B. '20250101'
DATA(lv_bis) = |{ sy-datum(4) }1231|.
```

String templates produce `string` type — fine as host variables.

Main statement (modern clause order):

```abap
SELECT FROM kna1 AS k
       INNER JOIN vbak AS v
               ON v~kunnr = k~kunnr
       FIELDS k~kunnr,
              k~name1,
              COUNT( * )       AS anzahl_auftraege,
              SUM( v~netwr )   AS gesamt_netwr,
              v~waerk          AS waehrung
       WHERE v~erdat BETWEEN @lv_von AND @lv_bis
         " AND v~auart = 'TA'   " optional: nur Verkaufsbelegart 'Auftrag'
       GROUP BY k~kunnr, k~name1, v~waerk
       HAVING COUNT( * ) > 5
       ORDER BY gesamt_netwr DESCENDING
       INTO TABLE @DATA(lt_kunde_umsatz).
```

Wait: comment placement inside the statement between WHERE and GROUP BY — fine.

Check strict-mode syntax: `SELECT FROM ... FIELDS ...` — FIELDS keyword introduced 7.40 SP08, fine for 7.50. INTO at end allowed. ORDER BY before INTO — yes, correct order: WHERE, GROUP BY, HAVING, ORDER BY, UP TO, INTO? Hmm — actually the order per docs: "SELECT ... FROM ... FIELDS ... WHERE ... GROUP BY ... HAVING ... UNION ... ORDER BY ... UP TO, OFFSET ... INTO/APPENDING". Wait, is INTO after UP TO? The INTO clause can be specified "in front of" or after? Let me recall the ABAP SQL syntax precisely.

ABAP keyword documentation for SELECT, main query: 

```
SELECT [DISTINCT]
  { select_list
  | FROM ... FIELDS select_list }
  ...
  INTO ...
```

The clauses: FROM, WHERE, GROUP BY, HAVING, UNION, ORDER BY, UP TO/OFFSET, INTO/APPENDING. The INTO clause: "INTO clause can be specified either directly after the SELECT clause (old syntax) or at the end of the query (recommended)." Actually the doc says: The INTO clause can be placed anywhere? No — I recall: "The INTO clause must be specified as the last clause of the SELECT statement" in strict modes? Hmm.

Let me think: Traditional syntax: `SELECT ... FROM ... INTO ... WHERE ...` — INTO right after FROM/select list. Modern strict mode (7.40 SP08+): the INTO clause should be at the end: `SELECT FROM ... FIELDS ... WHERE ... GROUP BY ... ORDER BY ... INTO TABLE @DATA(...)`. Yes — in strict mode, INTO must be the last clause (after ORDER BY, and UP TO/OFFSET come after INTO? Actually UP TO n ROWS comes after INTO: `INTO TABLE @DATA(x) UP TO 10 ROWS`? Hmm, no: In modern syntax, UP TO/OFFSET are specified after the INTO clause? Let me recall examples from SAP docs:

```abap
SELECT FROM sflight
       FIELDS carrid, SUM( price ) AS sum_price
       WHERE ...
       GROUP BY carrid
       INTO TABLE @DATA(result)
       UP TO 10 ROWS.
```

Hmm, I've seen `UP TO n ROWS` both before and after INTO. The official syntax: "UP TO, OFFSET — must be specified after the INTO clause"? Actually the ABAP doc: SELECT ... INTO target UP TO n ROWS. In the strict mode from 7.40 SP08, "UP TO n ROWS" can be specified after ORDER BY and before INTO? I believe the canonical modern order is:

SELECT ... FROM ... FIELDS ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... INTO ... UP TO ... OFFSET? 

Hmm, actually I recall: "The addition UP TO n ROWS must be specified after the INTO clause" — no wait. Let me look at a known example from SAP documentation (Open SQL, SELECT, INTO):

```abap
SELECT FROM scarr
       FIELDS carrid, carrname
       WHERE carrid BETWEEN 'AA' AND 'AC'
       ORDER BY carrid
       INTO TABLE @DATA(scarr_tab)
       UP TO 3 ROWS.
```

Hmm, I'm not 100% sure. I think UP TO/OFFSET come after INTO in strict mode. But since we don't need UP TO, it doesn't matter for the answer. ORDER BY before INTO TABLE is definitely correct in the modern style. Good.

Actually, to be safe about ORDER BY position: In strict mode, ORDER BY is before INTO. Yes — e.g., from SAP docs example:

```abap
SELECT FROM spfli
       FIELDS carrid, connid
       WHERE ...
       ORDER BY carrid, connid
       INTO TABLE @DATA(result).
```

Yes, that's the documented modern order. Good.

One more check: aliases in ORDER BY referencing aggregate alias — allowed: "If the alias name of an aggregate expression is specified after ORDER BY..." Actually docs for ORDER BY: "sort_key: ... column of the result set ... The columns can be specified using their names or alias names." And there's a note: aggregate expressions can only be referenced via alias. I'm fairly confident `ORDER BY gesamt_netwr DESCENDING` works in 7.50. Yes.

Also DESCENDING keyword: correct in ABAP SQL (not DESC). Good.

Also: `COUNT( * )` with space inside parentheses — required style in ABAP SQL: `COUNT( * )`. Yes, spaces are mandatory.

SUM( v~netwr ) — column selector with ~ inside aggregate: allowed. Yes.

HAVING COUNT( * ) > 5 — allowed. Yes.

BETWEEN @lv_von AND @lv_bis — host variables with @. Good.

Alternative without host variables: `WHERE SUBSTRING( v~erdat,1,4 ) = @sy-datum(4)`? @sy-datum(4) — substring of host variable in SQL? Not allowed; you'd compute lv_year. Could do `WHERE v~erdat LIKE ...` no. Keep host variable approach; mention alternative: `SUBSTRING( v~erdat, 1, 4 ) = @lv_jahr` (but no index support).

Also, in newer releases (7.55+? or 2022), there's the date function... Actually there IS a way: `WHERE v~erdat BETWEEN @lv_von AND @lv_bis` is the cleanest. Fine.

Also worth noting: KNA1 join is only needed for name1; if only KUNNR needed, skip join. Mention briefly.

Currency note: NETWR is CURR; sum across currencies only meaningful per WAERK — hence GROUP BY waerk; alternatively restrict `WHERE v~waerk = 'EUR'` (then remove waerk from SELECT/GROUP BY). I'll add this as a note.

Also mention: COUNT(*) counts rows of the joined result; since join KNA1–VBAK is n:1 (many VBAK per one KNA1), no duplication — COUNT(*) = number of orders. Good.

Also: result table lt_kunde_umsatz has fields KUNNR, NAME1, ANZAHL_AUFTRAEGE, GESAMT_NETWR, WAEHRUNG. Access e.g. LOOP AT lt_kunde_umsatz INTO DATA(...). Not needed.

Explanations (kurz):

1. **FROM ... INNER JOIN**: KNA1 (Kundenstamm) wird mit VBAK über KUNNR verknüpft; Aliase k und v. INNER JOIN: nur Kunden, die im Jahr Aufträge haben.
2. **FIELDS**: moderne Schreibweise der Auswahlliste; Spalten + Aggregatfunktionen mit Alias-Namen (AS), die später für ORDER BY und Zugriff genutzt werden.
3. **WHERE**: filtert Belege auf Erstdatum (ERDAT) im laufenden Jahr; @ markiert Host-Variablen (Pflicht ab 7.40 SP08). BETWEEN nutzt ggf. Index auf ERDAT.
4. **GROUP BY**: fasst alle Zeilen je Kunde (und Währung) zu einer Ergebniszeile zusammen; alle nicht-aggregierten Spalten der SELECT-Liste müssen hier stehen.
5. **HAVING**: Filter nach der Aggregation – nur Gruppen mit mehr als 5 Aufträgen (COUNT(*) > 5). WHERE würde vor der Aggregation filtern und könnte COUNT nicht prüfen.
6. **ORDER BY ... DESCENDING**: sortiert absteigend nach dem aggregierten Wert; Aggregat-Ausdrücke müssen über ihren Alias referenziert werden.
7. **INTO TABLE @DATA(...)**: deklariert die interne Tabelle inline (typableitung aus der SELECT-Liste); @ kennzeichnet Host-Variablen.

Notes:
- Währung: Summierung über WAERK gruppiert; alternativ WHERE v~waerk = 'EUR' und waerk raus.
- Auart-Filter optional ('TA' = Standardauftrag), da VBAK alle Verkaufsbelegarten enthält.
- LEFT OUTER JOIN statt INNER, falls auch Kunden ohne Aufträge (hier wegen HAVING > 5 irrelevant).
- Alternative Jahresfilter: SUBSTRING( v~erdat, 1, 4 ) = @lv_jahr (aber schlechter für den Index).

Format: German response. Start with the code (with the two DATA lines), then "Erklärung der Klauseln" as a compact list, then short "Hinweise" bullets. Use markdown code block with abap. Keep explanations short as requested. Length: medium — code block plus ~7 bullet points plus 3-4 notes. That's appropriate.

Let me finalize the code, double-checking syntax details:

- `DATA(lv_von) = |{ sy-datum(4) }0101|.` — sy-datum(4) substringing a system field: allowed? sy-datum is a data object (structure sy-datum component, type d). Substring access `sy-datum(4)` — yes, allowed on d (character-like). In a string template: `|{ sy-datum(4) }0101|` — embedded expression with offset/length: `{ sy-datum(4) }` — hmm, inside string templates, can you use offset/length in the embedded expression? The embedded expression is `sy-datum(4)` — this is parsed as... In string templates, `{ ... }` contains an abap expression; `sy-datum(4)` could be ambiguous (method call vs substring). For a data object with (4) it's a substring access — but ABAP might interpret `sy-datum(4)` as... For data objects, obj(len) is substring. Inside string templates, I believe `|{ sy-datum+0(4) }0101|` is safer. Actually the substring syntax is `sy-datum+0(4)` or `sy-datum(4)`? Both work: `data(4)` means first 4 characters? For character-like fields, `f(4)` = first 4 chars (offset 0 default). Yes, `sy-datum(4)` is valid substring syntax. Inside a string template embedded expression, using `sy-datum(4)` — I think it works since it's a valid expression? Embedded expressions allow "arithmetic and string expressions" and also simple data objects with... Hmm, to be safe, use `sy-datum+0(4)`. Actually I recall that in string templates, `{ sy-datum+0(4) }` definitely works. `{ sy-datum(4) }` — the parser: after the object name, `(4)` could look like a functional method call `sy-datum( 4 )`? sy-datum is not a method, so it should parse as substring. I've seen `|{ sy-datum(4) }|` used. Hmm, but there's a known ambiguity: `obj(4)` where obj is a data object = substring; where obj is a function = call. For sy-datum it's a data object → substring. It compiles. But to avoid any doubt, I'll write `sy-datum+0(4)`. That's unambiguous.

Actually cleaner: 

```abap
DATA(lv_jahr) = sy-datum+0(4).
DATA(lv_von)  = |{ lv_jahr }0101|.
DATA(lv_bis)  = |{ lv_jahr }1231|.
```

lv_jahr type string. Fine. Or single lines. I'll do:

```abap
DATA(lv_von) = |{ sy-datum+0(4) }0101|.   " z. B. 20250101
DATA(lv_bis) = |{ sy-datum+0(4) }1231|.
```

Good.

Alternatively use CONV d: `CONV d( ... )` — not needed.

Also, should I use `@sy-datum` directly? Not needed.

Double-check FIELDS clause position: `SELECT FROM kna1 AS k INNER JOIN vbak AS v ON v~kunnr = k~kunnr FIELDS ...` — yes, that's the strict-mode order: FROM before select list, with FIELDS keyword introducing the list. Correct for 7.50.

Alternatively classic order: `SELECT k~kunnr, ... FROM kna1 AS k INNER JOIN ... WHERE ... GROUP BY ... ORDER BY ... INTO TABLE @DATA(...).` Both fine. I'll present the modern one (FROM first, FIELDS) since user asked "modernes ABAP-SQL (7.50+)". Maybe mention that classic order also works.

JOIN condition: `ON v~kunnr = k~kunnr` — in strict mode, ON uses `=` with column selectors. Good.

GROUP BY: `GROUP BY k~kunnr, k~name1, v~waerk`. Good.

HAVING: `HAVING COUNT( * ) > 5`. Good.

ORDER BY: `ORDER BY gesamt_netwr DESCENDING`. Good.

INTO: `INTO TABLE @DATA(lt_kunde_umsatz).` Good.

One more consideration: In HAVING, could also use `> @lv_min_orders` with a host variable — could show that as it emphasizes host variables. E.g., `CONSTANTS lc_min_orders TYPE i VALUE 5.` then `HAVING COUNT( * ) > @lc_min_orders`? Constants as host variables with @ — allowed? Host variables include constants? Yes, @ works with any visible data object including constants. But keep literal 5 for simplicity; maybe mention it.

Result field names: KUNNR, NAME1, ANZAHL_AUFTRAEGE, GESAMT_NETWR, WAEHRUNG.

Also note about performance: index on VBAK~ERDAT? There's VBAK index on ERDAT (index VBAK~ERD? standard index "E" on ERDAT?). Not necessary to dive deep.

Now write the answer in German. Structure:

1. Kurzer Codeblock (Deklarationen + SELECT).
2. "Klausel für Klausel" list.
3. "Hinweise" (2–4 bullets).

Keep it tight. Use headers maybe "**Code**" and "**Erklärung**". Markdown appropriate since it's a technical chat answer.

Let me write the final code carefully:

```abap
" Zeitraum laufendes Jahr als Host-Variablen
DATA(lv_von) = |{ sy-datum+0(4) }0101|.   " z.B. 20250101
DATA(lv_bis) = |{ sy-datum+0(4) }1231|.   " z.B. 20251231

SELECT FROM kna1 AS k
       INNER JOIN vbak AS v
               ON v~kunnr = k~kunnr
       FIELDS k~kunnr,
              k~name1,
              COUNT( * )     AS anzahl_auftraege,
              SUM( v~netwr ) AS gesamt_netwr,
              v~waerk        AS waehrung
       WHERE v~erdat BETWEEN @lv_von AND @lv_bis
       GROUP BY k~kunnr, k~name1, v~waerk
       HAVING COUNT( * ) > 5
       ORDER BY gesamt_netwr DESCENDING
       INTO TABLE @DATA(lt_kunde_umsatz).
```

Wait — WHERE with only one condition; fine. Should I include the optional auart as commented line inside? Could add:

```
       WHERE v~erdat BETWEEN @lv_von AND @lv_bis
*         AND v~auart = 'TA"   " optional: nur Aufträge (Belegart)
```

Comment syntax inside: `AND v~auart = 'TA'` with `"` comment. I'll add it as a commented line to show optional filter. Careful: `WHERE v~erdat BETWEEN @lv_von AND @lv_bis` followed by a comment line `* AND v~auart = 'TA'  " optional`. ABAP full-line comment with `*`. Fine.

Hmm, but if I comment it out, the statement is valid. Good.

Explanations:

- **FROM … INNER JOIN**: KNA1 (Kundenstamm) mit VBAK (Auftragskopf) über KUNNR verknüpft; Aliase k/v. INNER JOIN → nur Kunden mit Aufträgen im Zeitraum erscheinen.
- **FIELDS**: moderne Auswahlliste (7.40 SP08+). Nicht-aggregierte Spalten + Aggregatfunktionen COUNT(*) und SUM(...) mit Alias-Namen – die Aliase braucht man später für ORDER BY und Zugriff.
- **WHERE**: Eingrenzung auf Erstdatum (ERDAT) im laufenden Jahr. `@` kennzeichnet Host-Variablen (Pflicht in modernem Open SQL). BETWEEN kann einen Index auf ERDAT nutzen.
- **GROUP BY**: bildet eine Ergebniszeile je Kunde (hier zusätzlich je Währung, weil man NETWR über verschiedene Währungen nicht sinnvoll summieren kann). Alle SELECT-Spalten ohne Aggregatfunktion müssen in der GROUP-BY-Liste stehen.
- **HAVING**: Filter auf aggregierte Gruppen – nur Kunden mit COUNT(*) > 5. (WHERE filtert Zeilen vor der Aggregation und darf keine Aggregate enthalten.)
- **ORDER BY … DESCENDING**: absteigende Sortierung nach dem Gesamtwert; Aggregate werden im ORDER BY über ihren Alias angesprochen.
- **INTO TABLE @DATA(...)**: inline Deklaration der Ergebnistabelle lt_kunde_umsatz; Typen werden aus der SELECT-Liste abgeleitet (kunnr, name1, anzahl_auftraege: int4, gesamt_netwr: netwr, waehrung).

Hinweise:
- Ohne Währungsbedenken: `WHERE v~waerk = 'EUR'`

</details>
