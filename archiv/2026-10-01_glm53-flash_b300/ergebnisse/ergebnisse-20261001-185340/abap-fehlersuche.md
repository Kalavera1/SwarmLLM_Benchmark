# ABAP: fehlersuche

## Aufgabe

Finde alle Fehler und Performance-Probleme in diesem ABAP-Code und gib eine korrigierte Fassung:

DATA: lt_vbap TYPE TABLE OF vbap, ls_vbap TYPE vbap, lv_sum TYPE p DECIMALS 2.
SELECT * FROM vbak INTO TABLE @DATA(lt_vbak) WHERE erdat = sy-datum.
LOOP AT lt_vbak INTO DATA(ls_vbak).
  SELECT * FROM vbap INTO ls_vbap WHERE vbeln = ls_vbak-vbeln.
    lv_sum = lv_sum + ls_vbap-netwr.
    APPEND ls_vbap TO lt_vbap.
  ENDSELECT.
ENDLOOP.
READ TABLE lt_vbap INTO ls_vbap WITH KEY matnr = 'XYZ'.
IF sy-subrc = 0.
  WRITE: / 'gefunden', ls_vbap-vbeln.
ENDIF.
COMMIT WORK.

## Antwort



---

<details><summary>Denkprozess (30305 Zeichen)</summary>

Let me analyze this ABAP code for errors and performance issues.

The code:
```abap
DATA: lt_vbap TYPE TABLE OF vbap, ls_vbap TYPE vbap, lv_sum TYPE p DECIMALS 2.
SELECT * FROM vbak INTO TABLE @DATA(lt_vbak) WHERE erdat = sy-datum.
LOOP AT lt_vbak INTO DATA(ls_vbak).
  SELECT * FROM vbap INTO ls_vbap WHERE vbeln = ls_vbak-vbeln.
    lv_sum = lv_sum + ls_vbap-netwr.
    APPEND ls_vbap TO lt_vbap.
  ENDSELECT.
ENDLOOP.
READ TABLE lt_vbap INTO ls_vbap WITH KEY matnr = 'XYZ'.
IF sy-subrc = 0.
  WRITE: / 'gefunden', ls_vbap-vbeln.
ENDIF.
COMMIT WORK.
```

Errors and performance issues:

1. **N+1 Select problem (SELECT inside LOOP)**: The SELECT ... ENDSELECT inside the LOOP AT lt_vbak is a classic performance killer. For each row in lt_vbak, a separate database query is executed. This should be replaced with a single SELECT with FOR ALL ENTRIES or a JOIN.

2. **SELECT * usage**: Selecting all fields when only VBELN, NETWR, MATNR are needed. Should select only needed fields.

3. **SELECT ... ENDSELECT with APPEND inside**: This is very inefficient - row-by-row processing. Better: SELECT ... INTO TABLE.

4. **Missing ORDER BY / PRIMARY KEY**: SELECT * FROM vbap WHERE vbeln = ... - actually vbeln is the key of vbap (partially - VBAP key is VBELN POSNR), so this uses the index. But still the N+1 issue.

5. **READ TABLE with linear search**: `READ TABLE lt_vbap INTO ls_vbap WITH KEY matnr = 'XYZ'` does a linear search on a potentially huge table. Should use a sorted/hashed table or BINARY SEARCH (though BINARY SEARCH requires sorted table). Better: define lt_vbap as SORTED TABLE or use a HASHED table, or sort before reading.

6. **COMMIT WORK without any changes**: There's no database modification, so COMMIT WORK is pointless. Also, in many contexts (e.g., during SELECT processing), COMMIT WORK is not allowed. It's simply unnecessary here.

7. **lv_sum not reset**: If this code is in a subroutine/Form that's called multiple times, lv_sum retains its value. Should initialize with CLEAR. Also, lv_sum is computed but never used/output - dead code (or at least the sum is calculated but not used).

8. **Missing sy-subrc check after first SELECT**: If no orders exist for today, the loop does nothing - not an error per se, but good practice to check.

9. **Old vs new syntax mixing**: Mixing old syntax (SELECT ... INTO TABLE with host variables without @) - actually wait: `SELECT * FROM vbak INTO TABLE @DATA(lt_vbak) WHERE erdat = sy-datum.` - the INTO TABLE @DATA(lt_vbak) is new syntax, but then `WHERE erdat = sy-datum` without escaping @sy-datum is inconsistent. In new open SQL (ABAP 7.40+), host variables must be escaped with @. So `WHERE erdat = @sy-datum`. Mixing: The first SELECT uses @DATA(...) which requires new syntax, so the WHERE clause must use @sy-datum. This is actually a syntax error in strict mode! When using new Open SQL features, the strict mode is activated and all host variables must be escaped with @. So `WHERE erdat = sy-datum` would cause a syntax error.

Wait, let me think. In the first SELECT: `SELECT * FROM vbak INTO TABLE @DATA(lt_vbak) WHERE erdat = sy-datum.` - using @DATA(lt_vbak) triggers strict mode from 7.40, so host variables in the WHERE clause must have @. So `WHERE erdat = @sy-datum` is required. This is a syntax error.

The second SELECT: `SELECT * FROM vbap INTO ls_vbap WHERE vbeln = ls_vbak-vbeln.` - this is old syntax (INTO ls_vbap without @), and ls_vbak-vbeln without @. If we keep old syntax entirely for this statement, it's fine as long as strict mode isn't triggered. Old syntax SELECT ... INTO ls_vbap ... ENDSELECT is still allowed (obsolete but allowed). But mixing in the same program is allowed as long as each statement is consistent.

Actually, in the loop, `LOOP AT lt_vbak INTO DATA(ls_vbak)` - DATA(ls_vbak) inline declaration works in LOOP AT since 7.40. That's fine.

But the second SELECT uses old-style INTO with a work area and ENDSELECT - allowed but obsolete.

10. **SELECT * FROM vbap INTO ls_vbap WHERE vbeln = ...**: Since VBAP's primary key is VBELN + POSNR, selecting with WHERE vbeln = ... will use the primary index. OK. But the row-by-row processing with ENDSELECT plus APPEND is inefficient.

11. **Potential duplicate data / memory**: Selecting all VBAP rows into memory could be huge. Also duplicates: if multiple VBAK entries... no, each VBELN is unique in VBAK, so no duplicates in lt_vbap.

12. **READ TABLE ... WITH KEY matnr = 'XYZ'**: matnr is CHAR18/CHAR40 depending on version; 'XYZ' may need conversion routine (leading zeros? MATNR typically has leading zeros for numeric material numbers, e.g., '000000000000000XYZ'?). Actually 'XYZ' is alphanumeric, but MATNR is typically 18 chars with leading zeros for numeric ones. Using a literal 'XYZ' without conversion exit could fail to match. Best practice: use a variable with conversion routine or use MATCH CODE. This is a subtle correctness issue - I can mention it.

13. **COMMIT WORK**: Not needed; no DB changes. Also, COMMIT WORK inside a SELECT...ENDSELECT loop is forbidden, but here it's after. Still, it's useless and potentially harmful (starts a new LUW, may trigger update tasks). Remove it.

14. **lv_sum overflow/precision**: NETWR is CURR 13,2 (or 15,2?). NETWR is CURR, length 15 (13 digits + 2 decimals?) Actually NETWR is CURR 15, 2 decimals? Let me recall: VBAP-NETWR is CURR, length 15, decimals 2. Packed decimal p with DECIMALS 2 default length... lv_sum TYPE p DECIMALS 2 has default length 8, which can hold up to 13 digits. NETWR has 15 digits? Hmm, VBAP-NETWR: domain NETWR, CURR, length 15, decimal 2. So values up to 13 digits before decimal? Actually length 15 with 2 decimals means 13 integer digits. lv_sum TYPE p DECIMALS 2 default length is 8 bytes = 15 digits? P length 8 = 16 digits? Packed: 2 digits per byte minus 1 for sign. Length 8 → 15 digits. So 15 digits total, minus 2 decimals = 13 integer digits. That matches NETWR's 13+2. But summing many orders could overflow. Better: use lv_sum TYPE vbap-netwr or p LENGTH 15 DECIMALS 2. Minor point. Actually better to compute the sum in the database with SUM( netwr ) GROUP BY or just SUM without GROUP BY.

15. **Better approach**: Use a single JOIN or FOR ALL ENTRIES:

```abap
SELECT vbeln, posnr, matnr, netwr
  FROM vbap
  INTO TABLE @DATA(lt_vbap)
  FOR ALL ENTRIES IN @lt_vbak
  WHERE vbeln = @lt_vbak-vbeln.
```

Or better, a JOIN:

```abap
SELECT a~vbeln, b~posnr, b~matnr, b~netwr
  FROM vbak AS a
  INNER JOIN vbap AS b
    ON b~vbeln = a~vbeln
  WHERE a~erdat = @sy-datum
  INTO TABLE @DATA(lt_result).
```

Even better: compute the sum directly in the DB:

```abap
SELECT SUM( netwr ) FROM vbap ... 
```

But with join: 

```abap
SELECT SUM( b~netwr ) 
  FROM vbak AS a 
  INNER JOIN vbap AS b ON b~vbeln = a~vbeln
  WHERE a~erdat = @sy-datum
  INTO @DATA(lv_sum).
```

16. **FOR ALL ENTRIES pitfalls**: need to check lt_vbak is not empty (otherwise all rows selected), duplicates handled automatically (FAE removes duplicates? Actually FAE with duplicates in the driver table - the rows are deduplicated in the result set comparison... no: FOR ALL ENTRIES implicitly removes duplicate rows from the result if the selected columns are identical? Actually, FOR ALL ENTRIES eliminates duplicates from the internal table used, and the result set... The SELECT with FOR ALL ENTRIES removes duplicate rows from the result set automatically? Yes - "duplicate rows are removed from the results set" unless the addition ... hmm. Actually: "If FOR ALL ENTRIES is used, all duplicate rows are removed from the result set by default" - no wait, that's only if you select all columns? Let me recall: With FOR ALL ENTRIES, duplicates in the result set are automatically deleted (as if DISTINCT was used)? The documentation says: "The result set of the SELECT statement is affected: ... rows that occur more than once are automatically removed" - Actually yes: with FOR ALL ENTRIES, the result set behaves as if DISTINCT were specified, meaning duplicate rows are removed. Hmm, I recall that FOR ALL ENTRIES implicitly removes duplicates from the result. From SAP docs: "If the addition FOR ALL ENTRIES is used, ... duplicate rows are removed from the results set" - yes, that's correct: the result set is implicitly deduplicated (like SELECT DISTINCT). So if you need duplicates (e.g., two VBAP lines with identical values but different POSNR), you must select POSNR too to make rows unique. Since we select posnr, no problem.

Also need to guard: IF lt_vbak IS NOT INITIAL before FAE.

17. **READ TABLE performance**: Use SORTED table or SORT + BINARY SEARCH, or better use a HASHED table with unique key... but matnr is not unique in VBAP. READ TABLE finds first match. Could use sorted table with key matnr (non-unique sorted key) for binary search. Or simply keep standard table and SORT + READ ... BINARY SEARCH. Or in modern ABAP: use a second SELECT with UP TO 1 ROWS, or use value lookup.

18. **The WRITE statement**: Classic list output - obsolete in modern context but not an error.

19. **Missing error handling**: no check of sy-subrc after SELECTs.

20. **lv_sum unused**: computed but never output. Either output it or remove.

21. **SELECT * with INTO ls_vbap in ENDSELECT loop**: also note that SELECT ... ENDSELECT bypasses table buffering? SELECT single record loops... Not important.

22. **Array fetch**: best practice: SELECT INTO TABLE.

23. **COMMIT WORK**: Also, if this runs in UPDATE task or during a SELECT loop it would dump. Here it's just unnecessary.

24. Also `DATA: lt_vbap TYPE TABLE OF vbap` - standard table without keys; READ TABLE linear search.

25. The first SELECT: `WHERE erdat = sy-datum` - ERDAT is DATS; sy-datum is DATS - fine. But performance: VBAK has ERDAT in index? VBAK primary key is VBELN. There's index VBAK~ERD? Not guaranteed. Selecting all orders created today could be large but presumably OK. Could mention index.

26. In new syntax, `SELECT * FROM vbak INTO TABLE @DATA(lt_vbak)` - fine. But mixing old INTO without @ in second select while the first uses new syntax - the program can mix, but per statement consistency matters. The second SELECT statement uses old syntax entirely (INTO ls_vbap, WHERE vbeln = ls_vbak-vbeln without @). Old syntax is still allowed outside strict mode. However, since the first statement triggers strict mode for that statement only. Each statement's syntax is checked per its own mode. So second statement old syntax is OK but obsolete. In the corrected version, use consistent new syntax.

27. Another subtle bug: `lv_sum` accumulates NETWR for all positions of all orders, but NETWR is document currency-dependent; summing across different currencies (waers) is meaningless. Could mention as business-logic caveat. Maybe mention briefly.

28. Also the loop `LOOP AT lt_vbak INTO DATA(ls_vbak)` - inline declaration inside LOOP is fine.

29. The READ TABLE overwrites ls_vbap which was used in loop - fine.

30. Potential issue: `SELECT * FROM vbap INTO ls_vbap WHERE vbeln = ls_vbak-vbeln.` - in old syntax, referencing ls_vbak-vbeln (declared inline earlier) is fine.

Let me also consider: The SELECT inside LOOP uses the same target `ls_vbap` declared globally and the loop variable... no conflict.

31. Missing `IF sy-subrc = 0` after first SELECT to avoid unnecessary FAE on empty table.

Now the corrected version. I'll provide a modern, clean version:

```abap
DATA lv_sum TYPE vbap-netwr.

" Ein einziger DB-Zugriff: Aufträge von heute mit Positionen (JOIN)
SELECT vbeln, posnr, matnr, netwr
  FROM vbak AS h
  INNER JOIN vbap AS p
    ON p~vbeln = h~vbeln
  WHERE h~erdat = @sy-datum
  INTO TABLE @DATA(lt_vbap).

IF sy-subrc = 0.
  " Summe direkt in der DB berechnen (statt im ABAP zu summieren)
  SELECT SINGLE SUM( p~netwr )
    FROM vbak AS h
    INNER JOIN vbap AS p
      ON p~vbeln = h~vbeln
    WHERE h~erdat = @sy-datum
    INTO @lv_sum.
ENDIF.

" Schnellen Zugriff ermöglichen: sortierte Hilfstabelle / BINARY SEARCH
" Variante A: SORT + READ BINARY SEARCH
SORT lt_vbap BY matnr.
READ TABLE lt_vbap INTO DATA(ls_hit) WITH KEY matnr = 'XYZ' BINARY SEARCH.
IF sy-subrc = 0.
  WRITE: / 'gefunden', ls_hit-vbeln.
ENDIF.
```

Hmm, but the sum could also be computed from lt_vbap in ABAP after selecting once - but DB sum is better. Alternatively compute sum in loop over lt_vbap - but then two passes. Simplest: compute sum in DB.

Alternatively, if we want to keep close to original structure with lt_vbak:

```abap
SELECT vbeln FROM vbak WHERE erdat = @sy-datum INTO TABLE @DATA(lt_vbak).
IF lt_vbak IS NOT INITIAL.
  SELECT vbeln, posnr, matnr, netwr
    FROM vbap
    FOR ALL ENTRIES IN @lt_vbak
    WHERE vbeln = @lt_vbak-vbeln
    INTO TABLE @DATA(lt_vbap).
ENDIF.
```

I'll present the JOIN as the primary solution and mention FOR ALL ENTRIES as alternative.

Also mention: matnr literal - use conversion exit: `CONVERT`... Actually for READ with matnr, better to use a variable of type matnr and let the user enter via selection screen (which applies conversion exit). I can note: `'XYZ'` may need leading zeros/alpha conversion; use `|...|` with conversion or a parameter. I'll note it briefly.

Also note that if only the existence of a row with matnr = 'XYZ' is needed, better do a SELECT SINGLE with UP TO 1 ROWS instead of loading everything:

Actually, the original logic: read first VBAP row with matnr 'XYZ' among today's orders. If that's the only purpose, a single SELECT UP TO 1 ROWS with join would be optimal. But the code also sums netwr and fills lt_vbap - though lt_vbap is only used for the READ and lv_sum never used. So the minimal fix: 

Actually let me re-read the original: lt_vbap is filled, lv_sum accumulated but never used, READ TABLE finds first row with matnr XYZ. So the real "business" output is just the found row. The sum is dead code. I should point that out and offer both: corrected faithful version + optimized version.

Let me structure the answer:

**Fehler (bugs):**
1. Syntaxfehler: fehlendes @ vor sy-datum im ersten SELECT (Strict Mode wegen @DATA(...)).
2. COMMIT WORK ohne vorausgegangene Änderung - sinnlos, startet neue LUW, kann in manchen Kontexten Dump verursachen (nicht erlaubt innerhalb SELECT...ENDSELECT - hier zwar außerhalb, aber trotzdem entfernen).
3. lv_sum wird nie zurückgesetzt (CLEAR) - bei Wiederverwendung (z.B. in Form-Routine) falsche Summen. Und lv_sum wird berechnet, aber nie verwendet (toter Code).
4. MATNR-Literal 'XYZ' ohne Conversion-Exit (führende Nullen/ALPHA) - READ findet Datensatz evtl. nicht.
5. Fehlende sy-subrc-Prüfungen.
6. Währungsproblem: Summieren von NETWR über verschiedene WAERS hinweg ist fachlich fragwürdig.

**Performance-Probleme:**
1. SELECT ... ENDSELECT innerhalb LOOP AT = N+1-Selects (klassischer Anti-Pattern). Lösung: JOIN oder FOR ALL ENTRIES.
2. SELECT * - unnötige Felder, Netzwerklast. Nur benötigte Felder selektieren.
3. Zeilenweise APPEND in ENDSELECT-Schleife statt INTO TABLE (Array Fetch).
4. READ TABLE ohne BINARY SEARCH / ohne sortierten Typ = linearer Suchlauf über große Tabelle.
5. Summierung im ABAP statt in der DB (SUM( ) ).
6. Standardtabelle ohne Schlüssel.
7. ggf. fehlender Index auf VBAK-ERDAT (je nach System) - hinweis.

**Korrigierte Fassung** (modern, 7.40+):

```abap
" Nur benötigte Felder, ein einziger DB-Zugriff (JOIN statt N+1)
SELECT h~vbeln,
       p~posnr,
       p~matnr,
       p~netwr
  FROM vbak AS h
  INNER JOIN vbap AS p
    ON p~vbeln = h~vbeln
  WHERE h~erdat = @sy-datum
  INTO TABLE @DATA(lt_pos).

IF sy-subrc <> 0.
  " nichts gefunden -> sauber beenden
  RETURN. " bzw. entsprechende Behandlung
ENDIF.

" Summe direkt in der Datenbank berechnen
SELECT SINGLE SUM( p~netwr )
  FROM vbak AS h
  INNER JOIN vbap AS p
    ON p~vbeln = h~vbeln
  WHERE h~erdat = @sy-datum
  INTO @DATA(lv_sum).

" Schnellen Zugriff auf erste Position mit MATNR = 'XYZ'
" Variante 1: sortierte Tabelle + BINARY SEARCH
SORT lt_pos BY matnr.
READ TABLE lt_pos INTO DATA(ls_pos) WITH KEY matnr = 'XYZ' BINARY SEARCH.
```

Hmm wait - READ TABLE ... WITH KEY ... BINARY SEARCH requires the table sorted by the fields used in the search - sorted by matnr, searching matnr - OK.

But careful: SORT lt_pos BY matnr then READ BINARY SEARCH finds the first row with that matnr? BINARY SEARCH returns the row where the binary search lands, which is *a* row with that key, not necessarily the first one. Actually with BINARY SEARCH, if there are multiple entries, it returns the one found by binary search - which may not be the first. SAP docs: "If several entries are found, the first one in the sorted sequence is returned"? Let me recall: READ TABLE ... BINARY SEARCH - "the row found is the one that the binary search algorithm would find first" - Actually the documentation says: if multiple rows match, which one is returned is not necessarily the first; but in practice, since 7.0? Hmm. The ABAP keyword documentation for READ TABLE: "If the addition BINARY SEARCH is used and several rows match, the row with the lowest index is returned" - I believe modern behavior returns the first matching row (lowest index) - Actually the doc says: "When multiple rows match, READ TABLE returns the first matching row" for standard READ (linear search returns first). For BINARY SEARCH: "the system reads the row for which the binary search finds the lowest index"? Let me think.

From ABAP docs (READ TABLE, itab): "If several rows match, ... sy-tabix is set to the index of the found row..." For binary search: "If there are several rows that match the key, the row with the lowest row index is read in the case of BINARY SEARCH" - Hmm, I recall there's a note: "If several rows are found, the behavior for BINARY SEARCH is: the row with the lowest index is returned, provided the table is sorted correctly." Actually I recall the opposite: binary search may return any of the matching rows and this changed - the documentation states: "If there are multiple hits, READ TABLE ... BINARY SEARCH returns the first hit in the sort order"? 

Let me check my memory of the actual doc: "If the search is successful ... sy-subrc is 0 ... If several rows have the same key, which row is read is undefined for BINARY SEARCH"? Hmm.

The ABAP documentation (READ TABLE - READ TABLE itab): "If several rows match the search key, and the addition BINARY SEARCH is not used, the first matching row is read. ... If BINARY SEARCH is used, the row found is the one that would be found by the binary search; if there are duplicates, it is the row with the LOWEST index" — I genuinely recall the doc saying: "When using BINARY SEARCH and there are several matching rows, the row with the smallest index is returned" was true historically? There's a known caveat: binary search finds *a* matching row, not necessarily the first, unless the table is sorted ascending by the key - and even then, standard binary search may land on any duplicate. SAP's implementation: binary search finds the insertion point; I believe it returns the first match in a correctly sorted table because the binary search converges... no, classic binary search with duplicates can land on any of the duplicates.

The official ABAP keyword doc says: "If several rows match the key and BINARY SEARCH is used, the row with the lowest row index is read." Hmm, I'm not 100% sure. Let me avoid the ambiguity: to be safe and match original semantics ("first row with matnr = XYZ in arbitrary order"), I can instead do a SELECT UP TO 1 ROWS for the find, or use a sorted table and READ TABLE (without binary search on sorted table uses optimized access anyway).

Actually for a SORTED table, READ TABLE WITH KEY uses binary search automatically and returns the first entry in sort order? For sorted tables, "the first row in sort order that matches" is returned. Yes: for sorted tables, READ returns the first entry that matches in the sort sequence.

Simplest robust modern approach: since we only need "the first position with material XYZ", do:

```abap
SELECT h~vbeln, p~posnr, p~matnr, p~netwr
  FROM vbak AS h
  INNER JOIN vbap AS p ON p~vbeln = h~vbeln
  WHERE h~erdat = @sy-datum
    AND p~matnr = @lv_matnr
  ORDER BY h~vbeln, p~posnr
  UP TO 1 ROWS
  INTO @DATA(ls_pos).
```

But that changes semantics slightly (original: first row in lt_vbap order = order of insertion = per SELECT loop order = per VBAK loop order...). The original READ TABLE finds the first row in lt_vbap with matnr XYZ, where lt_vbap was built order-by-order, position-by-position. So "first" = lowest vbeln/posnr among today's orders (assuming SELECT without ORDER BY returns in primary key order - not guaranteed but typical). To keep it simple, I'll present the corrected version faithful to the original logic (build table, sum, read first match) but optimized, and note the alternative minimal version.

For the READ: use SORT + BINARY SEARCH and note that it finds a matching row; or define the target as SORTED table. Alternative: keep it simple:

```abap
SORT lt_pos BY matnr vbeln posnr.
READ TABLE lt_pos INTO DATA(ls_pos) WITH KEY matnr = 'XYZ' BINARY SEARCH.
```

With sort by matnr vbeln posnr, binary search landing on any duplicate matnr would still give a row with matnr XYZ; if we want deterministic first, sort by matnr vbeln posnr and... binary search may still land on middle duplicate. Hmm.

Honestly, the cleanest deterministic modern solution: 

```abap
DATA(ls_pos) = VALUE #( lt_pos[ matnr = 'XYZ' ] DEFAULT ... ) 
```

Wait - table expression lt_pos[ matnr = 'XYZ' ] on a standard table does linear search and returns the first match - same as READ TABLE. If not found, raises exception; with VALUE ... DEFAULT or using lt_pos[ ... ] OPTIONAL. So:

```abap
DATA(ls_pos) = VALUE #( lt_pos[ matnr = conv matnr( 'XYZ' ) ] OPTIONAL ).
IF ls_pos IS NOT INITIAL.
```

Hmm, but VALUE #( ... OPTIONAL ) - syntax: `DATA(ls_pos) = VALUE #( lt_pos[ matnr = 'XYZ' ] OPTIONAL ).` Yes that works (7.40). For linear search on standard table, first match is returned - deterministic like READ TABLE.

But for performance, better to have sorted/hashed. With non-unique key matnr, sorted table: `DATA lt_pos_sorted TYPE SORTED TABLE OF ... WITH NON-UNIQUE KEY matnr.` READ TABLE on sorted table returns first in sort order.

To keep the answer focused, I'll do:

Corrected version (faithful, optimized):

```abap
DATA: lv_sum TYPE vbap-netwr.

" 1) Kopfdaten von heute (nur benötigtes Feld)
SELECT vbeln
  FROM vbak
  WHERE erdat = @sy-datum
  INTO TABLE @DATA(lt_vbak).

IF lt_vbak IS NOT INITIAL.
  " 2) Positionen in EINEM DB-Zugriff (FOR ALL ENTRIES statt SELECT im LOOP)
  SELECT vbeln, posnr, matnr, netwr
    FROM vbap
    FOR ALL ENTRIES IN @lt_vbak
    WHERE vbeln = @lt_vbak-vbeln
    INTO TABLE @DATA(lt_vbap).

  " 3) Summe direkt in der DB berechnen
  SELECT SINGLE SUM( netwr )
    FROM vbap
    FOR ALL ENTRIES IN @lt_vbak
    WHERE vbeln = @lt_vbak-vbeln
    INTO @lv_sum.
ENDIF.

" 4) Zugriff über sortierte Tabelle -> binäre Suche statt linearem Scan
DATA(lt_vbap_sorted) = VALUE ty_vbap_tab( ... )
```

Hmm, getting complicated. Maybe simpler: JOIN version as main solution:

```abap
SELECT h~vbeln AS vbeln,
       p~posnr,
       p~matnr,
       p~netwr
  FROM vbak AS h
  INNER JOIN vbap AS p
    ON p~vbeln = h~vbeln
  WHERE h~erdat = @sy-datum
  INTO TABLE @DATA(lt_vbap).

IF sy-subrc = 0.
  " Summe: ebenfalls von der DB berechnen lassen
  SELECT SINGLE SUM( p~netwr )
    FROM vbak AS h
    INNER JOIN vbap AS p ON p~vbeln = h~vbeln
    WHERE h~erdat = @sy-datum
    INTO @DATA(lv_sum).

  " ersten Treffer zu MATNR suchen – sortiert + BINARY SEARCH
  SORT lt_vbap BY matnr vbeln posnr.
  READ TABLE lt_vbap INTO DATA(ls_vbap)
       WITH KEY matnr = 'XYZ' BINARY SEARCH.
  IF sy-subrc = 0.
    WRITE: / 'gefunden', ls_vbap-vbeln.
  ENDIF.
ENDIF.
```

Note on BINARY SEARCH determinism: I'll sort by matnr first so any hit has the right matnr; to make it deterministic "first", mention that for sorted tables the first entry in sort order is returned. Actually, let me just define the table type as SORTED to be clean:

Alternative clean approach: declare result as sorted table:

```abap
TYPES: BEGIN OF ty_pos,
         vbeln TYPE vbap-vbeln,
         posnr TYPE vbap-posnr,
         matnr TYPE vbap-matnr,
         netwr TYPE vbap-netwr,
       END OF ty_pos,
       ty_pos_tab TYPE SORTED TABLE OF ty_pos WITH NON-UNIQUE KEY matnr vbeln posnr.

DATA lt_vbap TYPE ty_pos_tab.

SELECT h~vbeln, p~posnr, p~matnr, p~netwr
  FROM vbak AS h
  INNER JOIN vbap AS p ON p~vbeln = h~vbeln
  WHERE h~erdat = @sy-datum
  INTO TABLE @lt_vbap.
```

Hmm, INTO TABLE @lt_vbap with sorted table works (rows inserted in sorted order). Then READ TABLE lt_vbap WITH KEY matnr = ... uses optimized access and returns first in sort order. That's clean and deterministic.

But maybe simpler for the answer: keep standard table + SORT + READ BINARY SEARCH, and note the sorted-table alternative. I think showing a TYPES-based sorted table is good practice and answers the READ performance issue elegantly.

Also mention MATNR conversion: use a variable lv_matnr TYPE vbap-matnr and e.g. `lv_matnr = 'XYZ'.` — assignment to matnr field applies conversion exit ALPHA? MATNR domain MATNR has conversion exit MATN1. A direct assignment in ABAP of a char literal to a matnr-typed variable: conversion exits are NOT applied by plain assignment; they're applied on screen input and in some contexts. Actually, plain ABAP assignment does NOT call conversion exit. Hmm - so `lv_matnr = 'XYZ'` doesn't pad. For numeric materials you'd need ALPHA input format: `|XYZ| ALPHA = IN`? The correct way: `lv_matnr = 'XYZ'` then... Actually there's the function CONVERSION_EXIT_MATN1_INPUT, or in modern ABAP: `lv_matnr = |{ 'XYZ' ALPHA = IN }|`? The ALPHA = IN formatting applies leading zeros for purely numeric values. For 'XYZ' (alphanumeric) no padding needed. MATN1 conversion: numeric-only material numbers get leading zeros; alphanumeric ones are left as-is (shifted?). MATN1 converts: if the material number is numeric, it's right-aligned with leading zeros; otherwise unchanged (left-justified). 'XYZ' alphanumeric → stays 'XYZ'. So 'XYZ' literal is probably fine, but if the material number were numeric, '123' ≠ '000000000000000123'. I'll add a brief note: use a matnr-typed variable and consider conversion exit (ALPHA) when building the value dynamically.

Also the currency caveat: summing NETWR across currencies (WAERS) is meaningless - group by waers or convert. Brief note.

Also: the original writes only vbeln of found row. Keep.

Also mention: `SELECT * FROM vbak WHERE erdat = sy-datum` - check whether index exists on ERDAT; if the table is huge, ensure index. Brief note.

Also: In the original, if lt_vbak is empty, everything is skipped - fine. In FAE variant, must guard `IF lt_vbak IS NOT INITIAL` else full table select. In JOIN variant, no guard needed.

Also: COMMIT WORK removed - explain: no DB changes made; COMMIT WORK would end the SAP LUW, trigger update modules - dangerous/unnecessary. Also note: COMMIT WORK is not allowed inside SELECT...ENDSELECT loop (would cause runtime error if it were inside) - here it's outside, but still pointless.

Also: mixing old/new syntax: The first SELECT uses new syntax (@DATA) which activates strict mode → `sy-datum` must be `@sy-datum`. That's a hard syntax error in strict mode. Actually wait - is it? Let me double check: Using INTO TABLE @DATA(lt_vbak) - the @DATA(...) inline declaration itself requires the host variable escape. The strict mode of Open SQL from 7.40 is triggered by using any new feature in the statement; then ALL host variables must be escaped. So `WHERE erdat = sy-datum` without @ → syntax error "The element ... " something like "In the strict mode ... host variables must be escaped with @". Yes, syntax error. So point 1 is a genuine syntax error.

Second SELECT: old syntax without @ - allowed (no strict mode triggered). But `INTO ls_vbap` with `SELECT * ... ENDSELECT` - obsolete but legal. However, mixing is ugly; in corrected version use new syntax consistently.

Wait, one more check on the second SELECT: `SELECT * FROM vbap INTO ls_vbap WHERE vbeln = ls_vbak-vbeln.` In old syntax, host variables in WHERE don't need @. ls_vbak was declared inline via LOOP AT ... INTO DATA(ls_vbak) - fine.

Also the LOOP AT lt_vbak INTO DATA(ls_vbak) - inline declaration in LOOP AT is allowed since 7.40 SP8? LOOP AT ... INTO DATA(...) is allowed. Fine.

Another subtle issue: `READ TABLE lt_vbap INTO ls_vbap WITH KEY matnr = 'XYZ'.` - if lt_vbap is empty, sy-subrc = 4, fine.

Also, `lv_sum TYPE p DECIMALS 2` without length: default length 8 → 15 digits incl. sign → 13 integer digits + 2 decimals. NETWR is CURR length 15 decimals 2 → wait, CURR length 15 means 15 digits total? Domain NETWR: CURR, length 15, decimals 2? Let me recall: VBAP-NETWR is CURR 15, 2 decimals? Hmm, actually I think NETWR is length 15 with 2 decimals? Or 13,2? WERTV8? Let me think: NETWR domain: data type CURR, length 15, decimal places 2. Yes I believe NETWR is CURR 15 (2 decimals). So max 13 integer digits. p length 8 = 15 digits (2*8-1), minus 2 decimals = 13 integer digits. So capacity matches NETWR exactly, but a SUM over many positions can overflow 13 digits → runtime error overflow (in ABAP, arithmetic overflow → dump). Better: use TYPE vbap-netwr (same) or larger p length 16? p max length is 16 bytes = 31 digits. So `lv_sum TYPE p LENGTH 16 DECIMALS 2` would be safer. Minor point; mention briefly. Or compute SUM in DB where the DB handles larger ranges (still packed(9)? DB sum returns as per field). I'll mention using SUM( ) in DB.

Also the dead code: lv_sum computed but never used → either remove or output.

Also style: WRITE is obsolete list processing; in modern ABAP use CL_DEMO_OUTPUT or messages - minor note, keep WRITE for fidelity.

Let me also double check FOR ALL ENTRIES vs JOIN performance: JOIN is generally preferred; FAE has pitfalls (duplicates, empty driver table, plan confusion). I'll present JOIN as primary.

One more consideration: The JOIN with SELECT of header fields h~vbeln only - fine.

Also, if the intent is only to find the first position with material XYZ among today's orders, the optimal solution is a single SELECT UP TO 1 ROWS - I

</details>
