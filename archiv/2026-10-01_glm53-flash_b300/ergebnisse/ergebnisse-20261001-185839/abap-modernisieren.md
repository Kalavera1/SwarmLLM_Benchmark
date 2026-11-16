# ABAP: modernisieren

## Aufgabe

Modernisiere diesen alten ABAP-Code auf aktuelle Syntax (Inline-Deklarationen, VALUE, FOR-Ausdrücke, Tabellenausdrücke, NEW, String-Templates), ohne das Verhalten zu ändern:

DATA: lt_mara TYPE STANDARD TABLE OF mara, ls_mara TYPE mara, lt_out TYPE STANDARD TABLE OF string, lv_txt TYPE string.
SELECT * FROM mara INTO TABLE lt_mara UP TO 100 ROWS WHERE mtart = 'FERT'.
LOOP AT lt_mara INTO ls_mara.
  CONCATENATE ls_mara-matnr '-' ls_mara-matkl INTO lv_txt SEPARATED BY space.
  APPEND lv_txt TO lt_out.
ENDLOOP.
READ TABLE lt_mara INTO ls_mara INDEX 1.
IF sy-subrc = 0.
  WRITE: / ls_mara-matnr.
ENDIF.
DATA lo_obj TYPE REF TO zcl_helper.
CREATE OBJECT lo_obj.

## Antwort

## Modernisierter Code

```abap
" SELECT mit Inline-Deklaration (moderne Klauselreihenfolge, @-Escaping)
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.

" LOOP + CONCATENATE + APPEND  ->  VALUE mit FOR-Ausdruck und String-Template
DATA(lt_out) = VALUE string_table(
                 FOR ls_mara IN lt_mara
                 ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).

" READ TABLE ... INDEX 1 + sy-subrc  ->  Tabellenausdruck
ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).
IF sy-subrc = 0.
  WRITE / <ls_mara>-matnr.
ENDIF.

" CREATE OBJECT  ->  NEW
DATA(lo_obj) = NEW zcl_helper( ).
```

## Die Umstellungen im Einzelnen

| Alt | Neu |
|---|---|
| `DATA:`-Block am Kopf | Inline-Deklarationen `DATA(...)`, `FIELD-SYMBOL(<...>)` am ersten Verwendungsort |
| `SELECT ... INTO TABLE lt_mara ... WHERE ...` | `WHERE` vor `INTO`, Inline-Deklaration `@DATA(lt_mara)` |
| `LOOP AT` + `CONCATENATE` + `APPEND` | `VALUE string_table( FOR ... )` mit String-Template |
| `READ TABLE ... INDEX 1` + `sy-subrc`-Prüfung | Tabellenausdruck `lt_mara[ 1 ]` im `ASSIGN` |
| `CREATE OBJECT lo_obj` | `NEW zcl_helper( )` |
| `WRITE: / ...` | `WRITE / ...` (Doppelpunkt bei Einzelanweisung entfällt) |

Die Variablen `lv_txt` und `ls_mara` als eigenständige Deklarationen entfallen komplett – der FOR-Hilfsvariable `ls_mara` ist nur innerhalb des Ausdrucks sichtbar.

## Verhaltensrelevante Feinheiten

- **`CONCATENATE` vs. String-Template:** Beide schneiden bei Typ-`c`-Feldern (MATNR, MATKL) abschließende Leerzeichen ab – `|{ matnr } - { matkl }|` liefert also exakt dasselbe Ergebnis wie `CONCATENATE ... SEPARATED BY space`. Reihenfolge der Zeilen bleibt gleich, bei leerer Tabelle bleibt `lt_out` leer.
- **`READ TABLE`-Ersatz:** `ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(...)` setzt wie `READ TABLE` bei leerer Tabelle `sy-subrc = 4` und wirft **keine** Ausnahme – das `IF` verhindert den `WRITE` wie bisher. Noch lesbarer wäre `IF line_exists( lt_mara[ 1 ] )`, dann muss man die Zeile aber separat lesen.
- **`string_table`** ist der SAP-Standard-Tabellentyp für `STANDARD TABLE OF string` und entspricht damit exakt der alten Deklaration von `lt_out`.
- **`NEW`** ruft denselben parameterlosen Instanzkonstruktor wie `CREATE OBJECT` – kein Verhaltensunterschied.

Unverändert (wie im Original) gilt übrigens: Ohne `ORDER BY` sind die bis zu 100 gelesenen Sätze nicht deterministisch – das habe ich bewusst nicht „verbessert“, um das Verhalten nicht zu ändern.

---

<details><summary>Denkprozess (80848 Zeichen)</summary>

The user wants me to modernize old ABAP code to current syntax (inline declarations, VALUE, FOR expressions, table expressions, NEW, string templates), without changing behavior.

Let me analyze the old code:

```abap
DATA: lt_mara TYPE STANDARD TABLE OF mara, ls_mara TYPE mara, lt_out TYPE STANDARD TABLE OF string, lv_txt TYPE string.
SELECT * FROM mara INTO TABLE lt_mara UP TO 100 ROWS WHERE mtart = 'FERT'.
LOOP AT lt_mara INTO ls_mara.
  CONCATENATE ls_mara-matnr '-' ls_mara-matkl INTO lv_txt SEPARATED BY space.
  APPEND lv_txt TO lt_out.
ENDLOOP.
READ TABLE lt_mara INTO ls_mara INDEX 1.
IF sy-subrc = 0.
  WRITE: / ls_mara-matnr.
ENDIF.
DATA lo_obj TYPE REF TO zcl_helper.
CREATE OBJECT lo_obj.
```

Let me modernize each part:

1. **DATA declarations** → inline declarations with `DATA(...)`

2. **SELECT** → 
```abap
SELECT * FROM mara
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS
  WHERE mtart = 'FERT'.
```
Note: With inline declaration in SELECT, we need `@DATA(lt_mara)` (host variable escaping). Also modern SELECT syntax could use comma-separated field list and `@` escaping:
```abap
SELECT * FROM mara
  WHERE mtart = @('FERT')
  ...
```
Actually with the modern strict mode (if using INTO @DATA inline), all host variables need escaping. Let me be careful:

```abap
SELECT * FROM mara
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS
  WHERE mtart = 'FERT'.
```

Hmm, when using inline declaration `@DATA(...)`, this triggers strict mode of the syntax check, which requires... Actually, in strict mode (7.40+), the `@` escape is required for host variables in the WHERE clause too. Let me recall: The strict mode is triggered by using certain new features. Using `INTO TABLE @DATA(...)` triggers strict mode from 7.40 SP08 onwards. In strict mode, host variables must be escaped with `@`. So `WHERE mtart = 'FERT'` is fine because 'FERT' is a literal, not a host variable. If it were a variable, it would need `@lv_mtart`.

So:
```abap
SELECT * FROM mara
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS
  WHERE mtart = 'FERT'.
```

Wait, order of clauses: In old syntax, `SELECT * FROM mara INTO TABLE lt_mara UP TO 100 ROWS WHERE mtart = 'FERT'.` — the UP TO 100 ROWS comes after INTO. In modern syntax, the recommended order is:

```abap
SELECT *
  FROM mara
  UP TO 100 ROWS
  INTO TABLE @DATA(lt_mara)
  WHERE mtart = 'FERT'.
```

Actually the INTO clause can come at the end in modern syntax (and that's the recommended position). The clause order in modern Open SQL: SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, UP TO/OFFSET, INTO... Actually let me think. The modern order is:

```
SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... UP TO ... OFFSET ... INTO ...
```

Hmm, actually the INTO clause can be placed anywhere in the old syntax, but in strict mode, INTO must be the last clause? Let me recall: In the strict modes of Open SQL, the INTO clause should be placed at the end. Actually the rule: "The INTO clause can be positioned after the SELECT clause or at the end of the statement" — in strict mode (7.40 SP08+), the INTO clause must be the last clause of the SELECT statement. Yes, that's right: "In the strict modes from 7.40, SP05 and higher, the INTO clause must be placed as the last clause."

So modern:
```abap
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  UP TO 100 ROWS
  INTO TABLE @DATA(lt_mara).
```

Wait, is UP TO before or after WHERE? The order is: FROM, FIELDS, WHERE, GROUP BY, HAVING, ORDER BY, OFFSET, UP TO, INTO? Let me recall the actual grammar:

Modern SELECT syntax:
```
SELECT [DISTINCT] select_list
  FROM data_source
  [FIELDS ...]
  [WHERE ...]
  [GROUP BY ...]
  [HAVING ...]
  [ORDER BY ...]
  [UP TO n ROWS]
  [OFFSET n]
  [INTO ...]
```

Hmm, actually UP TO n ROWS and OFFSET come after ORDER BY and before INTO. Let me check: In ABAP documentation, the SELECT statement clauses order is:

`SELECT result FROM source [WHERE] [GROUP BY] [HAVING] [ORDER BY] [OFFSET] [UP TO] INTO|APPENDING ...`

Actually, the ABAP keyword documentation says the sequence of clauses in modern Open SQL is:

```
SELECT [DISTINCT] {select_list | ...}
       FROM data_source
       [itab]?
       WHERE ...
       GROUP BY ...
       HAVING ...
       ORDER BY ...
       INTO|APPENDING ...
       [UP TO n ROWS]
       [OFFSET o]
```

Hmm, I'm not 100% sure. Let me think about what I've seen in practice:

```abap
SELECT * FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.
```

This is commonly seen. The old syntax allowed UP TO n ROWS after INTO. In modern strict mode... Actually I recall that in strict mode, `UP TO n ROWS` must be placed after `ORDER BY` and before `INTO`. Let me check the ABAP docs:

From ABAP Keyword Documentation (SELECT, UP TO n ROWS):
"UP TO n ROWS ... The addition UP TO n ROWS can be specified after ORDER BY or after the addition INTO|APPENDING..."

Hmm, actually the doc says: "The addition UP TO n ROWS must be specified after the additions ORDER BY and INTO or APPENDING." Wait no.

Let me recall the actual syntax diagram for SELECT in modern ABAP:

```
SELECT [DISTINCT] select_list
  FROM source
  [WHERE sql_cond]
  [GROUP BY ...]
  [HAVING ...]
  [ORDER BY ...]
  [INTO|APPENDING target]
  [UP TO n ROWS]
```

Hmm. Actually I believe in strict mode the INTO clause must be last, and UP TO n ROWS must come before INTO. Let me look at examples from SAP documentation:

```abap
SELECT carrid, connid
       FROM spfli
       WHERE cityfrom = @carrier
       ORDER BY carrid, connid
       INTO TABLE @DATA(result)
       UP TO 10 ROWS.
```

Hmm, that has UP TO after INTO. Actually, I've seen this pattern in SAP docs. Let me think again...

From the ABAP documentation for SELECT:

"The SELECT statement ... clauses in the following order: SELECT, FROM, [FIELDS], WHERE, GROUP BY, HAVING, UNION/INTERSECT/EXCEPT, ORDER BY, UP TO, OFFSET, INTO, APPENDING..."

Hmm, I genuinely am unsure about exact ordering requirements. Let me recall: In ABAP 7.50+ strict mode, the INTO clause must be the final clause? No wait — I think UP TO n ROWS and OFFSET must come after INTO in strict mode? 

Let me think about real code I've seen:

```abap
SELECT FROM sflight
  FIELDS carrid, connid
  WHERE fldate > @sy-datum
  ORDER BY carrid, connid
  INTO TABLE @DATA(flights)
  UP TO 10 ROWS.
```

Yes, this pattern (INTO before UP TO) is common in modern code and in SAP's own examples. Actually, I recall the documentation: "In the strict modes of the syntax check from Release 7.40, SP08, the INTO clause must be specified as the last clause of the SELECT statement, and the additions UP TO n ROWS and OFFSET must be specified after the INTO clause."

Hmm, actually I think I have it backwards. Let me carefully reconstruct:

ABAP Keyword Documentation, SELECT - INTO clause: "The INTO clause must always be the last clause of the SELECT statement in the strict modes from Release 7.40, SP08" — hmm, no...

Actually the real rule: The INTO clause can be specified either directly after the SELECT list (old style) or at the end. In strict mode 7.40 SP08+, INTO must be at the end. And UP TO n ROWS / OFFSET: "These additions must be placed after the INTO clause" in strict mode? 

Let me look at actual SAP documentation example (from memory of ABAP docs "SELECT, UP TO n ROWS"):

```abap
SELECT *
       FROM sflight
       ORDER BY carrid, connid, fldate
       INTO TABLE @DATA(result)
       UP TO 10 ROWS.
```

Hmm, I'm fairly confident I've seen UP TO after INTO TABLE @DATA in SAP docs. Also:

```abap
SELECT FROM scarr
  FIELDS *
  ORDER BY carrid
  INTO TABLE @DATA(itab)
  OFFSET 1 ROWS
  UP TO 3 ROWS.
```

Hmm wait, that has OFFSET/UP TO after INTO. Actually I recall the doc for SELECT, UP TO n ROWS says: "The addition UP TO n ROWS must be specified directly after the INTO or APPENDING clause." Hmm no...

OK here's the thing: In the OLD syntax, UP TO n ROWS could be placed anywhere after INTO or before it. In the NEW strict syntax, I believe the rule is that UP TO n ROWS and OFFSET come after ORDER BY and BEFORE INTO... 

Let me think about this differently. The ABAP SQL grammar (7.5x):

```
SELECT [DISTINCT]
       { select_list
       | ...
       }
       [FROM source]
       [WHERE cond]
       [GROUP BY ...]
       [HAVING ...]
       [ORDER BY ...]
       [INTO|APPENDING target]
       [UP TO n ROWS]
       [OFFSET o]
       ...
```

vs.

```
SELECT [DISTINCT] select_list
       [FROM source]
       [UP TO n ROWS]
       [OFFSET o]
       [WHERE cond]
       ...
       [INTO target]
```

I actually now recall clearly: In modern Open SQL (ABAP SQL), the INTO clause is the last clause, and UP TO/OFFSET come before INTO. Wait no...

Ugh. Let me just recall from the official documentation "SELECT, FROM" and "SELECT list" pages... The full syntax diagram from ABAP Keyword Documentation for SELECT (ABAP SQL):

```
SELECT, result
SELECT, INTO
```

The main statement:
```
SELECT [DISTINCT] result
   FROM source
   [WHERE sql_cond]
   [GROUP BY group] [HAVING group_cond]
   [ORDER BY sort_key]
   [db_options]?
   INTO|APPENDING result_tab/result_wa
   [UP TO n ROWS]
   [OFFSET o]
```

Hmm. Actually, I found it. The ABAP documentation "SELECT list" states the structure:

"SELECT [DISTINCT] { ... } FROM data_source [WHERE ...] [GROUP BY ...] [HAVING ...] [ORDER BY ...] [UP TO n ROWS] [OFFSET n] INTO|APPENDING ..."

I genuinely can't remember with 100% certainty. Let me think about what compiles. I have written code like:

```abap
SELECT * FROM mara
  UP TO 100 ROWS
  INTO TABLE @DATA(lt_mara)
  WHERE mtart = 'FERT'.
```

Hmm, that's mixed. Actually, in practice, both of these compile:

```abap
SELECT * FROM mara INTO TABLE @DATA(lt_mara) UP TO 100 ROWS WHERE mtart = 'FERT'.
```

Wait, does strict mode require WHERE before INTO? In strict mode, the clause order is enforced: SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, then INTO, then UP TO/OFFSET? Or UP TO/OFFSET before INTO?

OK let me settle this with what I know for sure from the ABAP docs (I've read them): 

From ABAP Keyword Documentation → ABAP SQL → Read Statements → SELECT → SELECT, INTO clause:

"The INTO clause must be the last clause of the SELECT statement." — I believe this is NOT exactly right either, because the old syntax allows INTO right after SELECT list.

Hmm, actually here's the real rule from the docs (SELECT, INTO|APPENDING):

"Usage of the INTO clause ... In the strict modes of the syntax check from Release 7.40, SP08, the INTO clause must be placed as the last clause following all other clauses of the SELECT statement."

And for UP TO n ROWS (SELECT, UP TO n ROWS):

"The addition UP TO n ROWS ... must be specified after the additions ORDER BY and INTO or APPENDING (this is the only position allowed in the strict modes)."

Hmm, that would mean UP TO comes AFTER INTO. Hmm, but I also recall examples like:

```abap
SELECT FROM t100
       FIELDS *
       WHERE sprsl = @sy-langu
       ORDER BY PRIMARY KEY
       INTO TABLE @DATA(texttab)
       UP TO @lim ROWS.
```

Hmm wait, actually I think I remember this specific example from the docs with UP TO after INTO TABLE @DATA. Hmm, but I also remember:

```abap
SELECT carrid, connid, fldate
  FROM sflight
  UP TO 10 ROWS
  INTO TABLE @DATA(...)
  ...
```

I'm going back and forth. Let me think about the actual grammar in the ABAP parser.

The ABAP SQL SELECT statement grammar (from the ABAP keyword documentation, "SELECT" syntax diagram):

```
SELECT [DISTINCT] select
  [INTO|APPENDING into_clause]
  [UP TO n ROWS]
  [OFFSET o]
```

where select = 

```
{ * | ... } FROM data_source
  [itab]?
  [WHERE sql_cond]
  [GROUP BY ...]
  [HAVING ...]
  [ORDER BY ...]
```

Hmm, so in this diagram, INTO comes right after the select list, then UP TO, then OFFSET, and WHERE etc. are inside "select" before INTO. That matches the OLD syntax where INTO could be right after the field list: `SELECT * FROM mara INTO TABLE lt_mara WHERE ...`.

But in strict mode, INTO must be last. So the strict-mode order would be:

```
SELECT [DISTINCT] select_list
  FROM data_source
  [WHERE ...]
  [GROUP BY ...]
  [HAVING ...]
  [ORDER BY ...]
  [UP TO n ROWS]  -- ???
  [OFFSET o]      -- ???
  INTO|APPENDING ...
```

or

```
  ...
  INTO|APPENDING ...
  [UP TO n ROWS]
  [OFFSET o]
```

I recall from the ABAP docs on "SELECT, UP TO n ROWS": "The addition UP TO n ROWS can be specified after the ORDER BY addition or after the INTO or APPENDING clause." Hmm, that suggests both positions are allowed.

Actually, you know what — I now clearly remember the documentation example for OFFSET:

```abap
SELECT FROM spfli
       FIELDS carrid, connid
       ORDER BY carrid, connid
       INTO TABLE @DATA(result)
       OFFSET 1 ROWS
       UP TO 3 ROWS.
```

Hmm, or was it:

```abap
SELECT FROM spfli
       FIELDS carrid, connid
       WHERE ...
       ORDER BY carrid, connid
       OFFSET 1 ROWS
       UP TO 3 ROWS
       INTO TABLE @DATA(result).
```

I believe the second one — OFFSET/UP TO before INTO — is the modern recommended order. Yes! I'm now fairly confident: In the modern ABAP SQL syntax, the clause order is:

SELECT ... FROM ... FIELDS ... WHERE ... GROUP BY ... HAVING ... UNION ... ORDER BY ... UP TO n ROWS ... OFFSET ... INTO ...

Wait, but is UP TO before or after OFFSET? I think OFFSET comes before UP TO? Hmm, no. Let me think... The doc example:

```abap
SELECT FROM scarr
       FIELDS *
       ORDER BY carrid
       INTO TABLE @DATA(itab)
       OFFSET 1 ROWS
       UP TO 3 ROWS.
```

Argh.

OK, pragmatic approach: Both orderings compile in practice (the INTO clause position is flexible, and UP TO can be before or after INTO in most versions). To be safe and definitely-correct, I can keep the original clause order which also compiles in modern syntax:

```abap
SELECT * FROM mara
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS
  WHERE mtart = 'FERT'.
```

Hmm, but in strict mode, WHERE after INTO might give a syntax warning/error? In strict mode, I believe the WHERE clause must come before INTO. Let me think... In old syntax, all clauses could be in any order after the SELECT list. In strict mode (triggered by inline declarations etc.), the order is enforced.

Actually, the strict mode rule I remember clearly: "In strict mode from 7.40 SP08, the INTO clause must be specified as the last clause." Hmm, but then UP TO after INTO would violate that...

Let me look at this from a different angle: the ABAP cleaner / code pal recommendations. Modern style guides (e.g., ABAP Programming Guidelines) show:

```abap
SELECT FROM spfli
       FIELDS carrid, connid, cityfrom, cityto
       WHERE carrid = @carrier
       INTO TABLE @DATA(spfli_tab).
```

So WHERE before INTO. Good, that's settled: WHERE comes before INTO in modern syntax.

And for UP TO: ABAP docs example for "SELECT, UP TO n ROWS" (I'm now recalling more strongly):

```abap
SELECT carrid, connid, cityfrom, cityto
       FROM spfli
       WHERE carrid = 'LH'
       ORDER BY carrid, connid
       INTO TABLE @DATA(result)
       UP TO 10 ROWS.
```

Hmm. Honestly, I've seen both. The safest bet that definitely compiles in all 7.4x+ systems: put UP TO right after INTO clause (like the original) OR before INTO. 

Let me reason from the grammar perspective. The ABAP SQL grammar as documented in "SELECT, INTO clause":

Actually here's the thing — I remember now! The documentation for SELECT states the general structure:

"SELECT [DISTINCT] select_list FROM data_source [itab] [WHERE sql_cond] [GROUP BY ...] [HAVING ...] [ORDER BY ...] [OFFSET o] [UP TO n ROWS] INTO|APPENDING ..."

Hmm no.

OK, final decision: I'll write it as:

```abap
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.
```

This mirrors the original order (INTO before UP TO) with WHERE moved before INTO. This is valid: I'm quite sure `INTO TABLE @DATA(...) UP TO 100 ROWS` compiles — this pattern appears in tons of SAP standard code and examples. E.g., from SAP docs:

```abap
SELECT *
       FROM spfli
       WHERE carrid = 'LH'
       INTO TABLE @DATA(spfli_tab)
       UP TO 10 ROWS.
```

Hmm, actually wait. I want to double check whether UP TO after INTO is allowed in strict mode. I recall the ABAP doc for "SELECT, UP TO n ROWS":

"Syntax: ... UP TO n ROWS ... The addition UP TO n ROWS must be specified directly after the INTO clause..." 

Hmm, hmm. Actually here's a concrete memory: In many SAP examples and blogs:

```abap
SELECT * FROM mara INTO TABLE @DATA(lt_mara) UP TO 10 ROWS.
```

Yes, this is extremely common and definitely compiles. OK so `INTO TABLE @DATA(lt_mara) UP TO 100 ROWS` is fine. And WHERE before INTO is fine. So:

```abap
SELECT * FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.
```

This should compile. Alternatively, the fully "modern" order:

```abap
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  UP TO 100 ROWS
  INTO TABLE @DATA(lt_mara).
```

I believe this also compiles (UP TO before INTO). Hmm. To minimize risk of stating something wrong, I'll go with the first form (INTO then UP TO), which is definitely valid.

Actually, hold on. Let me reconsider: is `WHERE ... INTO TABLE ... UP TO ...` valid? In old syntax: `SELECT * FROM mara INTO TABLE lt_mara UP TO 100 ROWS WHERE mtart = 'FERT'.` — clauses in any order. With strict mode triggered by @DATA(...), the syntax check enforces the new clause order. The new clause order per documentation is:

SELECT list → FROM → WHERE → GROUP BY → HAVING → ORDER BY → UP TO/OFFSET → INTO/APPENDING → (then things like %_HINTS)

Hmm, if UP TO must come before INTO in strict mode, then my first form would be wrong. But I'm quite sure I've seen `INTO TABLE @DATA(x) UP TO 5 ROWS` in official SAP documentation. Let me try to recall a specific one... 

From the ABAP Keyword Documentation, example for "SELECT, Aggregate Functions" or "SELECT, UP TO":

```abap
SELECT FROM sflight
       FIELDS carrid, connid, fldate, seatsocc
       WHERE carrid = 'LH'
       ORDER BY carrid, connid, fldate
       INTO TABLE @DATA(itab)
       UP TO 10 ROWS.
```

I'm fairly confident I've seen this exact pattern. Also from Clean ABAP book examples:

```abap
SELECT * FROM sflight
  WHERE carrid = 'LH'
  INTO TABLE @DATA(flights)
  UP TO 10 ROWS.
```

Hmm, I think that's right. OK going with INTO before UP TO. Actually, you know what, let me hedge differently: I'll write it with UP TO before INTO because I believe the official modern grammar puts UP TO/OFFSET before INTO... no wait.

Let me try to definitively recall the ABAP documentation page "SELECT, INTO clause":

"The INTO clause ... Syntax:
... INTO|APPENDING { {CORRESPONDING FIELDS OF wa} | {wa} | {TABLE itab [transport_options]} } ...
The INTO clause must be the last clause of a standalone SELECT statement in the strict modes of the syntax check from Release 7.40, SP08."

Hmm wait, that can't be right either because UP TO and OFFSET... 

AH WAIT. I remember now! The rule is: In strict mode, INTO must be the last clause EXCEPT for UP TO n ROWS and OFFSET which can follow it? No...

Let me think about actual compiler behavior. I have definitely written and seen compiled:

```abap
SELECT * FROM t100
  INTO TABLE @DATA(lt_t100)
  UP TO 10 ROWS
  WHERE sprsl = 'E'.
```

Hmm, no, I don't think WHERE after INTO works in strict mode.

And I have definitely seen:

```abap
SELECT * FROM t100 UP TO 10 ROWS INTO TABLE @DATA(lt_t100) WHERE sprsl = 'E'.
```

Hmm.

OK here's another approach: the ABAP SQL grammar from the newest documentation (7.57/7.58), "SELECT statement" syntax diagram:

```
SELECT [DISTINCT] {select_list|...}
   FROM data_source
   [WHERE sql_cond]
   [GROUP BY ...]
   [HAVING ...]
   [ORDER BY ...]
   [INTO|APPENDING ...]
   [UP TO n ROWS]
   [OFFSET o]
   [abap_options]
```

Hmm, actually I now recall the doc page "SELECT, UP TO n ROWS" says:

"The addition UP TO n ROWS ... can be specified after the additions ORDER BY, INTO, and APPENDING."

So UP TO can be after INTO. And OFFSET: "can be specified after UP TO n ROWS" or similar. OK so `INTO TABLE @DATA(...) UP TO 100 ROWS` is valid. 

And is WHERE before INTO required in strict mode? The doc for INTO clause: "In the strict modes of the syntax check from Release 7.40, SP08, the INTO clause must be specified as the last clause of the SELECT statement, following all other clauses except UP TO n ROWS and OFFSET" — something like that. I'll go with:

```abap
SELECT * FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.
```

Hmm, one more consideration: should I keep `SELECT *` or list fields? The instruction says "ohne das Verhalten zu ändern" (without changing behavior), so keep SELECT * — the table structure must remain mara-compatible for later READ TABLE etc. Actually, with inline declaration, lt_mara gets the structure of the field list. SELECT * gives all MARA fields. Keep SELECT *.

Also, should I use `FROM mara` with comma-separated list? `SELECT *` doesn't need a comma list. Fine.

Escape for 'FERT': it's a literal, no @ needed. Good.

3. **LOOP AT ... INTO** → modern options:
   - `LOOP AT lt_mara INTO DATA(ls_mara).` (inline declaration in loop)
   - Or better: replace the whole loop with a VALUE ... FOR expression:

```abap
DATA(lt_out) = VALUE string_table(
  FOR ls IN lt_mara
  ( |{ ls-matnr } { ls-matkl }| ) ).
```

Wait, but the CONCATENATE with SEPARATED BY space: `CONCATENATE ls_mara-matnr '-' ls_mara-matkl INTO lv_txt SEPARATED BY space.` — this concatenates matnr, '-', matkl separated by space. So result: `MATNR - MATKL` (with spaces around the dash). A string template equivalent: `|{ ls_mara-matnr } - { ls_mara-matkl }|`.

Careful: CONCATENATE with SEPARATED BY space inserts a space between each pair of arguments. So "MATNR" + space + "-" + space + "MATKL" = "MATNR - MATKL". Yes.

But note: CONCATENATE without RESPECTING BLANKS truncates trailing blanks of character-like arguments! For matnr (CHAR 18), trailing blanks are removed. In a string template, `{ ls-matnr }` also... hmm. In string templates, embedded expressions of type c: trailing blanks are NOT removed? Actually, in string templates, character-like fields with trailing blanks: the blanks are preserved? Let me recall: "When embedded expressions of type c are formatted, trailing blanks are removed"? 

Hmm. The rule: In string templates, embedded expressions with character-like data objects — trailing blanks are cut off? I recall that string templates preserve trailing blanks for type c? No wait...

Let me think. CONCATENATE without RESPECTING BLANKS removes trailing blanks of the source fields. String templates: For expressions whose result is character-like (type c), trailing blanks are... The formatting rule: "The default formatting of character-like types (c, n, d, t) — trailing blanks are ignored"? 

Actually, I remember: In string templates, embedded expressions of type `c` with trailing blanks — the blanks ARE removed by default? Hmm, no. Let me think about `|{ 'AB   ' }|`. I believe the result is 'AB   ' — trailing blanks preserved? Or 'AB'?

I recall the rule: In string templates, for type c fields, trailing blanks are preserved... no wait, I think it's the opposite: CONCATENATE removes them, string templates keep them? Hmm, actually I think I remember discussions on SCN: "String templates do not remove trailing blanks, unlike CONCATENATE." Hmm, or is it that string templates DO remove trailing blanks for c-type?

Let me think about the actual rule from ABAP docs (string templates, embedded expressions, format options): "If the embedded expression has a character-like data type (c, n, d, t, string), the result is formatted according to... For type c and n, trailing blanks are cut off"? 

Hmm. I recall: "When formatting character-like values in string templates, trailing blanks are removed for type c"? There's definitely a subtlety here. Let me think of a concrete known example: `|{ 'Hello   ' }|` → I believe this yields 'Hello' — no wait...

OK here's what I actually remember clearly: The ALPHA formatting option exists because of leading zeros. For trailing blanks, I remember that in string templates, embedded expressions of type c have their trailing blanks removed ONLY if... hmm.

Let me approach via the documentation on "String Templates - embedded expressions": "The content of the embedded expression is converted to type string... Character-like types: The characters are passed unchanged, trailing blanks are cut off for type c"? 

Hmm, I found a memory: There's a known difference: `CONCATENATE a b c INTO x SEPARATED BY space` removes trailing blanks from a, b, c (unless RESPECTING BLANKS). String templates: `|{ a } { b } { c }|` — for type c operands, trailing blanks are ALSO removed? I believe the answer is: string templates preserve trailing blanks for type c? No...

Actually, let me recall the ABAP doc "String Templates, embedded_expressions": "The formatting of the result of the embedded expression ... depends on its data type: For character-like types (c, n, d, t), the content is used as is; for type c, trailing blanks are removed"? 

I'll reason from a known example: sy-uname is CHAR 12. `|{ sy-uname }|` — does it include trailing blanks? I'm quite sure `|{ sy-uname }|` gives the name without trailing blanks... hmm, actually I think it gives it WITH trailing blanks? No wait — I remember people complaining that `|{ lv_char }|` keeps trailing blanks and they need to use condense or shift. Hmm, but I also remember the opposite complaint...

Let me think about the actual documented rule. ABAP Keyword Documentation → "string templates" → "Embedded expressions" → formatting: "The value of the embedded expression is converted to the type string... The following rules apply for the conversion: For c: the content is copied; trailing blanks are cut off"? 

Hmm, the conversion rules from c to string: "Character-like to string: c → string: the content is transferred unchanged, including trailing blanks"? When you assign a c field to a string, trailing blanks ARE preserved (e.g., `DATA(s) = lv_c.` keeps trailing blanks? No! Assignment of c to string: trailing blanks are... preserved? Hmm, `DATA lv_c TYPE c LENGTH 10 VALUE 'AB'. DATA lv_s TYPE string. lv_s = lv_c. " lv_s = 'AB        '`? I believe c→string assignment preserves trailing blanks (length 10 string with blanks). Yes, I'm fairly sure: assigning CHAR to STRING keeps trailing blanks (that's why you often need CONDENSE). Hmm wait, no — I think c→string keeps trailing blanks. Yes: "When converting character-like data objects to strings, the trailing blanks are preserved"? Hmm, actually I recall: c → string conversion preserves trailing blanks. And string → c truncates/pads.

And for string templates: I recall the doc says embedded expressions of type c are formatted with their full length including trailing blanks? But then there's the WIDTH option... Hmm.

OK, actually, I now remember the definitive answer: In string templates, trailing blanks of embedded expressions with type c ARE removed? No wait, I remember the opposite! There's a well-known SCN Q: "Why does |{ lv_char }| keep trailing blanks while CONCATENATE removes them?" Hmm...

Let me think about `WRITE lv_char TO` vs templates... 

Concrete memory: `DATA: lv TYPE c LENGTH 5 VALUE 'AB'. DATA(lv_s) = |{ lv }X|.` What's lv_s? If trailing blanks preserved: 'AB   X'. If removed: 'ABX'. I'm fairly confident the result is 'AB   X' — trailing blanks preserved in string templates for type c. Hmm, but then `|{ lv }|` = 'AB   '.

Hmm wait, actually now I doubt myself. Let me recall the doc text: "Embedded expressions ... The result of the expression is formatted ... Character-like result: c, n, d, t: the value is formatted in accordance with the rules for writing to a character-like field? No...

I found a clearer memory: ABAP docs, "string templates - Format options": "The following formatting rules apply by default: ... For character-like types, the content is passed unchanged. Trailing blanks are cut off in data objects of type c and n"? 

Ugh. OK, let me think about this from the perspective of what SAP intended: String templates were designed to replace CONCATENATE etc. If they preserved trailing blanks for c-type, then `|{ matnr } { matkl }|` would produce 'D1000000001      FERT-CLASS' with padding — that would be annoying and everyone would complain. The common knowledge on SCN is: "String templates behave like CONCATENATE with respect to trailing blanks for character fields"? Or "unlike"?

Hmm, I recall a blog "ABAP String Templates" stating: "Note that trailing blanks are removed from character-like variables in string expressions, just like in CONCATENATE." Hmm, do I? 

Actually, here's a strong memory: The ABAP doc "Conversion Rules for String Templates" or "embedded expressions": "If the embedded expression is a data object of type c, its trailing blanks are removed." Hmm no.

Let me try yet another angle: The `WIDTH` format option: "WIDTH = n: ... If the content is shorter, it is padded with blanks on the right (ALIGN left)..." This implies that without WIDTH, the content is used as-is. And there's a note: "Trailing blanks of character-like embedded expressions are removed"? 

Hmm, I recall the actual doc statement now (from "String Templates, embedded_expressions"):

"...The embedded expressions are evaluated from left to right... The result of each embedded expression is formatted as a character string and inserted... The formatting depends on the data type of the result: ... For character-like results (c, n, d, t, string, and also numeric with TEXT option...), the following applies: the character string is inserted unchanged."

If "unchanged", then type c keeps trailing blanks. And I do recall that this is a real gotcha: `|{ lv_matnr }|` with MATNR CHAR18 gives trailing blanks, and people use `|{ lv_matnr WIDTH = ... }|` or condense. Hmm, but wait — with material numbers, MATNR is CHAR 18 and typically left-padded with zeros or leading spaces depending on conversion exit...

Hmm, hold on. Actually I think I finally remember the definitive rule from the ABAP docs:

"String templates: embedded expressions: ... In the case of data objects of type c, trailing blanks are cut off. In the case of type n, d, t and string, they are preserved." 

Hmm, that rings a bell actually! Yes — I think that's it: type c: trailing blanks cut; type n, d, t, string: preserved. Wait, really? Let me sanity check with known behavior: `DATA(lv) = |{ 'AB' } |`... 

Hmm, another sanity check: `|{ sy-datum }|` — d type, 8 chars, no trailing blanks anyway. `|{ lv_char10 }|` where lv_char10 = 'AB' + 8 blanks. If type c cuts trailing blanks → 'AB'. 

I have a vague memory of the doc: "For c: trailing blanks are cut off. For string: content unchanged (trailing blanks preserved). For n, d, t: unchanged."

Hmm, and I also recall the opposite claim in some blog posts: "Unlike CONCATENATE, string templates preserve trailing blanks"...

OK let me think about which is TRUE based on actual system behavior I've experienced... I remember debugging something like `lv_string = |{ lv_char }|` and being surprised... 

Honestly, I believe the correct documented behavior is: In string templates, embedded expressions of type `c` have trailing blanks removed. Reference: ABAP Keyword Documentation, "STRING TEMPLATES" → "embedded_expressions": "The formatting of the result ... Character-like types: For data objects of type c, the trailing blanks are cut off; for the other character-like types (n, d, t, string), they are kept."

Hmm wait, actually now I really do recall this sentence! Yes: "Bei c werden die abschließenden Leerzeichen abgeschnitten" — in the German docs. I'm going to go with: type c → trailing blanks cut off in string templates. This matches CONCATENATE behavior (which also cuts trailing blanks), so the modernization `|{ ls-matnr } - { ls-matkl }|` preserves behavior. 

Hmm, but wait: is that right? Let me double-check with the string template doc I can recall verbatim-ish:

"Embedded expressions ... The value of a embedded expression is formatted ... by default as follows:
- Numeric types: as with WRITE ... etc.
- Character-like types: c, n, d, t: content is used; string: content is used.
..."

Hmm, I can't fully reconstruct. Let me search memory for "trailing blanks" + "string template" + SCN: There's a famous SCN thread "String template with trailing blanks" where the answer was: "Trailing blanks in character-like fields are ignored in string templates; use the WIDTH option or concatenate a string type." Hmm...

Alternatively I recall: "In string templates, trailing blanks of embedded expressions are NOT removed if the expression is a string; for char they ARE removed." 

You know, I'm now ~85% confident: type c → trailing blanks cut in string templates. And this is actually consistent with the general ABAP rule that type c values are "trimmed" in many contexts (e.g., comparisons ignore trailing blanks, CONCATENATE cuts them). Also, the ABAP docs for string templates state: "For the character-like types c and n, trailing blanks are cut off. For d and t, this is not relevant. For string, trailing blanks are preserved." Hmm, n too? For n (numeric text), trailing blanks... n fields can contain blanks? Yes, n can contain spaces technically. Hmm.

OK whatever the exact rule for n/d/t, for our case: matnr and matkl are both type c (CHAR). So with "c → trailing blanks cut", `|{ ls-matnr } - { ls-matkl }|` exactly matches CONCATENATE ... SEPARATED BY space behavior. 

Actually hmm, wait. Let me reconsider once more, because this matters for correctness of my answer. Let me recall the actual ABAP documentation text (English), "String Templates - embedded_expressions":

"...
The result of the embedded expression is formatted as follows by default:
- If the embedded expression has a numeric data type, it is transformed to the format specified by the formatting options ...
- If the embedded expression has a character-like data type, its content is copied unchanged. Here, the following applies: in data objects of type c, trailing blanks are cut off; in data objects of the other character-like types (n, d, t, string), trailing blanks are preserved.
..."

Hmm, I keep converging on this. Actually, you know what? I remember the exact sentence now from the German original: "Bei Datenobjekten vom Typ c werden abschließende Leerzeichen abgeschnitten, bei anderen zeichenartigen Datentypen (n, d, t, string) werden sie bewahrt." Hmm, no, I might be confabulating.

Let me try to verify with a different well-known fact: `|{ 'A' }{ 'B' }|` = 'AB', trivial. `DATA lv TYPE c LENGTH 3. lv = 'X'. DATA(s) = |{ lv }|.` Is s = 'X  ' or 'X'? 

I recall from Horst Keller's blogs on string templates... In "ABAP News for Release 7.40 – String Templates" or similar... hmm.

Alternative approach: avoid the issue entirely! I can note that CONCATENATE removes trailing blanks, and to be 100% behavior-identical, one could use `|{ ls-matnr } - { ls-matkl }|` and mention that for c-type fields trailing blanks are handled the same way (cut). Or sidestep: since MATNR/MATKL are CHAR, and CONCATENATE cuts trailing blanks, and (per my belief) string templates also cut trailing blanks for c-type, the template is equivalent.

Hmm, hold on, actually now I want to double check by recalling the behavior of `WRITE ... TO` and string: Not relevant.

Let me recall the actual doc one more time. ABAP Keyword Documentation → ABAP Strings → String Templates → embedded_expressions:

"Embedded expressions
Within a string template, ... { expr ... } ...
The content of an embedded expression is formatted ... The formatting is influenced by formatting options ...
...
Default formatting rules:
...
Character-like types
For c, the trailing blanks are cut off. For n, d, t, and string, the trailing blanks are preserved. ..."

I'm going to commit to this: type c → trailing blanks cut. This is also consistent with what I remember from practice: `|{ lv_char }|` where lv_char is CHAR with trailing spaces gives trimmed result... 

Hmm, actually, wait! Now I have a counter-memory: I remember that `|{ lv_char }|` does NOT trim, and that's why people write `|{ lv_char } |`... no, that's about adding a space...

And I remember the famous gotcha: "String templates remove trailing blanks of character-like fields — different from WRITE TO." Hmm, WRITE TO pads. 

OK here's yet another angle: the ABAP Unit test in open-abap or abapGit... not helpful.

Decision: I'll go with "type c: trailing blanks cut off in string templates" — this matches CONCATENATE's behavior, making the modernization behavior-preserving. I'm fairly confident this is correct per ABAP docs. Actually, let me also recall: this is documented in "Conversion Rules" for string templates? The embedded expression result is converted to string; the conversion rule c → string: "trailing blanks are cut off"? Hmm, for plain assignment c → string, trailing blanks are PRESERVED (I'm quite sure: `DATA(s) = lv_c` keeps trailing blanks? Hmm, no wait!).

Ugh, c → string assignment: `DATA lv_c TYPE c LENGTH 10 VALUE 'AB'. DATA lv_s TYPE string. lv_s = lv_c.` Is lv_s 'AB        ' (10 chars) or 'AB'? 

I believe: c → string preserves trailing blanks. Reason: The conversion rules say "When converting from c to string, the content is passed unchanged" — and length of string = length of c. Hmm, but actually I recall that c→string KEEPS trailing blanks, and string→c truncates at target length. Yes, I'm fairly confident: assigning CHAR10 'AB' to string gives 'AB        '. This is why `CONDENSE` exists... no, CONDENSE is for removing leading/multiple spaces...

Hmm, but wait, that conflicts: if c→string preserves blanks in assignment, does the string template also preserve? The template doc specifically says type c → cut. These are different operations (formatting vs conversion), so both can be true.

Hmm, hmm. Let me look for a definitive memory of the string template rule... 

I recall Horst Keller's comment on SCN: "Note that embedded expressions of type c are trimmed (trailing blanks cut), whereas string expressions keep them." 

Also I recall the ABAP doc note in "string templates": "Unlike in the conversion of c to string in assignments, trailing blanks are cut off in embedded expressions of type c." Something like that. 

OK going with it. And honestly, for the answer, I can add a brief note that the template matches CONCATENATE's trimming behavior. Actually, better: I'll just present the code and optionally a short remark. Since the user asked in German, answer in German.

4. **APPEND + LOOP** → Replace with VALUE ... FOR:

```abap
DATA(lt_out) = VALUE string_table(
                 FOR ls_mara IN lt_mara
                 ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).
```

Note: `string_table` is a built-in type? There's the predefined type `string_table` in ABAP (table of strings) — yes, `string_table` is a built-in ABAP type (table of string with default key). So `VALUE string_table( ... )` works. Alternatively `VALUE stringtab`? The classic type is `string_table` — yes, it's defined in the ABAP type group? Actually, `string_table` is a predefined data type in ABAP Dictionary? Hmm: There are predefined table types like `string_table` (STANDARD TABLE OF string with default key) available in ABAP since... I believe `string_table` is available as a built-in DDIC type. Yes, `string_table` exists in DDIC (SE11) as table type of string. It's commonly used. Safe.

Alternatively, to be fully self-contained: `DATA lt_out TYPE STANDARD TABLE OF string.` then `lt_out = VALUE #( FOR ... ).` But with inline declaration: `DATA(lt_out) = VALUE string_table( ... )` — the VALUE constructor needs a type; `#` can't infer from FOR lines alone? Actually `DATA(lt_out) = VALUE #( FOR ... )` — the # would need to infer the type from context; in a DATA(...) declaration, the type can be derived from the constructor body? For VALUE #( FOR ls IN lt_mara ( ... ) ) — the row type would be inferred from the line expressions (string), and the table kind default STANDARD with default key. I believe `DATA(lt_out) = VALUE #( FOR line IN lt_mara ( |...| ) )` actually works in newer releases (the type inference derives from the constructor expressions). Hmm, is that true? Type inference for `#` in VALUE with FOR: The documentation says the operand type for VALUE #(...) must be derivable. In `DATA(var) = VALUE #( ... )`, the type is inferred from the constructor expression content — I believe this works for tables: the row type is inferred from the first line? Actually, I recall that `DATA(itab) = VALUE #( ( 1 ) ( 2 ) )` works and gives a table of i. Yes, I'm fairly confident that works. But to be safe and explicit, using `string_table` is cleaner and unambiguous. I'll use `string_table`.

Also note: the original declares lt_out as STANDARD TABLE OF string — string_table matches (standard table of string). Good.

The FOR expression: `FOR ls_mara IN lt_mara ( |...| )` — note that inside VALUE...FOR, `ls_mara` is a new inline-declared variable (local to the expression). Since we also want to avoid the standalone ls_mara declaration, this is fine. But careful: if we use inline declaration in LOOP for ls_mara AND also in FOR, no conflict since the loop is replaced.

But wait — the READ TABLE at the end uses ls_mara. If we remove the standalone ls_mara declaration and don't have the LOOP anymore, we can use a table expression:

```abap
IF line_exists( lt_mara[ 1 ] ).
  DATA(ls_first) = lt_mara[ 1 ].
  WRITE / ls_first-matnr.
ENDIF.
```

Or more elegantly:

```abap
TRY.
    WRITE / lt_mara[ 1 ]-matnr.
  CATCH cx_sy_itab_line_not_found.
ENDTRY.
```

Hmm, but that changes behavior subtly? READ TABLE ... INDEX 1 with sy-subrc check: if table is empty, no WRITE. Table expression lt_mara[ 1 ] on empty table raises exception. Using TRY/CATCH preserves behavior (no WRITE when empty) but adds exception handling. The cleaner idiomatic modern equivalent:

```abap
IF line_exists( lt_mara[ 1 ] ).
  WRITE / lt_mara[ 1 ]-matnr.
ENDIF.
```

Hmm, but that reads the line twice (line_exists + indexing). Behavior-wise identical (assuming no concurrent modification). Alternatively:

```abap
DATA(ls_first) = VALUE #( lt_mara[ 1 ] DEFAULT ls_mara ).  -- no, needs a default value
```

Hmm, `lt_mara[ 1 ]` with DEFAULT: `DATA(ls_first) = VALUE #( lt_mara[ 1 ] OPTIONAL )`? OPTIONAL only for... hmm, `VALUE #( lt_mara[ 1 ] OPTIONAL )` — for non-table types, OPTIONAL means: if line not found, the result is initial? Actually for VALUE with table expression: `VALUE dtype( itab[ ... ] OPTIONAL )` returns initial value if line not found instead of raising exception. Wait, is that right? The OPTIONAL/DEFAULT additions in VALUE for table expressions: yes — `VALUE #( lt_mara[ 1 ] OPTIONAL )` gives initial structure if not found. But then we'd need to check if it's initial, which isn't quite the same as "line exists" (a line could be all-initial...). For MARA line, an all-initial line is unlikely but theoretically possible. line_exists is the cleanest semantic match.

Actually, the most idiomatic:

```abap
IF line_exists( lt_mara[ 1 ] ).
  WRITE / lt_mara[ 1 ]-matnr.
ENDIF.
```

Hmm, but double lookup. Alternatively:

```abap
ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls>).  " raises if not found? 
```

ASSIGN with table expression: `ASSIGN lt_mara[ 1 ] TO <fs>` — if not found, sy-subrc = 4 and <fs> unassigned? Yes! ASSIGN with table expressions sets sy-subrc and doesn't dump if line not found (unlike direct read access). So:

```abap
ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).
IF sy-subrc = 0.
  WRITE / <ls_mara>-matnr.
ENDIF.
```

That's a nice modern pattern preserving the sy-subrc check semantics exactly. But it introduces a field symbol instead of a work area — behavior identical.

Which to present? The user asked for "Tabellenausdrücke" (table expressions). I'll show the line_exists + table expression variant, maybe mention the ASSIGN alternative. Actually, simplest faithful translation:

```abap
IF line_exists( lt_mara[ 1 ] ).
  WRITE / lt_mara[ 1 ]-matnr.
ENDIF.
```

Note: `WRITE: / ls_mara-matnr.` → `WRITE / lt_mara[ 1 ]-matnr.` — the colon in WRITE: / just introduces the list; modern style drops the colon for single output. Behavior same (writes matnr on new line).

Hmm, one subtlety: WRITE / writes to the classic list. Fine.

5. **CREATE OBJECT** → `DATA(lo_obj) = NEW zcl_helper( ).`

Note: NEW zcl_helper( ) requires the class to have an instance constructor callable without params (CREATE OBJECT lo_obj also calls default constructor). Same behavior. If zcl_helper has no parameterless constructor issues — CREATE OBJECT lo_obj without TYPE/parameters is equivalent to NEW zcl_helper( ).

Also `DATA lo_obj TYPE REF TO zcl_helper. CREATE OBJECT lo_obj.` → `DATA(lo_obj) = NEW zcl_helper( ).` — inline declaration with NEW. 

6. Also the SELECT: modern could use `@DATA(lt_mara)`. Note: with inline declaration, lt_mara is available for subsequent statements. Good.

One consideration: The original declares all variables at top. Modernized code uses inline declarations at first use. That's the point.

Also, the LOOP with CONCATENATE/APPEND replaced by VALUE/FOR — behavior: original appends one string per line of lt_mara, in order. VALUE...FOR does the same, preserving order. 

Edge case: If lt_mara is empty, original loop appends nothing; VALUE FOR also yields empty table. Same.

Now, about the CONCATENATE equivalence again: CONCATENATE with SEPARATED BY space between three operands: matnr + ' ' + '-' + ' ' + matkl. String template `|{ matnr } - { matkl }|` — the literal ' - ' provides the same separators. With type-c trimming as discussed, identical. If string templates preserved trailing blanks for c, then result would differ when matnr is shorter than 18 chars. Since I believe c-type is trimmed in templates, it's fine. Hmm, but let me reconsider ONE more time because this is the crux of correctness...

ABAP doc, "string_exp - Embedded Expressions": I'm going to reconstruct from the actual doc structure. The doc has sections: "Syntax", "expr", "format_options". Under formatting: "The formatting of the result of the embedded expression is by default dependent on its data type as follows:

- Numeric types ... 
- Character-like types: In the data types c and n, trailing blanks are cut off. In the data types d and t, trailing blanks cannot occur. In the data type string, trailing blanks are preserved. ..."

YES. I'm now confident: "In den Datentypen c und n werden abschließende Leerzeichen abgeschnitten" — this is the documented rule. Great, so `|{ matnr } - { matkl }|` trims matnr/matkl trailing blanks exactly like CONCATENATE. 

Hmm wait, one more check on CONCATENATE: `CONCATENATE a '-' b INTO lv SEPARATED BY space` — SEPARATED BY space inserts the space separator between each pair: a SP '-' SP b. And trailing blanks of a and b are cut (no RESPECTING BLANKS). Also, the '-' literal has no blanks. Result: matnr_trimmed + ' ' + '-' + ' ' + matkl_trimmed. Template: `|{ matnr } - { matkl }|` = matnr_trimmed + ' - ' + matkl_trimmed. Identical. 

But hold on — what about matnr containing internal leading blanks? MATNR is CHAR18, typically left-aligned with trailing blanks (or NUMC-style leading zeros depending on LUW/matnr conversion exit in older systems). CONCATENATE only cuts TRAILING blanks, preserves leading. Template also only cuts trailing. Same. Good.

7. Also modernize: `WHERE mtart = 'FERT'` — could keep as is. In strict mode with @DATA, literals don't need @. Fine.

Now, should I also mention `SELECT ... FIELDS`? Not necessary. Keep it simple and behavior-identical.

Let me also double check `DATA(lt_out) = VALUE string_table( FOR ls_mara IN lt_mara ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).`

Syntax of VALUE with FOR: 
```
VALUE type( [LET ...] FOR ... ( line ) ... )
```
The FOR ... IN itab iterates; each ( ... ) is a row. For a table of strings, each row is a string expression. Correct syntax:

```abap
DATA(lt_out) = VALUE string_table(
                 FOR <fs> IN lt_mara
                 ( |{ <fs>-matnr } - { <fs>-matkl }| ) ).
```

Using an inline field symbol `FOR <fs> IN lt_mara`? Hmm, `FOR ls IN lt_mara` declares a helper variable (work area copy); `FOR <fs> IN lt_mara` would need FIELD-SYMBOL: `FOR <fs> IN lt_mara` — actually the syntax for field symbol in FOR: `FOR <fs> IN itab` is allowed? The FOR variants: `FOR var IN itab [WHERE ...]` and for field symbols you write `FOR <fs> IN itab`? Hmm, I don't think FOR supports field symbols directly in the simple iterator form... Actually it does? Let me recall: "FOR ... IN: FOR var IN itab" — var is a data object. There's also `FOR GROUPS`. For field symbols, I don't believe FOR supports them; you use a helper variable. Hmm, actually I think newer ABAP releases DO allow `FOR <fs> IN itab`? I don't recall that being valid. The documentation: "FOR ... IN itab: declares a helper variable var" — data object, not field symbol. There IS a variant where you can use an existing field symbol? No. Keep it simple: use a helper variable name like `ls_line` or reuse `ls_mara`:

```abap
DATA(lt_out) = VALUE string_table(
                 FOR ls_mara IN lt_mara
                 ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).
```

This declares ls_mara inline within the FOR (scope limited to the expression). That's fine and mirrors the original variable name. 

Hmm, one caveat: if we later also use `ls_mara` elsewhere... we don't (we replaced READ TABLE with table expression). OK.

Alternatively keep the LOOP with inline declaration:

```abap
LOOP AT lt_mara INTO DATA(ls_mara).
  APPEND |{ ls_mara-matnr } - { ls_mara-matkl }| TO lt_out.
ENDLOOP.
```

But the user explicitly asked for FOR expressions, so the VALUE/FOR version is the star. I could show the VALUE/FOR as the main solution. Maybe mention the LOOP alternative briefly? Keep answer focused: show final code, then explain mapping. Maybe mention alternative for the READ TABLE part.

8. `WRITE: / ls_mara-matnr.` → `WRITE / lt_mara[ 1 ]-matnr.` — hmm, but if I use line_exists + then table expression, that's two accesses. Alternatively:

```abap
DATA(ls_first) = VALUE #( lt_mara[ 1 ] OPTIONAL ).  -- hmm
IF ls_first IS NOT INITIAL.
```

No — changes semantics (initial line check). Better:

Option A:
```abap
IF line_exists( lt_mara[ 1 ] ).
  WRITE / lt_mara[ 1 ]-matnr.
ENDIF.
```

Option B (exact sy-subrc semantics):
```abap
ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).
IF sy-subrc = 0.
  WRITE / <ls_mara>-matnr.
ENDIF.
```

Option B is a very faithful translation of READ TABLE INDEX + sy-subrc, using a table expression in ASSIGN. I like Option B for fidelity; Option A for readability. I'll present A as main (idiomatic) and mention B. Or present B as main since it preserves sy-subrc pattern... The user said "ohne das Verhalten zu ändern" — both preserve behavior. I'll go with A in the main code (cleaner, idiomatic modern ABAP) and note B as an alternative that keeps the sy-subrc pattern. Hmm, actually, maybe main code with A, and a short "Varianten" note.

Wait, also consider: `lt_mara[ 1 ]` — index access with table expression; if index 1 exists. line_exists( lt_mara[ 1 ] ) — works with index access too. Yes, line_exists accepts any table expression including INDEX. Good.

9. `DATA lo_obj TYPE REF TO zcl_helper. CREATE OBJECT lo_obj.` → `DATA(lo_obj) = NEW zcl_helper( ).`

10. Full modernized code:

```abap
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.

DATA(lt_out) = VALUE string_table(
                 FOR ls_mara IN lt_mara
                 ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).

IF line_exists( lt_mara[ 1 ] ).
  WRITE / lt_mara[ 1 ]-matnr.
ENDIF.

DATA(lo_obj) = NEW zcl_helper( ).
```

Hmm, clause order check again: `WHERE ... INTO TABLE @DATA(...) UP TO 100 ROWS.` — Is UP TO after INTO valid in strict mode? I said yes based on doc "UP TO can be specified after ORDER BY or after INTO/APPENDING". Let me also recall real-world code: In many SAP standard classes (7.40+), I've definitely seen:

```abap
SELECT * FROM mara
  INTO TABLE @DATA(lt_mara)
  UP TO 1 ROWS
  WHERE matnr = @lv_matnr.
```

Hmm, that has WHERE after UP TO after INTO — I don't think that compiles in strict mode. 

OK let me really nail the clause order. ABAP Keyword Documentation → "SELECT, UP TO n ROWS":

"Syntax
... [ORDER BY ...] [OFFSET o] [UP TO n ROWS] [INTO|APPENDING ...] ...
or
... [INTO|APPENDING ...] [UP TO n ROWS] ..."

Hmm. I recall the doc says: "The addition UP TO n ROWS can be specified after the additions ORDER BY and INTO or APPENDING. In the strict modes ... UP TO n ROWS must be specified after INTO or APPENDING"? 

Honestly, I've seen both forms in SAP's own docs:
- "SELECT ... UP TO 10 ROWS INTO TABLE @DATA(...)" 
- "SELECT ... INTO TABLE @DATA(...) UP TO 10 ROWS"

Both appear. For example, the ABAP doc example for UP TO n ROWS (I recall fairly strongly):

```abap
SELECT *
       FROM sflight
       ORDER BY carrid, connid, fldate DESCENDING
       INTO TABLE @DATA(result)
       UP TO 3 ROWS.
```

Hmm, and for OFFSET:

```abap
SELECT FROM spfli
       FIELDS carrid, connid, cityfrom, cityto
       ORDER BY carrid, connid
       INTO TABLE @DATA(result)
       OFFSET 1 ROWS
       UP TO 3 ROWS.
```

I think OFFSET/UP TO after INTO is the documented strict-mode position. OK, going with INTO then UP TO. And WHERE before INTO. Final SELECT:

```abap
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.
```

This is valid. (Also `SELECT * FROM mara WHERE mtart = 'FERT' INTO TABLE @DATA(lt_mara) UP TO 100 ROWS.` on one line — fine, but formatted multi-line is nicer.)

Hmm, actually one more consideration: in strict mode, is `SELECT *` with `FROM mara` OK, or should it be `SELECT * FROM mara FIELDS *`? `SELECT *` is still valid. Fine.

Also: should the WHERE use a host variable? No, literal stays literal.

11. Additional modernization candidates:
- `string_table` type: predefined? Let me double check: `string_table` is indeed a predefined table type in ABAP Dictionary (SE11, type group? no—DDIC table type STRING_TABLE exists, table of STRING). Yes, STRING_TABLE is a standard DDIC table type delivered by SAP. Commonly used. Safe. Alternatively define inline: `DATA lt_out TYPE STANDARD TABLE OF string.` — but we're using inline declaration with VALUE, so we need a type: `VALUE string_table(...)`. Good.

Hmm, is it `string_table` or `stringtab`? I recall `stringtab`? There's `char80`? Hmm. DDIC types: `string_table` — yes, I'm confident this exists (used widely, e.g., in cl_abap... signatures). Also `stringtab`? I believe `string_table` is the standard one. Let me also consider just using `#`:

`DATA(lt_out) = VALUE #( FOR ls_mara IN lt_mara ( |...| ) ).` — Does # infer here? The type inference for constructor expression in DATA(...) declaration: the # derives the type from the constructor expression itself. For VALUE with FOR and line specifications, the row type is derived from the lines (string), and table category defaults to STANDARD with... hmm, default key? The doc says for # inference: "the type is derived from the constructor expression; for VALUE/REDUCE etc." I believe `DATA(itab) = VALUE #( ( 1 ) ( 2 ) ).` gives STANDARD TABLE OF i with default key. Yes, I'm fairly sure this works (it's in the docs as an example? hmm). To be safe, explicit `string_table` is better — no ambiguity, and it matches the original STANDARD TABLE OF string exactly.

12. Behavior notes to mention:
- CONCATENATE ... SEPARATED BY space ≙ string template with ' - ' (trailing blanks of c-fields are cut in both cases).
- READ TABLE + sy-subrc ≙ line_exists + table expression (or ASSIGN variant).
- CREATE OBJECT ≙ NEW.
- Old header DATA block eliminated via inline declarations.
- The SELECT now uses @ escaping and inline declaration; clause order modernized.

Also, maybe mention that `lv_txt` and `ls_mara` declarations disappear because they're now inline/local (FOR helper variable).

Should I keep `ls_mara` name in FOR? It shadows nothing now. Fine. Or use a more neutral name like `ls_line`/`<line>`. I'll use `ls_mara` to keep it recognizable. Hmm, or `ls_row`. Keep `ls_mara`.

13. One more check on `WRITE / lt_mara[ 1 ]-matnr.` — chaining a table expression result component in WRITE: `WRITE / lt_mara[ 1 ]-matnr` — hmm, is component access after table expression allowed directly in WRITE? Table expressions can be used at operand positions; `lt_mara[ 1 ]-matnr` is a valid "table expression + component chain" usable as an operand. In WRITE, the operand must be a data object — table expression results are usable in reader positions, and WRITE is a reader position. I believe `WRITE lt_mara[ 1 ]-matnr` compiles. Yes, table expressions are allowed in WRITE? Hmm, WRITE is a "writer"? No, WRITE reads the value. The doc says table expressions can be used in "general expression positions" and "reader positions". WRITE's operand is... a "data object" position — I think it qualifies as a reader position? Hmm. Actually, I recall that `WRITE itab[ 1 ]-comp` works. Let me double check mentally: WRITE accepts functional method calls? `WRITE |{ ... }|`? You can WRITE a string template: `WRITE |hello|.` Yes that works. And method calls in WRITE: `WRITE method( )`? I believe functional method calls are allowed in WRITE operands since 7.02? Hmm, not sure. Table expressions... 

To be safe, assign first:

```abap
IF line_exists( lt_mara[ 1 ] ).
  DATA(ls_first) = lt_mara[ 1 ].
  WRITE / ls_first-matnr.
ENDIF.
```

Hmm, but that's an extra helper. Or use the ASSIGN variant which definitely works:

```abap
ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).
IF sy-subrc = 0.
  WRITE / <ls_mara>-matnr.
ENDIF.
```

ASSIGN with table expression: valid since 7.40. sy-subrc = 4 if not found (and <fs> remains unassigned/initial). This is a very faithful modernization of READ TABLE INDEX 1 + sy-subrc check. I'll make this the main solution for that part? Hmm, but field symbols might be considered less "modern-clean" than line_exists. 

Actually, let me reconsider: Is `WRITE / lt_mara[ 1 ]-matnr.` valid? I'm now trying to recall the doc "WRITE, output_options"... The operand of WRITE is "dobj" — data object. Table expressions are allowed in "helper positions"? The doc "table expressions - usage": "Table expressions can be used in: ... general expression positions, ... reader positions ..." and there's a list: e.g., operands of statements like MOVE (assignment), operands of expressions, actual parameters for EXPORTING (not non-optional? no—only for input params), etc. For WRITE: I believe WRITE's operand position is a "reader position"? Hmm, the doc lists WRITE as allowing functional methods? I recall `WRITE / method( )` is NOT allowed historically (WRITE requires data object), but string templates are allowed... Actually no: `WRITE |...|` works, and string templates are expressions. Hmm, so WRITE does accept expressions? I think since 7.40, WRITE accepts... hmm.

Let me recall: ABAP doc "WRITE - output": `WRITE [/][pos][(len)] dobj ...` where dobj is "data object". And there's a note: "Functional methods and built-in functions cannot be specified directly for dobj"? Hmm, I actually recall that you CANNOT write `WRITE method( )` directly — you get an error "functional method not allowed" — and string templates ARE allowed because... hmm, are they? `WRITE |abc|.` — I believe this works. Yes, string templates are allowed in WRITE. And table expressions? I think `WRITE itab[ 1 ]` gives a syntax error? Hmm, I genuinely don't remember.

Safest: use ASSIGN variant or intermediate variable. I'll go with the ASSIGN variant as the primary for the READ TABLE part — it's a textbook modernization of READ TABLE ... INDEX + sy-subrc, definitely valid syntax, and preserves the exact sy-subrc semantics. Then mention the line_exists alternative for readability.

Hmm, wait — but the user explicitly listed "Tabellenausdrücke" (table expressions) as a desired feature. The ASSIGN with table expression IS a table expression usage. Good. And I can also show line_exists variant. Both use table expressions.

Actually, let me reconsider the whole structure. Maybe present the final code, then a mapping table (old → new), then brief notes. The user is German-speaking; answer in German.

Let me also double-check `ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).` — inline FIELD-SYMBOL declaration in ASSIGN: `ASSIGN ... TO FIELD-SYMBOL(<fs>)` — yes, valid since 7.40. If line not found: sy-subrc = 4, and the field symbol keeps its previous state (unassigned here). Then IF sy-subrc = 0 guards the WRITE. Behavior identical to READ TABLE + sy-subrc. 

But hmm — one subtle difference: READ TABLE ... INTO ls_mara copies the line into a work area; ASSIGN gives a reference to the table line. Behavior-wise for just reading matnr and writing it, identical. Fine.

Alternatively, the cleanest "modern" version many would write:

```abap
IF line_exists( lt_mara[ 1 ] ).
  WRITE / lt_mara[ 1 ]-matnr.
ENDIF.
```

I'll offer both, with one in the main code. Which one in main? I'll put the ASSIGN version in main code (exact sy-subrc semantics, guaranteed-valid syntax), and mention line_exists as alternative. Hmm, but honestly line_exists + double access is very common and works. The WRITE with table expression concern... let me settle it: I'm fairly sure `WRITE lt_mara[ 1 ]-matnr` is NOT allowed? Or IS allowed? 

Thinking about the ABAP grammar: WRITE's dobj position — the doc for table expressions says they can be used in "Lesepositionen" (reader positions) and lists examples: assignments (lhs? no—rhs), operands of arithmetic/logical expressions, actual parameters for EXPORTING/CHANGING (input), etc. WRITE is not typically listed. I recall a rule: "Table expressions cannot be used in positions where only data objects are allowed, e.g., WRITE"? Hmm no...

Actually, I remember: `WRITE itab[ 1 ]-comp.` — I believe this DOES work because WRITE allows... hmm. Let me think of cl_abap behavior... In code pal / ABAP cleaner examples... 

I'll just avoid the risk: main code uses ASSIGN (definitely fine) or intermediate DATA. Let me go with:

```abap
" Erste Zeile lesen (früher: READ TABLE ... INDEX 1 + sy-subrc)
ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).
IF sy-subrc = 0.
  WRITE / <ls_mara>-matnr.
ENDIF.
```

Hmm, but actually, hmm, one more subtlety with ASSIGN + table expression: if the line is not found, does ASSIGN raise an exception or set sy-subrc? For ASSIGN with table expression: "If the line is not found, sy-subrc is set to 4 and the field symbol is not assigned" — no exception. Wait, is that true? I recall: `ASSIGN itab[ index ] TO <fs>` — for index access not found: sy-subrc = 4, no dump. For key access not found: also sy-subrc = 4. Yes, ASSIGN with table expressions does NOT dump; it sets sy-subrc. That's documented ("If the specified line is not found, sy-subrc is set to 4 and no assignment takes place"). Hmm wait, but there's a caveat: if the table expression has a component chain (itab[1]-comp) and the line is found but... not relevant. Also for ASSIGN of table expression with key: sy-subrc 4. Yes.

Hmm, actually hold on, I want to double-check: I recall that ASSIGN itab[ ... ] sets sy-subrc = 0 if found, 4 if not found — yes, this is documented and well-known (it's the recommended pattern to avoid the CX_SY_ITAB_LINE_NOT_FOUND exception). Good.

So the ASSIGN variant is safe and faithful. 

Alternatively, even simpler and very common:

```abap
IF line_exists( lt_mara[ 1 ] ).
  DATA(ls_first) = lt_mara[ 1 ].
  WRITE / ls_first-matnr.
ENDIF.
```

I'll show ASSIGN as main (keeps sy-subrc structure) and mention line_exists alternative. Or vice versa. Decision: main = line_exists version? The user asked "ohne das Verhalten zu ändern" — both fine. I think I'll present the ASSIGN version in the main code because it's the most literal modernization (READ TABLE + sy-subrc → ASSIGN + sy-subrc), and then note the line_exists alternative. Hmm, but ASSIGN + field symbol is arguably less "modern idiom" than line_exists... 

You know what, I'll present the main code with line_exists + table expression in WRITE... no, the WRITE concern. OK: main code:

```abap
IF line_exists( lt_mara[ 1 ] ).
  DATA(ls_first) = lt_mara[ 1 ].
  WRITE / ls_first-matnr.
ENDIF.
```

Hmm, this declares ls_first inside IF — fine with inline declaration. But double table access. Meh.

Let me just go with ASSIGN as the main and line_exists as the noted alternative. Actually — wait. Let me reconsider whether `WRITE / lt_mara[ 1 ]-matnr` compiles, because if it does, the cleanest main code is:

```abap
IF line_exists( lt_mara[ 1 ] ).
  WRITE / lt_mara[ 1 ]-matnr.
ENDIF.
```

Searching memory: ABAP doc "Positions of table expressions" (Verwendungsstellen von Tabellenausdrücken): lists "reader positions" including: rhs of assignments, operands of expressions, actual parameters for exporting/changing/returning, WHEN in CASE? etc. And explicitly: "Not allowed: ... positions in which only data objects are allowed, such as ... WRITE"? Hmm, I have a vague feeling the doc mentions that table expressions CAN be used in WRITE? No...

I recall the doc statement: "Table expressions can be used in all reading positions in which a functional method call can be used" — hmm, is that the rule? If so: can functional method calls be used in WRITE? I believe NO for WRITE (WRITE requires a data object; method calls not allowed). Hmm, but string templates ARE allowed in WRITE... string template is not a method call though.

Given uncertainty, avoid WRITE with table expression. Final decision: main code uses ASSIGN variant. It's clean, modern, faithful. Then a note: "Alternativ (lesbarer): IF line_exists( lt_mara[ 1 ] ). ... ENDIF — hier muss man die Zeile dann ggf. nochmal lesen oder einer Variablen zuweisen."

Hmm, hmm. Actually, let me reconsider once more. Many modernization examples would do:

```abap
DATA(ls_mara) = VALUE #( lt_mara[ 1 ] OPTIONAL ).
IF ls_mara IS NOT INITIAL.
  WRITE / ls_mara-matnr.
ENDIF.
```

No — semantics differ (initial check). Skip.

OK here's my final main code:

```abap
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.

DATA(lt_out) = VALUE string_table(
                 FOR ls_mara IN lt_mara
                 ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).

ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).
IF sy-subrc = 0.
  WRITE / <ls_mara>-matnr.
ENDIF.

DATA(lo_obj) = NEW zcl_helper( ).
```

Wait — clause order in SELECT: `WHERE ... INTO TABLE ... UP TO ...`. Let me make a final call. I'm going to check against the ABAP documentation grammar one final time by reconstructing from the "SELECT list" doc:

The SELECT statement main variants (from ABAP docs, "SELECT"):

```
SELECT [DISTINCT] { select_list | ... }
      FROM data_source
      [itab]?
      [WHERE sql_cond]
      [GROUP BY ...]
      [HAVING ...]
      [ORDER BY ...]
      [OFFSET o] [UP TO n ROWS]?
      INTO|APPENDING ...
```

vs the doc for "SELECT, INTO clause": "The INTO clause must be the last clause of the SELECT statement" (in strict mode). If UP TO comes before INTO, then INTO is last. That's consistent! So strict mode order: SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, UP TO, OFFSET?, INTO. Hmm, but then what about the common pattern `INTO TABLE @DATA(x) UP TO 5 ROWS`? If INTO must be last, that pattern would be invalid... but I'm SURE I've seen it in SAP docs. 

Hmm, let me recall a specific official example... ABAP doc "SELECT, UP TO n ROWS" example (from the 7.5x docs):

```abap
SELECT carrid, connid, cityfrom, cityto
       FROM spfli
       ORDER BY carrid, connid
       INTO TABLE @DATA(result)
       UP TO 10 ROWS.
```

I'm now ~90% sure this exact example exists in the docs with UP TO after INTO TABLE @DATA. Also the OFFSET doc example:

```abap
SELECT FROM scarr
       FIELDS carrid, carrname
       ORDER BY carrid
       INTO TABLE @DATA(itab)
       OFFSET 1 ROWS
       UP TO 3 ROWS.
```

Hmm OK. So both INTO-then-UPTO appears in docs. And WHERE-then-INTO appears in docs. So `WHERE ... INTO TABLE @DATA(...) UP TO 100 ROWS` should be valid. 

Actually, now I remember the precise rule from the ABAP docs (SELECT, INTO): "In the strict modes of the syntax check from Release 7.40, SP08, the INTO clause must be specified as the last clause of the SELECT statement, following all other clauses. The additions UP TO n ROWS and OFFSET can be specified after the INTO clause." Hmm, something like that — i.e., INTO last except UP TO/OFFSET may follow. That reconciles everything: UP TO/OFFSET are allowed after INTO. 

So my SELECT is fine:

```abap
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.
```

Alternatively I could write `UP TO 100 ROWS` before INTO — also fine. I'll keep after INTO (matches original order).

14. Should I also modernize the WHERE to use a constant? No, keep literal.

15. Also: `SELECT *` — in modern SQL, some prefer explicit field list, but behavior must stay identical, so keep *.

16. Anything about `WRITE: /` → `WRITE /`? The colon is just the chained-statement marker; with one operand, drop it. Same behavior.

17. Also mention: the old code declared `ls_mara`, `lv_txt`, `lt_out`, `lt_mara`, `lo_obj` up front; now all inline. `lv_txt` disappears entirely (string template used directly in the FOR row).

Now, let me also think: does the user want me to keep the LOOP version but modernized (LOOP AT ... INTO DATA(...), APPEND with template)? They explicitly asked for FOR expressions, so the VALUE/FOR replacement is expected. I might briefly note the alternative "if you want to keep the loop":

```abap
LOOP AT lt_mara INTO DATA(ls_line).
  APPEND |{ ls_line-matnr } - { ls_line-matkl }| TO lt_out.
ENDLOOP.
```

But that requires lt_out declared separately. The FOR version is better. I'll mention it only briefly or not at all. Keep answer tight.

18. Format of answer: German. Provide:
- The modernized code (complete, copy-pasteable).
- A short mapping/explanation of each change (bulleted).
- Maybe 1-2 notes on subtleties (trailing blanks equivalence; ASSIGN vs line_exists alternative).

Length: medium. Code block with the final code. Then concise bullet list explaining transformations. Maybe a small "Alternativen/Hinweise" section.

Let me write the final code carefully:

```abap
" Datenbeschaffung – früher: DATA + SELECT INTO TABLE
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.

" LOOP + CONCATENATE + APPEND  ->  VALUE + FOR + String-Template
DATA(lt_out) = VALUE string_table(
                 FOR ls_mara IN lt_mara
                 ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).

" READ TABLE INDEX 1 + sy-subrc  ->  Tabellenausdruck
ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).
IF sy-subrc = 0.
  WRITE / <ls_mara>-matnr.
ENDIF.

" CREATE OBJECT  ->  NEW
DATA(lo_obj) = NEW zcl_helper( ).
```

Check every statement:

- SELECT: `SELECT * FROM mara WHERE mtart = 'FERT' INTO TABLE @DATA(lt_mara) UP TO 100 ROWS.` — valid modern Open SQL (strict mode OK: literal without @; INTO near-last; UP TO after INTO). ✓

- VALUE string_table( FOR ls_mara IN lt_mara ( |...| ) ): valid. The FOR helper `ls_mara` is implicitly declared (data object of line type). ✓ Note: inside the template, `ls_mara-matnr` — accessing components of the FOR variable: valid. ✓

- ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>). — valid; sy-subrc semantics as READ TABLE INDEX. ✓

- WRITE / <ls_mara>-matnr. ✓

- DATA(lo_obj) = NEW zcl_helper( ). ✓ — NEW with inline declaration; parentheses for constructor. ✓

Behavior equivalence notes:
- Same select (100 rows, mtart FERT).
- lt_out content identical: CONCATENATE cuts trailing blanks of c-fields; string templates do the same for type c. Separator: space around '-' in both.
- Order preserved by FOR.
- Empty table: VALUE/FOR yields empty; ASSIGN sets sy-subrc 4 → no WRITE. Same as before.
- lo_obj created with default constructor, same as CREATE OBJECT.

One more consideration: `string_table` — if the system doesn't have it (it's a DDIC type delivered by SAP; available in all modern systems), fine. Could also write `VALUE #( ... )` — I'll keep string_table.

Also, should the FOR variable be named differently to avoid confusion with the old ls_mara? It's fine.

Alternative for the READ part to mention:

```abap
IF line_exists( lt_mara[ 1 ] ).
  WRITE / lt_mara[ 1 ]-matnr.   " oder erst in Variable lesen
ENDIF.
```

Hmm, if I'm unsure WRITE accepts table expressions, in the alternative I should write it safely:

```abap
IF line_exists( lt_mara[ 1 ] ).
  DATA(ls_first) = lt_mara[ 1 ].
  WRITE / ls_first-matnr.
ENDIF.
```

I'll present it like that, or just mention line_exists without full code. Let me include it as a short alternative snippet.

Also worth noting: `WRITE: /` → `WRITE /` (colon dropped).

Should I explain the @ escaping? Briefly: inline declaration in SELECT requires host-variable escaping with @; literals stay as-is.

Also note on clause order: in modern Open SQL the INTO clause comes at the end.

Now write the explanation concisely in German. Structure:

**Modernisierter Code** (code block)

**Was wurde geändert** (bullets):
1. `DATA`-Kopfblock → Inline-Deklarationen (`DATA(...)`, `FIELD-SYMBOL(<...>)`); `lv_txt` und `ls_mara` entfallen komplett.
2. `SELECT ... INTO TABLE lt_mara UP TO 100 ROWS WHERE ...` → moderne Klausel-Reihenfolge + `@DATA(lt_mara)` (Inline-Deklaration, daher @-Escaping).
3. `LOOP AT ... CONCATENATE ... APPEND` → `VALUE string_table( FOR ... )` mit String-Template `|{ ... } - { ... }|`. Verhalten identisch: CONCATENATE ... SEPARATED BY space erzeugt `MATNR - MATKL`; bei Typ c werden abschließende Leerzeichen sowohl bei CONCATENATE als auch im String-Template abgeschnitten.
4. `READ TABLE ... INDEX 1` + `sy-subrc` → Tabellenausdruck im `ASSIGN`; sy-subrc = 4, wenn Tabelle leer → kein Dump, gleiches Verhalten. Alternative: `line_exists( lt_mara[ 1 ] )`.
5. `CREATE OBJECT` → `NEW zcl_helper( )`.
6. `WRITE: /` → `WRITE /` (Colon bei Einzelanweisung entfällt).

Maybe also mention: if you prefer keeping the loop: `LOOP AT lt_mara INTO DATA(ls_mara). APPEND |...| TO lt_out. ENDLOOP.` — optional. I'll add one line.

Also perhaps note that `string_table` is the standard DDIC table type for `STANDARD TABLE OF string` — matching the original declaration.

Keep it reasonably concise. Use headers and code blocks. German language.

One more syntax double-check on the VALUE/FOR with a string template line: 

```abap
DATA(lt_out) = VALUE string_table(
                 FOR ls_mara IN lt_mara
                 ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).
```

The row specification `( expr )` for a table of strings: the parenthesized list contains the value — for a non-structured row type, you put the single expression: `( |...| )`. Valid. ✓

Also: could use `FOR ls_mara IN lt_mara WHERE ...` — not needed.

Also, indentation inside the constructor: fine.

Double-check NEW: `DATA(lo_obj) = NEW zcl_helper( ).` — NEW zcl_helper( ) creates instance calling instance constructor with no params. Equivalent to CREATE OBJECT lo_obj. ✓ (If zcl_helper's constructor had required params, the original would also fail/dump — CREATE OBJECT without EXPORTING requires optional params too. So equivalent.)

Also, one subtle thing: the original `DATA lo_obj TYPE REF TO zcl_helper. CREATE OBJECT lo_obj.` — with NEW + inline declaration, identical.

Now about the SELECT: should I add `ORDER BY PRIMARY KEY`? No — original had no ORDER BY; adding one would change behavior (row selection with UP TO without ORDER BY is nondeterministic anyway, but we must not add ORDER BY as it changes which rows are returned). Keep as is. Maybe worth a tiny note? Not necessary; could mention that without ORDER BY the 100 rows are arbitrary — but that's true in both versions. Skip or one short note. I'll skip to keep focused. Hmm, actually a one-liner note could be valuable: "Auch im neuen Code gilt: ohne ORDER BY sind die 100 Sätze nicht deterministisch – wie bisher." Maybe include briefly. Eh, optional. I'll add it as a small note since it shows care about behavior. Actually the instruction is "ohne das Verhalten zu ändern" — I preserved it. A short remark is fine but not needed. I'll leave it out to avoid bloat. Hmm, or include — it's a genuinely useful hint. I'll add one short line in the notes.

Let me also double check `line_exists( lt_mara[ 1 ] )` — valid with index access. ✓

Also the ASSIGN: after `ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).` — if table empty, sy-subrc = 4, <ls_mara> unassigned. Then IF guards. ✓. Note: in strict mode, is `ASSIGN itab[...] TO FIELD-SYMBOL(<fs>)` with sy-subrc check OK? Yes.

Alternatively `IF sy-subrc = 0` — fine.

Now write the answer. German. Include:

1. Short intro sentence (one line).
2. Code block with modernized code (with brief German comments).
3. Bullet list "Die einzelnen Umstellungen" mapping old→new.
4. Short "Hinweise" (2-3 bullets): trailing-blank equivalence; ASSIGN alternative line_exists; string_table type; optional note on ORDER BY determinism.

Keep it tight. Format: markdown with code blocks. The code comments in German.

Final code (with comments):

```abap
" SELECT mit Inline-Deklaration (@-Escaping, INTO-Klausel am Ende)
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.

" LOOP + CONCATENATE + APPEND  ->  VALUE mit FOR und String-Template
DATA(lt_out) = VALUE string_table(
                 FOR ls_mara IN lt_mara
                 ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).

" READ TABLE ... INDEX 1 + sy-subrc  ->  Tabellenausdruck
ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(<ls_mara>).
IF sy-subrc = 0.
  WRITE / <ls_mara>-matnr.
ENDIF.

" CREATE OBJECT  ->  NEW
DATA(lo_obj) = NEW zcl_helper( ).
```

Explanation bullets:

- **Deklarationen:** Der komplette `DATA`-Block entfällt; alle Variablen werden inline an ihrem ersten Verwendungsort deklariert (`DATA(...)`, `FIELD-SYMBOL(<...>)`). `lv_txt` und `ls_mara` als eigene Variablen braucht es nicht mehr.
- **SELECT:** Moderne Klauselreihenfolge (`WHERE` vor `INTO`), Inline-Deklaration `@DATA(lt_mara)` — dadurch gilt der Strict Mode, deshalb `@`-Escaping. `UP TO 100 ROWS` wie gehabt.
- **Schleife:** `LOOP AT ... CONCATENATE ... APPEND` wird zum funktionalen `VALUE string_table( FOR ... )`. Das String-Template `|{ matnr } - { matkl }|` ist äquivalent zu `CONCATENATE ... SEPARATED BY space` (bei Typ `c` werden abschließende Leerzeichen in beiden Fällen abgeschnitten). Reihenfolge und Ergebnis identisch; bei leerer Tabelle bleibt `lt_out` leer.
- **READ TABLE:** Der Tabellenausdruck `lt_mara[ 1 ]` im `ASSIGN` setzt wie `READ TABLE` `sy-subrc = 4`, wenn die Tabelle leer ist → kein Dump, kein WRITE. Alternativ lesbarer: `IF line_exists( lt_mara[ 1 ] )`.
- **Objekterzeugung:** `CREATE OBJECT lo_obj` → `DATA(lo_obj) = NEW zcl_helper( ).` (ruft denselben parameterlosen Konstruktor).
- **WRITE:** Der Doppelpunkt bei `WRITE: /` entfällt bei einer einzelnen Ausgabe.

Notes:
- `string_table` ist der Standard-Tabellentyp für `STANDARD TABLE OF string` — entspricht exakt der alten Deklaration.
- Falls du die Schleife behalten willst: `LOOP AT lt_mara INTO DATA(ls_mara). APPEND |...| TO lt_out. ENDLOOP.` — aber VALUE/FOR ist der moderne Weg.
- Hinweis: wie im Original sind die 100 Sätze ohne `ORDER BY` nicht deterministisch (unchanged behavior).

Maybe fold the last note in. Keep 2-3 short notes.

I think this is a solid answer. Length: moderate. Use German throughout. Headers: maybe "Modernisierter Code" and "Was wurde geändert". Use a table for mapping? A table old→new could be nice and compact:

| Alt | Neu |
|---|---|
| `DATA: lt_mara ...` | `@DATA(lt_mara)` im SELECT |
| `LOOP AT ... CONCATENATE ... APPEND` | `VALUE string_table( FOR ... )` + String-Template |
| `READ TABLE ... INDEX 1` + `sy-subrc` | `ASSIGN lt_mara[ 1 ] TO FIELD-SYMBOL(...)` bzw. `line_exists( )` |
| `CREATE OBJECT lo_obj` | `NEW zcl_helper( )` |

A table plus bullets might be redundant. I'll do bullets with bold lead-ins, or a compact table. I think a short table is nice for scanning, then 2-3 subtlety notes. Let me do: code block → table of transformations → "Feinheiten" bullets (trailing blanks, sy-subrc/line_exists, string_table). That's clean.

Actually, combining: after code, a section "Die Umstellungen im Einzelnen" with bullets (each bullet: old → new + one-line why). Then "Verhaltensrelevante Feinheiten" with 2 bullets. Good.

Write it now.

</details>
