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



---

<details><summary>Denkprozess (32875 Zeichen)</summary>

The user wants me to modernize old ABAP code to current syntax, using inline declarations, VALUE, FOR expressions, table expressions, NEW, string templates — without changing behavior.

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

Modernization:

1. Inline declarations with `DATA(...)`:
   - `DATA(lt_mara) = VALUE ...` or inline in SELECT: `SELECT * FROM mara INTO TABLE @DATA(lt_mara) UP TO 100 ROWS WHERE mtart = 'FERT'.` — Actually with new syntax: `SELECT * FROM mara WHERE mtart = 'FERT' INTO TABLE @DATA(lt_mara) UP TO 100 ROWS.` Or keep order. Modern ABAP SQL: `SELECT * FROM mara WHERE mtart = @... INTO TABLE @DATA(lt_mara) UP TO 100 ROWS.` The clauses order: SELECT ... FROM ... WHERE ... INTO TABLE ... UP TO n ROWS. Actually UP TO n ROWS comes after UP TO/ORDER BY etc. Standard order: SELECT ... FROM ... FIELDS ... WHERE ... GROUP BY ... ORDER BY ... UP TO n ROWS INTO ... Actually the INTO clause position: In the strict modes, INTO should be at the end. Let me write:

```abap
SELECT * FROM mara
  WHERE mtart = 'FERT'
  INTO TABLE @DATA(lt_mara)
  UP TO 100 ROWS.
```

Hmm, the correct order: SELECT ... FROM ... [FIELDS] ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... UP TO, OFFSET ... INTO ... Actually UP TO n ROWS must come after ORDER BY and before INTO? Let me recall: In ABAP SQL, the clause order is:

SELECT [DISTINCT] select_list
  FROM data_source
  [FIELDS ...]
  WHERE ...
  GROUP BY ...
  HAVING ...
  [ORDER BY ...]
  [UP TO n ROWS]
  [OFFSET o]
  INTO ...
  [appending]

Actually the INTO clause can be placed at various positions in the short forms, but in the strict mode (from 7.40 SP08), INTO must be at the end. UP TO n ROWS is placed before INTO? Let me check: The syntax diagram for SELECT: 

SELECT [DISTINCT] { select_list | ... }
  FROM ...
  [WHERE ...]
  [GROUP BY ...]
  [HAVING ...]
  [ORDER BY ...]
  [UP TO {n|@n} ROWS]
  [OFFSET ...]
  INTO|APPENDING ...
  [into_clause]
  ...

Yes, UP TO n ROWS comes before INTO in the modern strict mode. Example from SAP docs:

```
SELECT FROM spfli
       FIELDS carrid, connid
       WHERE ...
       INTO TABLE @DATA(result)
       UP TO 10 ROWS.
```

Hmm, actually I've seen examples with UP TO after INTO TABLE as well. Let me recall the documentation: "INTO clause ... The ABAP SQL statement clauses SELECT, FROM, WHERE, GROUP BY, HAVING, and ORDER BY ... The INTO clause can be specified before or after..." In strict mode from 7.40 SP08, "the INTO clause must be specified as the last clause of the SELECT statement". And UP TO n ROWS: "UP TO n ROWS ... must be specified after ORDER BY ... and before INTO"? 

From SAP documentation on SELECT: The clause sequence is:

```
SELECT [DISTINCT] ...
       FROM ...
       [WHERE ...]
       [GROUP BY ...]
       [HAVING ...]
       [ORDER BY ...]
       [UP TO n ROWS]
       [OFFSET o]
       INTO ...
```

Actually, I recall that UP TO n ROWS and OFFSET come after ORDER BY and before INTO in strict mode. Example from SAP docs:

```
SELECT carrid, connid
       FROM spfli
       WHERE ...
       ORDER BY carrid, connid
       INTO TABLE @DATA(itab)
       UP TO 10 ROWS.
```

Hmm no. Let me think again. The ABAP keyword documentation for SELECT, UP TO n ROWS: "UP TO n ROWS ... This addition must be specified after the additions ORDER BY ... and before the addition INTO clause in the strict modes..." Actually I believe in strict mode the INTO clause must be last, so UP TO must come before INTO. Let me check an actual example from SAP documentation (ABAP SQL examples):

```abap
SELECT FROM scarr
       FIELDS carrid, carrname
       UP TO 10 ROWS
       INTO TABLE @DATA(scarr_tab).
```

Yes! I've definitely seen "UP TO 10 ROWS" before "INTO TABLE @DATA(...)" in modern examples. So the order is: SELECT ... FROM ... WHERE ... UP TO n ROWS INTO TABLE @DATA(itab).

So:

```abap
SELECT * FROM mara
  WHERE mtart = 'FERT'
  UP TO 100 ROWS
  INTO TABLE @DATA(lt_mara).
```

Wait — but with `*` and FIELDS clause. In strict mode with comma-separated list you need FIELDS, but `SELECT *` without commas is fine. `SELECT * FROM mara WHERE mtart = 'FERT' UP TO 100 ROWS INTO TABLE @DATA(lt_mara).` That's valid modern syntax. Note: 'FERT' literal — in strict mode, literals in WHERE need to be fine; host variables need @, but literals are OK without @.

2. LOOP AT ... INTO ls_mara → `LOOP AT lt_mara INTO DATA(ls_mara).` or better: use FOR ... IN to build lt_out:

```abap
DATA(lt_out) = VALUE string_table( FOR ls_mara IN lt_mara
                                   ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).
```

Wait — careful with behavior: CONCATENATE ... SEPARATED BY space produces "MATNR - MATKL"? Let's see: CONCATENATE ls_mara-matnr '-' ls_mara-matkl INTO lv_txt SEPARATED BY space → result: matnr + space + '-' + space + matkl. So "MATNR - MATKL". A string template `|{ matnr } - { matkl }|` — with spaces inside the template around expressions... In string templates, the literal text is preserved: `|{ ls_mara-matnr } - { ls_mara-matkl }|` produces matnr + " - " + matkl. Yes, spaces inside the template between } and - are literal. Actually the template `|{ a } - { b }|`: the text between { a } and { b } is " - " (space, dash, space). So the result is a + " - " + b. That matches CONCATENATE with SEPARATED BY space: a + ' ' + '-' + ' ' + b = a + " - " + b. 

But wait — CONCATENATE truncates? CONCATENATE into a string (lv_txt TYPE string) doesn't truncate since target is string. matnr is CHAR18, matkl CHAR9. CONCATENATE keeps trailing blanks? CONCATENATE ignores trailing blanks of source fields? For character-like fields, CONCATENATE moves them including trailing blanks? No — CONCATENATE: "In character-like source fields, trailing blanks are ignored"? Hmm. Actually for CONCATENATE with SEPARATED BY, trailing blanks in the source fields are... Let me recall: CONCATENATE ignores trailing blanks in source fields of fixed length? The documentation: "In the case of character-like source fields, trailing blanks are cut off and are not passed to the target field." Hmm, I think that's true for CONCATENATE: trailing blanks of the arguments are not transferred. But SEPARATED BY space blanks are transferred. So CONCATENATE matnr '-' matkl SEPARATED BY space gives matnr (trailing blanks stripped) + ' ' + '-' + ' ' + matkl (trailing blanks stripped).

String template `|{ matnr } - { matkl }|` — embedded expressions: the value of matnr is inserted with its full length? For character-like data objects, embedded expressions insert the value including trailing blanks? Actually in string templates, embedded expressions of character-like type insert the string including trailing blanks? Hmm. The formatting of embedded expressions: by default, character-like data objects are inserted in their full length including trailing blanks? I believe trailing blanks ARE included for character-like fields in string templates (since the value is converted to string preserving length). Wait, no — let me think. 

In string templates, when you embed a character-like variable, the result includes the variable's content with trailing blanks? Example: DATA text TYPE c LENGTH 10 VALUE 'AB'. |{ text }| → "AB        " (with trailing blanks)? I believe yes — embedded expressions preserve the full length for character-like types, trailing blanks included. Actually hmm, I recall that in string templates, trailing blanks ARE included for character-like data objects. Let me verify: The ABAP doc says: "In string templates, the embedded expression is converted to a character-like field... For character-like data objects, the content is inserted in its full length, including trailing blanks." Yes, I'm fairly confident: `|{ lv_c10 }|` where lv_c10 = 'AB' gives "AB        ". This is a known gotcha.

So `|{ matnr } - { matkl }|` would give "MATNR            - MATKL    " with trailing blanks of matnr preserved (matnr CHAR18) and matkl CHAR9 trailing blanks preserved. That differs from CONCATENATE which strips trailing blanks!

To preserve behavior exactly, we should use CONDENSE or formatting options. Options:
- `|{ ls_mara-matnr } - { ls_mara-matkl }|` with... hmm.
- Use ALPHA? No.
- Use `|{ ls_mara-matnr WIDTH = ... }|`? Not helpful.

Better: use embedded expression with formatting option... There's no "trim" option directly, but you can use `condense( val = ... )`? condense removes leading and trailing? CONDENSE condense( ) removes leading/trailing blanks and squeezes internal ones to single space by default (del = ``). Hmm, condense( val = matnr ) would remove trailing blanks and also squeeze internal blanks — for MATNR internal blanks are unlikely but could exist? MATNR can contain spaces? Material numbers are CHAR18, typically no internal spaces, but could be in theory. To be safe, use `|{ condense( val = ls_mara-matnr ) } - { condense( val = ls_mara-matkl ) }|`? Hmm, but condense also squeezes internal multiple blanks into one. CONCATENATE would keep internal blanks. Edge case.

Alternative: use the built-in function `match`? No. There's `shift_left`? There is no simple trim function... Actually there IS: `condense` with del = NO-GAPS etc. Hmm.

Wait — actually, is it true that string templates include trailing blanks? Let me double-check. From ABAP documentation on string templates: "The characters of the text ... In embedded expressions, the result of the expression is converted ... If the embedded expression is a character-like data object with fixed length, its trailing blanks are respected"? 

Hmm, I recall discussions: In string templates, trailing blanks of character-like fields ARE included. E.g., `DATA: lv TYPE c LENGTH 5 VALUE 'AB'. DATA(lv_str) = |{ lv }X|.` gives "AB   X"? I believe yes, that's a well-known behavior difference vs CONCATENATE. Actually wait, let me think again... I recall the opposite for some contexts... Let me reason from the docs: "string templates ... Embedded expressions ... The value of the embedded expression is converted to the type string ... For character-like types, the conversion rules apply: conversion of type c to string: trailing blanks are cut off"? Hmm! Conversion rules from c to string: "When converting from type c to type string, trailing blanks are cut off"? Actually the conversion rule c → string: the content is transferred including trailing blanks? Let me recall: Converting char-like to string: "the content is passed unchanged, including trailing blanks"? 

ABAP conversion rules: Conversion between character-like data types: c → string: "The content is transferred unchanged, including trailing blanks"? Hmm, I think for c → string conversion, trailing blanks ARE preserved because string has variable length and the source length defines content. E.g., MOVE c10 'AB' TO string → string = 'AB        ' (10 chars). Yes! That's right: assigning a c field to a string preserves trailing blanks (the string gets the full length content). E.g., `DATA str TYPE string. DATA c10 TYPE c LENGTH 10 VALUE 'AB'. str = c10. " str = 'AB        '` — yes, that's standard: the assignment of a fixed-length char to string includes trailing blanks. That's why CONCATENATE explicitly strips them ("trailing blanks are not passed").

So in string templates, embedding a c field: the expression result is converted to string — preserving trailing blanks. So `|{ c10 }|` = 'AB        '. Yes, I'm confident: string templates preserve trailing blanks of fixed-length char fields. This is a known difference and often people use `|{ lv }|` and get trailing blanks.

So to replicate CONCATENATE behavior (which strips trailing blanks of source fields), we need to strip them. Common approach: `|{ ls_mara-matnr } - { ls_mara-matkl }|` would NOT be identical. Hmm, but many "modernization" answers ignore this subtlety. The user said "ohne das Verhalten zu ändern" (without changing behavior). So I should be careful and mention this.

Options to exactly replicate:
1. Keep CONCATENATE — but that defeats the purpose.
2. Use string template with embedded expressions wrapped in condense: `condense( val = ... )` — but condense squeezes internal sequences of blanks too (default del = space, "from" ... default: leading/trailing removed and internal sequences shortened to single blank). CONCATENATE keeps internal content as-is (only trailing blanks of each argument stripped). For MATNR/MATKL, internal blanks are essentially nonexistent in practice, but strictly not identical.

Hmm, is there a trim-only function? There's `shift_left( val = ... places = ... )`? Not trim. In newer releases (ABAP 7.5x / cloud), there are functions like `trim( )`? Hmm — actually, yes! In ABAP Cloud / newer ABAP platform releases there are built-in functions `trim( )`, `trim_lower`, `trim_upper`? Let me recall: ABAP built-in functions include `condense`, `repeat`, `replace`, `reverse`, `segment`, `shift_*`, `substring_*`, `to_lower`, `to_upper`, `to_mixed`, `from_mixed`, `translate`, `match`, `find`, `count`, `contains`, `insert`, `nmax`, `nmin`, `cmax`, `cmin`, `ipow`, `abs`, `ceil`, `floor`, `round`, `trunc`, `xsdbool`, `boolc`, `boolx`, `char_off`, `charlen`, `dbmaxlen`, `numofchar`, `strlen`, `xstrlen`, `line_exists`, `line_index`, `value`... 

Hmm, `trim`? I don't think classic ABAP has a `trim` built-in. There's `shift_left( val = text sub = `` )`? shift_left with sub removes leading occurrences. Not trailing.

Hmm, actually in ABAP for Cloud / ABAP 7.57+? I'm not sure `trim` exists. Let me not rely on it.

Alternative exact approach: use `|{ ls_mara-matnr } - { ls_mara-matkl }|` and then... no.

Wait — actually, maybe I'm wrong about string templates preserving trailing blanks. Let me think hard. 

ABAP documentation "string_templates - embedding expressions": "...the result of the embedded expression is transformed into a character-like value..." Formatting options... For character-like data objects without formatting options, "the value is inserted in its full length"? 

I recall the classic example: 
```abap
DATA text TYPE c LENGTH 10 VALUE '  ABC  '.
DATA(result) = |{ text }|.
```
result = '  ABC     '? Hmm.

Actually, I now recall clearly: There IS a known behavior where string templates preserve trailing blanks for fixed-length char. E.g., SAP Community threads: "String template adds trailing blanks". Yes — `|{ lv_matnr }|` where matnr is CHAR18 gives 18 characters including trailing blanks. People often use `|{ lv_matnr ALPHA = OUT }|` etc. Also `CONDENSE` to remove.

Hmm wait, but actually let me reconsider: maybe embedded expressions cut trailing blanks? There's a difference between the value being converted to string (which preserves trailing blanks per conversion rules c→string? or does c→string cut trailing blanks?).

Conversion rules c → string: From ABAP docs: "Character-Like ... Conversion of type c to type string: The content is transferred unchanged, including trailing blanks"? Hmm, actually I recall: "When converting between character-like data types c, d, n, t and string: ... For target type string, the content is passed with trailing blanks"? Let me think of a concrete known example: 

```abap
DATA: c10 TYPE c LENGTH 10 VALUE 'AB',
      s TYPE string.
s = c10.
WRITE strlen( s ). " 10 or 2?
```

I'm quite sure this yields 10 — assignment preserves the full 10 characters including trailing blanks. Yes: "When a character-like field with fixed length is assigned to a string, the trailing blanks are retained." Hmm, actually wait. I recall the opposite for some operations: e.g., `CONCATENATE` strips trailing blanks (documented explicitly as an exception), and `SPLIT` ... For plain assignment, trailing blanks ARE kept. Yes, I'm confident: assignment c→string keeps trailing blanks. That's why CONCATENATE documentation explicitly says trailing blanks are not passed (because normally they would be).

So string templates: embedded expression → converted to string → trailing blanks kept. So `|{ matnr }|` has trailing blanks. Confirmed by many community posts: "In string templates, trailing blanks of CHAR fields are included; use CONDENSE or formatting to remove."

OK so to be exact, I should handle this. Options:

Option A: Use string template with `CONDENSE( )`:
```abap
DATA(lt_out) = VALUE string_table(
  FOR ls IN lt_mara
  ( |{ condense( val = ls-matnr ) } - { condense( val = ls-matkl ) }| ) ).
```
Hmm wait, but condense( ) default also compresses internal blanks to single. For material numbers that's fine practically, but strictly different if internal double blanks exist.

Hmm, actually there's a cleaner trick: `|{ ls-matnr } - { ls-matkl }|` — no. 

Another approach: The exact CONCATENATE semantics: strip trailing blanks of each argument, join with single space separators. Equivalent: build with `&&`? The concatenation operator `&&` also... `&&` for strings: trailing blanks of the operands are respected? For `&&` (string concatenation operator), the operands are converted to string — trailing blanks of c fields... I believe `&&` also keeps trailing blanks (since conversion preserves them). Actually the docs: "The concatenation operator && ... trailing blanks in character-like operands with fixed length are respected"? Hmm. Let me recall: `&` vs `&&`: The older `&` in string templates context... The `&&` operator: "character-like expressions ... trailing blanks are cut off"? 

Hmm, I recall: For the concatenation operator `&&`, trailing blanks of character-like operands ARE cut off? No wait... Let me think. There's a documented difference: `&&` respects trailing blanks? The ABAP doc on concatenation operators: "In the case of character-like operands, trailing blanks are respected by && and ignored by ... "? Hmm.

Let me recall precisely: ABAP keyword documentation, "concatenation operators && / &": "The concatenation operator && ... is only allowed for character-like expressions... Unlike with CONCATENATE, trailing blanks in character-like operands are respected"? Hmm, I genuinely can't remember 100%. Let me think about known examples:

```abap
DATA: a TYPE c LENGTH 3 VALUE 'ab ',
      b TYPE string.
b = a && 'x'. " 'ab x' or 'ab  x'?
```

I believe `&&` preserves trailing blanks (operand converted to string preserving length). Hmm, but actually I recall a rule: "For the operator &&, the operands are treated as strings; trailing blanks of character-like flat operands are cut off"? 

Let me look at this from the doc memory: "string expressions - concatenation operators": "The concatenation operator && concatenates ... character-like ... operands. ... In contrast to CONCATENATE, the operands are not ... trailing blanks are respected..." 

Hmm. I found it: The ABAP documentation states for `&&`: "Unlike in the CONCATENATE statement, trailing blanks in character-like operands are respected." Wait, or is it the reverse? There's a well-known difference between `&` and `&&` in string templates: within string templates, `&` and `&&`... In string templates, embedded string expressions with `&`/`&&` — trailing blanks... 

OK here's what I actually remember solidly: In string templates, `|{ a } && { b }|` vs `|{ a } & { b }|`: `&` cuts trailing blanks, `&&` keeps them? Something like that exists. The doc: "The operator & is a shorthand for && in string templates where trailing blanks are cut"? Hmm, no.

Let me just recall the actual doc text: ABAP Keyword Documentation, "concatenate expressions": 

"&& — Concatenation operator for character-like operands... The operands must be character-like... Result of type string... Trailing blanks in character-like operands are respected." 

Hmm, I think that's right: `&&` respects trailing blanks. And there's also `&` which is only allowed within string templates and cuts trailing blanks? Actually I recall: "& behaves like && except that trailing blanks of operands are cut off" — no wait, that's backwards too.

Hmm, let me think about the actual documented behavior: From ABAP docs (String expressions → Concatenation operators):

"&& ... The concatenation operator && ... has the same effect as the CONCATENATE statement ... with one exception: trailing blanks in character-like operands are respected..." 

Hmm, I really think `&&` keeps trailing blanks. Example: `DATA(x) = 'ab' && |cd| && 'ef'.` trivial. With c-field: `DATA(c3) = VALUE c3( 'ab ' ). DATA(s) = c3 && 'x'.` → s = 'ab x'? If trailing blanks respected: 'ab x'. If cut: 'abx'.

I recall SAP Community discussions: "&& does not remove trailing blanks, CONCATENATE does." Yes, I'm fairly confident that's correct: `&&` keeps trailing blanks of fixed-length char operands.

OK so regardless, `&&` doesn't help replicate CONCATENATE exactly.

Simplest exact replication with modern syntax while keeping readability: honestly, the pragmatic modernization everyone writes is:

```abap
lt_out = VALUE #( FOR ls_mara IN lt_mara ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).
```

and note the trailing-blank caveat. But the user explicitly said "ohne das Verhalten zu ändern" — without changing behavior. So I should either produce exact behavior or clearly note the difference and provide the exact variant.

Exact approach options:

1. Use string template with embedded expressions and the `WIDTH` formatting? No.

2. Use `condense( val = ... )`: changes internal blanks too.

3. Use `substring`? We could compute strlen without trailing blanks: `numofchar`? numofchar counts characters excluding trailing blanks? Actually `numofchar( )` — "returns the number of characters in the argument, where trailing blanks are not counted"? Hmm: `strlen` for strings counts all chars; for c fields, strlen counts length including trailing blanks? For c, strlen returns the declared length? No: strlen for c returns number of characters up to... For fixed-length char, strlen returns the length of the field (declared length) — no wait. 

Built-in functions: `strlen( arg )` — "content of arg without trailing blanks"? Let me recall: For c, strlen returns the number of characters "including trailing blanks up to the last non-blank"? Hmm.

ABAP doc: `strlen` — "Length of the argument measured in characters... For character-like data objects, the number of characters in the argument is determined, where trailing blanks are not counted"? No wait, that's `numofchar`? 

Actually: 
- `strlen`: for string: full length; for c: number of characters excluding trailing blanks? Hmm no...
- `numofchar`: similar but counts... 

Let me recall precisely: 
- `strlen( )`: "The function strlen returns the number of characters in the argument. For fixed-length character-like fields, trailing blanks are included"? Hmm.

I remember: For `c` fields, `strlen` counts up to and including trailing blanks? No...

OK, concrete known example: `DATA c10 TYPE c10 VALUE 'AB'. strlen( c10 )` → 10? or 2? I'm fairly sure strlen( c10 ) = 10 for c fields? Hmm, no wait. I recall `strlen` for char fields returns length without trailing blanks... 

Ugh. Let me think: STRLEN in ABAP: "STRLEN( x ) for character-like x: number of characters in x, trailing blanks not included"? The classic STRLEN function: For type c fields, STRLEN returns the length of the content up to the last non-blank character. E.g., STRLEN( 'AB  ' ) = 2. Yes! Classic STRLEN ignores trailing blanks for c fields. And for type string, STRLEN returns full length. And NUMOFCHAR: "number of characters, where for c fields trailing blanks ARE included"? Hmm, NUMOFCHAR: "returns the number of characters in the argument; for character-like fields, trailing blanks are counted"? 

I recall: NUMOFCHAR for c counts the full declared length? No... NUMOFCHAR: "The number of characters ... is determined regardless of the type; trailing blanks in type c are counted"? 

Hmm, from docs: "numofchar — Similar to strlen, but for all character-like types the full length is used, i.e., trailing blanks of type c are also counted"? Hmm, I think: strlen(c) excludes trailing blanks; numofchar(c) includes them. For strings both are equal. Yes, that matches my memory: strlen ignores trailing blanks for fixed-length char; numofchar includes them.

Anyway, this is getting deep. The cleanest exact replication: honestly, keep the CONCATENATE? No — the user wants modernization. 

Alternative: Use string template but explicitly handle: since CONCATENATE strips trailing blanks of each source field, and the separator is a single space, the exact equivalent is:

`|{ ls_mara-matnr } - { ls_mara-matkl }|` — with trailing blanks included — differs.

Exact: `condense( val = |{ ls_mara-matnr } - { ls_mara-matkl }| )`? No — condense on the whole would also squeeze the separators... Actually condense with default del=' ' removes leading/trailing blanks of the whole and shortens internal blank sequences to one blank. The whole string is "MATNR<blanks> - MATKL<blanks>". Internal blank runs: between matnr and '-' there might be multiple blanks (matnr trailing + separator). Condensing would reduce to single blank → "MATNR - MATKL". And trailing blanks of matkl removed. Leading: matnr presumably has no leading blanks. So condense of the whole string gives "MATNR - MATKL" — which equals CONCATENATE result IF matnr/matkl have no leading/internal blanks. But if matnr had internal double blanks, condense would squeeze them — different. Also if matnr had leading blanks, CONCATENATE keeps them, condense removes them. Edge cases.

Hmm. Actually, wait. Let me reconsider whether string templates really include trailing blanks. I want to be careful because this is the crux.

ABAP Keyword Documentation, "string_exp - String Templates": embedded_exp: "{ exp ... }". "The value of the embedded expression exp is converted ... to a character-like value ... and inserted in the template... If no formatting options are used, the result of the expression is inserted ... in its full length"? 

I recall the doc explicitly: "In embedded expressions, the trailing blanks of character-like data objects with fixed length are respected." Hmm... Actually, you know what — I recall the opposite claim in some contexts! Let me think of the famous example:

```abap
DATA: lv TYPE c LENGTH 4 VALUE 'AB'.
DATA(lv_str) = |Hello { lv }!|.
```
Result: "Hello AB  !"? or "Hello AB!"?

I'm now fairly sure it's "Hello AB  !" — trailing blanks included. Evidence: SAP Community Q&A "String template: trailing blanks" — answers confirm that embedded expressions of fixed-length char include trailing blanks, and recommend using condense or ALPHA or `|{ lv }|` with... Hmm, but also I recall people being surprised that `|{ lv }|` does NOT have trailing blanks... 

Let me approach via conversion rules: embedded expression without formatting → the value is converted to type string? Or to type c with the template's length? The template is processed by creating an anonymous data object... The embedded expression result is converted to string (if the expression is not already string-like). Conversion c(18) → string: per conversion rules, "c → string: content including trailing blanks"? 

Conversion rules between character-like types: When converting c to string: "The content is transferred unchanged. The length of the string is the length of the field c, including trailing blanks." Hmm — actually I recall the conversion rule table: "c → string: The content is transferred, trailing blanks are cut off"? 

Argh. Let me settle with a definitive memory: 

```abap
DATA: c5 TYPE c LENGTH 5.
c5 = 'AB'.
DATA(s) = CONV string( c5 ).
```
What is strlen( s )? 

I'm now recalling the ABAP doc "Conversion Rules for Character-Like Data Types": "When converting the types c, d, n, t to string: The content is transferred unchanged... including trailing blanks"? Hmm, no — I actually recall: "In conversions to string, trailing blanks are cut off"? 

Hmm hmm. Let me think about a very common practical observation: `CONCATENATE` docs explicitly note: "In character-like source fields, trailing blanks are ignored" — and this is called out because in ASSIGNMENTS trailing blanks are NOT ignored. Yes — the CONCATENATE doc says something like: "Unlike in assignments, trailing blanks are cut off." That confirms: plain assignment c→string keeps trailing blanks. 

And string templates: The embedded expression is converted "in accordance with the conversion rules" — so c→string keeps trailing blanks → template includes them. I'm going to go with: string templates include trailing blanks of fixed-length char operands. This matches the widely known gotcha. E.g., famous example: `|{ sy-uname }|` with sy-uname CHAR12 gives trailing blanks — yes! I remember this: people write `|{ sy-uname }|` and get trailing blanks, needing condense. Yes, definitely a known thing.

OK so my modernization must address this to be behavior-preserving. 

Practical exact solution: 

```abap
lt_out = VALUE string_table(
           FOR ls_mara IN lt_mara
           ( |{ ls_mara-matnr } - { ls_mara-matkl }| ) ).
```
— not exact (trailing blanks).

Exact alternatives:
a) `|{ condense( ls_mara-matnr ) } - { condense( ls_mara-matkl ) }|` — condense as functional: `condense( val = ... )` default: remove leading/trailing blanks and shorten internal blank sequences to exactly one blank. For typical MATNR/MATKL (no internal blanks), identical to CONCATENATE. Strictly, differs if internal/leading blanks exist.

Hmm wait, actually condense( val = x ) with default del = ' ': "Leading and trailing blanks are removed and internal blank sequences are shortened to exactly one blank each"? Hmm, actually CONDENSE statement: "sequences of blanks are compressed to exactly one blank; leading and trailing blanks are removed" — yes by default (without NO-GAPS). So condense( val = 'AB  C  ' ) = 'AB C'. CONCATENATE of 'AB  C  ' (c7) would pass 'AB  C' (trailing stripped, internal kept). Different.

b) Use `shift_left`? No trim function for trailing specifically... Actually there IS a way: `|{ ls_mara-matnr }|` then... no.

c) Honestly, maybe the cleanest exact approach: keep CONCATENATE inside the FOR? You can't put statements in FOR. 

d) Use REDUCE with &&? Same trailing-blank issue.

e) Use string template with formatting option that trims? There's `ALPHA`, `WIDTH`, `ALIGN`, `CASE`, `ZERO`, `RAW`, `TIME`, `DATE`, `TIMESTAMP`, `NUMBER`, `XSD`... None trims.

f) Actually — hmm, wait. Is there a `trim` function now? In ABAP release 7.5x+? Let me think... I don't believe classic ABAP has trim(). ABAP Cloud added some functions? I recall new built-in functions in recent releases: `contains`, `matches` (regex), `to_blob`, ... I don't recall `trim`. There's `condense` only. OK.

g) Use `replace( val = ... sub = ... with = ... )`? Overkill.

h) Use `segment`? No.

Given the practical context (MATNR, MATKL — material numbers/groups never contain leading/internal blanks in practice; well, MATNR could theoretically contain spaces in old systems? Material numbers are typically alphanumeric without spaces), the pragmatic answer: use the string template and add a note about the trailing-blank difference, offering the exact-preserving variant with condense if needed. Actually, hmm, but wait: with condense applied to each field, leading blanks would also be removed — CONCATENATE keeps leading blanks. For MATNR with leading blanks (possible? material numbers can be like ' 123'?), CONCATENATE keeps leading blanks; condense would remove them. Strictly different again.

The truly exact functional equivalent of CONCATENATE a '-' b SEPARATED BY space: result = a(without trailing blanks) + ' ' + '-' + ' ' + b(without trailing blanks). 

A function that strips only trailing blanks: `shift_right`? No. Hmm: There's no built-in "rtrim". But we can do: `substring( val = x len = strlen( x ) )`? For c fields, strlen excludes trailing blanks! So `substring( val = ls_mara-matnr len = strlen( ls_mara-matnr ) )` gives the content without trailing blanks, preserving leading/internal blanks exactly. That's exact! But verbose.

Hmm wait, is strlen for c really excluding trailing blanks? Classic STRLEN: "STRLEN( arg ): Number of characters in arg, where trailing blanks are not counted" — for type c, yes; for string, all chars counted. I'm fairly confident. E.g., STRLEN( 'AB  ' ) = 2. Yes, that's the classic behavior of STRLEN for c fields.

Hmm, but actually wait: I recall STRLEN for c fields returns the declared length minus trailing blanks — i.e., position of last non-blank. Yes.

So exact: `|

</details>
