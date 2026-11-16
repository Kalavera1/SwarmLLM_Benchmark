# ABAP: alv-report

## Aufgabe

Schreibe einen ABAP-Report (S/4HANA, ABAP 7.5x-Syntax), der Kundenaufträge aus VBAK/VBAP für einen Selektionsbildschirm (Verkaufsorganisation, Erstelldatum von–bis) liest und als SALV-ALV ausgibt: Auftragsnummer, Position, Material, Menge, Nettowert. Mit Summen über den Nettowert, Inline-Deklarationen und sauberer Fehlerbehandlung.

## Antwort



---

<details><summary>Denkprozess (30825 Zeichen)</summary>

The user wants an ABAP report (S/4HANA, ABAP 7.5x syntax) that:
1. Reads sales orders from VBAK/VBAP
2. Selection screen: Sales organization (Verkaufsorganisation), creation date from-to (Erstelldatum von-bis)
3. Output as SALV ALV with: Order number (Auftragsnummer), Item (Position), Material (Material), Quantity (Menge), Net value (Nettowert)
4. With totals over the net value
5. Inline declarations
6. Clean error handling

The response should be in German since the question is in German. Let me write a proper ABAP report.

Key points for ABAP 7.5x:
- Inline declarations with DATA(...) and FINAL or DATA
- VALUE # constructors
- SALV (CL_SALV_TABLE)
- Exceptions with TRY/ENDTRY or classic EXCEPTIONS
- Modern SQL: SELECT with @ inline host variables, comma-separated field lists, INTO TABLE @DATA(...)
- FOR ALL ENTRIES or better: JOIN in single SELECT
- Aggregate for total: could use SUM in SQL or just use SALV aggregations

Best practice: Use a single SELECT with JOIN between VBAK and VBAP, using inline declaration. Then display with CL_SALV_TABLE, add aggregation for NETWR sum.

Error handling:
- Check if selection screen entries are valid
- Check if data is empty → message
- CATCH cx_salv_not_found, cx_salv_existing, cx_salv_msg when creating SALV
- Maybe check sales org exists (TVKO or just let it be)

Let me write the code:

```abap
REPORT zsd_sales_orders.

*----------------------------------------------------------------------*
* Selektionsbild
*----------------------------------------------------------------------*
SELECTION-SCREEN BEGIN OF BLOCK blk1 WITH FRAME TITLE TEXT-001.
  SELECT-OPTIONS s_vkorg FOR vbak-vkorg OBLIGATORY.
  PARAMETERS     p_erdat_f TYPE vbak-erdat OBLIGATORY.
  PARAMETERS     p_erdat_b TYPE vbak-erdat OBLIGATORY.
SELECTION-SCREEN END OF BLOCK blk1.
```

Hmm, better: SELECT-OPTIONS for ERDAT too, or PARAMETERS for from/to. The user said "Erstelldatum von–bis". Could use SELECT-OPTIONS s_erdat FOR vbak-erdat. That's simpler. Let me use SELECT-OPTIONS for both VKORG and ERDAT, with OBLIGATORY on erdat maybe not.

Actually "von–bis" suggests two parameters or a select-option. I'll use SELECT-OPTIONS s_erdat FOR vbak-erdat NO-EXTENSION NO INTERVALS? No — von-bis means intervals, so plain SELECT-OPTIONS works. Or PARAMETERS p_dat_vb and p_dat_bis. I'll go with SELECT-OPTIONS for flexibility but mention it. Actually let me keep it simple and clear: SELECT-OPTIONS s_vkorg FOR ... and s_erdat FOR ... Both OBLIGATORY? VKORG obligatory yes; erdat maybe obligatory to avoid full table scan. I'll make erdat obligatory as well — good practice for performance. Hmm, but obligatory on select-options means at least one value must be entered. That's fine.

Validation in AT SELECTION-SCREEN:
- Check ERDAT low <= high
- Optionally check VKORG exists in TVKO

Data selection:

```abap
SELECT v~vbeln,
       p~posnr,
       p~matnr,
       p~kwmeng,
       p~vrkme,
       p~netwr,
       v~waerk
  FROM vbak AS v
  INNER JOIN vbap AS p
    ON p~vbeln = v~vbeln
  WHERE v~vkorg IN @s_vkorg
    AND v~erdat IN @s_erdat
    AND v~trvog = @space  " hmm not needed
  ORDER BY v~vbeln, p~posnr
  INTO TABLE @DATA(lt_orders).
```

Wait — with inline declaration in INTO TABLE @DATA(lt_orders), the types come from the DB. NETWR is CURR 15,2? Actually VBAP-NETWR is CURR length 15 decimals 2. KWMENG is QUAN 13,3. WAERK is CUKY 5.

For the ALV output structure, I might define a local type or just use the derived type. But for SALV column settings, using the DDIC types helps with automatic currency/quantity handling. If we use inline declared table, the ALV will still pick up DDIC reference if the fields keep their DDIC types (they do, since SELECT preserves them). Currency reference: NETWR needs currency reference WAERK for correct display; KWMENG needs unit VRKME. SALV can handle that if the DDIC types are used — actually the currency/quantity relationship is defined at DDIC structure level (e.g., in a structure with reference fields). If we just select into an inline table, the ALV may not know the reference field. To be safe, I can define a local structure in the program with ... no, better: use SALV and set currency reference via column? CL_SALV_COLUMN_TABLE has set_currency_reference? There's set_quantity_reference? Actually in SALV: cl_salv_column_table->set_currency_reference( value = 'WAERK' ) and set_quantity_reference? Let me recall.

SALV column methods: CL_SALV_COLUMN_TABLE has methods SET_CURRENCY_REFERENCE? Hmm. There is SET_CURRENCY_SUBREFERENCE? I recall for SALV you can set:
- column->set_currency_reference( 'WAERK' )
- column->set_quantity_reference( 'VRKME' )

Actually the methods exist: CL_SALV_COLUMN_TABLE->SET_CURRENCY_REFERENCE( EXPORTING value ) and SET_QUANTITY_REFERENCE. Let me think... In SALV, there's IF_SALV_COLUMN... Hmm.

I know cl_salv_column_table has set_currency_reference and set_quantity_reference — yes, I'm fairly confident these exist (they mirror the ALV fieldcat properties CURRENCYNAME/QUANTITYNAME). Actually I recall the methods being on CL_SALV_COLUMN_TABLE: SET_CURRENCY_REFERENCE( 'WAERK' ) and SET_QUANTITY_REFERENCE( 'VRKME' ). Yes, these exist in SALV object model.

Alternatively, define a DDIC-independent local structure and set the references. To keep the example self-contained without custom DDIC structures, I'll set the references programmatically via loop over columns, or simpler: rely on SALV's automatic detection? SALV does automatic currency/quantity handling if the field names of reference fields are present in the data table and the column types are CURR/QUAN. Actually yes — SALV (and ALV) automatically detects reference fields by name if the output table fields have DDIC types CURR/QUAN and there are fields named like the reference... Hmm, not exactly: classic ALV fieldcat needs REF_FIELD/REF_TABLE or the field name of the currency field in the same table with CURRENCYNAME. SALV does automatic optimization: if the underlying type has DDIC references (via structure), it works. For inline declared types, the currency reference isn't automatically set because the derived structure has no reference fields defined.

To be robust, I'll explicitly set currency/quantity references in code. That demonstrates expertise.

Structure of the report:

1. REPORT statement with LINE-SIZE not needed.
2. TABLES: not needed (modern).
3. Selection screen with frame, texts (use text symbols or literal titles). Since I can't create text elements, I'll use string literals for frame titles? SELECTION-SCREEN ... WITH FRAME TITLE TEXT-001 requires text elements. I can define the title via SELECTION-SCREEN COMMENT or just use text symbols and note that they should be maintained. Common practice in examples: use TEXT-001 and mention maintaining text symbols. Alternatively use `WITH FRAME TITLE lv_title`? The TITLE addition expects a text symbol or a character variable? Actually `SELECTION-SCREEN BEGIN OF BLOCK b1 WITH FRAME TITLE text-001.` — text-001. You can also use a variable? I believe you can use any character-like field: `WITH FRAME TITLE title` where title is a data object filled at runtime — yes, that works (it's evaluated at AT SELECTION-SCREEN OUTPUT? Actually it's read at PAI/initialization...). Hmm, simpler: use TEXT-001 and add a comment that text symbols must be maintained, or avoid frames entirely. I'll use text symbols and note them. Or use SELECTION-SCREEN BEGIN OF BLOCK with frame title from a variable set in INITIALIZATION. That's clunky.

I'll just use TEXT symbols and mention in comments which text elements to maintain (001: 'Selektionskriterien', etc.). That's standard practice.

4. AT SELECTION-SCREEN validation:
   - s_erdat: check low/high
   - check VKORG against TVKO? Could do SELECT SINGLE FROM tvko. With inline: SELECT SINGLE @abap_true FROM tvko WHERE vkorg IN @s_vkorg. If sy-subrc <> 0 → message. That's nice modern syntax with @abap_true.

5. START-OF-SELECTION: data select with JOIN, inline declarations.

6. Error handling: if no data → MESSAGE 'Keine Daten...' TYPE 'S' DISPLAY LIKE 'E' and RETURN (or LEAVE LIST-PROCESSING).

7. END-OF-SELECTION: build SALV:
   - cl_salv_table=>factory( IMPORTING r_salv_table = DATA(lo_alv) CHANGING t_table = lt_orders ) with TRY/ENDTRY catching cx_salv_msg? Actually factory raises cx_salv_msg? The factory method has exception cx_salv_msg? Hmm: cl_salv_table=>factory raises CX_SALV_MSG? Let me recall: factory( ) exceptions: cx_salv_msg? I think it's CX_SALV_MSG? Hmm, actually I believe factory raises `cx_salv_msg`? Let me think. The SALV factory method signature:

```abap
cl_salv_table=>factory(
  IMPORTING
    r_salv_table = lo_alv
  CHANGING
    t_table = lt_tab ).
```

Exceptions: CX_SALV_MSG? I recall CX_SALV_MSG is raised by factory. Hmm, there's also CX_SALV_NOT_FOUND, CX_SALV_EXISTING, CX_SALV_ALREADY_CONNECTED... For factory, the declared exception is cx_salv_msg? Let me recall from SAP examples:

```abap
TRY.
    cl_salv_table=>factory(
      IMPORTING
        r_salv_table = gr_table
      CHANGING
        t_table      = gt_table ).
  CATCH cx_salv_msg INTO lx_msg.
ENDTRY.
```

Yes, standard SAP tutorial uses CATCH cx_salv_msg. Good.

   - Functions: lo_alv->get_functions( )->set_all( abap_true ).
   - Columns: optimize width, set texts maybe.
   - Aggregations: lo_alv->get_aggregations( )->add_aggregation( columnname = 'NETWR' aggregation = if_salv_c_aggregation=>total ). Also set the aggregation to be displayed: get_aggregations( )->set_aggregation_before_items? For flat table, total row shows at bottom. Need lo_alv->get_aggregations( )->add_aggregation( ... ). Also maybe set display settings: lo_alv->get_display_settings( )->set_list_header(...). 
   - Layout: set key columns (VBELN, POSNR) via get_columns( )->set_key_fixation? Or column->set_key( ). 
   - Sort by VBELN/POSNR: get_sorts( )->add_sort( columnname = 'VBELN' ... ).
   - Display: lo_alv->display( ).

   Catch cx_salv_not_found for column operations (e.g., set column references). Wrap in TRY.

8. Also add total via SQL? The user says "Mit Summen über den Nettowert" — sums over net value. SALV aggregation gives interactive totals. Could also compute a total in the select via UNION or a second SELECT with SUM. I think SALV aggregation (Total row) is the cleanest interpretation. I could additionally show the total as a message or compute SUM in SQL. I'll implement SALV aggregation (subtotal/total) — that's the standard approach. Maybe also mention alternative: SUM in SELECT.

Actually, to be thorough: I can do the aggregation in SALV and mention that. The requirement "Mit Summen über den Nettowert" — totals over net value. SALV total row satisfies it.

Let me also consider: NETWR is net value of the item (VBAP-NETWR). Yes.

Quantity: KWMENG (cumulative order quantity) with VRKME (sales unit). Material: MATNR.

Selection screen fields: VKORG (Verkaufsorganisation) — SELECT-OPTIONS or PARAMETER? "für einen Selektionsbildschirm (Verkaufsorganisation, Erstelldatum von–bis)" — I'll use SELECT-OPTIONS for VKORG (multiple possible) and SELECT-OPTIONS for ERDAT (interval). Or PARAMETER for VKORG. Either fine. I'll use SELECT-OPTIONS for both, obligatory.

Additional nice touches:
- Use FINAL for read-only inline declarations (7.5x? FINAL is 7.50+? FINAL inline declaration DATA(...) vs FINAL(...) — FINAL is available since 7.50/7.51? FINAL(...) inline declarations came with 7.50? Actually FINAL was introduced in ABAP 7.50? Hmm. FINAL( ) for immutable inline declarations was introduced in ABAP release 7.50? I believe FINAL came with 7.50 ("FINAL - Inline-Deklaration ... Verfügbare Releases: ab 7.50"? Let me think. ABAP News for 7.50: FINAL inline declarations? I recall FINAL was introduced with ABAP 7.50 (NetWeaver 7.50) — actually I think it was 7.50. Hmm, some sources say FINAL is available as of 7.50. Let me double check memory: ABAP keyword documentation "FINAL, Inline" — "Availability: ABAP 7.50"? I'm not 100% sure. I recall blogs "ABAP 7.50: FINAL(...)"? Hmm, actually I think FINAL inline declaration was introduced in ABAP 7.50 along with table functions? There were ABAP news for 7.50: table expressions enhancements, CONV, FINAL? I believe FINAL came with 7.50. Wait — I recall Horst Keller's blog "ABAP News for Release 7.50" mentioning FINAL? Hmm, I actually recall FINAL being introduced in 7.50: "FINAL(...) can be used instead of DATA(...) for read-only". Hmm, but I also have a memory that FINAL came with 7.40 SP08? No...

Let me think more carefully. ABAP 7.40 introduced inline DATA(...). FINAL(...) — I'm fairly sure it's 7.50. Yes, ABAP News for 7.50 included FINAL inline declarations (immutable helper variables). Actually hold on, I think I recall "FINAL" being introduced with ABAP 7.50 in the context of "Value semantics"? Hmm.

To be safe, I can use DATA(...) everywhere and mention FINAL(...) as an option in a comment. Since the user said "7.5x-Syntax", FINAL would be fine if it's 7.50+. I'll use FINAL for the internal result table and helper variables where appropriate, but if uncertain, DATA is safer. Let me verify: ABAP keyword docs: "FINAL - Inline declaration for immutable variables ... Introduced in ABAP 7.50"? I genuinely believe FINAL is 7.50. There's a known blog by Horst Keller: "ABAP News for Release 7.50 – FINAL"? Hmm... I recall "ABAP 7.50: FINAL" yes. OK I'll use FINAL for the selected data table (it's not modified) — that showcases 7.5x. But careful: if we pass the table to SALV CHANGING t_table, it doesn't modify contents, fine. But FINAL variables can't be changed; passing to CHANGING parameter doesn't require modification by us. OK.

Hmm, but risk: if FINAL is actually 7.52+? Let me think again. I have decent memory that FINAL(...) was introduced in ABAP 7.50. Example from Keller's blog "ABAP News for 7.50": features included: table expressions with VALUE, FINAL? Hmm. Actually I now recall more specifically: FINAL inline declarations were introduced with ABAP 7.50 — yes, e.g., "FINAL(lo_alv)"? Hmm.

Alternatively, to minimize risk of using a feature that might not exist in the customer's release, I could use DATA(...) throughout and add a comment that FINAL(...) could be used for read-only variables as of 7.50. That's safe and still "7.5x". Actually, let me just be confident: FINAL is documented as "Verfügbar ab ABAP 7.50"? I'm going to check my memory of the ABAP keyword documentation: "FINAL - Inline-Deklaration ... Der Operator FINAL ... seit Release 7.50"? I believe there's a statement in ABAP docs: "FINAL is available since 7.50". Hmm, I also recall that FINAL was introduced together with "with ... then" (7.50)? No, WITH...THEN is 7.50 too? WITH...THEN (common table expressions) is 7.50? Hmm, WITH came in 7.50. REDUCE 7.40. COND/SWITCH 7.40. FILTER 7.40. FINAL 7.50 — yes I'm fairly confident.

OK, I'll use FINAL for the data table and maybe lo_alv. But note: with FINAL, you cannot use it in CHANGING? You can pass it as actual parameter to CHANGING formal param — the restriction is you can't modify it in the program itself; passing to CHANGING is allowed? Actually FINAL variables cannot be used in positions where they could be changed — passing to a CHANGING parameter is such a position! The ABAP checker may reject FINAL variables as actual parameters for CHANGING/P (non-use) positions. Yes! That's a real restriction: FINAL variables can only be used in reading positions. A CHANGING parameter is a writing position, so FINAL(...) cannot be passed to CHANGING t_table. So for the SALV factory call I must use DATA(lo_alv) and the table passed as CHANGING must also not be FINAL. Hmm — t_table is CHANGING, so passing a FINAL table would be a syntax error. So use DATA(...) for the result table. OK, I'll use DATA(...) for the table, and FINAL for genuinely read-only things like counts or the check result. Fine.

Also modern: use @abap_true, strict mode declared via pragma? Add "##TODO"? Not needed.

Let me draft the full code:

```abap
*&---------------------------------------------------------------------*
*& Report ZSD_ORDER_LIST
*& Listet Kundenaufträge (VBAK/VBAP) als SALV-ALV mit Nettowert-Summe
*&---------------------------------------------------------------------*
REPORT zsd_order_list.

*----------------------------------------------------------------------*
* Selektionsbild
*----------------------------------------------------------------------*
SELECTION-SCREEN BEGIN OF BLOCK b1 WITH FRAME TITLE TEXT-001.
  SELECT-OPTIONS: s_vkorg FOR vbak-vkorg OBLIGATORY MEMORY ID vko,
                  s_erdat FOR vbak-erdat OBLIGATORY.
SELECTION-SCREEN END OF BLOCK b1.

* Zusätzlich: Auftragsart optional
SELECT-OPTIONS s_auart FOR vbak-auart.
```

Hmm, keep it to what was asked; maybe add AUART as optional bonus? The user asked specifically for VKORG and ERDAT. Keep it minimal but maybe add order type as optional — no, keep exactly what's asked to avoid clutter. Maybe I'll keep just the two.

Note: using `FOR vbak-vkorg` requires the table to be known — without TABLES statement, referring to vbak-vkorg in SELECT-OPTIONS... In modern ABAP, you can't use `FOR vbak-vkorg` without TABLES or NODES? Actually you can reference DDIC types directly: `SELECT-OPTIONS s_vkorg FOR vbak-vkorg` — this uses the DDIC table field, which is allowed because VBAK is a DDIC table/structure visible in the ABAP data dictionary — the FOR reference needs a flat structure/field visible in the program. DDIC tables are visible without TABLES since... hmm. Classic: you need TABLES: vbak. to use vbak-vkorg. But you can also do `SELECT-OPTIONS s_vkorg FOR gv_vkorg` with DATA gv_vkorg TYPE vkorg. Or reference the data element directly: `SELECT-OPTIONS s_vkorg FOR ...` must reference a field of a structure. 

Modern approach: `SELECT-OPTIONS s_vkorg FOR vbak-vkorg.` works without TABLES? I believe referencing DDIC table fields in SELECT-OPTIONS FOR requires the object to be declared — TABLES statement makes the flat structure available. Without TABLES, `vbak-vkorg` is not a valid reference in the program... Actually, in ABAP Objects context, DDIC table fields like `vbak-vkorg` are not accessible without TABLES/NODES. Hmm, but I've seen many modern programs write `SELECT-OPTIONS s_matnr FOR mara-matnr.` without TABLES — does that compile? I believe yes it does! Because SELECT-OPTIONS FOR with a DDIC table field is allowed; the system implicitly? Hmm.

Let me think. The rule: FOR must reference a data object or a DDIC structure field? The documentation: "SELECT-OPTIONS seltab FOR dobj." — dobj must be a data object that is character-like or... Actually there's a variant referencing DDIC: "FOR f" where f is a flat field from ABAP Dictionary — this requires TABLES? In older ABAP, TABLES declared the work area. In modern syntax checks, I believe `SELECT-OPTIONS s_matnr FOR mara-matnr.` still works because the DDIC field reference is resolved statically — many standard SAP reports use it without TABLES? Hmm, actually no — standard reports typically have TABLES: mara. or use `FOR gs_data-matnr`.

Let me recall concretely: I've written reports like:

```abap
SELECT-OPTIONS: s_werks FOR t001w-werks.
```

without TABLES and it compiled fine. Yes — I'm quite sure this works in modern ABAP (7.40+): the FOR reference can be a DDIC table field directly, no TABLES needed. The ABAP doc says: "The data object dobj... can be a data object of the program or a flat structure/field of the ABAP Dictionary"? Hmm.

Actually the documentation for SELECT-OPTIONS: "seltab FOR dobj" where dobj: "Data object... It can be a data object of the same program or a component of a flat data structure from ABAP Dictionary (table or view field)". And I believe DDIC references don't require TABLES. Yes — e.g., `PARAMETERS p_carrid TYPE s_carr_id` uses data element; for SELECT-OPTIONS people commonly use `FOR mara-matnr` without TABLES and it works. I'm fairly confident. Many community code samples do exactly that. OK, use it.

Alternatively, to be extra safe, declare data objects: `DATA gv_vkorg TYPE vkorg.` and `SELECT-OPTIONS s_vkorg FOR gv_vkorg.` That also works and is unambiguous. But using DDIC field gives F4 help automatically (search help from DDIC). `FOR vbak-vkorg` gives the F4 of the DDIC field. I'll use DDIC fields directly — standard practice.

Text symbols: I'll reference TEXT-001 etc. and add a comment listing suggested texts. Or use literals? Frame TITLE requires text symbol or variable? Actually `WITH FRAME TITLE title` where title can be a text symbol or a data object of type c? The doc: "TITLE title: title expects a character-like data object or text symbol". Hmm, if it's a data object, its content at AT SELECTION-SCREEN OUTPUT time? I think frame titles from variables are read when the screen is generated (PBO), so you could fill in INITIALIZATION. To keep it simple: use text symbols TEXT-001, TEXT-002 and note them. Many example programs do this. I'll add a comment block listing the text elements to maintain.

Alternatively avoid frames: just SELECT-OPTIONS without block. But a block with frame looks professional. I'll include with text symbols and document them.

Now the main select. Consider performance: VBAK/VBAP join with VKORG + ERDAT ranges uses index VBAK~0? Primary key is VBELN. Index on ERDAT exists? There's index VBAK~ERD (ERDAT?) not guaranteed. Standard practice: FOR ALL ENTRIES or join. A join VBAK→VBAP with WHERE vkorg IN s_vkorg AND erdat IN s_erdat is fine for a report; SAP pushes down to HANA in S/4. Fine.

Also add AUART filter to only sales orders? "Kundenaufträge" = document type TA (order). Could restrict VBAK~TRVOG = space and VBAK~AUART... Not necessary; keep general but maybe comment. I might restrict to `v~trvog = space`? Hmm, TRVOG distinguishes transaction group (0 = order?). Actually TRVOG: 0 = sales order etc. Not needed; keep simple. Maybe add optional AUART select-option — I'll skip to keep focused, but could mention in remarks.

Field list: vbeln, posnr, matnr, arktx (optional), kwmeng, vrkme, netwr, waerk. The user asked: Auftragsnummer, Position, Material, Menge, Nettowert. I'll include VRKME and WAERK as reference fields (needed for correct display) — justified.

SELECT:

```abap
SELECT vbak~vbeln,
       vbap~posnr,
       vbap~matnr,
       vbap~arktx,
       vbap~kwmeng,
       vbap~vrkme,
       vbap~netwr,
       vbak~waerk
  FROM vbak
  INNER JOIN vbap ON vbap~vbeln = vbak~vbeln
  WHERE vbak~vkorg IN @s_vkorg
    AND vbak~erdat IN @s_erdat
  ORDER BY vbak~vbeln, vbap~posnr
  INTO TABLE @DATA(lt_items).
```

In S/4HANA, VBAP-MATNR is MATNR (40 chars in S/4 with MATNR extended). Fine.

If sy-subrc <> 0 → message.

SALV:

```abap
TRY.
    cl_salv_table=>factory(
      IMPORTING
        r_salv_table = DATA(lo_alv)
      CHANGING
        t_table      = lt_items ).
  CATCH cx_salv_msg INTO DATA(lx_msg).
    MESSAGE lx_msg->get_text( ) TYPE 'E'.
    RETURN.
ENDTRY.
```

Hmm, MESSAGE with a string: MESSAGE ... TYPE 'E' — in a report, TYPE 'E' in list processing shows as status? For simplicity use TYPE 'S' DISPLAY LIKE 'E' then RETURN? In START-OF-SELECTION, TYPE 'E' terminates. Fine either way. I'll use 'S' DISPLAY LIKE 'E' to be gentle, then RETURN.

Functions: lo_alv->get_functions( )->set_all( abap_true ).

Columns: 
- optimize: lo_alv->get_columns( )->set_optimize( abap_true ).
- key columns: DATA(lt_cols)? Loop: 

```abap
LOOP AT lo_alv->get_columns( ) INTO DATA(lo_col)? 
```

Hmm, get_columns returns CL_SALV_COLUMNS_TABLE; to iterate individual columns: `lo_alv->get_columns( )->get( )` returns table of ref? Simpler: set specific ones:

```abap
TRY.
    DATA(lo_col_netwr) = CAST cl_salv_column_table( lo_alv->get_columns( )->get_column( 'NETWR' ) ).
    lo_col_netwr->set_currency_reference( 'WAERK' )? 
```

Hmm wait — does CL_SALV_COLUMN_TABLE have SET_CURRENCY_REFERENCE? Let me recall SALV column API: CL_SALV_COLUMN has methods: set_long_text, set_medium_text, set_short_text, set_output_length, set_visible, set_technical, set_alignment... CL_SALV_COLUMN_TABLE adds: set_ddic_reference? Hmm. Let me recall the actual methods for currency/quantity in SALV.

I recall in SALV you set currency/quantity via the column object: cl_salv_column_table->set_currency_reference( value = 'WAERK' )? Hmm, I genuinely recall these methods existing: SET_CURRENCY_REFERENCE and SET_QUANTITY_REFERENCE on CL_SALV_COLUMN_TABLE. Let me search memory: In many SALV examples:

```abap
DATA(lo_column) = CAST cl_salv_column_table( alv->get_columns( )->get_column( 'NETWR' ) ).
lo_column->set_currency_reference( 'WAERK' ).
```

Hmm... I've also seen: `lo_column->set_quantity_reference( 'VRKME' )`? I believe both exist. Actually wait — I think the methods might be on CL_SALV_COLUMN_TABLE: yes, there are methods SET_CURRENCY_REFERENCE and SET_QUANTITY_REFERENCE? Hmm, alternatively it's done via r_salv_table->get_columns()->set_currency_reference? No.

Let me think about the SALV class hierarchy: CL_SALV_COLUMN (abstract) → CL_SALV_COLUMN_TABLE. CL_SALV_COLUMN_TABLE methods include: SET_CURRENCY_REFERENCE? Hmm, I recall the property in the underlying field catalog is CURRENCYNAME / QUANTITYNAME, and SALV exposes them... I'm fairly confident there are methods set_currency_reference( ) and set_quantity_reference( ) on cl_salv_column_table. Yes — e.g., from SAP community examples:

```abap
lo_column ?= lo_cols->get_column( 'NETWR' ).
lo_column->set_currency_reference( 'WAERK' ).
```

I've definitely seen this pattern. OK good.

Alternatively, avoid the issue: since we select WAERK and VRKME into the table, and the columns keep DDIC types (CUKY/UNIT), ALV might auto-detect? Classic ALV auto-detects reference fields only if REF_FIELD/REF_TABLE set or if the field catalog field CURRENCYNAME is filled. SALV auto-generates fieldcat from the table type; for inline table types, the components have DDIC types but no reference field assignments. So auto-detection of currency reference does NOT happen automatically. So explicit set is right.

Hmm wait, actually there IS automatic currency/quantity handling in ALV when the output structure contains fields of type CURR and the reference field is in the same structure with a name that... no, classic ALV requires CURRENCYNAME explicitly unless using DDIC structure where reference is defined. So explicit setting is correct and demonstrates know-how.

Also set texts for columns (long text) — optional; SALV takes DDIC texts automatically since types are DDIC. Good.

Aggregation:

```abap
DATA(lo_aggr) = lo_alv->get_aggregations( ).
lo_aggr->add_aggregation( columnname = 'NETWR'
                          aggregation = if_salv_c_aggregation=>total ).
```

add_aggregation raises cx_salv_not_found / cx_salv_existing / cx_salv_data_error? Wrap in TRY.

Also: lo_aggr->set_aggregation_before_items( abap_false )? For flat lists, the total appears as a separate row at the end automatically. Hmm, in flat (non-hierarchical) SALV, adding a TOTAL aggregation shows a total row at the bottom. Yes.

Sorts:

```abap
lo_alv->get_sorts( )->add_sort( columnname = 'VBELN' position = 1 sequence = if_salv_c_sort=>sort_up ).
```

add_sort raises cx_salv_not_found etc.

Display settings: 
```abap
lo_alv->get_display_settings( )->set_list_header( 'Kundenaufträge' )? 
```
set_list_header( |Kundenaufträge ...| ). Also set_striped_pattern( abap_true ).

Layout key: lo_alv->get_layout( )->set_key( VALUE #( report = sy-repid ) )? and set_default? get_layout( )->set_save_restriction( if_salv_c_layout=>restrict_none ). Nice touch for saving layouts. Keep moderate.

Display: lo_alv->display( ).

Error handling around column/sort/aggregation ops: wrap all in one TRY ... CATCH cx_salv_not_found INTO DATA(lx_not_found) ... etc. Or catch cx_salv_not_found and cx_salv_existing and cx_salv_data_error. There's also CX_SALV_MSG base? CX_SALV_NOT_FOUND etc. inherit from CX_SALV_EXCEPTION? Hmm: CX_SALV_NOT_FOUND inherits from CX_SALV_EXCEPTION? I think the SALV exception hierarchy: CX_SALV_EXCEPTION (CX_STATIC_CHECK?) with subclasses CX_SALV_NOT_FOUND, CX_SALV_EXISTING, CX_SALV_DATA_ERROR, CX_SALV_MSG, CX_SALV_OBJECT_NOT_FOUND... Catching CX_SALV_EXCEPTION? Hmm, not sure CX_SALV_EXCEPTION exists. I recall CX_SALV_MSG is a catchable class used by factory. And CX_SALV_NOT_FOUND, CX_SALV_EXISTING, CX_SALV_DATA_ERROR are separate. To be safe, catch the specific ones: cx_salv_not_found, cx_salv_existing, cx_salv_msg, cx_salv_data_error. Hmm, is CX_SALV_DATA_ERROR a thing? There's CX_SALV_DATA_ERROR? I recall CX_SALV_DATA_ERROR exists? Hmm. Known SALV exceptions: CX_SALV_MSG, CX_SALV_NOT_FOUND, CX_SALV_EXISTING, CX_SALV_DATA_ERROR, CX_SALV_OBJECT_NOT_FOUND, CX_SALV_WC_... For add_aggregation: exceptions CX_SALV_NOT_FOUND, CX_SALV_EXISTING, CX_SALV_DATA_ERROR. For add_sort: CX_SALV_NOT_FOUND, CX_SALV_EXISTING, CX_SALV_DATA_ERROR. For get_column: CX_SALV_NOT_FOUND. For factory: CX_SALV_MSG? Hmm factory exceptions: CX_SALV_MSG? Let me recall SAP's example program SALV_DEMO_TABLE_FUNCTIONS: 

```abap
TRY.
    cl_salv_table=>factory( IMPORTING r_salv_table = gr_table CHANGING t_table = gt_table ).
  CATCH cx_salv_msg.
ENDTRY.
```

Yes, cx_salv_msg. OK.

I'll structure error handling:

```abap
TRY.
    " factory + settings
  CATCH cx_salv_msg cx_salv_not_found cx_salv_existing cx_salv_data_error INTO DATA(lx_salv).
    MESSAGE lx_salv->get_text( ) TYPE 'S' DISPLAY LIKE 'E'.
    RETURN.
ENDTRY.
```

Wait — can CATCH multiple classes INTO one ref? Yes: CATCH cx_a cx_b cx_c INTO lx — the ref type must be common super class; if all inherit from CX_ROOT, INTO DATA(lx_salv) infers... With inline declaration in CATCH, the type is inferred as the most specific common superclass? Actually with CATCH ... INTO DATA(ref), the declared type is the static type of the first? Hmm: "CATCH cx1 cx2 INTO REF" — the inline declared variable gets the type of the broadest? The rule: for inline declaration, the static type is determined as the most general common superclass of the listed exception classes? I believe the inferred type is the common super class — e.g., CX_ROOT? Hmm, that could be CX_DYNAMIC_CHECK or CX_STATIC_CHECK depending. SALV exceptions: CX_SALV_MSG — inherits from CX_DYNAMIC_CHECK? CX_SALV_NOT_FOUND — CX_DYNAMIC_CHECK? If they share CX_DYNAMIC_CHECK, inferred type would be CX_DYNAMIC_CHECK and calling get_text( ) is fine (defined on CX_ROOT? get_text is on IF_MESSAGE_T100&CX_ROOT — get_text( ) is available on CX_ROOT via interface IF_MESSAGE). Yes, get_text( ) is in IF_MESSAGE implemented by CX_ROOT, so any exception ref can call it. OK safe.

But careful: if inferred type is CX_DYNAMIC_CHECK, MESSAGE lx_salv->get_text( ) works. Fine.

Alternatively catch each separately for cleaner messages. One combined CATCH is fine and concise.

Also AT

</details>
