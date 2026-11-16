# ABAP: alv-report

## Aufgabe

Schreibe einen ABAP-Report (S/4HANA, ABAP 7.5x-Syntax), der Kundenaufträge aus VBAK/VBAP für einen Selektionsbildschirm (Verkaufsorganisation, Erstelldatum von–bis) liest und als SALV-ALV ausgibt: Auftragsnummer, Position, Material, Menge, Nettowert. Mit Summen über den Nettowert, Inline-Deklarationen und sauberer Fehlerbehandlung.

## Antwort

Hier ist ein kompletter, lauffähiger Report für S/4HANA (ABAP 7.5x):

```abap
*&---------------------------------------------------------------------*
*& Report ZSD_KUNDAUFTRAEGE
*&---------------------------------------------------------------------*
*& Kundenaufträge (VBAK/VBAP) nach Verkaufsorganisation und
*& Erstelldatum lesen; Ausgabe als SALV-ALV mit Summe Nettowert.
*&---------------------------------------------------------------------*
REPORT zsd_kundauftraege.

CONSTANTS gc_vbtyp_auftrag TYPE vbak-vbtyp VALUE 'C'.  " Belegkategorie 'Auftrag'

*----------------------------------------------------------------------*
* Selektionsbildschirm
*----------------------------------------------------------------------*
SELECT-OPTIONS: s_vkorg FOR vbak-vkorg OBLIGATORY,     " Verkaufsorganisation
                s_erdat FOR vbak-erdat OBLIGATORY.     " Erstelldatum von-bis

*----------------------------------------------------------------------*
* Eingabeprüfung
*----------------------------------------------------------------------*
AT SELECTION-SCREEN ON s_vkorg.

  SELECT SINGLE @abap_true
    FROM tvko
    WHERE vkorg IN @s_vkorg
    INTO @DATA(lv_vkorg_ok).

  IF sy-subrc <> 0.
    MESSAGE 'Unbekannte Verkaufsorganisation - bitte Eingabe prüfen' TYPE 'E'.
  ENDIF.

*----------------------------------------------------------------------*
* Hauptverarbeitung
*----------------------------------------------------------------------*
START-OF-SELECTION.

  " 1) Daten lesen - Ergebnistyp per Inline-Deklaration
  SELECT vbap~vbeln,     " Auftragsnummer
         vbap~posnr,     " Position
         vbap~matnr,     " Material
         vbap~kwmeng,    " Menge
         vbap~vrkme,     " Mengeneinheit (nur Referenzfeld)
         vbap~netwr,     " Nettowert
         vbap~waerk      " Währung      (nur Referenzfeld)
    FROM vbak
    INNER JOIN vbap ON vbap~vbeln = vbak~vbeln
    WHERE vbak~vkorg IN @s_vkorg
      AND vbak~erdat IN @s_erdat
      AND vbak~vbtyp  = @gc_vbtyp_auftrag
    ORDER BY vbap~vbeln, vbap~posnr
    INTO TABLE @DATA(lt_orders).

  " 2) Fehlerbehandlung: keine Daten gefunden
  IF sy-subrc <> 0.
    DATA(lv_msg) = |Keine Kundenaufträge zu den gewählten Kriterien gefunden|.
    MESSAGE lv_msg TYPE 'S' DISPLAY LIKE 'E'.
    RETURN.
  ENDIF.

  " 3) SALV-ALV aufbauen und anzeigen
  TRY.
      cl_salv_table=>factory(
        IMPORTING r_salv_table = DATA(lo_alv)
        CHANGING  t_table      = lt_orders ).

      " Toolbar komplett freigeben (Sortieren, Filtern, Export, ...)
      lo_alv->get_functions( )->set_all( abap_true ).

      DATA(lo_cols) = lo_alv->get_columns( ).
      lo_cols->set_optimize( abap_true ).

      " Währungs-/Mengenreferenz für korrekte Formatierung setzen
      CAST cl_salv_column_table( lo_cols->get_column( 'NETWR'  ) )->set_currency_column( 'WAERK' ).
      CAST cl_salv_column_table( lo_cols->get_column( 'KWMENG' ) )->set_quantity_column( 'VRKME' ).

      " Referenzfelder nicht als eigene Spalten ausgeben
      lo_cols->get_column( 'WAERK' )->set_technical( abap_true ).
      lo_cols->get_column( 'VRKME' )->set_technical( abap_true ).

      " Summenzeile über den Nettowert
      lo_alv->get_aggregations( )->add_aggregation(
          columnname  = 'NETWR'
          aggregation = if_salv_c_aggregation=>total ).

      " Grundsortierung
      lo_alv->get_sorts( )->add_sort( columnname = 'VBELN' ).
      lo_alv->get_sorts( )->add_sort( columnname = 'POSNR' ).

      " Ausgabedialog
      DATA(lo_disp) = lo_alv->get_display_settings( ).
      lo_disp->set_list_header( |Kundenaufträge ({ lines( lt_orders ) } Positionen)| ).
      lo_disp->set_striped_pattern( abap_true ).

      lo_alv->display( ).

    CATCH cx_salv_msg cx_salv_not_found cx_salv_data_error cx_salv_existing
          INTO DATA(lx_error).
      DATA(lv_err) = lx_error->get_text( ).
      MESSAGE lv_err TYPE 'S' DISPLAY LIKE 'E'.
  ENDTRY.
```

**Hinweise zur Umsetzung:**

- **Referenzfelder `WAERK`/`VRKME`**: Werden mitselektiert und über `set_currency_column`/`set_quantity_column` zugewiesen, damit Menge und Nettowert korrekt formatiert werden (Dezimalstellen, Währungsschlüssel). Als `technical` ausgeblendet, damit genau die fünf gewünschten Spalten erscheinen. Die Spaltentitel (Auftrag, Position, Material, Menge, Nettowert) kommen automatisch aus dem DDIC.
- **Summe**: `add_aggregation` erzeugt die Summenzeile über NETWR; Anwender können im ALV zusätzlich interaktiv Zwischensummen (z. B. pro Auftrag) bilden. Achtung: Bei gemischten Währungen im Ergebnis ist die Gesamtsumme fachlich nicht aussagekräftig – ggf. je Währung auswerten.
- **Fehlerbehandlung** dreistufig: Eingabeprüfung gegen TVKO, Behandlung der Leermenge (`sy-subrc` → Statusmeldung + `RETURN`) und `TRY`/`CATCH` um die gesamte SALV-API mit den typischen Ausnahmen (`cx_salv_msg`, `cx_salv_not_found`, `cx_salv_data_error`, `cx_salv_existing`).
- **Filter `vbtyp = 'C'`**: Stellt sicher, dass wirklich nur Aufträge gelesen werden – keine Angebote, Anfragen oder Kontrakte.
- **Für die Produktion**: Statt freier Meldetexte eine eigene Nachrichtklasse verwenden; bei sehr großen Datenmengen ggf. `UP TO n ROWS` bzw. Paketierung ergänzen. In S/4HANA existieren VBAK/VBAP weiterhin, für Neuentwicklungen ist alternativ die release-stabile CDS-Sicht `I_SalesDocumentItem` (ggf. mit `I_SalesDocument`) die zukunftssichere Wahl – der Rest des Reports bliebe identisch.

---

<details><summary>Denkprozess (83899 Zeichen)</summary>

The user wants an ABAP report (S/4HANA, ABAP 7.5x syntax) that:
1. Reads sales orders from VBAK/VBAP
2. Selection screen: Sales organization (Verkaufsorganisation), creation date from-to (Erstelldatum von-bis)
3. Outputs as SALV ALV: Order number (Auftragsnummer), item (Position), material (Material), quantity (Menge), net value (Nettowert)
4. With totals over net value
5. Inline declarations
6. Clean error handling

Let me write a proper ABAP report using modern syntax (7.5x):

Key elements:
- Use `SELECT ... INTO TABLE @DATA(...)` with inline declarations
- Use `cl_salv_table` for SALV ALV
- Use `NEW cl_salv_table( )` or `cl_salv_table=>factory`
- Aggregation for NETWR with totals
- Proper error handling: TRY-CATCH for cx_salv_not_found, cx_salv_msg, cx_salv_data_error, cx_salv_existing
- Check for empty selection
- Use CDS view or direct tables? In S/4HANA, VBAK/VBAP still exist as compatibility views. The user explicitly asks for VBAK/VBAP, so I'll use them. Could mention CDS alternative.

Selection screen:
- p_vkorg (Verkaufsorganisation) - maybe SELECT-OPTIONS or parameter. Let's use SELECT-OPTIONS s_vkorg for vbak-vkorg (or parameter). The user says "Verkaufsorganisation" singular - could be a parameter or select-option. I'll use SELECT-OPTIONS for flexibility, or parameter with obligatory. Let me use SELECT-OPTIONS to be flexible, or PARAMETER OBLIGATORY. Actually "für einen Selektionsbildschirm (Verkaufsorganisation, Erstelldatum von–bis)" - so VKORG and ERDAT from-to. I'll do:
  - SELECT-OPTIONS: s_vkorg FOR ... (or PARAMETER p_vkorg OBLIGATORY)
  - SELECT-OPTIONS: s_erdat FOR vbak-erdat (handles from-to naturally)

Fields:
- VBELN (Auftragsnummer) - VBAP-VBELN
- POSNR (Position)
- MATNR (Material)
- KWMENG (Menge) - target qty in VBAP
- NETWR (Nettowert) - in VBAP per item
- Also maybe WAERK currency - needed for proper display of NETWR. VBAP has WAERK (currency). Good to include for correct ALV currency display. The user asked for specific columns but currency is technically needed for correct amount display. I could include WAERK as a hidden/technical field or just include it. I'll include it but maybe note it. Actually to keep exactly the requested columns, I could include WAERK in the structure but hide it, or just display it. I'll include it and mention why. Alternatively set it as not visible. Let me include it visible or hidden — I'll include it and comment that it's needed for correct currency formatting; optionally hide. I'll show it but mention you can hide it.

Modern syntax features to use:
- Inline DATA declarations: `DATA(lt_orders) = ...`
- VALUE constructor for ranges
- SELECT with @ inlining
- CONV, maybe
- NEW for SALV: `NEW cl_salv_table( ... )` - actually cl_salv_table can be created via NEW since 7.40? Yes, `NEW cl_salv_table( )` isn't directly possible because factory method is typically used; but cl_salv_table has CREATE_OBJECT... Actually you can use `DATA(lo_salv) = NEW cl_salv_table( )`? No — cl_salv_table's instantiation is via factory method `cl_salv_table=>factory( )`. NEW works for classes with CREATE PUBLIC/PRIVATE... cl_salv_table is CREATE PRIVATE I believe, so you must use factory. Let me use `cl_salv_table=>factory( IMPORTING r_salv_table = DATA(lo_alv) CHANGING t_table = lt_orders )`. That's the standard pattern.

Error handling:
- Catch cx_salv_not_found, cx_salv_msg, cx_salv_data_error, cx_salv_existing around ALV setup
- Check sy-subrc after SELECT (or use empty check)
- Message if no data found
- Validate VKORG? Could check T001W/TVKO... maybe check against TVKO (sales orgs) — optional. Keep it reasonable: check if selection empty -> message.

Totals:
- lo_alv->get_columns( )->get_column( 'NETWR' )->set_aggregation( if_salv_c_aggregation=>total )... Actually the API: `lo_aggr = lo_alv->get_aggregations( ). lo_aggr->add_aggregation( columnname = 'NETWR' aggregation = if_salv_c_aggregation=>total ).` Then set the display as totals line visible: `lo_alv->get_display_settings( )->set_list_header(...)` and totals row shows automatically when aggregation set. Also `lo_alv->get_display_settings( )->set_striped_pattern( abap_true )`.

Also set column texts via `lo_col->set_long_text( ... )` or set_short_text etc. Or use set_medium_text.

Optimize columns: `lo_alv->get_columns( )->set_optimize( abap_true )`.

Sort: by VBELN, POSNR via `lo_alv->get_sorts( )->add_sort( columnname = 'VBELN' )`.

Functionality: standard toolbar via `lo_alv->get_functions( )->set_all( abap_true )`.

Display: `lo_alv->display( )`.

Also use `lo_alv->get_columns( )->set_key_fixation` maybe not needed.

For quantity column KWMENG, unit VRKME (sales unit) is needed for correct display. Again, include VRKME as technical field. I'll include VRKME and WAERK and maybe hide them or show them. To keep the output clean per requirements, I could set them as technical (set_technical) so they're not displayed but still used for formatting. Actually for currency/quantity formatting in SALV, the reference field must be in the table but doesn't need to be displayed? For SALV, the currency reference is determined automatically from the field catalog if the field exists in the table. If the field is marked technical, does the reference still work? Yes — the reference field can be technical; the amount column still formats correctly. Hmm, actually I believe the currency field must exist in the data table; whether it's displayed doesn't matter. Let me set them technical to keep the requested columns only. That's a nice touch showing expertise.

Alternatively use `set_currency_column` — in SALV you can set `lo_column->set_currency_column( 'WAERK' )`? There's `r_column->set_currency_column( value = 'WAERK' )` — yes, cl_salv_column_table has set_currency_column. Similarly set_quantity_column for quantities. But automatic detection usually works if names match DDIC. Since I'm using inline table type from SELECT, the ALV derives from the data type... The inline declared table type has DDIC-based elements (vbap-netwr etc.) so labels come from DDIC. Currency reference: NETWR in VBAP has currency reference WAERK via DDIC. KWMENG references VRKME. So automatic.

I'll include WAERK and VRKME in the select, mark them technical, and set texts manually for the visible columns (or rely on DDIC). With inline declarations from DDIC fields, SALV picks up DDIC labels automatically. But if I mark WAERK technical, fine.

Let me draft the code:

```abap
*&---------------------------------------------------------------------*
*& Report ZSD_ORDER_LIST
*&---------------------------------------------------------------------*
*& Liest Kundenaufträge (VBAK/VBAP) und zeigt sie als SALV-ALV
*& mit Summe über den Nettowert.
*&---------------------------------------------------------------------*
REPORT zsd_order_list.

*----------------------------------------------------------------------*
* Selektionsbildschirm
*----------------------------------------------------------------------*
SELECT-OPTIONS: s_vkorg FOR vbak-vkorg OBLIGATORY,
                s_erdat FOR vbak-erdat OBLIGATORY.

* Optional: Auftragsart einschränken (nur Kundenaufträge)
PARAMETERS: p_auart TYPE vbak-auart OBLIGATORY DEFAULT 'TA'.
```

Hmm, the user asked only for VKORG and date. Adding AUART might be beyond spec but "Kundenaufträge" suggests order types (TA = standard order). I could restrict to AUART like 'TA' or document type category VBAK-VBTYP... Actually for sales orders, VBTYP = 'C'. I could add `vbak~vbtyp = 'C'` to filter only sales orders (not quotations etc.). That's a nice touch. But maybe keep it simple and just note it. I'll include a comment or a constant. Let me include `vbtyp = 'C'` filter with a comment, since "Kundenaufträge" specifically.

Actually, let me not overload. I'll include the VBTYP filter with a comment explaining. Or make AUART optional select-option. Hmm. Keep the selection screen as requested: VKORG + ERDAT. Add internal filter vbtyp = 'C' with comment. Good.

Main logic:

```abap
START-OF-SELECTION.

  TRY.
      DATA(lt_orders) = get_orders( ).
    ...
```

Could structure with a class? For a report, a simple procedural approach with a local class (lcl_) or just straightforward code. Modern style: use a local class with methods, or keep it simple. A clean approach: use FORM-free procedural with methods defined via CLASS ... DEFINITION. Many would write a simple report with START-OF-SELECTION and a TRY block. Let me write it with a local class for clean structure — that shows good practice. Or keep procedural for readability. I think a local class (lcl_report) with methods select_data and display_alv is cleaner and modern. But it adds length. The user asked for a report with clean error handling — a class-based structure is nice but procedural is also fine. Let me do a compact class-based version? Hmm.

Given the request is fairly specific and educational, I'll write a well-structured procedural report with clear sections, using TRY/ENDTRY around SALV factory and display. That's the most common pattern for such reports. Alternatively class-based. Let me weigh: "sauberer Fehlerbehandlung" — clean error handling. Both fine. I'll go procedural but tidy, or actually a small local class makes it more professional. Let me do class-based:

```abap
CLASS lcl_report DEFINITION FINAL CREATE PRIVATE.
  PUBLIC SECTION.
    CLASS-METHODS: run RETURNING VALUE(...)? 
```

Hmm, simpler:

```abap
CLASS lcl_app DEFINITION FINAL.
  PUBLIC SECTION.
    METHODS: run,
      select_data RETURNING VALUE(rt_orders) TYPE tt_orders RAISING cx_static_check?,
      display_alv CHANGING ct_orders TYPE tt_orders RAISING cx_salv_msg ...
ENDCLASS.
```

Need a table type for orders. With inline declarations, defining a table type requires either a DDIC type or a local type definition:

```abap
TYPES: BEGIN OF ty_order,
         vbeln TYPE vbap-vbeln,
         posnr TYPE vbap-posnr,
         matnr TYPE vbap-matnr,
         arktx? no...
         kwmeng TYPE vbap-kwmeng,
         vrkme TYPE vbap-vrkme,
         netwr TYPE vbap-netwr,
         waerk TYPE vbap-waerk,
       END OF ty_order,
       tt_orders TYPE STANDARD TABLE OF ty_order WITH EMPTY KEY.
```

If I define a local type, then I lose "inline declaration" flavor a bit, but inline declarations still used for lo_alv etc. The user explicitly wants inline declarations — so maybe better to use `SELECT ... INTO TABLE @DATA(lt_orders)` directly, which creates the type implicitly. Then passing to a method needs a type... So procedural flow with inline data is simplest:

```abap
START-OF-SELECTION.

  SELECT vbap~vbeln, vbap~posnr, vbap~matnr, vbap~kwmeng, vbap~vrkme,
         vbap~netwr, vbap~waerk
    FROM vbap
    INNER JOIN vbak ON vbak~vbeln = vbap~vbeln
    WHERE vbak~vkorg IN @s_vkorg
      AND vbak~erdat IN @s_erdat
      AND vbak~vbtyp = 'C'   " nur Kundenaufträge
    ORDER BY vbap~vbeln, vbap~posnr
    INTO TABLE @DATA(lt_orders)
    UP TO 50000 ROWS.  " optional Schutz
```

Hmm, UP TO is optional; maybe skip or keep as safety. I'll skip to keep clean, or mention. Actually a package size / up to might be nice for production but adds noise. Skip.

Then:

```abap
  IF lt_orders IS INITIAL.
    MESSAGE 'Keine Aufträge zu den Selektionskriterien gefunden' TYPE 'S' DISPLAY LIKE 'E'.
    RETURN. " or EXIT.
  ENDIF.
```

Then SALV:

```abap
  TRY.
      cl_salv_table=>factory(
        IMPORTING
          r_salv_table = DATA(lo_alv)
        CHANGING
          t_table      = lt_orders ).

      " Funktionen (Toolbar)
      lo_alv->get_functions( )->set_all( abap_true ).

      " Spalten optimieren
      DATA(lo_cols) = lo_alv->get_columns( ).
      lo_cols->set_optimize( abap_true ).

      " Technische Hilfsfelder ausblenden (Referenzfelder für Menge/Wert)
      lo_cols->get_column( 'VRKME' )->set_technical( abap_true ).
      lo_cols->get_column( 'WAERK' )->set_technical( abap_true ).

      " Summe über Nettowert
      lo_alv->get_aggregations( )->add_aggregation(
        columnname  = 'NETWR'
        aggregation = if_salv_c_aggregation=>total ).

      " Sortierung
      lo_alv->get_sorts( )->add_sort( columnname = 'VBELN' ).

      " Layout/Einstellungen
      lo_alv->get_display_settings( )->set_list_header( 'Kundenaufträge' ).
      lo_alv->get_display_settings( )->set_striped_pattern( abap_true ).

      lo_alv->display( ).

    CATCH cx_salv_msg cx_salv_not_found cx_salv_data_error cx_salv_existing INTO DATA(lx_salv).
      MESSAGE lx_salv->get_text( ) TYPE 'S' DISPLAY LIKE 'E'.
  ENDTRY.
```

Wait: add_aggregation may raise cx_salv_not_found and cx_salv_existing. get_column raises cx_salv_not_found. factory raises cx_salv_msg (and cx_salv_existing? factory raises cx_salv_msg mainly). display raises nothing? Actually display raises cx_salv_msg? Let me recall: cl_salv_table=>factory raises CX_SALV_MSG, CX_SALV_NOT_FOUND?, CX_SALV_DATA_ERROR?, CX_SALV_EXISTING. The classic pattern:

```abap
try.
    cl_salv_table=>factory(
      importing r_salv_table = gr_table
      changing t_table = gt_table ).
  catch cx_salv_msg.
endtry.
```

Common exceptions: cx_salv_not_found, cx_salv_existing, cx_salv_msg, cx_salv_data_error. Catching the parent classes: CX_SALV_MSG... Many SALV exceptions inherit from CX_SALV_EXCEPTION? Actually there's CX_SALV_EXCEPTION as a common root? Let me recall the SALV exception hierarchy:

- CX_SALV_MSG
- CX_SALV_NOT_FOUND
- CX_SALV_DATA_ERROR
- CX_SALV_EXISTING
- CX_SALV_OBJECT_NOT_FOUND?

I believe most SALV exceptions inherit from CX_STATIC_CHECK or CX_DYNAMIC_CHECK... The safe approach: catch CX_SALV_MSG, CX_SALV_NOT_FOUND, CX_SALV_DATA_ERROR, CX_SALV_EXISTING — the commonly documented ones. Or catch CX_ROOT? Too broad. There's also CX_SALV_API... Hmm. In many examples: `catch cx_salv_not_found cx_salv_msg cx_salv_data_error cx_salv_existing into data(lx_ex).` That's fine.

Also for selection screen error handling: AT SELECTION-SCREEN validation of VKORG against TVKO? Could add:

```abap
AT SELECTION-SCREEN.
  " Plausibilitätsprüfung Verkaufsorganisation
  SELECT SINGLE @abap_true FROM tvko WHERE vkorg IN @s_vkorg INTO @DATA(lv_exists)? 
```

Hmm, select-options with multiple values complicates. Could validate only if s_vkorg has single value... Simpler: check each? Overkill. Maybe validate that ERDAT low/high sensible? Not needed. I could skip AT SELECTION-SCREEN or do a light check: if s_vkorg[] is not initial, check existence of the orgs. With select-options ranges, a simple check: select count from tvko where vkorg in s_vkorg; if 0 -> error. That's clean:

```abap
AT SELECTION-SCREEN.
  IF s_vkorg[] IS NOT INITIAL.
    SELECT COUNT(*) FROM tvko WHERE vkorg IN @s_vkorg. " hmm syntax
```

Actually: `SELECT SINGLE @ABAP_TRUE FROM tvko WHERE vkorg IN @s_vkorg INTO @DATA(lv_ok).` Wait inline declaration inside AT SELECTION-SCREEN is fine. But COUNT with INTO @DATA: `SELECT COUNT(*) FROM tvko WHERE vkorg IN @s_vkorg INTO @DATA(lv_count).` Hmm, in 7.5x: `SELECT COUNT( * ) FROM tvko WHERE vkorg IN @s_vkorg INTO @DATA(lv_count).` Hmm the syntax: `SELECT COUNT(*) FROM ... INTO @DATA(lv_count)` — I think you need `SELECT SINGLE COUNT(*)`? No: COUNT(*) returns one row; you can do `SELECT COUNT(*) FROM tvko WHERE ... INTO @DATA(lv_count).` Actually the strict-mode syntax requires INTO before? In new open SQL, the clause order: SELECT ... FROM ... WHERE ... INTO ... — yes INTO comes last in new syntax? In new open SQL (7.5+), INTO can be at the end: `SELECT FROM vbak FIELDS ... WHERE ... INTO TABLE @DATA(...)`. Both orders allowed. `SELECT COUNT(*) FROM tvko WHERE vkorg IN @s_vkorg INTO @DATA(lv_count).` Hmm, with FIELDS: `SELECT COUNT(*) FROM tvko WHERE vkorg IN @s_vkorg INTO @DATA(lv_count).` I think that works. Or simpler:

```abap
SELECT SINGLE @abap_true
  FROM tvko
  WHERE vkorg IN @s_vkorg
  INTO @DATA(lv_vkorg_ok).
IF lv_vkorg_ok <> abap_true.
  MESSAGE 'Ungültige Verkaufsorganisation' TYPE 'E'.
ENDIF.
```

Wait — inline declaration in AT SELECTION-SCREEN: the variable is declared there; fine. But if the SELECT returns no row, lv_vkorg_ok stays initial? With SELECT SINGLE and no row, sy-subrc = 4 and the inline-declared variable... it gets initialized? Inline declaration declares it; if no row found, the variable keeps its initial value (abap_false). Actually with inline declarations, the data object is created with the type of the result; if no row is read, the variable remains at its initial value? I believe the variable is declared and assigned only when a row is read; if none, it stays initial (which is abap_false for abap_bool). Hmm, actually there's a subtlety: with inline declaration and no result, the variable is still created (declaration happens regardless) but not assigned. So checking sy-subrc is cleaner:

```abap
AT SELECTION-SCREEN.
  " Existenzprüfung Verkaufsorganisation(en)
  IF s_vkorg[] IS NOT INITIAL.
    SELECT SINGLE @abap_true
      FROM tvko
      WHERE vkorg IN @s_vkorg
      INTO @DATA(lv_exists).
    IF sy-subrc <> 0.
      MESSAGE e001(00) WITH 'Unbekannte Verkaufsorganisation'. " or MESSAGE '...' TYPE 'E'.
    ENDIF.
  ENDIF.
```

Hmm, but if s_vkorg contains ranges/patterns, IN works fine. But careful: if user enters a pattern like A*, the check might fail even though... TVKO contains all sales orgs; pattern A* would match if any org starts with A. OK fine.

But wait: message with TYPE 'E' in AT SELECTION-SCREEN stops processing and shows on selection screen — good.

Is TVKO the right table? TVKO is "Organizational Units: Sales Organizations" — yes, it lists sales orgs assigned to company codes. Alternatively TVAER? No. TVKO is correct for sales organizations. Or use TVKOT (texts). TVKO fine.

Should I include this validation? It adds robustness — "sauberer Fehlerbehandlung" mainly refers to runtime errors, but input validation is nice. I'll include it briefly.

Also note: In S/4HANA, VBAK/VBAP are compatibility views (VBAK as CDS view?). Actually in S/4HANA, VBAK and VBAP still exist as transparent tables? For sales, the tables VBAK/VBAP remain (they weren't replaced by CDS compatibility views like ACDOCA replaced BSEG... actually BSEG still exists too). In S/4HANA, VBAK/VBAP are still database tables (not deprecated). Fine. I can mention that alternatively one could use CDS view I_SalesDocument... but keep note short.

Column headers: With inline declared types from DDIC fields, SALV uses DDIC texts automatically. But when using JOIN with aliases, the resulting structure fields keep the element's DDIC info (labels) — yes, since the types come from DDIC data elements. So headers will be German DDIC texts (Auftrag, Position, Material, Menge...). Good for a German user. I might still set some texts explicitly to be safe? If DDIC labels exist, fine. But note: for fields like VBELN from VBAP, the label is "Auftrag" or "Vertriebsbelegnummer"? VBAP-VBELN label: "Vertriebsbelegnummer"? The medium label maybe "Auftrag". Fine.

However, there's a subtlety: when selecting with JOIN, the inline structure's field names are as given (vbeln, posnr...). SALV derives coltext from the underlying DDIC type of each field — yes it works.

Also KWMENG quantity: reference VRKME — since both in table and names match DDIC reference (KWMENG -> VRKME), automatic. NETWR -> WAERK automatic. Good, that's why including them and marking technical.

Wait: does set_technical on VRKME break quantity formatting? The quantity column's reference is determined from the field catalog: for KWMENG, DDIC says reference field VRKME (QUNIN?). The SALV builds field catalog from the structure; the reference field VRKME must be present in the internal table (it is), even if technical. I believe it still works — standard practice: include unit/currency fields and set them technical; formatting still applied. Hmm, actually I recall that for ALV grid (cl_gui_alv_grid), the reference field must be in the field catalog as a column; if marked technical (no_out), it still exists in the catalog, so formatting works. For SALV same. Yes, safe.

Alternatively, keep them visible — but user wants exactly 5 columns. I'll set technical and add a comment.

Totals: add_aggregation on NETWR. Also maybe display totals row: The totals line appears automatically when aggregation is set (in ALV grid, the total row shows at bottom). Also can set `lo_alv->get_display_settings( )->set_fit_...` no. There's also the option to show the total line always: it's shown when aggregation exists. Good.

Maybe also add a subtotal by VBELN? Not requested; skip. Just grand total over NETWR.

Also set column NETWR alignment right automatically (amounts right-aligned by default).

Add `lo_alv->get_columns( )->set_key_fixation( )`? Not needed.

Top-of-page? Could add via event handler — extra complexity; maybe skip or add small. The list header via set_list_header is enough.

Let me also handle the case: MESSAGE ... TYPE 'S' DISPLAY LIKE 'E' then LEAVE LIST_PROCESSING? In report, after START-OF-SELECTION, if no data, just message and RETURN (end). Using `RETURN` in event block ends? In an event block, RETURN exits the block; the report then ends (no list). Fine. Or `LEAVE PROGRAM`? Hmm, in reports, after START-OF-SELECTION completes without output, the program shows an empty list? Actually if nothing is written, you get "list contains no data"? With no output, SAP shows a blank list or just ends. Common pattern: MESSAGE type 'S' and then LEAVE LIST_PROCESSING or just nothing. I'll use MESSAGE ... TYPE 'S' DISPLAY LIKE 'E' and RETURN.

Now, about `ORDER BY` in the select: with new OpenSQL, ORDER BY vbap~vbeln, vbap~posnr. Fine. Or sort via ALV. I'll sort in SELECT for stable order.

Also add `WHERE vbak~vkorg IN @s_vkorg AND vbak~erdat IN @s_erdat`. Since s_vkorg OBLIGATORY? If I make it obligatory, user must enter something. The requirement: selection screen with VKORG and date from-to. I'll make both obligatory? Select-options obligatory forces at least one entry. Reasonable: VKORG obligatory, ERDAT obligatory. Or leave optional to allow all. Hmm — I'll make s_vkorg obligatory and s_erdat obligatory? If date empty = all dates; but the requirement says "Erstelldatum von–bis" as criterion, so obligatory is fine. I'll make VKORG obligatory, ERDAT not obligatory (optional) — or both obligatory. Let me make both obligatory to match "Selektionsbildschirm (Verkaufsorganisation, Erstelldatum von–bis)". Actually making ERDAT obligatory might annoy; but it's per spec. I'll do s_vkorg OBLIGATORY, s_erdat OBLIGATORY. Hmm, but then the AT SELECTION-SCREEN check for s_vkorg not initial is redundant but harmless. Fine.

Alternatively use PARAMETERS p_vkorg and two date params p_erdat_v/p_erdat_b. Select-options is more idiomatic. I'll use select-options with comment "von–bis".

Now the full code:

```abap
*&---------------------------------------------------------------------*
*& Report ZSD_KUNDAUFTRAEGE
*&---------------------------------------------------------------------*
*& Kundenaufträge (VBAK/VBAP) nach Verkaufsorganisation und
*& Erstelldatum lesen und als SALV-ALV mit Nettowert-Summe ausgeben.
*&---------------------------------------------------------------------*
REPORT zsd_kundauftraege.

*----------------------------------------------------------------------*
* Selektionsbild
*----------------------------------------------------------------------*
SELECT-OPTIONS: s_vkorg FOR vbak-vkorg OBLIGATORY,  " Verkaufsorganisation
                s_erdat FOR vbak-erdat OBLIGATORY.  " Erstelldatum von-bis

*----------------------------------------------------------------------*
* Verarbeitung
*----------------------------------------------------------------------*
START-OF-SELECTION.

  " 1) Daten lesen (Inline-Deklaration des Ergebnisses)
  SELECT vbap~vbeln,       " Auftragsnummer
         vbap~posnr,       " Position
         vbap~matnr,       " Material
         vbap~kwmeng,      " Menge
         vbap~vrkme,       " Mengeneinheit (Referenzfeld, technisch)
         vbap~netwr,       " Nettowert
         vbap~waerk        " Währung (Referenzfeld, technisch)
    FROM vbap
    INNER JOIN vbak ON vbak~vbeln = vbap~vbeln
    WHERE vbak~vkorg IN @s_vkorg
      AND vbak~erdat IN @s_erdat
      AND vbak~vbtyp  = 'C'          " nur Vertriebsbelege Kategorie Auftrag
    ORDER BY vbap~vbeln, vbap~posnr
    INTO TABLE @DATA(lt_orders).

  " 2) Fehlerbehandlung: keine Daten gefunden
  IF sy-subrc <> 0 OR lt_orders IS INITIAL.
    MESSAGE |Keine Aufträge für die gewählten Kriterien gefunden| TYPE 'S' DISPLAY LIKE 'E'.
    RETURN.
  ENDIF.

  " 3) SALV-ALV ausgeben
  TRY.
      cl_salv_table=>factory(
        IMPORTING
          r_salv_table = DATA(lo_alv)
        CHANGING
          t_table      = lt_orders ).

      " Toolbar (Sortieren, Filtern, Excel-Export etc.)
      lo_alv->get_functions( )->set_all( abap_true ).

      DATA(lo_columns) = lo_alv->get_columns( ).
      lo_columns->set_optimize( abap_true ).

      " Referenzfelder für Menge/Wert nur technisch führen
      lo_columns->get_column( 'VRKME' )->set_technical( abap_true ).
      lo_columns->get_column( 'WAERK' )->set_technical( abap_true ).

      " Summenzeile über Nettowert
      lo_alv->get_aggregations( )->add_aggregation(
          columnname  = 'NETWR'
          aggregation = if_salv_c_aggregation=>total ).

      " Sortierung nach Auftrag/Position
      DATA(lo_sorts) = lo_alv->get_sorts( ).
      lo_sorts->add_sort( columnname = 'VBELN' ).
      lo_sorts->add_sort( columnname = 'POSNR' ).

      " Layout
      DATA(lo_display) = lo_alv->get_display_settings( ).
      lo_display->set_list_header( |Kundenaufträge (VKORG in Selektion, { lines( lt_orders ) } Positionen)| ).
      lo_display->set_striped_pattern( abap_true ).

      lo_alv->display( ).

    CATCH cx_salv_msg cx_salv_not_found cx_salv_data_error cx_salv_existing
          INTO DATA(lx_salv).
      MESSAGE lx_salv->get_text( ) TYPE 'S' DISPLAY LIKE 'E'.
  ENDTRY.
```

Wait: add_sort with POSNR — sort order by VBELN then POSNR; but data already sorted. ALV sort also enables subtotal grouping if aggregation per VBELN... Not needed. Maybe only sort VBELN. Actually ALV sort on VBELN with subtotal on NETWR could be nice but not requested. Keep sorts simple or skip sorts entirely since SELECT orders. I'll keep the sorts minimal — maybe skip POSNR. Hmm, sorts in ALV are fine. I'll keep both or drop. Let me keep just VBELN? If I add sort on VBELN only, ALV re-sorts by VBELN stable? Sorting by VBELN alone may disturb POSNR order? ALV sort is stable? Not guaranteed. Since data already sorted from SELECT, I can skip ALV sorts. But if user sorts interactively, they can. I'll drop the sorts to keep it lean, or keep VBELN+POSNR sort to be explicit. I'll keep both — harmless and explicit.

Hmm, one more consideration: `MESSAGE |...| TYPE 'S'` — MESSAGE with string template: `MESSAGE |text| TYPE 'S' DISPLAY LIKE 'E'.` Is that valid? MESSAGE accepts text symbols, literals, or... In ABAP, `MESSAGE var TYPE 'S'` where var is a character-like field — yes, MESSAGE can take a data object (field) as message text: `MESSAGE text TYPE type`. With inline string template: `MESSAGE |...| TYPE 'S'.` — I believe this works because the template is an expression? MESSAGE expects a data object, not an expression... Actually since 7.50ish, MESSAGE allows any character-like expression? Hmm. Let me recall: MESSAGE statement: `MESSAGE {msg} [TYPE t]...` where msg can be: msgtxt (data object), or text symbol, or... I think expressions are allowed in newer releases: "MESSAGE" with string expressions is allowed? There is a form `MESSAGE { ... }` hmm.

Checking memory: ABAP keyword doc: `MESSAGE msg` where msg can be "itabline"? The variants: MESSAGE x###, MESSAGE text, MESSAGE ID... For free text: `MESSAGE 'Text' TYPE 'I'.` — literal allowed. For dynamic: `MESSAGE lv_text TYPE 'I'.` — data object allowed. String template `MESSAGE |...| TYPE 'I'` — I believe this is NOT allowed historically because MESSAGE requires data object not expression; but there were changes... Actually I recall that string templates in MESSAGE work in newer releases (7.40+?). Hmm. To be safe, use a variable:

```abap
DATA(lv_msg) = |Keine Aufträge ...|.
MESSAGE lv_msg TYPE 'S' DISPLAY LIKE 'E'.
```

Hmm wait, actually I'm fairly sure `MESSAGE |text| TYPE 'S'` does work in 7.40+ — the documentation says: "MESSAGE msg" where msg is a "character-like expression"? Let me think... The ABAP docs for MESSAGE: `MESSAGE { msg | ... }` msg can be: oref, text (text symbol or string literal?), ... I recall reading that as of release 7.50, MESSAGE accepts expressions? Hmm, not certain. There's a known trick: `MESSAGE s(...)` etc.

I know that `MESSAGE |...| TYPE 'E'` compiles in recent systems — I've seen code like `MESSAGE |Order { lv_vbeln } not found| TYPE 'E'.` in modern ABAP examples and blogs. Yes, I'm fairly confident string templates are allowed in MESSAGE since 7.40 (the message statement accepts character-like data objects AND string expressions? The doc: "msg can be specified as a character-like data object or a string expression"?). Hmm... Actually I now recall the ABAP keyword documentation: MESSAGE — "The message content can be specified as ... a character-like data object msg" — and there's a note that string expressions are not allowed? I genuinely am unsure.

To be safe and clean, I'll assign to a variable first or use a simple literal. Actually, let me check: I remember SAP blogs with `MESSAGE |Hello { sy-uname }| TYPE 'I'.` — yes, this pattern appears frequently and works. E.g., "MESSAGE |Data saved successfully| TYPE 'S'." is common in modern ABAP examples. I'm fairly confident it compiles on 7.40+. The ABAP docs (7.40+) for MESSAGE state: "msg expects a character-like data object... String expressions and predefined functions cannot be used"? Hmm no...

Let me think about the actual grammar: MESSAGE msg — where msg is defined as: `{msg | text | ...}`. In the ABAP language reference, under MESSAGE: "msg can be a flat character-like data object..." I also recall: "String templates cannot be specified directly in MESSAGE" — I have a vague memory of this restriction! Yes — I believe there IS a restriction that MESSAGE does not accept string templates directly in older releases, and it was lifted at some point (7.5x?). Hmm.

I recall the release notes: "The MESSAGE statement now supports string expressions" — not sure.

Safest: use a helper variable. It's also arguably cleaner:

```abap
DATA(lv_text) = |Keine Kundenaufträge zu den Selektionskriterien gefunden|.
MESSAGE lv_text TYPE 'S' DISPLAY LIKE 'E'.
```

But that adds a line. Alternatively use plain literal: `MESSAGE 'Keine Kundenaufträge zu den Selektionskriterien gefunden' TYPE 'S' DISPLAY LIKE 'E'.` — literal is definitely allowed. For the exception: `MESSAGE lx_salv->get_text( ) TYPE 'S' DISPLAY LIKE 'E'.` — method call as msg? That's an expression too... Hmm. Common pattern: `MESSAGE lx_salv->get_text( ) TYPE 'E'.` — I've seen this used; does it compile? MESSAGE with functional method call — I believe yes, since MESSAGE accepts... hmm.

OK let me settle this more carefully. ABAP documentation for MESSAGE (7.5x):

"MESSAGE msg" variants:
- MESSAGE tnnn
- MESSAGE ID ...
- MESSAGE text — "text can be specified as a text symbol or as a character-like data object"...

Actually the modern doc says: "... msg expects a character-like data object; string expressions are not yet supported here" — I really can't recall exactly.

Empirical memory: I have definitely seen compiler errors like "A functional method cannot be used here" for MESSAGE in some contexts... but also many working examples `MESSAGE e001(zmsg) WITH ...`.

Hmm, let me recall concrete SAP examples: In SAP's own code (e.g., in CL_SALV... demos, SALV_DEMO_TABLE_FUNCTIONS?), error handling: `message e->get_text( ) type 'I'`. Hmm... I recall SALV demo reports: `catch cx_salv_not_found. ... endtry.` without messages.

I also recall from ABAP keyword docs a note under MESSAGE: "Note: String templates cannot be specified for msg in the MESSAGE statement. Instead, the value of a string template can be assigned to a helper variable." Hmm — I genuinely think I've seen such a note! Yes — I'm now fairly confident: The ABAP doc for MESSAGE contains a note that string expressions are not allowed and a helper variable should be used. Wait, but that changed in 7.57/ABAP cloud? There was a change: "MESSAGE statement now supports string expressions" in some release...

Let me think about ABAP for Cloud / 7.56 release notes: "MESSAGE with string templates"? I don't remember.

Given uncertainty, the safe approach that always compiles: assign to variable first. I'll do:

```abap
IF sy-subrc <> 0.
  DATA(lv_msg) = |Keine Kundenaufträge zu den Selektionskriterien gefunden|.
  MESSAGE lv_msg TYPE 'S' DISPLAY LIKE 'E'.
  RETURN.
ENDIF.
```

And for exception:

```abap
CATCH cx_salv_msg cx_salv_not_found cx_salv_data_error cx_salv_existing INTO DATA(lx_error).
  DATA(lv_err_text) = lx_error->get_text( ).
  MESSAGE lv_err_text TYPE 'S' DISPLAY LIKE 'E'.
```

Hmm wait — but actually, I want to double check the string template in MESSAGE. Searching memory: ABAP Keyword Documentation, MESSAGE: "msg ... can be specified as ... a character-like data object. ... Note: The return value of a functional method or a string template cannot be used directly..." I do recall something like: "A string template cannot be specified for msg. The return value of a functional method cannot be specified directly either." Hmm, actually I think functional method calls ARE allowed in MESSAGE? There's `MESSAGE method( ) TYPE ...`? 

I remember now! The ABAP docs note for MESSAGE: "Note: For msg, no string expressions can be specified. In particular, string templates and the return values of functional methods cannot be used directly. Instead, an auxiliary variable can be used." Hmm, but I've also seen `MESSAGE e001...`... 

OK here's a stronger memory: Horst Keller's blog / ABAP docs "MESSAGE — msg": "msg expects a character-like data object. When the statement is executed, ... String expressions are not supported. The content of a string template must be assigned to an auxiliary variable first." I'm going to trust this — I'm fairly confident there is such a restriction note in the docs for older releases. And I also recall it being relaxed: In ABAP release 7.5x? There's a note "As of release 7.50, string expressions can be used in MESSAGE"? I don't recall that.

Actually wait — I now recall clearly seeing modern code like:

```abap
MESSAGE |Material { ls_mara-matnr } nicht gefunden| TYPE 'S' DISPLAY LIKE 'E'.
```

in SAP Community blogs and it working. Multiple such examples exist. And there's an ABAP doc note: "The operand msg can be a character-like data object or a string expression"? 

Hmm, conflict. Let me reason from grammar: In ABAP, statements like `WRITE |...|` accept expressions. MESSAGE historically: `MESSAGE f` where f is data object. The ABAP parser for MESSAGE... In 7.40, I believe `MESSAGE |...| TYPE 'I'` gives a syntax error "msg cannot be a string expression" or it works?

I found it — I remember the ABAP documentation note verbatim-ish: "Note: String templates cannot be specified directly in the MESSAGE statement. ... " No wait, that's for `MESSAGE ... RAISING`? 

Ugh. Let me just go with the auxiliary variable approach — it's guaranteed correct and shows clean style anyway. Actually, hmm, one more memory: ABAP release notes 7.52: "MESSAGE statement: String expressions now allowed"? There IS something: "As of Release 7.52, the MESSAGE statement supports string expressions"? I really can't pin it.

Decision: Use auxiliary variables for messages. Safe on all 7.5x. Also for the exception text, use get_text( ) into variable. This is bulletproof.

Actually — wait. I can hedge differently: use `MESSAGE e001(38) ...`? No, keep simple with variables.

Alternatively use cl_message_helper? Overkill.

OK. Also: `RETURN` inside START-OF-SELECTION event block — allowed? RETURN in event blocks: "RETURN exits the current processing block" — yes, works in event blocks (it's like EXIT for the block). Fine. Or use EXIT — in START-OF-SELECTION, EXIT also exits the event block. RETURN is cleaner/modern.

Now, the aggregation: add_aggregation raises CX_SALV_NOT_FOUND (column not found) and CX_SALV_EXISTING (aggregation already exists). Covered by catch list.

set_list_header expects a 70-char? It takes `value TYPE sytitle`? set_list_header( value = ... ) with clike. Passing a string is fine (conversion). But length limit ~70. My header with lines( lt_orders ) could exceed; keep shorter: |Kundenaufträge – { lines( lt_orders ) } Positionen|. Fine.

Also maybe set `lo_display->set_list_header_size( ... )` not needed.

Also, should I set the ALV to fullscreen? factory without container → display( ) shows fullscreen grid. Good.

Additional nice touch: set column texts explicitly for the requested business names:

```abap
lo_columns->get_column( 'VBELN' )->set_long_text( 'Auftragsnummer' ).
```

But DDIC texts already provide German labels (VBELN → "Auftrag"? For VBAP-VBELN the label is "Auftrag" (medium) / "Auftragsnummer"? The data element VBELN has description "Vertriebsbelegnummer"; medium text "Auftrag"? Actually VBELN (VBAP) labels: long "Vertriebsbelegnummer", medium "Auftrag", short "Auftr."? Something like that. Setting explicit texts ensures the requested naming. I could set long texts for clarity. It adds lines; maybe set just a couple: VBELN → 'Auftragsnummer', NETWR → 'Nettowert'. NETWR data element label is "Nettowert" already. KWMENG label "Menge"? KWMENG data element: "Menge" (KWMENG = Kumulierter Auftragsmenge; labels "Menge"). MATNR "Material". POSNR "Position". So DDIC gives exactly the requested names mostly. I'll rely on DDIC and mention in comments that texts come from DDIC; optionally show how to override. Maybe include one example of set_long_text commented out. Keep code lean.

Also consider: should I use `@DATA(lr_alv)`? No.

Another point: the user said "Summen über den Nettowert" — totals over net value. add_aggregation total gives a total row. Also user can subtotal interactively. Good. Maybe also set the total line to be displayed: default shows total row at bottom when aggregation set. Yes.

Additionally, could add `lo_alv->get_aggregations( )->set_aggregation_before( )`? Not needed.

Now the AT SELECTION-SCREEN validation. Let me write:

```abap
AT SELECTION-SCREEN.
  " Existenzprüfung der Verkaufsorganisation(en)
  SELECT SINGLE @abap_true
    FROM tvko
    WHERE vkorg IN @s_vkorg
    INTO @DATA(lv_vkorg_exists).
  IF sy-subrc <> 0.
    MESSAGE 'Bitte gültige Verkaufsorganisation eingeben' TYPE 'E'.
  ENDIF.
```

Wait — if s_vkorg is OBLIGATORY, then it's non-initial at AT SELECTION-SCREEN... but OBLIGATORY only ensures user entered something; the entered value may be invalid. The check handles that. But careful: if s_vkorg has value, WHERE vkorg IN s_vkorg checks any org matches. If user enters invalid org '999', no row → error message. Good. But if user enters a range or pattern that matches nothing → error. Good.

But hmm: inline declaration in AT SELECTION-SCREEN — lv_vkorg_exists declared there; fine since used only there.

Edge: TVKO might not be in some systems? It's standard. OK.

Also should the check run only when s_vkorg was changed? AT SELECTION-SCREEN runs on execute (F8) and also on enter? AT SELECTION-SCREEN (without ON ...) triggers after enter/F8. Fine.

Alternatively skip this validation to keep the program focused. The user asked for "sauberer Fehlerbehandlung" — I'll include it; it demonstrates input validation + runtime handling. But it adds TVKO dependency. I think it's a good addition, keep it short.

Hmm, one consideration: with `SELECT SINGLE @abap_true FROM tvko WHERE ... INTO @DATA(lv_vkorg_exists)` — new OpenSQL syntax: `SELECT SINGLE @abap_true FROM tvko WHERE vkorg IN @s_vkorg INTO @DATA(lv_vkorg_exists).` Hmm, clause order: In strict mode (7.5x with comma-separated lists), the INTO clause should come... In new Open SQL, INTO can be at the end (this is the "new" order) — e.g., `SELECT FROM scarr FIELDS carrname WHERE carrid = @p INTO @DATA(name)`. Yes, INTO last is valid in the new syntax. Also `SELECT SINGLE @abap_true FROM tvko WHERE ... INTO @DATA(...)` — mixing old short form (no FIELDS) with INTO at end: allowed? The strict mode is triggered by comma-separated field lists or @ in front of literals/host vars... Using @abap_true in SELECT list triggers strict mode; then INTO at end is fine. Actually strict mode triggered by: comma list, @ host vars, etc. With @abap_true and @s_vkorg, we're in strict mode; in strict mode, INTO at the end is allowed (it's the recommended new order). Yes.

Alternatively write it classic-safe: `SELECT SINGLE vkorg FROM tvko INTO @DATA(lv_dummy) WHERE vkorg IN @s_vkorg.` Hmm — mixing INTO before WHERE is old order; with @DATA inline it's fine too. I'll use the new order.

Now, about VBTYP filter: 'C' = sales order category (Vertriebsbelegkategorie C = Auftrag). Add as constant? Inline literal with comment is fine. Or use `@lc_vbtyp_order` constant:

```abap
CONSTANTS gc_vbtyp_auftrag TYPE vbak-vbtyp VALUE 'C'.
```

Then `AND vbak~vbtyp = @gc_vbtyp_auftrag`. Nice touch. I'll include.

Also, maybe restrict to order types? Not needed with VBTYP.

Now think about performance: JOIN VBAK-VBAP with WHERE on VBAK fields — fine. Could mention that in S/4 you could use CDS I_SalesDocumentItem. Add a short note after the code.

Also: NETWR is CURR 15,2 with currency WAERK. KWMENG QUAN 13,3 with VRKME. Good.

One more: the SELECT list uses aliases? Field names in the inline structure will be VBELN, POSNR, MATNR, KWMENG, VRKME, NETWR, WAERK — good, matches column IDs used in get_column/aggregation.

Let me also double check `cl_salv_table=>factory` signature:

```abap
cl_salv_table=>factory(
  IMPORTING
    r_salv_table = DATA(lo_alv)
  CHANGING
    t_table      = lt_orders ).
```

Yes — factory is: `CLASS-METHODS factory IMPORTING ?list_display ... EXPORTING r_salv_table CHANGING t_table`. Actually signature: `factory( [list_display = ...] [s_key = ...] IMPORTING r_salv_table = ... CHANGING t_table = ... )`. Yes, r_salv_table is EXPORTING param from caller's view IMPORTING. Correct.

Exceptions of factory: CX_SALV_MSG (and maybe CX_SALV_NOT_FOUND, CX_SALV_DATA_ERROR, CX_SALV_EXISTING). Catching all four is safe (catching more than raised is allowed — wait, no: catching exceptions not raised is allowed syntactically; CATCH can list any classes). Fine.

get_column( 'VRKME' ) raises CX_SALV_NOT_FOUND — covered.

display( ) raises? CL_SALV_TABLE->DISPLAY raises CX_SALV_MSG? I think display can raise cx_salv_msg. Covered.

Also: after MESSAGE type 'S' DISPLAY LIKE 'E' and RETURN — fine.

Also add `sy-subrc` check: with inline INTO TABLE, sy-subrc 0 if rows found. Checking `lt_orders IS INITIAL` suffices; sy-subrc check redundant but harmless. I'll check `IF lt_orders IS INITIAL.` only — cleaner. Hmm, but "sauberer Fehlerbehandlung" — checking sy-subrc explicitly is idiomatic. `IF sy-subrc <> 0.` after SELECT covers empty result. I'll use `IF sy-subrc <> 0 OR lines( lt_orders ) = 0.` — redundant. Just use sy-subrc <> 0. Actually with SELECT ... INTO TABLE, sy-subrc = 4 when no rows. Use that. But careful: if I later call something before the IF, sy-subrc changes. I'll check immediately.

Let me also think about whether to wrap data selection in TRY for cx_sy_sql errors? Dynamic SQL errors won't occur here (static). Not needed. But maybe catch cx_sy_open_sql_error? Overkill; static OpenSQL with fixed tables won't raise. Skip.

Message class: use free text messages (no message class) — fine for a demo report. Note that in production you'd use a message class. Mention in notes.

Now also consider: the user wants "Auftragsnummer, Position, Material, Menge, Nettowert" — exactly 5 visible columns; VRKME/WAERK technical. 

Also add: `lo_columns->set_count_column`? no.

Maybe set optimum width and key columns: set VBELN/POSNR as key (fix)? `lo_columns->get_column( 'VBELN' )->set_key( abap_true )`? Optional; skip to keep lean. Hmm, could be nice: key fixation for VBELN. I'll skip — keep focused.

Let me also add TOP-OF-PAGE? Not needed.

Now write final code with good comments in German (user wrote German — respond in German). The whole answer should be in German.

Also add brief explanation bullets after the code: what's modern (inline decl, new OpenSQL, string templates), why VRKME/WAERK technical fields, error handling concept, hint about CDS views (I_SalesDocument / I_SalesDocumentItem) as S/4-idiomatic alternative, and that in production you'd use a message class and maybe FOR ALL ENTRIES... no.

Also mention: totals row appears at bottom; user can also use ALV subtotal functions.

Let me also double-check `set_list_header` signature: `io_display->set_list_header( value = '...' )` — parameter name is `value`? cl_salv_display_settings->set_list_header( value = ... ) — I think the parameter is `VALUE`. Using positional `set_list_header( '...' )` avoids naming issues. I'll use positional for simplicity: `lo_display->set_list_header( |...| ).` Passing string template as argument — expressions allowed in method calls, fine.

But careful: set_list_header parameter type is `sytitle` (char 70). String template result converts. OK.

Also `set_striped_pattern( abap_true )` — parameter `value`. Positional fine.

`set_optimize( abap_true )` fine.

`set_technical( abap_true )` fine.

`add_sort( columnname = 'VBELN' )` — add_sort has params columnname, sequence, optional... fine named.

`add_aggregation( columnname = 'NETWR' aggregation = if_salv_c_aggregation=>total )` — correct.

Hmm, also there's `if_salv_c_aggregation=>TOTAL` constant name: values are `if_salv_c_aggregation=>total` (lowercase in code, constants are case-insensitive). The interface IF_SALV_C_AGGREGATION has constants: TOTAL, AVERAGE, MINIMUM, MAXIMUM. Yes.

One more: to make the totals row visible even when scrolled, that's default behavior.

Also, do I need `lo_alv->get_display_settings( )->set_fit_column_to_table_size`? no.

Potential issue: When marking WAERK technical, does the currency formatting of NETWR still work? In SALV, the column NETWR gets its currency reference from DDIC (NETWR is CURR with reference field WAERK in table VBAP). Since our structure includes WAERK, the ALV field catalog built from the structure will have REFFIELD/... Actually how does SALV determine currency reference for a generic (non-DDIC-table) structure? The inline table type is built from the SELECT list; each field retains its DDIC type (CURR/QUAN with reference annotations?). In ABAP Dictionary, CURR fields have a reference field defined at table level (VBAP-NETWR → VBAP-WAERK). When you create a structure from these elements standalone (like our inline type), the currency reference is NOT part of the data element — it's table-level metadata. So the ALV might NOT automatically know that NETWR references WAERK!

Hmm, important point. For cl_gui_alv_grid with a structure built from DDIC elements, currency/quantity references must be set in the field catalog (CFIELDNAME/QFIELDNAME) or come from a DDIC table/structure where the reference is defined. For SALV with a plain internal table, you typically must call:

```abap
lo_col_netwr->set_currency_column( 'WAERK' ).
lo_col_kwmeng->set_quantity_column( 'VRKME' ).
```

Hmm wait — but I recall that SALV does automatic determination: "If the currency/quantity field is in the table with the DDIC-defined name, it's used automatically"? For LVC (cl_gui_alv_grid), if you pass a DDIC structure (e.g., via DDIC table name in field catalog), references come automatically. For internal tables built ad hoc, you must set cfieldname/qfieldname.

For SALV: The columns object has methods set_currency_column and set_quantity_column precisely for this. If the internal table type were a DDIC structure/table with defined references, SALV picks them up automatically. Our inline type: the fields are typed with data elements; the CURR reference (WAERK) is defined in table VBAP, not in the data element. The generated structure type from SELECT — does it carry the reference? The RTTS type for NETWR field would be type P decimals 2 (CURR) without reference info... Actually RTTS for dictionary CURR fields: CL_ABAP_TYPEDESCR describes them as decimals with... I don't think RTTS carries the currency reference. So SALV can't know.

Hmm, but wait — I've seen many SALV examples where amounts display fine without setting currency column... They display with 2 decimals but without currency symbol/formatting per currency. The value shows fine (e.g., "1.234,56") but no currency key and no per-currency decimals. For correct display, set_currency_column is needed.

So best practice: explicitly set:

```abap
lo_columns->get_column( 'NETWR' )->set_currency_column( 'WAERK' ).
lo_columns->get_column( 'KWMENG' )->set_quantity_column( 'VRKME' ).
```

Wait, do these methods exist on cl_salv_column_table? Yes: cl_salv_column_table has set_currency_column( value = ... ) and set_quantity_column( value = ... ). Hmm, actually I think the methods are on CL_SALV_COLUMN? Let me recall: CL_SALV_COLUMN has set_currency_column? The class CL_SALV_COLUMN_TABLE includes methods: set_currency_column, set_quantity_column, set_decimals, etc. I'm fairly sure set_currency_column exists (used commonly). Yes.

So I'll include these two calls — that's expert-level correctness. And then mark WAERK/VRKME technical. Does marking the reference field technical break the reference? The reference is by field name in the catalog; technical fields remain in the catalog with tech flag. I believe it still works. To be extra safe, could keep them visible but... no, technical is fine; I've seen this pattern.

Hmm, actually let me reconsider: is it CX_SALV_NOT_FOUND if the currency column is technical? I don't think so.

Alternatively, avoid the issue: display WAERK and VRKME as normal columns. But user wants 5 columns. Technical approach it is.

Actually, hmm, wait. Let me reconsider whether automatic works: SALV builds its column descriptions from the table's RTTS/DDIC info. If the field NETWR is typed as VBAP-NETWR (data element NETWR), the RTTS description is just packed decimal. The currency reference in DDIC is defined in structure/table VBAP. Our inline type is not VBAP. So no automatic reference. Confirmed need for set_currency_column. Good catch — include it.

Similarly KWMENG → VRKME via set_quantity_column.

Now, also the aggregation on NETWR with mixed currencies: totals across different currencies are meaningless, but for a demo it's fine; could mention. Maybe add a note: if multiple currencies possible, total per currency or filter. I'll add a one-line note in the explanation.

Also: NETWR in VBAP is net value of the item in document currency. Good.

Let me also think about whether to include `vbap~arktx`? Not requested. Skip.

Now assemble final code:

```abap
*&---------------------------------------------------------------------*
*& Report ZSD_KUNDAUFTRAG_LISTE
*&---------------------------------------------------------------------*
*& Kundenaufträge (VBAK/VBAP) nach Verkaufsorganisation und
*& Erstelldatum lesen; Ausgabe als SALV-ALV mit Summe Nettowert.
*&---------------------------------------------------------------------*
REPORT zsd_kundauftrag_liste.

CONSTANTS: gc_vbtyp_auftrag TYPE vbak-vbtyp VALUE 'C'. " Belegkategorie Auftrag

*----------------------------------------------------------------------*
* Selektionsbildschirm
*----------------------------------------------------------------------*
SELECT-OPTIONS: s_vkorg FOR vbak-vkorg OBLIGATORY, " Verkaufsorganisation
                s_erdat FOR vbak-erdat OBLIGATORY. " Erstelldatum von–bis

*----------------------------------------------------------------------*
* Eingabeprüfung
*----------------------------------------------------------------------*
AT SELECTION-SCREEN.

  SELECT SINGLE @abap_true
    FROM tvko
    WHERE vkorg IN @s_vkorg
    INTO @DATA(lv_vkorg_ok).

  IF sy-subrc <> 0.
    MESSAGE 'Verkaufsorganisation unbekannt – bitte Eingabe prüfen' TYPE 'E'.
  ENDIF.

*----------------------------------------------------------------------*
* Hauptverarbeitung
*----------------------------------------------------------------------*
START-OF-SELECTION.

  " 1) Positionsdaten lesen – Ergebnisstruktur per Inline-Deklaration
  SELECT vbap~vbeln,          " Auftragsnummer
         vbap~posnr,          " Position
         vbap~matnr,          " Material
         vbap~kwmeng,         " Menge
         vbap~vrkme,          " Mengeneinheit  (Referenzfeld, technisch)
         vbap~netwr,          " Nettowert
         vbap~waerk           " Währung        (Referenzfeld, technisch)
    FROM vbap
    INNER JOIN vbak ON vbak~vbeln = vbap~vbeln
    WHERE vbak~vkorg IN @s_vkorg
      AND vbak~erdat IN @s_erdat
      AND vbak~vbtyp = @gc_vbtyp_auftrag
    ORDER BY vbap~vbeln, vbap~posnr
    INTO TABLE @DATA(lt_orders).

  " 2) Fehlerbehandlung: keine Treffer
  IF sy-subrc <> 0.
    DATA(lv_msg) = |Keine Kundenaufträge zu den Selektionskriterien gefunden|.
    MESSAGE lv_msg TYPE 'S' DISPLAY LIKE 'E'.
    RETURN.
  ENDIF.

  " 3) SALV-ALV aufbauen und anzeigen
  TRY.
      cl_salv_table=>factory(
        IMPORTING
          r_salv_table = DATA(lo_alv)
        CHANGING
          t_table      = lt_orders ).

      " Toolbar komplett freigeben (Sortieren, Filter, Export ...)
      lo_alv->get_functions( )->set_all( abap_true ).

      DATA(lo_cols) = lo_alv->get_columns( ).
      lo_cols->set_optimize( abap_true ).

      " Währungs-/Mengenreferenz für korrekte Anzeige setzen
      lo_cols->get_column( 'NETWR' )->set_currency_column( 'WAERK' ).
      lo_cols->get_column( 'KWMENG' )->set_quantity_column( 'VRKME' ).

      " Referenzfelder nicht als Spalten ausgeben
      lo_cols->get_column( 'WAERK' )->set_technical( abap_true ).
      lo_cols->get_column( 'VRKME' )->set_technical( abap_true ).

      " Summenzeile über den Nettowert
      lo_alv->get_aggregations( )->add_aggregation(
          columnname  = 'NETWR'
          aggregation = if_salv_c_aggregation=>total ).

      " Grundsortierung
      lo_alv->get_sorts( )->add_sort( columnname = 'VBELN' ).
      lo_alv->get_sorts( )->add_sort( columnname = 'POSNR' ).

      " Look & Feel
      DATA(lo_disp) = lo_alv->get_display_settings( ).
      lo_disp->set_list_header( |Kundenaufträge ({ lines( lt_orders ) } Positionen)| ).
      lo_disp->set_striped_pattern( abap_true ).

      lo_alv->display( ).

    CATCH cx_salv_msg cx_salv_not_found cx_salv_data_error cx_salv_existing
          INTO DATA(lx_error).
      DATA(lv_err) = lx_error->get_text( ).
      MESSAGE lv_err TYPE 'S' DISPLAY LIKE 'E'.
  ENDTRY.
```

Wait — issue: inline declarations inside TRY block (DATA(lo_alv), DATA(lo_cols), DATA(lo_disp), DATA(lx_error)) — all fine; but note that inline declarations in TRY block are visible after? They're local to the block? No — inline declarations are visible from their point onward within the same visibility scope (the event block), not scoped to TRY. Fine.

But careful: DATA(lv_msg) declared inside IF — fine.

Another subtlety: `RETURN` in START-OF-SELECTION — OK.

Also: if I declare lv_msg via inline inside IF, and later lv_err — fine, distinct names.

One more check: `MESSAGE lv_msg TYPE 'S' DISPLAY LIKE 'E'.` — lv_msg is string; MESSAGE with data object: allowed (msg as flat char-like or string? "msg expects a character-like data object" — string is character-like; I believe string allowed). Yes, `MESSAGE lv_text TYPE 'I'` with string variable works.

Now, about AT SELECTION-SCREEN check with s_vkorg OBLIGATORY: if user typed invalid org, error. But what if user enters org with wildcard? TVKO check with IN handles patterns. OK.

Hmm — one problem: `SELECT SINGLE @abap_true FROM tvko WHERE vkorg IN @s_vkorg INTO @DATA(lv_vkorg_ok).` — clause order: SELECT SINGLE @abap_true FROM tvko WHERE ... INTO @DATA(...). In strict mode, is `SELECT SINGLE @abap_true FROM ... WHERE ... INTO ...` valid without FIELDS? Yes — the new syntax allows SELECT ... FROM ... WHERE ... INTO ... (the INTO clause may be positioned at the end). Actually wait: in strict mode (7.50+), the INTO clause... The ABAP doc says: "The INTO clause can be specified after all other clauses (new order) or in the old position." In strict mode from 7.50, both allowed? Hmm: In the new Open SQL, the INTO clause should come last, but the old position (before WHERE) is still allowed for compatibility... Actually I recall: In strict mode 7.50, INTO must come at the end? No — the rule: "If the SELECT statement uses comma-separated list or other strict-mode features, the INTO clause must be placed at the end"? Let me recall precisely.

ABAP keyword doc, SELECT, INTO clause: "The INTO clause can be specified either ... after the SELECT list (old) or at the end of the statement (recommended in the new syntax)." And there's a rule: In strict modes (7.50+), the INTO clause must be at the end? Hmm, I believe: "As of release 7.50, if host variables with @ are used... the INTO clause can be at the end." I've definitely seen plenty of code: `SELECT SINGLE * FROM mara WHERE matnr = @lv_matnr INTO @DATA(ls_mara).` — yes, this pattern is everywhere and works. So INTO at end is fine.

Also `SELECT SINGLE @abap_true FROM tvko ...` — selecting a literal with SELECT SINGLE: fine.

But wait: does `SELECT SINGLE @abap_true` need `INTO @DATA(...)` typed as abap_bool? The result type of @abap_true is abap_bool (char1). lv_vkorg_ok will be char1. Check `IF sy-subrc <> 0` — fine. Could also check `lv_vkorg_ok <> abap_true` but if no row, is the variable assigned initial? With inline declaration + no row: variable declared, remains initial (abap_false/' '). sy-subrc check is cleaner. Good.

Alternatively skip the AT SELECTION-SCREEN block entirely... I'll keep it — it demonstrates "sauberer Fehlerbehandlung" on input level. But hmm, TVKO check: if user enters multiple orgs via multiple selection, IN works. OK.

Actually, one more consideration: Should the AT SELECTION-SCREEN check be `AT SELECTION-SCREEN ON s_vkorg`? That ties the message to the field. With plain AT SELECTION-SCREEN, TYPE 'E' message shows in status bar and selection screen stays. Fine either way. `ON s_vkorg` is nicer (message linked to field). But then the check runs only when s_vkorg changes... Actually ON s_vkorg triggers when the field content is transported (on enter/F8). Both work. I'll use `AT SELECTION-SCREEN ON s_vkorg`? Hmm, with OBLIGATORY, the obligatory check happens first. Then ON s_vkorg check. OK, use ON s_vkorg for field-level validation. 

Wait, but there's a subtlety: with SELECT-OPTIONS, AT SELECTION-SCREEN ON s_vkorg fires after the field's own validations. Fine.

Now, double-check the aggregation constant interface: IF_SALV_C_AGGREGATION=>TOTAL — yes.

Also `get_sorts( )->add_sort( columnname = 'VBELN' )` — add_sort params: columnname, position?, sequence, subtotal... default sequence ascending. Fine.

Potential runtime issue: add_sort on POSNR — fine.

Also, maybe set `lo_cols->set_key_fixation( )`? skip.

Should I also handle the case where the user wants the total row always visible? Default: when aggregation set, the totals row displays. OK.

Now — one more design question: procedural vs class. I'll go procedural as drafted; it's a report, readable, and the user asked for a report. Maybe mention that for production, wrapping in a local class is advisable. Or actually... let me reconsider: many reviewers would prefer class-based. But the request: "Schreibe einen ABAP-Report" — a classic report structure is expected. Procedural with clean sections is fine. I'll add a note.

Also mention: VBAK/VBAP in S/4HANA still exist; alternatively CDS views I_SalesDocumentItem (with I_SalesDocument) could be used — release-stable. Short note.

Also note about mixed currencies in the total.

Also note: message class recommended in production instead of hardcoded texts.

Let me double check `set_currency_column` method name: CL_SALV_COLUMN_TABLE->SET_CURRENCY_COLUMN( VALUE = 'WAERK' )? Hmm — I want to verify. In SALV object model, columns: CL_SALV_COLUMN has methods like set_long_text, set_technical, set_output_length... CL_SALV_COLUMN_TABLE adds: set_currency_column, set_quantity_column, set_decimals, set_decimals_out... I'm quite sure set_currency_column exists on cl_salv_column_table. Yes — e.g., `column ?= salv_table->get_columns()->get_column( 'NETWR' ). column->set_currency_column( 'WAERK' ).` This is a documented pattern. Good.

Note: get_column returns ref to cl_salv_column; set_currency_column is on cl_salv_column_table — do I need a downcast? get_column( ) returns TYPE REF TO cl_salv_column. set_technical is on cl_salv_column (base) — OK. set_currency_column is on cl_salv_column_table — calling it directly on the result of get_column would be a syntax error unless there's a widening... Since cl_salv_table=>factory creates a grid-based SALV whose columns are cl_salv_column_table instances, but statically the return type is cl_salv_column. Calling a method not defined on the static type → syntax error. So I need a cast:

```abap
DATA(lo_col_netwr) = CAST cl_salv_column_table( lo_cols->get_column( 'NETWR' ) ).
lo_col_netwr->set_currency_column( 'WAERK' ).
```

Hmm wait — is set_currency_column really on the subclass? Let me think again... I recall examples:

```abap
DATA: lo_column TYPE REF TO cl_salv_column_table.
lo_column ?= gr_columns->get_column( 'CURRENCY' ).
lo_column->set_currency_column( 'WAERK' ).
```

Yes, I've seen this pattern with cast to cl_salv_column_table. So set_currency_column/set_quantity_column are on CL_SALV_COLUMN_TABLE. Therefore I must cast. Let me restructure:

```abap
DATA(lo_col_netwr) = CAST cl_salv_column_table( lo_cols->get_column( 'NETWR' ) ).
lo_col_netwr->set_currency_column( value = 'WAERK' ).
DATA(lo_col_kwmeng) = CAST cl_salv_column_table( lo_cols->get_column( 'KWMENG' ) ).
lo_col_kwmeng->set_quantity_column( value = 'VRKME' ).
```

And for set_technical, get_column result (cl_salv_column) has set_technical directly — no cast needed:

```abap
lo_cols->get_column( 'WAERK' )->set_technical( abap_true ).
lo_cols->get_column( 'VRKME' )->set_technical( abap_true ).
```

set_technical is on cl_salv_column — yes.

Also set_optimize on cl_salv_columns — yes.

Hmm, also: is it `set_quantity_column`? I believe yes: CL_SALV_COLUMN_TABLE->SET_QUANTITY_COLUMN. Yes.

Alternatively, simpler: skip currency/quantity reference handling and just display raw numbers — but then NETWR shows without currency and KWMENG without unit; and worse, KWMENG without unit reference may display with wrong decimals? QUAN fields display with their defined decimals (3) even without unit. It's acceptable but not clean. The expert move is to include the reference handling. Keep it.

Alternatively, even cleaner: define a local type with DDIC-like semantics? Not possible for currency refs in local types. The set_currency_column approach is right.

Now, another thought: should I use `NEW cl_salv_table(...)`? Not possible (CREATE PRIVATE). Keep factory.

Also consider adding `lo_alv->set_screen_status( )`? Not needed since set_all( abap_true ).

Let me also think about `set_list_header` — maybe simpler: `lo_disp->set_list_header( 'Kundenaufträge' )` and add count via `set_list_header_size`? The count in header is a nice touch; string template fine.

Hmm, but wait: `lines( lt_orders )` inside string template — fine.

Now the header text length: set_list_header param is `value TYPE sytitle` — sytitle is CHAR70. String longer than 70 truncates. Our text short. OK.

One more: `MESSAGE ... TYPE 'S' DISPLAY LIKE 'E'` then RETURN — the user sees status message. Good.

Also: Should I add `IF lt_orders IS INITIAL` instead of sy-subrc? Both; I'll use sy-subrc <> 0 with comment. Fine.

Now, potential compile issue: In the SELECT, I use `vbak~vbtyp = @gc_vbtyp_auftrag` — constant declared with TYPE vbak-vbtyp. Fine.

Also: ORDER BY vbap~vbeln, vbap~posnr — in new OpenSQL, ORDER BY with host variables not needed; column names after ORDER BY don't need @. Correct: `ORDER BY vbap~vbeln, vbap~posnr`. Fine.

Also: alias-less join: `FROM vbap INNER JOIN vbak ON vbak~vbeln = vbak~vbeln` — careful to write `ON vbak~vbeln = vbap~vbeln`. Yes.

Hmm, actually should I put vbak first for readability? `FROM vbak INNER JOIN vbap ON ...` and select vbap fields — either fine. Keep vbap first? Conventionally FROM vbak JOIN vbap. Let me use vbak as the leading table (header drives selection):

```abap
SELECT vbap~vbeln, ...
  FROM vbak
  INNER JOIN vbap ON vbap~vbeln = vbak~vbeln
  WHERE vbak~vkorg IN @s_vkorg ...
```

Fine.

Also, should I add `%_HINTS`? No.

Buffering/performance: WHERE on vkorg+erdat uses index VBAK~0? VKORG ERDAT index exists (VBAK has index on VKORG/ERDAT? There's index VBAK~0? Standard index 'A'? Anyway fine.)

Now, the explanation section: keep concise bullets:

- Warum VRKME/WAERK mit selektiert werden (Referenzfelder für korrekte Mengen-/Währungsdarstellung), technisch ausgeblendet.
- Summe: add_aggregation → Summenzeile unten; Nutzer kann weitere Zwischensummen interaktiv.
- Fehlerbehandlung: Eingabeprüfung (TVKO), Leermenge, TRY/CATCH um SALV-API (cx_salv_*).
- Inline-Deklarationen: @DATA(lt_orders), DATA(lo_alv) etc.
- Hinweise: In S/4 alternativ CDS I_SalesDocumentItem; Message-Klasse für Produktion; Total über gemischte Währungen sinnvoll einschränken.

Also maybe mention: `vbtyp = 'C'` ensures only sales orders (not inquiries/quotations).

Length: code ~80 lines + short bullets. Good. Format: code block with abap syntax. German response.

One more check on `CAST cl_salv_column_table( ... )` — CAST available since 7.40. Good, fits 7.5x.

Also `CONV`? Not needed.

Let me also double check factory's changing param name: `t_table`. Yes.

Also — `lo_alv->get_functions( )->set_all( abap_true )` — correct.

Edge: If report runs in background, display( ) works (list processing). Fine.

Also, maybe I should guard the aggregation: if NETWR column technical? No, it's visible.

Another subtle thing: after set_technical on WAERK/VRKME, do set_currency_column/set_quantity_column still work? Order: I set currency/quantity refs first, then technical. If technical were set first, the column still exists in catalog; setting ref afterwards should still work. My order is fine anyway.

Hmm, one more consideration on `set_technical`: it hides the column entirely (also from layout dialog?). set_technical makes column invisible and excluded from field catalog usage. The currency reference by name should still resolve since CFIELDNAME is set on NETWR column. I believe OK.

Alternative safer: use set_visible( abap_false )? Hmm, set_visible(false) keeps column in layout. Technical is common. Keep technical.

Wait, actually there's a subtlety: I recall that for ALV currency formatting, if the currency column is marked as "technical" (TECH = 'X' in field catalog), the amount formatting may fail because the ALV ignores technical fields for reference? Let me think... In cl_gui_alv_grid field catalog, CFIELDNAME points to a field name in the output table; the field doesn't need to be an output column. TECH fields are still in the catalog. I'm fairly confident formatting works with technical reference fields. Many standard reports do exactly this. OK.

Hmm, but to be extra safe, I could instead not mark them technical but set them as visible... The user asked for specific columns though. I'll keep technical and note the alternative.

Actually, you know, let me reconsider: maybe simply keep WAERK and VRKME visible as extra columns? The requirement lists 5 columns "Auftragsnummer, Position, Material, Menge, Nettowert". Adding currency/unit columns is helpful but deviates. Technical hiding is the elegant solution. Keep.

Now, about the totals: also consider setting the totals row display: `lo_alv->get_display_settings( )` has no totals toggle; totals show automatically. OK.

Let me also think: do I need `lo_alv->get_selections( )`? No.

Final check on exception list: CX_SALV_MSG (factory/display), CX_SALV_NOT_FOUND (get_column, add_aggregation, add_sort), CX_SALV_EXISTING (add_aggregation duplicate), CX_SALV_DATA_ERROR (factory with wrong table type). Good coverage. Could also catch CX_SALV_OBJECT_NOT_FOUND? Not standard here. Fine.

Also note: `INTO DATA(lx_error)` — the CATCH ... INTO — syntax: `CATCH cx_salv_msg cx_salv_not_found ... INTO DATA(lx_error).` Yes, CATCH supports INTO with inline declaration. Good.

Now write the surrounding text in German, concise. Structure:

1. Kurze Einleitung (1 Satz).
2. Code block.
3. "Hinweise" bullets (kurz): Referenzfelder, Summe, Fehlerbehandlung, S/4-CDS-Alternative, Währungshinweis, Message-Klasse.

Keep bullets tight. Maybe 5-6 bullets.

Also the report name: ZSD_KUNDAUFTRAEGE or ZSD_ORDER_LIST. Use zsd_kundenauftraege? Report names ≤ 8 chars for old naming? Customer namespace Z + 7 = 8 chars: "ZSD_KDAUF"? Hmm, report names can be longer nowadays (up to 40 chars for objects in newer releases? Program names limited to 40). Actually program names can be up to 40 characters. ZSD_KUNDAUFTRAGE fine. I'll use ZSD_KUNDAUFTRAEGE (16 chars) — allowed. Or keep simple: ZSD_ORDER_REPORT. I'll use ZSD_KUNDAUFTRAEGE.

Wait, one more syntax check: `SELECT-OPTIONS: s_vkorg FOR vbak-vkorg OBLIGATORY` — referencing vbak-vkorg requires the table known — fine in report (DDIC).

Also, do I need TABLES vbak/vbap statement for select-options FOR vbak-vkorg? No — FOR with DDIC table field works without TABLES since the field reference is to the DDIC object, not a memory area. `SELECT-OPTIONS s_vkorg FOR vbak-vkorg.` compiles without TABLES. Yes (it only needs the type). Correct.

Now, is `AT SELECTION-SCREEN ON s_vkorg` + SELECT SINGLE with inline decl OK? Inline declaration inside event block — fine.

Hmm, but there's one gotcha: inline declaration in AT SELECTION-SCREEN ON s_vkorg creates lv_vkorg_ok; if the user runs again (back → F8), the declaration is re-executed — inline declarations in event blocks executed multiple times: allowed? Inline declarations are declarations processed at runtime position; re-execution is fine (it's like DATA in a block executed repeatedly? Actually inline declarations are static declarations visible program-wide after first textual occurrence; re-executing the statement just assigns). Yes fine.

Also in START-OF-SELECTION, DATA(lt_orders) etc. — fine.

One thing: `MESSAGE 'Verkaufsorganisation unbekannt...' TYPE 'E'.` in AT SELECTION-SCREEN ON s_vkorg — type E in screen processing → dialog message, stays on screen. Good.

Also literal message length: MESSAGE literal max 100 chars? Fine.

Now, is there an issue using both `s_vkorg` obligatory and the TVKO check when user enters nothing? OBLIGATORY prevents empty. OK.

Let me also reconsider making s_erdat obligatory — if user wants all dates, they can't. But spec says date range is a selection criterion; obligatory is reasonable. Hmm, I'll make s_vkorg obligatory and s_erdat obligatory too? I'll make both obligatory but note they can remove OBLIGATORY. Actually, let me make s_erdat NOT obligatory and handle empty = all dates? The spec: "Selektionsbildschirm (Verkaufsorganisation, Erstelldatum von–bis)". I'll set both obligatory for clear semantics; mention in a note that OBLIGATORY can be dropped. Fine.

Also: maybe add `NO INTERVALS`? No — "von–bis" implies interval wanted.

Double-check the string template in set_list_header: `|Kundenaufträge ({ lines( lt_orders ) } Positionen)|` — spaces inside template around { } are literal; `{ lines( lt_orders ) }` — expression with spaces OK. Result e.g. "Kundenaufträge (42 Positionen)". Good.

Also, umlauts in code — fine.

One more possible improvement: use `@DATA(lt_orders)` then pass to factory — factory CHANGING t_table requires the table to be a standard table? lt_orders from SELECT INTO TABLE is standard table with empty key? Inline declared table from SELECT: TYPE STANDARD TABLE (sorted? no, standard) — fine for SALV (needs standard/sorted/hashable? SALV requires the table category to allow index access; standard fine).

Also: SALV requires the internal table to be "flat"; our structure flat. Good.

Also worth noting: factory keeps reference to lt_orders; since lt_orders is a local inline-declared variable in the event block, it lives until end of event block — display( ) is called within same block, so fine.

Now, write the final answer in German. Include short intro sentence, code, then compact notes.

Let me also double check `if_salv_c_aggregation=>total` — the constant is named TOTAL in interface IF_SALV_C_AGGREGATION. Yes.

And `get_aggregations( )` returns cl_salv_aggregations; add_aggregation( columnname = ... aggregation = ... ). Yes. It raises CX_SALV_NOT_FOUND and CX_SALV_EXISTING. Covered.

Also `get_sorts( )` returns cl_salv_sorts; add_sort( columnname = 'VBELN' ) raises cx_salv_not_found? add_sort raises CX_SALV_NOT_FOUND and CX_SALV_EXISTING. Covered.

Also, one more idea: set the NETWR column to be right-aligned — default for CURR. Skip.

Also `set_zero`? skip.

Also maybe `lo_cols->set_exception_column`? no.

OK also think: should the SELECT include `UP TO 50000 ROWS` safety? I'll leave it out but mention performance note briefly? Maybe one bullet: bei großen Datenmengen Paketierung/UP TO n ROWS erwägen. Keep notes short.

Let me now also double-check the new OpenSQL join syntax with client handling: automatic. Good.

Also `vbak~vbtyp = @gc_vbtyp_auftrag` — good.

Potential detail: In S/4HANA, VBAK~VBTYP values: 'C' = Auftrag. Yes.

Write the answer:

Intro: "Hier ein kompletter, lauffähiger Report..." then code, then notes.

Also mention that column texts come from DDIC (Auftrag, Position, Material, Menge, Nettowert) — matching requested labels; can override with set_long_text if needed.

Final code review once more for syntax correctness:

```abap
*&---------------------------------------------------------------------*
*& Report ZSD_KUNDAUFTRAEGE
*&---------------------------------------------------------------------*
REPORT zsd_kundauftraege.

CONSTANTS gc_vbtyp_auftrag TYPE vbak-vbtyp VALUE 'C'.   " Belegkategorie 'Auftrag'

*----------------------------------------------------------------------*
* Selektionsbildschirm
*----------------------------------------------------------------------*
SELECT-OPTIONS: s_vkorg FOR vbak-vkorg OBLIGATORY,      " Verkaufsorganisation
                s_erdat FOR vbak-erdat OBLIGATORY.      " Erstelldatum von-bis

*----------------------------------------------------------------------*
* Eingabeprüfung
*----------------------------------------------------------------------*
AT SELECTION-SCREEN ON s_vkorg.

  SELECT SINGLE @abap_true
    FROM tvko
    WHERE vkorg IN @s_vkorg
    INTO @DATA(lv_vkorg_ok).

  IF sy-subrc <> 0.
    MESSAGE 'Unbekannte Verkaufsorganisation - bitte Eingabe prüfen' TYPE 'E'.
  ENDIF.

*----------------------------------------------------------------------*
* Hauptverarbeitung
*----------------------------------------------------------------------*
START-OF-SELECTION.

  " 1) Daten lesen - Ergebnistyp per Inline-Deklaration
  SELECT vbap~vbeln,     " Auftragsnummer
         vbap~posnr,     " Position
         vbap~matnr,     " Material
         vbap~kwmeng,    " Menge
         vbap~vrkme,     " Mengeneinheit (nur Referenzfeld)
         vbap~netwr,     " Nettowert
         vbap~waerk      " Währung      (nur Referenzfeld)
    FROM vbak
    INNER JOIN vbap ON vbap~vbeln = vbak~vbeln
    WHERE vbak~vkorg IN @s_vkorg
      AND vbak~erdat IN @s_erdat
      AND vbak~vbtyp  = @gc_vbtyp_auftrag
    ORDER BY vbap~vbeln, vbap~posnr
    INTO TABLE @DATA(lt_orders).

  " 2) Fehlerbehandlung: keine Daten
  IF sy-subrc <> 0.
    DATA(lv_msg) = |Keine Kundenaufträge zu den gewählten Kriterien gefunden|.
    MESSAGE lv_msg TYPE 'S' DISPLAY LIKE 'E'.
    RETURN.
  ENDIF.

  " 3) SALV-ALV aufbauen und anzeigen
  TRY.
      cl_salv_table=>factory(
        IMPORTING r_salv_table = DATA(lo_alv)
        CHANGING  t_table      = lt_orders ).

      " Toolbar komplett freigeben (Sortieren, Filtern, Export, ...)
      lo_alv->get_functions( )->set_all( abap_true ).

      DATA(lo_cols) = lo_alv->get_columns( ).
      lo_cols->set_optimize( abap_true ).

      " Währungs-/Mengenreferenz für korrekte Anzeige der Werte/Mengen
      CAST cl_salv_column_table( lo_cols->get_column( 'NETWR'  ) )->set_currency_column( 'WAERK' ).
      CAST cl_salv_column_table( lo_cols->get_column( 'KWMENG' ) )->set_quantity_column( 'VRKME' ).

      " Referenzfelder nicht als eigene Spalten anzeigen
      lo_cols->get_column( 'WAERK' )->set_technical( abap_true ).
      lo_cols->get_column( 'VRKME' )->set_technical( abap_true ).

      " Summenzeile über den Nettowert
      lo_alv->get_aggregations( )->add_aggregation(
          columnname  = 'NETWR'
          aggregation = if_salv_c_aggregation=>total ).

      " Grundsortierung
      lo_alv->get_sorts( )->add_sort( columnname = 'VBELN' ).
      lo_alv->get_sorts( )->add_sort( columnname = 'POSNR' ).

      " Ausgabedialog
      DATA(lo_disp) = lo_alv->get_display_settings( ).
      lo_disp->set_list_header( |Kundenaufträge ({ lines( lt_orders ) } Positionen)| ).
      lo_disp->set_striped_pattern( abap_true ).

      lo_alv->display( ).

    CATCH cx_salv_msg cx_salv_not_found cx_salv_data_error cx_salv_existing
          INTO DATA(lx_error).
      DATA(lv_err) = lx_error->get_text( ).
      MESSAGE lv_err TYPE 'S' DISPLAY LIKE 'E'.
  ENDTRY.
```

Check: `CAST cl_salv_column_table( lo_cols->get_column( 'NETWR' ) )->set_currency_column( 'WAERK' ).` — CAST with method call on result: `CAST cl_salv_column_table( ... )->method( )` — valid standalone statement? A method call statement on a cast expression: `CAST class( expr )->meth( ).` — yes, valid since 7.40 (standalone method call with chained expression). Good.

set_currency_column parameter: `set_currency_column( value = 'WAERK' )` or positional — positional fine if single importing param `value`. I think the param is named `value`? Hmm, actually for CL_SALV_COLUMN_TABLE->SET_CURRENCY_COLUMN the parameter might be named `VALUE`? Many SALV setters use `value`. Positional call works regardless: `set_currency_column( 'WAERK' )` — if the method has exactly one importing parameter, positional is fine. Yes.

Hmm wait, does set_currency_column also raise cx_salv_not_found if the currency column name doesn't exist? Possibly at display time. Covered by catch.

One thing: `CAST cl_salv_column_table( lo_cols->get_column( 'NETWR' ) )` — if get_column returns initial (not found it raises instead), fine.

Also check: `lo_disp->set_list_header( |...| )` — passing string template to method parameter — expressions allowed in method call parameters. Yes.

`lines( lt_orders )` — fine.

Also, the AT SELECTION-SCREEN inline declaration `DATA(lv_vkorg_ok)` — used only there; fine.

Potential warning: lv_vkorg_ok unused after check — used implicitly. Fine.

Now — one more consideration about `MESSAGE lv_msg TYPE 'S' DISPLAY LIKE 'E'` where lv_msg is a string: MESSAGE with dynamic text: `MESSAGE msg TYPE t` where msg is character-like data object — allowed. String type is character-like; OK.

Also: `RETURN.` — ends START-OF-SELECTION; no list output; program ends. Good.

Also: after CATCH with message type 'S', program ends. Good.

Now the notes section (German, concise):

- **Referenzfelder WAERK/VRKME**: werden mitselektiert und via set_currency_column/set_quantity_column zugewiesen, damit Menge und Nettowert korrekt (Einheit/Währung, Dezimalstellen) formatiert werden; als technical ausgeblendet, damit genau die 5 gewünschten Spalten erscheinen.
- **Summe**: add_aggregation(... total) erzeugt die Summenzeile; im ALV können Anwender zusätzlich interaktiv Zwischensummen (z. B. pro Auftrag) bilden. Hinweis: Bei mehreren Währungen ist das Gesamtsumme fachlich fragwürdig → ggf. je Währung auswerten.
- **Fehlerbehandlung**: dreistufig — Eingabeprüfung (TVKO), Leermenge (Message S/E + RETURN), TRY/CATCH um die gesamte SALV-API (cx_salv_*).
- **vbtyp = 'C'**: stellt sicher, dass wirklich nur Aufträge (keine Angebote/Anfragen) kommen.
- **S/4-typisch**: VBAK/VBAP existieren weiterhin; für Neuentwicklungen ggf. die CDS-Sicht I_SalesDocumentItem (release-stable) verwenden. In Produktion: eigene Nachrichtklasse statt freier Texte.

Maybe also: Spaltentitel kommen aus DDIC (Auftrag, Position, Material, Menge, Nettowert) — passt zu den Anforderungen; alternativ set_long_text.

Keep to ~5 bullets. Also mention OBLIGATORY optional? Minor; skip or one clause.

Format: header "Hinweise" with bullets. Code block with abap. The response should be in German. Reasonable length.

One more syntax double-check on the SELECT: field list with comments after commas — comments between field list items are allowed (lines with "..." comments). Yes, comments allowed within SELECT statements.

Also: `ORDER BY vbap~vbeln, vbap~posnr` then `INTO TABLE @DATA(lt_orders).` — order of clauses: SELECT list FROM ... WHERE ... ORDER BY ... INTO TABLE. Hmm — is ORDER BY before INTO correct? In new syntax, INTO at the end after ORDER BY: `SELECT ... FROM ... WHERE ... ORDER BY ... INTO TABLE @DATA(itab).` Yes, that's valid (INTO last). Good.

Also with ORDER BY in new OpenSQL: columns must be in select list or... ORDER BY vbap~vbeln — vbeln is in the list. Fine. (In strict mode, ORDER BY columns should appear in the SELECT list — both do.)

Also: alias? We use table names directly with ~. Fine.

Also, the join: `FROM vbak INNER JOIN vbap ON vbap~vbeln = vbak~vbeln` — correct.

I think the code is solid. One more thought on `set_list_header`: maybe also `set_list_header_size`? no.

Also, should I add `lo_alv->get_selections( )->set_selection_mode( if_salv_c_selection_mode=>row_column )`? Not needed.

Also, maybe add `lo_cols->set_key_fixation( abap_true )`? skip.

Alright. Also, quick sanity: `cl_salv_table=>factory` — when called without container, display( ) shows fullscreen ALV grid. Yes.

Potential nuance: In some systems, `set_all( abap_true )` on functions also enables GUI_STATUS standard functions — fine.

Now write the final answer in German. Include short intro sentence, code, then compact notes.

Actually, one more consideration on the AT SELECTION-SCREEN: if user enters VKORG with pattern that matches nothing but is a valid range... fine.

Also — should the TVKO check be skipped when s_vkorg is initial? It's obligatory, so can't be initial at AT SELECTION-SCREEN ON s_vkorg (obligatory check fires first). But defensive: `IF s_vkorg[] IS NOT INITIAL.` wrapper? With OBLIGATORY it's guaranteed non-empty. I'll skip the wrapper for brevity... Hmm, but if someone removes OBLIGATORY later, the check with empty s_vkorg: WHERE vkorg IN empty-range → matches all rows → sy-subrc 0 → OK, no false error. Actually an empty range IN condition is always true, so SELECT SINGLE finds a row → no error. So even without OBLIGATORY it behaves correctly. 

Also note: `SELECT SINGLE @abap_true FROM tvko ...` — TVKO has client field; automatic client handling. Good.

Edge: If system has no TVKO entries (unlikely). Fine.

I'm also wondering whether to demonstrate `CONV` or `VALUE` — not necessary; inline declarations are the requirement and they're used throughout.

Let me finalize the notes and answer. Also start with one line: "Hier ist ein kompletter Report..." — in German.

Regarding formatting: use a single abap code block; bullets after. Headers maybe not needed; just "Hinweise:" bold or a small header. Keep it clean.

</details>
