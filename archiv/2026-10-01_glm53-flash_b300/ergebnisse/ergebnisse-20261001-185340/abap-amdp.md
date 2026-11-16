# ABAP: amdp

## Aufgabe

Schreibe eine AMDP-Klasse (ABAP Managed Database Procedure) für SAP HANA, die für eine übergebene Verkaufsorganisation die Top-10-Materialien nach Umsatz aus VBAP/VBAK liefert. Mit Klassendefinition (IF_AMDP_MARKER_HDB), Methodensignatur, SQLScript-Implementierung und einem Aufruf aus ABAP. Erkläre, wann sich AMDP gegenüber ABAP-SQL lohnt.

## Antwort



---

<details><summary>Denkprozess (31852 Zeichen)</summary>

The user wants an AMDP class for SAP HANA in ABAP that returns Top 10 materials by revenue for a given sales organization from VBAP/VBAK. They want:
1. Class definition with IF_AMDP_MARKER_HDB
2. Method signature
3. SQLScript implementation
4. Call from ABAP
5. Explanation when AMDP is beneficial vs. ABAP SQL

The request is in German, so I should respond in German.

Let me write this properly:

**Class definition:**

```abap
CLASS cl_top_materials_amdp DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.
    INTERFACES: if_amdp_marker_hdb.

    TYPES: BEGIN OF ty_top_material,
             vbeln_pos TYPE vbap-posnr,
             matnr     TYPE vbap-matnr,
             arktx     TYPE vbap-arktx,
             umsatz    TYPE p LENGTH 15 DECIMALS 2,
             menge     TYPE vbap-kwmeng,
           END OF ty_top_material.
           
    TYPES: tt_top_materials TYPE STANDARD TABLE OF ty_top_material WITH DEFAULT KEY.

    METHODS get_top_materials
      IMPORTING VALUE(iv_vkorg)     TYPE vkorg
                VALUE(iv_top_n)     TYPE i DEFAULT 10
      EXPORTING VALUE(et_result)    TYPE tt_top_materials
      RAISING   cx_amdp_error.
ENDCLASS.
```

Wait, let me think about the correct structure. The AMDP method needs:
- The class must implement IF_AMDP_MARKER_HDB
- The method must be flagged with `BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT [OPTIONS READ-ONLY]`
- Parameters: pass-by-value (VALUE), no generic types, no reference types
- Tables types must be declared in the class (or DDIC)

For the SQLScript implementation:

```abap
CLASS cl_top_materials_amdp IMPLEMENTATION.

  METHOD get_top_materials
    BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT
    OPTIONS READ-ONLY
    USING vbak vbap.

    DECLARE lv_top_n INT = 10; -- hmm, can't use ABAP variable iv_top_n directly in LIMIT
```

Actually in SQLScript, LIMIT requires a constant in older versions, but with :iv_top_n you can use variables. Actually in SQLScript, `LIMIT :iv_top_n` works with variables in newer HANA versions. But to be safe, I could use `TOP :iv_top_n` or just LIMIT :iv_top_n. Actually LIMIT with a variable works: `LIMIT :iv_top_n` — yes, SQLScript supports LIMIT with a host variable.

Let me write the SQLScript:

```sql
    et_result = SELECT TOP 10
                  vbap.matnr AS matnr,
                  MAX(vbap.arktx) AS arktx,
                  SUM(vbap.netwr) AS umsatz,
                  SUM(vbap.kwmeng) AS menge
                FROM vbap
                INNER JOIN vbak ON vbak.vbeln = vbap.vbeln
                WHERE vbak.vkorg = :iv_vkorg
                  AND vbak.auart <> 'XXX'  -- maybe not needed
                GROUP BY vbap.matnr
                ORDER BY umsatz DESC
                LIMIT 10;
```

Wait — one important detail: SUM(netwr) — NETWR is CURR type with 2 decimals. In AMDP, the return type must match. Currency handling: NETWR is stored with 2 decimals in the DB (CURR with 2 decimals). If I define the ABAP type as `p LENGTH 15 DECIMALS 2` that should work. Actually NETWR is CURR 15,2? NETWR is CURR length 15 (13 digits + 2 decimals?). NETWR domain: WERTV8? Let me think. VBAP-NETWR is CURR, length 15, decimals 2? Actually NETWR is of domain NETWR which is CURR(15) with 2 decimals? Hmm, NETWR domain: data type CURR, length 15, decimal places 2? Actually I believe NETWR is CURR 15,2? Let me recall: VBAP-NETWR — Net value — CURR, 15 length, 2 decimals? Hmm, actually I think it's length 15 with 2 decimals in the dictionary but stored as DEC(15,2)? Wait, on HANA, currency fields... NETWR domain is CURR, length 15, decimals 2. Hmm, actually I recall NETWR being CURR(15,2)? Or is it 13,2? Let me think: KWMENG is QUAN 13,3. NETWR is CURR 15,2? I believe NETWR is CURR length 15 decimals 2 — actually the domain NETWR has length 15 and 2 decimal places. Hmm, I've seen NETWR described as CURR(15,2). Yes, I'll go with that.

For the ABAP type, I can just use `vbap-netwr` directly for the sum? SUM(netwr) returns same type. But safer to define a dedicated type. In AMDP, the exporting table type must be a flat structure with elementary components — no strings, no deep types. Packed numbers are fine.

Also important: AMDP requires the types used for parameters to be known — DDIC types or types defined in the class (visible). Table types for tabular parameters must be DDIC table types or class-defined table types? For AMDP methods, tabular parameters must be typed with a table type that is either a DDIC table type or a type defined in the class public section? Actually: "The typing of tabular AMDP parameters must be a table type defined in ABAP Dictionary or in the class" — hmm. Let me recall the rules: AMDP parameters: elementary types are fine; tabular parameters must be typed with a table type from ABAP Dictionary (DDIC) — I believe class-local types are also allowed since they're flattened... Actually, from the documentation: "The typing of the tabular parameters must be a table type in ABAP Dictionary". Hmm, I recall that class-local table types work too as long as they are declared in the public visibility section? Let me think carefully.

From SAP documentation on AMDP: "Tabular input and output parameters must be typed with a table type from ABAP Dictionary." Hmm, actually I remember: "The type of a tabular parameter must be a table type defined in ABAP Dictionary." But I also recall that with newer releases, class-defined table types are allowed... Actually no. Let me recall more precisely: In AMDP, "The typing of tabular parameters must be a table type from the ABAP Dictionary" — I'm fairly sure the classic rule is DDIC table type. However, I've seen many examples using class-local types... Let me think about real examples from SAP documentation:

```abap
CLASS cl_demo_amdp DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES: BEGIN OF wa,
             id TYPE i,
             name TYPE string,
           END OF wa,
           itab TYPE STANDARD TABLE OF wa WITH EMPTY KEY.
    METHODS select_data
      IMPORTING VALUE(clnt) TYPE sy-mandt
      EXPORTING VALUE(results) TYPE itab.
ENDCLASS.

METHOD select_data BY DATABASE PROCEDURE
                   FOR HDB LANGUAGE SQLSCRIPT
                   OPTIONS READ-ONLY.
  results = SELECT id, name FROM demo_table
            WHERE mandt = :clnt
            ORDER BY id;
ENDMETHOD.
```

Hmm, actually in the official ABAP keyword documentation example for AMDP, they use a DDIC table type? Let me recall the demo class CL_DEMO_AMDP_INHERITANCE... I recall examples like:

```abap
METHODS select_data
  IMPORTING VALUE(mandt) TYPE sy-mandt
  EXPORTING VALUE(result) TYPE cl_demo_amdp=>itab.
```

Hmm. Actually I'm now fairly confident: Since 7.40, the rule is that tabular AMDP parameters must be typed with a table type from ABAP Dictionary OR a type defined in the same class (public section). Let me check my memory of the ABAP docs: "The typing of the tabular parameters must be a table type defined in ABAP Dictionary or in the public visibility section of the class." Hmm...

Actually, from the ABAP Keyword Documentation (AMDP - parameter interface): "Tabular parameters must be typed with a table type of the ABAP Dictionary." I keep going back and forth. Let me think about actual code I've seen in SAP standard: CL_ABAP_DAEMON... no. AMDP examples in SAP standard: CL_SADL_... hmm.

I recall the doc statement precisely now: from ABAP Keyword Documentation, "AMDP - Parameter Interface": "The typing of the tabular input and output parameters must be a table type in ABAP Dictionary." Hmm, but then there's a note: "In classes, the table types can also be defined in the visibility section of the class"? 

OK here's what I actually remember from writing AMDP: You CAN use class-local types declared in the PUBLIC SECTION. E.g., many blog examples:

```abap
CLASS zcl_amdp DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES: BEGIN OF ty_result,
             matnr TYPE matnr,
             umsatz TYPE netwr,
           END OF ty_result,
           tt_result TYPE STANDARD TABLE OF ty_result WITH DEFAULT KEY.
    METHODS get_data
      IMPORTING VALUE(iv_vkorg) TYPE vkorg
      EXPORTING VALUE(et_data) TYPE tt_result.
```

Yes, this pattern is extremely common in blogs and works. The documentation says: "The typing of the tabular parameters must be a table type from ABAP Dictionary or a table type defined in the class" — I'm now confident class-defined table types in the public section are allowed. Actually the exact doc text (7.52): "The typing of the tabular parameters must be a table type defined in ABAP Dictionary or in the public visibility section of the class." Hmm, I think there might be a restriction that the type must be visible... To be safe, I'll define the types in the public section of the class, which definitely works.

Now, the method signature rules:
- All parameters must be passed by value (VALUE(...)).
- No optional parameters? Actually optional parameters are allowed with DEFAULT? I think AMDP methods can have optional parameters... Hmm, actually I recall "no optional parameters" isn't a rule; RETURNING parameters are not allowed, only IMPORTING/EXPORTING/CHANGING? CHANGING is allowed? I believe IMPORTING and EXPORTING (and CHANGING?) are allowed, all by value. RAISING cx_amdp_error (or cx_amdp_creation_error, cx_amdp_execution_error) is recommended. Actually cx_amdp_error is the root? There's CX_AMDP_ERROR, CX_AMDP_CREATION_ERROR, CX_AMDP_EXECUTION_ERROR, CX_AMDP_ERROR_DYN... The common practice: `RAISING cx_amdp_error`.

- The method must be declared in a class implementing IF_AMDP_MARKER_HDB (for HANA).
- Implementation: `METHOD name BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT OPTIONS READ-ONLY USING vbak vbap.`

- The USING list must include all DDIC tables accessed (for read-only and dependency tracking). Actually with OPTIONS READ-ONLY, all accessed tables must be listed in USING. Yes.

Now the SQLScript body. Important details:
- Host variables in SQLScript are referenced with `:iv_vkorg`.
- The exporting table parameter is a scalar table variable; assign with `et_result = SELECT ...`.
- Aggregation: group by matnr, sum netwr, sum kwmeng, maybe count orders.
- TOP 10 vs LIMIT :iv_top_n — LIMIT with variable works in SQLScript: `LIMIT :iv_top_n`. But TOP requires constant? `TOP :iv_top_n` — I think TOP accepts a variable too in newer versions. Safest: use LIMIT :iv_top_n. Actually, in SQLScript, `LIMIT` can take a variable. Yes, LIMIT :var is supported.

But wait — if I want to demonstrate passing iv_top_n, using LIMIT :iv_top_n is nice. Alternatively hardcode TOP 10. The requirement says "Top-10-Materialien". I could make it flexible with iv_top_n default 10, or just hardcode 10. Let me include the parameter to show dynamism, but note that LIMIT :iv_top_n works. Hmm, but to keep it simple and robust, maybe I'll include iv_top_n with LIMIT :iv_top_n. That's fine.

Currency consideration: NETWR is in document currency (WAERS from VBAK). Summing NETWR across different currencies would be wrong, but for a demo it's typical to sum per sales org where currency is usually the same. I could group by matnr and mention currency caveat. Better: include WAERS in the result or note the caveat in the explanation. I'll mention it. Alternatively group by matnr, waers? VBAP has VRKME, VBAP-WAERS? No, WAERS is in VBAK. I could add vbak.waers to GROUP BY to be technically correct. Hmm, that complicates the "top 10 by revenue" if multiple currencies. For a clean demo, I'll sum NETWR and mention the currency caveat in the notes. Or include waers in the output and group by it. Let me keep it simple: group by matnr, take MAX(arktx), SUM(netwr) as umsatz, SUM(kwmeng) as menge. Add a comment about currency.

Actually, a nicer touch: use `CURRENCY_CONVERSION`? That's overkill. Just note it.

Also, should I filter out cancelled documents (VBAK-FAKSK?) or rejected items (VBAP-ABGRU)? A realistic touch: exclude items with ABGRU <> '' (rejection reason). I can add `AND vbap.abgru = ''`. That's a nice realistic detail. Also maybe only completed orders? Keep it simple but mention.

Let me also think about client handling: In AMDP, when accessing client-dependent tables, you should filter MANDT. Since AMDP runs on the DB with the session client... Actually AMDP does NOT automatically add client handling! Important: In AMDP, client handling must be done manually — the session variable CDS_CLIENT... Hmm. For AMDP methods, automatic client handling is not performed (unlike ABAP SQL). The recommendation: pass the client (sy-mandt) as an importing parameter and filter `WHERE mandt = :iv_mandt`. Yes — AMDP methods access tables without implicit client filtering; you must add MANDT explicitly. This is an important best practice to demonstrate. I'll include iv_mandt parameter and filter both vbak and vbap by mandt.

Wait, is that right? Let me double check: AMDP - client handling: "In AMDP methods, no implicit client handling is performed... the current client must be specified explicitly." Yes, that's correct. AMDP does not do implicit client handling; you must pass sy-mandt and filter. (There's also the option of using session variable via CDS, but for plain tables, explicit filter.) Good — I'll include that, it's an important correctness point.

Now the full code:

```abap
CLASS zcl_sd_top_materials DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    INTERFACES if_amdp_marker_hdb.

    TYPES: BEGIN OF ty_top_material,
             matnr  TYPE matnr,
             arktx  TYPE arktx,
             umsatz TYPE vbap-netwr,
             menge  TYPE vbap-kwmeng,
             waers  TYPE waers,
           END OF ty_top_material,

           tt_top_materials TYPE STANDARD TABLE OF ty_top_material WITH DEFAULT KEY.

    METHODS get_top_materials
      IMPORTING VALUE(iv_mandt) TYPE sy-mandt
                VALUE(iv_vkorg) TYPE vkorg
                VALUE(iv_top_n) TYPE i DEFAULT 10
      EXPORTING VALUE(et_top)   TYPE tt_top_materials
      RAISING   cx_amdp_error.
ENDCLASS.


CLASS zcl_sd_top_materials IMPLEMENTATION.

  METHOD get_top_materials
    BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT
    OPTIONS READ-ONLY
    USING vbak vbap.

    et_top =
      SELECT TOP :iv_top_n   -- hmm, TOP with variable?
```

Hmm, TOP with a variable: `SELECT TOP :iv_top_n` — I believe TOP requires a literal? In HANA SQL, TOP n where n must be a non-negative integer constant? Actually HANA supports `TOP ?` with parameter binding. In SQLScript, `SELECT TOP :var` — I'm not 100% sure. LIMIT :var is definitely supported in HANA SQL (LIMIT accepts expression). Let me use `LIMIT :iv_top_n` at the end. Yes, LIMIT with a variable is supported.

So:

```sql
    et_top =
      SELECT vbap.matnr                    AS matnr,
             MAX( vbap.arktx )             AS arktx,
             SUM( vbap.netwr )             AS umsatz,
             SUM( vbap.kwmeng )            AS menge,
             MAX( vbak.waers )             AS waers
        FROM vbap
        INNER JOIN vbak
           ON vbak.mandt = vbap.mandt
          AND vbak.vbeln = vbap.vbeln
       WHERE vbap.mandt = :iv_mandt
         AND vbak.vkorg = :iv_vkorg
         AND vbap.abgru = ''           -- keine abgelehnten Positionen
       GROUP BY vbap.matnr
       ORDER BY umsatz DESC
       LIMIT :iv_top_n;
```

Hmm wait, one issue: ORDER BY umsatz DESC — can you order by alias in SQLScript? Yes, HANA allows ordering by column alias. Yes.

Another consideration: `vbap.abgru = ''` — in SQLScript, comparing to empty string: ABGRU is CHAR 2. `''` works. Or `vbap.abgru = ' '`. In HANA, '' and ' ' — HANA SQL treats '' as empty string; for CHAR columns with trailing space semantics... ABAP CHAR fields are space-filled. Comparing = '' in HANA on a NVARCHAR column: HANA pads? HANA VARCHAR comparison doesn't pad by default? Actually HANA does compare with padding for CHAR? Hmm. In AMDP, ABAP CHAR fields map to NVARCHAR. Comparing `abgru = ''` — HANA: '  ' = '' is false unless padding... Actually HANA SQL: trailing spaces are significant in comparison? For VARCHAR, 'a' <> 'a '. Hmm, but many AMDP examples use `= ''` for CHAR fields and it works because... Actually in HANA, when comparing string values, blank-padded comparison is used for CHAR type but NVARCHAR is not blank-padded. ABAP CHAR maps to NVARCHAR in HANA. So '  ' (two spaces) = '' would be FALSE. Hmm, that could be a bug.

Safer: `AND vbap.abgru = '  '`? That's fragile too (length 2). Better: `AND LENGTH(TRIM(vbap.abgru)) = 0`? Or `AND vbap.abgru NOT BETWEEN ...` hmm. Common approach in AMDP examples: `WHERE abgru = ''` — I've seen this in SAP examples... Actually, hmm. Let me think. In HANA, string comparison: '  ' = '' → I believe HANA does NOT pad, so false. But wait, many AMDP code samples filter `land1 = 'DE'` fine; for empty char, people often use `field = ''` and it seems to work? Let me think again: HANA SQL reference: "Character String Types — comparison: trailing blanks are considered"? Actually HANA: "When you compare two strings of different lengths, the shorter string is padded with blanks"? I recall HANA does blank-padded comparison semantics for CHAR but for VARCHAR/NVARCHAR it's binary comparison. Hmm, but actually I believe HANA treats all character comparisons with padding? Let me recall: In HANA, `SELECT ... WHERE 'a' = 'a '` returns... I believe TRUE because HANA pads shorter string with spaces for comparison? Hmm, I genuinely am not sure. 

Actually, I recall from SAP AMDP examples in the ABAP documentation: `WHERE carrid = :carrid AND connid = :connid` — no empty-string examples. But I've seen community code like `WHERE loekz = ''`. Hmm.

To be safe and pedagogically clean, I could avoid the ABGRU filter or use `IF vbap.abgru IS NOT NULL`... ABGRU empty in ABAP is '  ' (spaces), stored as '  ' in NVARCHAR(2). So `vbap.abgru = ' '`? For NVARCHAR(2), the value stored is '  ' (two spaces). Comparing with '' — if HANA pads, true; if not, false.

Alternative safe approach: `AND vbap.abgru = SPACE(2)`? Or simply drop this filter to avoid the rabbit hole, or mention it as optional. Actually, I know HANA does blank-padded comparison: From HANA SQL docs: "Comparison predicates... For character string types, the values are compared... shorter operand is padded with blanks"? Hmm, I really think HANA pads: e.g., `SELECT 'a' FROM DUMMY WHERE 'a' = 'a '` returns 'a'. I'm fairly confident HANA ignores trailing blanks in comparisons (like padding semantics). Yes — HANA SQL: "Trailing blanks are not significant in string comparisons" — I believe that's right for HANA. E.g., WHERE 'abc' = 'abc ' is TRUE in HANA. I'm fairly confident about this.

OK so `vbap.abgru = ''` would be TRUE for '  '. I'll keep it but maybe simplify. Actually, to reduce risk of confusing the reader, I might keep the filter with a comment "abgelehnte Positionen ausschließen". It adds realism. Fine.

Another point: SUM(netwr) — netwr is CURR 15,2? Actually VBAP-NETWR domain NETWR: CURR, length 15, decimal 2? Hmm, I think NETWR is CURR(15,2)? Wait — I recall NETWR being length 15 with 2 decimals... Actually I now recall: domain NETWR: Data type CURR, Length 15, Decimal places 2? Hmm, but there's also WERTV8... VBAP-NETWR: I'm fairly sure it's CURR 15,2? Let me think of KZWRT... In ECC, VBAP-NETWR is CURR length 15 decimals 2? Hmm, actually I think it might be 13,2? Let me recall SE11: NETWR domain — "Net value" — CURR, 15, 2? I've seen `netwr TYPE netwr` with values like 1,000.00. The exact length doesn't matter much if I type the component as `vbap-netwr` directly. SUM over it in HANA returns DECIMAL(15,2)? On HANA, CURR columns are DECIMAL(15,2)? Actually on HANA, CURR 15,2 is stored as DECIMAL(15,2)? Hmm, HANA stores currency fields as DECIMAL with the dictionary scale... The ABAP type mapping: CURR → DEC(n,s). SUM(DEC(15,2)) → DECIMAL(15,2)? HANA's SUM returns same data type for decimals? Might escalate precision but mapping back to p 15,2 works.

To be safe, I'll type umsatz as `TYPE vbap-netwr` — wait, but can I reference `vbap-netwr` in a TYPES statement? Yes: `umsatz TYPE vbap-netwr`. That's clean.

Hmm, but one subtlety: SUM(netwr) could overflow netwr's range? Unlikely for demo. Fine.

Also menge: SUM(kwmeng) — kwmeng is QUAN 13,3. Type `vbap-kwmeng`. Fine.

Now, about the AMDP method parameter types: `iv_top_n TYPE i` — integer is fine (maps to INT). `iv_mandt TYPE sy-mandt` — CLNT(3) fine. `iv_vkorg TYPE vkorg` — CHAR 4 fine.

One more AMDP rule: parameters must be passed by value — I have VALUE(...) everywhere. Exporting parameters in AMDP must also be by value. Yes.

Also: the AMDP method cannot have RETURNING parameters; only IMPORTING/EXPORTING/CHANGING? CHANGING allowed? I think CHANGING is allowed for AMDP? Hmm, actually I believe AMDP methods support IMPORTING, EXPORTING, and CHANGING parameters, all pass-by-value. RAISING cx_amdp_error is good practice.

Now the USING clause: `USING vbak vbap` — must list all DDIC tables accessed. Correct.

OPTIONS READ-ONLY: the method only reads. Good practice; also required for usage in certain contexts (e.g., during replication?). I'll use READ-ONLY.

Now the ABAP call:

```abap
DATA(lo_top) = NEW zcl_sd_top_materials( ).

TRY.
    lo_top->get_top_materials(
      EXPORTING
        iv_mandt = sy-mandt
        iv_vkorg = '1000'
        iv_top_n = 10
      IMPORTING
        et_top   = DATA(lt_top) ).

    cl_demo_output=>display( lt_top ).  -- or write a loop
  CATCH cx_amdp_error INTO DATA(lx_amdp).
    MESSAGE lx_amdp->get_text( ) TYPE 'I'.
ENDTRY.
```

Or in modern syntax:

```abap
TRY.
    NEW zcl_sd_top_materials( )->get_top_materials(
      EXPORTING iv_mandt = sy-mandt
                iv_vkorg = '1000'
      IMPORTING et_top   = DATA(lt_top) ).
  CATCH cx_amdp_error INTO DATA(lx).
    ...
ENDTRY.
```

Note: since et_top is EXPORTING, inline declaration with IMPORTING works: `IMPORTING et_top = DATA(lt_top)`.

Also note: AMDP methods can be called only within the same system (no RFC), and the class instance — AMDP methods are instance methods typically (can also be static? AMDP methods can be instance or static methods; both allowed). I'll make it an instance method; could also make it static. Instance is the common pattern.

Now the explanation part: "Wann lohnt sich AMDP gegenüber ABAP-SQL?"

Key points:
1. **Push-down of complex logic**: When large data volumes must be aggregated/filtered/joined and only a small result is needed — code pushdown reduces data transfer between DB and AS. But note: modern ABAP SQL also does pushdown (aggregations, joins run on DB too). So AMDP is not automatically faster for simple queries — ABAP SQL generates SQL that runs on the DB as well.

2. When AMDP really adds value:
   - **HANA-specific features** not available in ABAP SQL: e.g., hierarchical queries (HIERARCHY functions are in ABAP SQL now), window functions (now available in ABAP SQL since 7.54), but things like: `MAP`, geospatial functions, full-text search (CONTAINS), fuzzy search, text analysis, predictive functions (PAL/APL), series data, `UNNEST`, `GREATEST`... Some are now in ABAP SQL. Still: AMDP gives full access to SQLScript: imperative logic (IF/WHILE/loops), local table variables, intermediate results, dynamic SQL (with AMDP procedures using EXEC?), CE functions (CALCULATION ENGINE), user-defined libraries.
   - **Multi-step procedural logic**: intermediate result sets reused multiple times (temp results), avoiding repeated subqueries; imperative flow.
   - **Reuse of existing HANA artifacts?** Actually AMDP can implement database procedures that other DB objects call... and AMDP can call other AMDPs and database procedures.
   - **Performance-critical algorithms** where row-by-row logic in ABAP would require massive data transfer: implement in SQLScript with loops on DB side.
   - **CDS-based analyses with parameters + complex logic** — AMDP as implementation of CDS table functions! Important: CDS table functions with AMDP — access via Open SQL with parameters. That's a big use case.
   - **Lateral derivation**: AMDP needed for CDS table functions (client handling, parameters).
   - **Calling from AMDP: access to HANA-native objects** (calculation views, procedures) — e.g., read from a HANA calculation view via AMDP.
   - **Bypassing ABAP-only restrictions**: e.g., accessing tables not in ABAP Dictionary (schema objects) — AMDP can access any object in the schema.

3. When NOT needed:
   - Simple reads/joins/aggregations → Open SQL/ABAP SQL is sufficient, portable (any DB), supports buffering? (aggregates bypass buffer anyway), easier to maintain, testable, CDS integration, client handling automatic, authorization via CDS/AMDP? Note: AMDP has no automatic client handling and no implicit authority checks (ABAP SQL neither, but CDS access control only via Open SQL on CDS views).
   - Portability: AMDP is HANA-only (FOR HDB); code runs only on HANA DB. In mixed landscapes (anyDB), AMDP code is dead — though with dynamic switching... AMDP classes can have DB-specific implementations (marker interfaces for other DBs? There are marker interfaces for other DBs? IF_AMDP_MARKER... only HDB? There's a concept of AMDP alternatives with different DB procedures per DB — classes can implement multiple marker interfaces and the runtime picks the right one. E.g., IF_AMDP_MARKER_HDB for HANA. For other vendors there are no standard markers; you'd need your own? Actually the AMDP framework supports multiple database platforms via different marker interfaces — SAP delivers... hmm, I recall only IF_AMDP_MARKER_HDB exists for HANA; for other DBs there's the concept but SAP doesn't deliver markers for e.g. MSSDN? I think there are none delivered; the fallback: if no matching implementation, exception. There's a pattern with a factory selecting a class per DB. Keep it simple: AMDP = HANA-only.)

4. Technical considerations:
   - Debugging/tracing harder (though HANA Studio/ Eclipse debugging of SQLScript possible, AMDP debugger in ADT exists).
   - Transport/creation: procedures are created lazily at first call; syntax checked by ADT; requires correct DBML? 
   - No implicit client handling → must pass sy-mandt.
   - No automatic buffering.
   - Unit testing harder.
   - Only flat, elementary parameter types; no strings/deep types? Strings are not allowed in AMDP parameter types? Correct: AMDP parameters cannot be strings? Hmm — actually scalar types: "The elementary types of the parameters must be... no strings"? Let me recall: AMDP parameter typing: elementary ABAP types are allowed except... strings? I believe STRING/RAWSTRING are not allowed for AMDP parameters (because no SQLScript equivalent mapping for IN/OUT params? Actually HANA has NVARCHAR, could map...). The rule: "The typing of the parameters must be... elementary flat types; strings, deep types, reference types not allowed"? Hmm, I recall that STRING is NOT allowed in AMDP interfaces. Let me think: ABAP doc "AMDP - Parameter Interface": "The parameters must be passed by value... The typing must be... elementary types... Not allowed are strings..."? Hmm, actually I think strings ARE allowed? There's a known restriction: no strings, no deep types, no reference types, no generic types. I'm fairly confident STRING is not allowed for AMDP parameters. Wait — but I've seen AMDP with string parameters? Hmm. The ABAP docs: "The following is not supported: ... string, rawstring..."? Let me think about the actual doc: "AMDP methods can only have flat, elementary typed parameters" — I'll say: keine tiefen Typen, keine Strings? Hmm, risk. Let me recall concrete: trying `VALUE(iv_text) TYPE string` in an AMDP method → syntax error "Parameter IV_TEXT cannot be typed with a deep type"? I believe that's correct — deep types including strings are not allowed. Yes, I'm fairly confident: AMDP parameters must be typed with elementary flat types or table types of flat structures; STRING/RAWSTRING/deep are not allowed. Hmm wait, actually I now recall that strings ARE allowed since some release? There was a change: "AMDP: strings allowed"? I don't recall such a change. Keep the statement general: "nur flache, elementare Typen bzw. flache Tabellentypen; keine tiefen Typen". To be safe I'll say "flache Strukturen/elementare Typen; tiefe Typen (Strings, Tabellen in Strukturen) sind nicht erlaubt" — hmm, but is STRING really disallowed? Let me think once more... 

From ABAP Keyword Documentation, AMDP → "AMDP - Parameter-Interface": "Die Typing der Eingabe-/Ausgabeparameter muss ... elementare, flache Typen ... Tabellenparameter müssen mit Tabellentypen typisiert sein, deren Zeilentyp flach ist..." And there's a list of forbidden: "Generische Typen, Referenztypen, tiefere Typen wie Strings..." Hmm. Actually I found in memory: "The following types are not allowed: string, rawstring, decfloat16/34?" No, decfloat is fine I think. I'll just say deep/generic types not allowed and avoid claiming specifically about STRING... but STRING is a common gotcha. I'm quite sure STRING is not allowed in AMDP interfaces (mapping problem: HANA NVARCHAR is fine, but ABAP doc says no). Hmm, hmm. Actually wait — I recall CDS table function AMDP implementations often have parameters of type... abap.char etc. And I recall a rule "no strings" indeed. Let me just phrase: "nur elementare flache Typen und flache Tabellentypen – keine Strings, tiefen oder generischen Typen". I'll accept small risk; this is standard knowledge. Actually, to be safer, I could say "keine tiefen/generischen Typen (z. B. Strings, Referenzen)". OK.

5. Also mention: AMDP for CDS table functions (with parameters & client handling) is THE canonical use case; also AMDP as data source in CDS views? (CDS view entities can't include table functions? They can via association? Table functions can be used in CDS views.)

6. Mention alternatives timeline: since 7.40/7.50+, ABAP SQL got powerful features (window functions, CTE, expressions), so "pushdown" alone is not a reason anymore — the decision is about SQLScript-specific capabilities and procedural multi-step logic.

Also mention: buffering, portability, tooling (ADT required for AMDP editing — you can't properly edit AMDP in SE80? You can write it but syntax check of SQLScript requires... the ABAP syntax check checks the SQLScript? The SQLScript inside is checked at runtime creation; ADT provides static analysis. Mention ADT/Eclipse recommended.)

Also: AMDP cannot be called remotely; runs only on current DB connection; requires the AS ABAP to be connected to HANA as primary DB (or secondary connection? AMDP runs on the primary database by default; there's also AMDP via secondary connections? No — AMDP methods execute on the standard connection of the AS ABAP to its central DB; if the central DB is HANA. There's no AMDP on secondary connections.)

Let me also double check the SQLScript details:

- In AMDP SQLScript, referencing parameters: `:iv_vkorg`.
- Assigning result to export table parameter: `et_top = SELECT ...;` — correct. Each statement ends with `;`.
- The USING list: `USING vbak vbap` — table names in ABAP (they'll be mapped to actual schema tables).
- Client: I filter `vbap.mandt = :iv_mandt` and join condition includes mandt. Good.

- GROUP BY: `GROUP BY vbap.matnr` — but I select MAX(arktx) and MAX(waers) so it's consistent. OK.

- ORDER BY umsatz DESC: alias reference in ORDER BY — allowed in HANA. Also could ORDER BY 3 DESC. Fine.

- LIMIT :iv_top_n: supported. Also guard: if iv_top_n <= 0? Could add `IF :iv_top_n <= 0 THEN ...` — maybe add a small procedural touch to show SQLScript imperative features? Could demonstrate DECLARE + IF. But keep it focused; maybe show a tiny bit of procedural logic

</details>
