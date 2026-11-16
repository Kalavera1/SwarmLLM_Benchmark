# ABAP: amdp-high

## Aufgabe

Schreibe eine AMDP-Klasse (ABAP Managed Database Procedure) für SAP HANA, die für eine übergebene Verkaufsorganisation die Top-10-Materialien nach Umsatz aus VBAP/VBAK liefert. Mit Klassendefinition (IF_AMDP_MARKER_HDB), Methodensignatur, SQLScript-Implementierung und einem Aufruf aus ABAP. Erkläre, wann sich AMDP gegenüber ABAP-SQL lohnt.

## Antwort

# AMDP-Klasse: Top-10-Materialien nach Umsatz

## Vorbereitung: DDIC-Tabellentyp (Voraussetzung)

AMDP-Schnittstellenparameter müssen **Dictionary-Typen** sein (keine lokalen ABAP-Typen). Im SE11 wird daher ein Tabellentyp benötigt:

```
ZTT_TOP_MATERIALS  (Tabellentyp, Zeilentyp: ZST_TOP_MATERIAL)
  ZST_TOP_MATERIAL (Struktur):
    MATNR   TYPE MATNR
    ARKTX   TYPE ARKTX
    WAERK   TYPE WAERK
    UMSATZ  TYPE NETWR
```

## Klassendefinition

```abap
CLASS zcl_top_materials DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    INTERFACES if_amdp_marker_hdb.   " Kennzeichnet HANA-AMDP-Klasse

    TYPES: BEGIN OF ty_top_material,
             matnr  TYPE matnr,
             arktx  TYPE arktx,
             waerk  TYPE waerk,
             umsatz TYPE netwr,
           END OF ty_top_material.

    " Für AMDP: DDIC-Tabellentyp verwenden (ztt_top_materials),
    " lokale Typen wie ty_top_material sind in AMDP-Schnittstellen NICHT erlaubt
    CLASS-METHODS get_top_materials
      IMPORTING VALUE(iv_vkorg) TYPE vkorg
      EXPORTING VALUE(et_result) TYPE ztt_top_materials
      RAISING   cx_amdp_error.

ENDCLASS.
```

## Implementierung (SQLScript)

```abap
CLASS zcl_top_materials IMPLEMENTATION.

  METHOD get_top_materials
         BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT
         OPTIONS READ-ONLY
         USING vbak vbap.

    -- Aggregation: Umsatz je Material für die Verkaufsorganisation
    lt_sales =
      SELECT DISTINCT
             vbap.matnr            AS matnr,
             MAX( vbap.arktx )     AS arktx,
             vbap.waerk            AS waerk,
             SUM( vbap.netwr )     AS umsatz
        FROM vbap
        INNER JOIN vbak
           ON  vbak.vbeln = vbap.vbeln
       WHERE vbak.vkorg = :iv_vkorg
         AND vbak.auart <> 'ZC'          " z. B. Kontraktaufträge ausklammern
       GROUP BY vbap.matnr, vbap.waerk;

    -- Top 10: Sortierung + Limit direkt in der DB
    et_result =
      SELECT matnr, arktx, waerk, umsatz
        FROM :lt_sales
       ORDER BY umsatz DESC
       LIMIT 10;

  ENDMETHOD.

ENDCLASS.
```

> **Hinweis:** Die Gruppierung enthält `WAERK`, da Umsätze unterschiedlicher Währungen nicht sinnvoll summiert werden können. Bei gemischten Währungen müsste zusätzlich umgerechnet oder je Währung ausgewiesen werden.

## Aufruf aus ABAP

```abap
DATA(go_out) = cl_demo_output=>new( ).

TRY.
    zcl_top_materials=>get_top_materials(
      EXPORTING iv_vkorg  = CONV vkorg( '1010' )
      IMPORTING et_result = DATA(lt_top_materials) ).

    go_out->display( lt_top_materials ).

  CATCH cx_amdp_error INTO DATA(lx_amdp).
    MESSAGE |AMDP-Fehler: { lx_amdp->get_text( ) }| TYPE 'E'.
ENDTRY.
```

Der Aufruf ist ein normaler Methodenaufruf – die Ausführung findet aber vollständig auf der HANA statt (Code-to-Data-Paradigma).

---

## Wann lohnt sich AMDP gegenüber ABAP-SQL?

**AMDP lohnt sich, wenn:**

- **Rechenintensive Operationen auf großen Datenmengen** anfallen und das Ergebnis klein ist (Aggregationen, Top-N, Gruppierungen). Daten werden nicht erst ins ABAP kopiert, sondern auf der DB reduziert – das ist der größte Performancehebel.
- **SQLScript-Funktionen benötigt werden**, die ABAP-SQL nicht oder nur umständlich bietet: imperative Logik, lokale temporäre Tabellen, komplexe Window-Funktionen, prozedurale Abläufe mit Zwischenergebnissen.
- **Mehrschrittige Berechnungen** mit Zwischentabellen nötig sind, die in einem einzelnen `SELECT` nicht ausdrückbar sind (wie oben: erst aggregieren, dann Top-N).
- Die Logik **nur auf HANA lauffähig sein darf** bzw. das System bewusst HANA-only ist und man maximale DB-Power nutzen will.
- Die Logik von **CDS-Views und anderen AMDP-Methoden wiederverwendet** werden soll.

**ABAP-SQL (Open SQL / CDS) ist besser, wenn:**

- Es sich um **einfache Selektionen, Joins oder Aggregationen** handelt – Open SQL deckt heute sehr viel ab (inkl. `WINDOW`-Funktionen, CTEs, `LIMIT`) und ist **DB-agnostisch**.
- **Testbarkeit und Debugging** wichtig sind: AMDP lässt sich nicht im ABAP Debugger debuggen (nur via HANA Studio/SQL Trace) und nicht über ABAP Unit testen.
- **Portabilität** gefordert ist (z. B. AnyDB-Support).
- Die Logik **deklarativ** ausdrückbar ist – CDS-Views bieten dort bessere Wiederverwendbarkeit und Erweiterbarkeit (VDM).

**Faustregel:** Erst mit Open SQL/CDS lösen; erst wenn die Ausdrucksstärke oder Performance dort nicht reicht (Pushdown komplexer, datenintensiver Logik), ist AMDP das richtige Werkzeug.

---

<details><summary>Denkprozess (2346 Zeichen)</summary>

User wants an AMDP class in German, with class definition, method signature, SQLScript implementation, ABAP call, and explanation when AMDP is beneficial over ABAP SQL. Provide code with proper syntax: CLASS ... DEFINITION, INTERFACES if_amdp_marker_hdb, METHOD ... BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT. Include types (table types), AMDP options READ-ONLY, error handling via RAISE AMDP... maybe keep simple. Also call example with exception handling cx_amdp_error.

Let me write it carefully.

Class: zcl_top_materials. Types: ty_sales type standard table with fields matnr, arktx?, umsatz. Use VBAP/VBAK fields: netwr, waerk. Group by matnr, sum netwr. Top 10 via LIMIT.

CDS or DDIC types needed — AMDP interface parameters must be DDIC types (or CDS). I'll define DDIC table types in comments, or use existing types. I'll note that parameter types must be dictionary types.

Method signature:

CLASS-METHODS get_top_materials
  IMPORTING VALUE(iv_vkorg) TYPE vkorg
  EXPORTING VALUE(et_result) TYPE ztt_top_materials
  RAISING cx_amdp_error.

Implementation:

METHOD get_top_materials BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT
                         OPTIONS READ-ONLY
                         USING vbak vbap.

  lt_sales = SELECT ... FROM vbap INNER JOIN vbak ...

  et_result = SELECT ... :lt_sales ... ORDER BY umsatz DESC LIMIT 10;

Note: in SQLScript, export param assignment via et_result = SELECT ... Also need DECLARE for table variable: lt_sales = SELECT ... creates implicitly.

Currency: sum netwr per waerk? Simplify: group by matnr, sum(netwr) — mention currency consideration. Maybe group by matnr and waerk, or assume single currency. I'll include waerk in grouping or note it.

ABAP call:

TRY.
    zcl_top_materials=>get_top_materials( EXPORTING iv_vkorg = '1010' IMPORTING et_result = DATA(lt_result) ).
  CATCH cx_amdp_error INTO DATA(lx).
    ...
ENDTRY.

cl_demo_output=>display( lt_result ).

Explanation when AMDP worthwhile: pushdown of compute-intensive logic, SQLScript features (window functions, complex joins, loops), code-to-data, when ABAP SQL can't express (imperative logic, temp tables), reuse across ABAP + other consumers, performance on large data volumes; not worthwhile for simple selects, debugging/testing harder, no Open SQL optimizations, only HANA.

Write the answer in German.

</details>
