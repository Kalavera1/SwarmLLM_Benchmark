# ABAP: amdp

## Aufgabe

Schreibe eine AMDP-Klasse (ABAP Managed Database Procedure) für SAP HANA, die für eine übergebene Verkaufsorganisation die Top-10-Materialien nach Umsatz aus VBAP/VBAK liefert. Mit Klassendefinition (IF_AMDP_MARKER_HDB), Methodensignatur, SQLScript-Implementierung und einem Aufruf aus ABAP. Erkläre, wann sich AMDP gegenüber ABAP-SQL lohnt.

## Antwort



---

<details><summary>Denkprozess (127831 Zeichen)</summary>

The user wants an AMDP class (ABAP Managed Database Procedure) for SAP HANA in ABAP. The task:

1. Write an AMDP class for SAP HANA that, for a given sales organization (Verkaufsorganisation), returns the top 10 materials by revenue (Umsatz) from VBAP/VBAK.
2. Include:
   - Class definition with IF_AMDP_MARKER_HDB
   - Method signature
   - SQLScript implementation
   - Call from ABAP
3. Explain when AMDP is worthwhile compared to ABAP SQL.

The user writes in German, so I should respond in German.

Let me think about the correct AMDP implementation:

Key points for AMDP:
- Class must implement IF_AMDP_MARKER_HDB
- Method must be declared in a special way: `CLASS-METHODS` or `METHODS` with `BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT [OPTIONS READ-ONLY] USING vbak vbap.`
- The method implementation contains only SQLScript code (no ABAP statements inside)
- Parameters: pass-by-value, and for the client handling: in newer releases, AMDP methods in classes should handle client via parameter or implicit client handling. Actually, for AMDP, the client field must be handled explicitly or via the session variable. In AMDP, there's implicit client handling if the method is declared with the client as parameter... Let me recall precisely.

AMDP client handling: Since ABAP 7.40/7.50, AMDP methods can have implicit client handling if the first parameter is the client (clnt) of type... Actually the rules: For AMDP, the client handling is explicit by default; you can enable implicit client handling by declaring the method with parameter `clnt` as first importing parameter of type... Hmm. Let me recall.

For AMDP methods:
- The method declaration: `METHODS get_data BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT OPTIONS READ-ONLY USING sflight.`
- Parameters must be passed by VALUE.
- Tables types must be defined in the ABAP Dictionary (DDIC) or as types of the class? For AMDP, the tabular parameters must be DDIC table types (types with a DDIC structure as line type). Actually: "The type of the parameters must be either elementary or table types from ABAP Dictionary" — table types must be defined in ABAP Dictionary with a DDIC structure as row type. In newer releases (7.52+?), also types defined in class... no, still DDIC table types required. Actually, since 7.53 or so, "The tabular input and output parameters of AMDP methods must be typed with table types from the ABAP Dictionary" — that's still the rule. Hmm, but there's also the possibility of using types from the class if they're based on DDIC structures? Let me be careful: The rule is: elementary types or DDIC table types whose row type is a DDIC structure (or elementary). Since ABAP 7.52, AMDP can also use CDS-based types? For safety, I'll use DDIC table types.

For the client: In AMDP, implicit client handling: If the AMDP method has an importing parameter named `clnt` (or declared with `USING`?)... The actual rule: AMDP methods get implicit client handling if the method declaration includes a parameter for the client. From SAP documentation: "For AMDP methods, implicit client handling is switched on by declaring an input parameter clnt of type abap.clnt" — hmm, not exactly. Let me recall the documentation:

"Client handling in AMDP: By default, AMDP procedures do not get automatic client handling. Implicit client handling can be enabled by declaring a mandatory input parameter clnt of type... as the first parameter? " 

Actually from SAP doc (ABAP Keyword Documentation, "AMDP - Client Handling"): 
- For AMDP methods, implicit client handling is not automatic. It is enabled by declaring a client parameter `clnt` as the first input parameter of the method? Hmm.

Let me recall precisely: In the ABAP documentation for AMDP methods:

"AMDP methods are handled as follows with respect to client handling:
- If the AMDP method has an input parameter named clnt of type abap.clnt (or a DDIC data element with client reference?), the current client is passed to it implicitly... no wait.

Actually the correct rule (from ABAP docs, topic "AMDP - Client Handling"): 

"AMDP methods and AMDP function implementations can be declared with implicit client handling by declaring an input parameter clnt as first parameter..." Hmm, I think the rule is:

For implicit client handling in AMDP:
- The method must have a parameter `clnt` of type `abap.clnt`? Hmm, but actually I recall it's: the parameter must be named `clnt` and be the first importing parameter? No...

Let me think about real examples from SAP documentation:

```abap
CLASS cl_demo_amdp DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES: t_sflight TYPE TABLE OF sflight WITH EMPTY KEY.
    CLASS-METHODS get_flights
      IMPORTING VALUE(clnt)     TYPE sy-mandt
                VALUE(carrid)   TYPE sflight-carrid
      EXPORTING VALUE(flights)  TYPE t_sflight.
ENDCLASS.
```

Hmm, but that's explicit passing of sy-mandt.

The implicit client handling: From ABAP docs "AMDP - Client Handling":

"AMDP methods: If the AMDP method has an input parameter clnt of type abap.clnt as its first parameter? ..." 

Actually I recall now: The rule for implicit client handling in AMDP is that the client parameter must be named `clnt` and be the first importing parameter of the method. Then the current client is passed automatically when the method is called without specifying clnt? No — when called, you still pass it? Hmm.

Let me recall the actual documentation text: 

From ABAP Keyword Documentation (7.5x), "AMDP - Client Handling":

"Client handling is not performed implicitly in AMDP procedures... AMDP methods can be declared with implicit client handling by declaring a mandatory input parameter clnt of type abap.clnt... " Hmm.

Actually here's what I remember more concretely: For AMDP methods, implicit client handling is enabled when the method has an input parameter named `clnt` of type... and then when calling the method, the parameter clnt can be omitted and sy-mandt is passed automatically? No — I think for AMDP methods, you must pass the client explicitly; the implicit client handling means that the client parameter is automatically filled with the current client if... Hmm.

Let me look at this from a different angle: In CDS table functions, implicit client handling is done via the `clnt` parameter — the first parameter of type abap.clnt, and when you access the table function in ABAP SQL, the session variable CDS_CLIENT / sy-mandt is passed automatically.

For AMDP methods: The documentation says (I'm fairly confident): "For AMDP methods, implicit client handling is switched on by declaring a mandatory input parameter clnt as first input parameter of the method. When the method is called, the current client is passed automatically to this parameter..." Hmm, no — I think you still have to pass it, but the AMDP framework ensures the session variable CDS_CLIENT is set? 

OK here's what I actually remember from the ABAP docs (https://help.sap.com/doc/abapdocu... "AMDP - Client Handling"):

"AMDP methods are called using the CALL METHOD statement... The client handling of AMDP methods is performed as follows:
- By default, no implicit client handling is performed. The client must be handled explicitly in the procedure body using WHERE conditions, or the session variable CDS_CLIENT must be evaluated.
- Implicit client handling can be enabled by declaring a client parameter: The first input parameter of the AMDP method must be named clnt and typed with abap.clnt? ... When the method is called, the current client is passed implicitly..."

Hmm, I believe the actual rule is: If the AMDP method has an input parameter `clnt` typed as `abap.clnt` as its first parameter, then implicit client handling is active: the current client (sy-mandt) is passed automatically when the method is called without specifying the parameter? No wait — ABAP method calls require all non-optional parameters. So it can't be omitted...

Let me recall from actual SAP example code (e.g., CL_DEMO_AMDP_...):

From the ABAP documentation example:

```abap
CLASS cl_demo_amdp_client DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES flights_tab TYPE STANDARD TABLE OF demo_flshts WITH EMPTY KEY.
    CLASS-METHODS select_flights
      IMPORTING VALUE(clnt)      TYPE abap.clnt
                VALUE(carrid)     TYPE sflight-carrid
      EXPORTING VALUE(flights)    TYPE flights_tab.
ENDCLASS.

CLASS cl_demo_amdp_client IMPLEMENTATION.
  METHOD select_flights BY DATABASE PROCEDURE
                        FOR HDB LANGUAGE SQLSCRIPT
                        OPTIONS READ-ONLY
                        USING sflight.
    flights = SELECT * FROM sflight
              WHERE mandt = :clnt AND
                    carrid = :carrid
              ORDER BY carrid, connid, fldate;
  ENDMETHOD.
ENDCLASS.
```

And the call:

```abap
cl_demo_amdp_client=>select_flights(
  EXPORTING clnt    = sy-mandt
            carrid  = 'LH'
  IMPORTING flights = DATA(flights) ).
```

So in that example, the client is passed explicitly. But there's also implicit client handling: From ABAP docs: "If the AMDP method has a first input parameter named clnt of type abap.clnt, the current client is passed automatically to this parameter when the method is called and the parameter does not need to be filled." Hmm — actually I now recall: For AMDP methods, implicit client handling means: the parameter clnt is supplied automatically with sy-mandt when the method is called — you don't pass it. Wait, that doesn't sound right either because ABAP method calls...

Actually YES — I now remember clearly: For AMDP methods with implicit client handling, the `clnt` parameter is NOT passed by the caller. The AMDP framework fills it automatically with the current client. From the ABAP documentation:

"AMDP - Client Handling: ... For AMDP methods, implicit client handling is enabled by declaring a mandatory input parameter clnt as first input parameter of the method. ... When the method is called, the current client is passed to the parameter clnt automatically and it cannot be specified explicitly."

Hmm, is that right? Let me think about CDS table functions: there, the first parameter clnt is automatically filled when the table function is used in ABAP SQL. For AMDP methods called from ABAP, I believe the same mechanism applies: if the method has clnt as first parameter, the caller does NOT pass it; the AMDP runtime passes sy-mandt.

Actually, I found it in memory: ABAP Keyword Documentation, "AMDP - Client Handling":

"AMDP methods can be enabled for implicit client handling by declaring an input parameter clnt of type abap.clnt as first input parameter after the value parameters? ... In this case, when the method is called, the current client is passed to the parameter clnt automatically and the parameter cannot be filled explicitly. ... In the procedure body, the parameter clnt must be used in WHERE conditions for client-dependent data sources."

Hmm, I'm not 100% sure whether it's "cannot be filled explicitly" or "must be filled". Let me think about real-world examples... 

I recall CL_CDS_TESTER or standard SAP code... In many SAP standard AMDP classes, the method signature includes `IV_MANDT` or similar and callers pass sy-mandt explicitly. That suggests explicit client handling is common. But the implicit client handling feature exists: 

From ABAP docs (I'm now quite confident): "Client Handling in AMDP Methods: For AMDP methods, implicit client handling is switched on by declaring a mandatory input parameter clnt as first input parameter of the method. This parameter must be typed with abap.clnt or a data element whose... When the method is called, the current client is passed to this parameter automatically. It cannot be specified in the call."

Hmm wait, actually I think I might be mixing it up. Let me recall the exact doc text from ABAP 7.52 documentation:

"AMDP - Client Handling
- Client handling is not performed implicitly in AMDP methods. ...
- Implicit client handling can be switched on for AMDP methods by declaring a mandatory input parameter clnt as first input parameter of the method. The parameter must be typed with the type abap.clnt... When an AMDP method with implicit client handling is called, the current client is passed to the parameter clnt automatically. The parameter clnt cannot be specified in the method call. In the AMDP method, the parameter clnt must be used to restrict the access to client-dependent database tables."

Yes, I'm fairly confident this is correct: For AMDP methods with implicit client handling, the clnt parameter is automatically filled at call time and must NOT be passed by the caller. Hmm, but wait — is that true? Let me double check with a known example from the ABAP docs...

Actually, I recall the ABAP doc example for implicit client handling in AMDP:

```abap
CLASS cl_demo_amdp_client DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES flights_tab TYPE STANDARD TABLE OF demo_flshts WITH EMPTY KEY.
    CLASS-METHODS select_flights
      IMPORTING VALUE(clnt)   TYPE abap.clnt
                VALUE(carrid) TYPE sflight-carrid
      EXPORTING VALUE(flights) TYPE flights_tab.
ENDCLASS.
```

and the call:

```abap
cl_demo_amdp_client=>select_flights( EXPORTING carrid = 'AA' IMPORTING flights = DATA(flights) ).
```

Hmm — in this call, clnt is not passed. I believe this is indeed how it works: the clnt parameter is implicitly supplied with sy-mandt. Yes — I'm now fairly confident: For AMDP methods, if the first importing parameter is named `clnt` (typed abap.clnt), implicit client handling is active and the caller does not pass it. This matches the CDS table function pattern.

Hmm, but actually wait. Let me reconsider. I've seen AMDP code in production where the client is passed explicitly as IV_MANDT. Both patterns exist. The implicit client handling requires the parameter to be named exactly `clnt` and be the first parameter. If named differently, you pass it explicitly.

To be safe and pedagogically clear, I could use the implicit client handling pattern with `clnt` as first parameter and explain that it's automatically filled with sy-mandt — OR use an explicit parameter. Given the user asked for "für eine übergebene Verkaufsorganisation" (for a passed sales organization), the sales org is definitely an explicit parameter. For the client, I'll use the implicit client handling pattern and explain it, or pass it explicitly to be safe.

Hmm, let me be careful about correctness. Let me reconstruct from the ABAP Keyword Documentation (ABAP 7.5x), section "AMDP - Client Handling":

The documentation states (paraphrasing):

"AMDP methods: For AMDP methods, implicit client handling is enabled by declaring a mandatory input parameter clnt as first input parameter of the method. The parameter must be typed with abap.clnt or with a data element... When the AMDP method is called, the current client is passed automatically to the parameter clnt. The parameter clnt cannot be specified explicitly in the method call. In the procedure body, the parameter clnt must be used in the WHERE condition..."

Hmm, actually I want to double check "cannot be specified explicitly". I recall there being a subtlety: For AMDP methods, the clnt parameter CAN be passed explicitly too? No... For CDS table function access in ABAP SQL, the clnt parameter is implicitly filled and cannot be passed. For AMDP methods... 

I found in memory: ABAP doc "AMDP - Client Handling":

"By default, AMDP methods do not get implicit client handling. ... Implicit client handling can be enabled by declaring a mandatory input parameter clnt as first input parameter of the method. ... In this case, the current client is passed automatically to the parameter clnt when the method is called and the parameter cannot be specified explicitly."

Hmm OK. But actually, I have doubts. Let me think about the syntax check behavior: If you declare an AMDP method with first parameter clnt TYPE abap.clnt, and then call it passing clnt = sy-mandt, does the syntax check complain? I believe there might be a warning/error "Parameter CLNT is filled implicitly" or similar. Actually I recall the syntax check message: "The parameter CLNT is supplied automatically. It cannot be filled." Something like that.

Alternatively, I recall that for AMDP methods, the implicit client handling parameter must be declared and the caller CAN pass it or not? Hmm.

Let me think about another source: The AMDP book by Löffler/... or the SAP Community blogs. In many blog examples:

```abap
CLASS-METHODS get_top_materials
  IMPORTING VALUE(iv_vkorg) TYPE vkorg
  EXPORTING VALUE(et_data)  TYPE tt_data.
```

with explicit client handling inside via session variable or passed mandt.

To avoid stating something incorrect, I could do explicit client handling: pass `iv_mandt` (or use the session variable $session.user? no, client is CDS_CLIENT session variable). In SQLScript, you can access the client via `SESSION_CONTEXT('CDS_CLIENT')`? Actually the session variable for client in HANA is `$session.user`... no. In HANA SQLScript, ABAP session variables are accessible via SESSION_CONTEXT('CDS_CLIENT') — yes, since HANA 2.0 SPS02 / ABAP 7.52, the ABAP session variable CDS_CLIENT can be read via SESSION_CONTEXT('CDS_CLIENT'). But to keep it simple and compatible, explicit client parameter is safest.

Actually, let me settle this. I'm going to check my memory of the ABAP documentation more carefully. The relevant doc section is "AMDP - Client Handling" in the ABAP Keyword Documentation. I remember the structure:

"Client handling is not performed implicitly in AMDP methods. This means that the client handling must be performed explicitly in the procedure body of AMDP methods or the session variable CDS_CLIENT must be evaluated.

- Implicit client handling can be enabled for AMDP methods by declaring a mandatory input parameter clnt as first input parameter of the method. The parameter must be typed with abap.clnt or a data element with... hmm.

- When an AMDP method with implicit client handling is called, the current client is passed automatically to the parameter clnt and the parameter cannot be specified explicitly in the call.

- In the procedure body of an AMDP method with implicit client handling, the parameter clnt must be used in the WHERE conditions..."

Hmm, wait. Actually now I remember there's a distinction: For AMDP methods, I believe the rule is that the clnt parameter IS passed explicitly by the caller — no wait.

OK let me try to recall an actual SAP example with implicit client handling in AMDP. The ABAP docs example "AMDP - Client Handling" shows:

```abap
CLASS cl_demo_amdp_client_handling DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES: t_scarr TYPE STANDARD TABLE OF scarr WITH EMPTY KEY.
    CLASS-METHODS get_carriers
      IMPORTING VALUE(clnt)    TYPE abap.clnt
      EXPORTING VALUE(carriers) TYPE t_scarr.
ENDCLASS.
```

Hmm, and then the call... I genuinely can't recall whether the example passes clnt = sy-mandt.

Alternative approach: I'll write the code with explicit client parameter (e.g., `iv_mandt TYPE sy-mandt` or using implicit `clnt`) and describe both options in the explanation, noting that with a parameter named `clnt` as first parameter, implicit client handling kicks in (current client passed automatically). Actually, to be safe, I'll pass the client explicitly in the call example AND mention the implicit option. Hmm, but if I declare the parameter as `clnt` and then also pass it explicitly in the example call, and implicit client handling forbids passing it, my example would be wrong.

Safest: Use a parameter NOT named `clnt` (e.g., `iv_mandt`), pass it explicitly in the call. Then add a note: "Alternativ kann man den Parameter `clnt` als ersten Importing-Parameter nennen — dann übernimmt die AMDP-Laufzeit automatisch die aktuelle Mandantennummer (implizite Mandantenbehandlung)." That's accurate regardless of the exact call semantics.

Hmm, but actually, let me try once more to pin down the implicit client handling rule for AMDP methods, because it's a well-known detail:

From ABAP Keyword Documentation (7.51+), "AMDP - Client Handling":

"AMDP methods: For AMDP methods, implicit client handling is switched on by declaring a mandatory input parameter clnt as first input parameter of the method. The parameter must be typed with the type abap.clnt... When the method is called, the current client is passed to the parameter clnt automatically. It cannot be specified in the call. ... This means that an AMDP method with implicit client handling is called without the parameter clnt."

I'm now about 85% confident this is right: the clnt parameter is auto-filled and must not be passed. Yes — I recall the syntax check error when trying to pass it: "Parameter CLNT cannot be filled explicitly" or the docs saying "the parameter clnt is not specified in the method call". Also I recall Horst Keller's examples in the ABAP doc where the call is `cl_demo_amdp=>select_flights( EXPORTING carrid = ... IMPORTING ... )` without clnt.

OK so here's my plan: I'll use the implicit client handling pattern (parameter `clnt` as first importing parameter, type abap.clnt), and in the call example, NOT pass clnt, with a comment explaining it's filled automatically with sy-mandt. And I'll add a note explaining this behavior explicitly, plus mention the alternative (explicit client parameter with a different name) for older releases or clarity.

Hmm, wait. Actually, let me reconsider once more. I want to avoid an error here. Let me search memory for "clnt" AMDP...

From the ABAP documentation (help.sap.com ABAP 7.52), section "AMDP - Client Handling":

"Client Handling in AMDP Methods

For AMDP methods, implicit client handling is switched on by declaring a mandatory input parameter clnt as first input parameter of the method. This parameter must be typed with abap.clnt or with a data element whose... 

When an AMDP method with implicit client handling is called, the current client is passed automatically to the parameter clnt. The parameter clnt cannot be specified explicitly in the method call.

In the procedure body of an AMDP method with implicit client handling, the parameter clnt must be evaluated in the WHERE condition..."

Hmm, "must be evaluated" — actually I think the doc says the client handling must be implemented in the body using the parameter, and the AMDP framework checks? No, the framework doesn't check the body. The doc says: "the parameter clnt must be used in the WHERE conditions of the client-dependent data sources" — as a rule/recommendation, not enforced.

Hmm, hold on. Actually I now recall there IS a check: AMDP methods with implicit client handling... no, I don't think the runtime verifies the body. The developer is responsible.

OK. Also important: implicit client handling for AMDP methods requires... the class must not be... hmm, there's a restriction: AMDP methods with implicit client handling cannot be... I don't remember restrictions. Fine.

Alternatively — you know what, there's another consideration. Many real-world AMDP examples (including SAP standard) pass the client explicitly as a normal parameter (e.g., `iv_mandt`). This is unambiguous and works in all releases. Given the audience (likely learning), I'll go with the implicit client handling pattern because it's the modern best practice, and clearly explain it. Actually hmm, let me weigh: If I'm wrong about the auto-fill behavior, my example call would be broken. If I use explicit passing with a non-`clnt` name, it's definitely correct. The implicit pattern is a nice-to-have.

Decision: I'll use the implicit client handling pattern BUT carefully: declare `VALUE(clnt) TYPE abap.clnt` as first parameter, and in the call, don't pass it, with a comment. And add a note box explaining: "Der Parameter clnt wird bei der Deklaration als erster Importing-Parameter automatisch mit der aktuellen Mandantennummer (sy-mandt) versorgt und darf im Aufruf nicht explizit übergeben werden (implizite Mandantenbehandlung der AMDP-Laufzeit). Alternativ: eigener Name → explizite Übergabe."

Hmm, actually, hmm. Let me reconsider AGAIN because correctness matters a lot here. Let me try to recall the exact ABAP doc example for AMDP client handling. I believe there are two examples in the docs: one with implicit client handling and one without.

Example from ABAP docs "AMDP - Client Handling" (I'm reconstructing):

```abap
CLASS cl_demo_amdp_client DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES flights_tab TYPE STANDARD TABLE OF demo_flshts WITH EMPTY KEY.
    CLASS-METHODS select_flights
      IMPORTING VALUE(clnt)   TYPE abap.clnt
                VALUE(carrid) TYPE sflight-carrid
      EXPORTING VALUE(flights) TYPE flights_tab.
ENDCLASS.

CLASS cl_demo_amdp_client IMPLEMENTATION.
  METHOD select_flights BY DATABASE PROCEDURE
                        FOR HDB LANGUAGE SQLSCRIPT
                        OPTIONS READ-ONLY
                        USING sflight.
    flights = SELECT *
              FROM sflight
              WHERE mandt = :clnt
                AND carrid = :carrid
              ORDER BY carrid, connid, fldate;
  ENDMETHOD.
ENDCLASS.
```

And the call in the demo report:

```abap
cl_demo_amdp_client=>select_flights(
  EXPORTING carrid = 'LH'
  IMPORTING flights = DATA(flights) ).
```

Hmm, I genuinely believe I've seen this call without clnt. Yes. OK, going with implicit client handling.

Wait, one more consideration: is it "first input parameter" or can it be anywhere? The doc says: "declaring a mandatory input parameter clnt as first input parameter". Hmm, actually I recall it must be the FIRST importing parameter. Yes.

Also the type: `abap.clnt` — the ABAP type abap.clnt exists (like abap.c, length 3). Yes, abap.clnt is a valid predefined ABAP type. Alternatively sy-mandt. The doc example uses... I think `abap.clnt`. I'll use `abap.clnt`.

Now, the data model: VBAP (sales document item) and VBAK (sales document header). Fields:
- VBAK: MANDT, VBELN (sales document), VKORG (sales organization), ERDAT, AUDAT (document date), NETWR (header net value), WAERK, VKORG, VTWEG, SPART...
- VBAP: MANDT, VBELN, POSNR, MATNR (material), ARKTX, KWMENG (quantity), VRKME (sales unit), NETWR (item net value), WAERK (currency), ...

Revenue per material: sum of VBAP-NETWR (net value of the order item) for orders in the given VKORG. Top 10 by revenue.

Join: VBAP JOIN VBAK ON VBAP~VBELN = VBAK~VBELN (and mandt). Filter VBAK~VKORG = :iv_vkorg. Group by VBAP~MATNR. Sum(VBAP~NETWR) as UMSATZ. Order by sum desc, take top 10 via LIMIT 10.

Optionally filter by document category VBAK~VBTYP = 'C' (orders) to exclude quotations/contracts? Could mention. Keep it simple but maybe add a comment. Actually, for a realistic example, one might restrict to AUART or VBTYP = 'C'. I'll mention it as a comment/optional.

Currency: NETWR is CURR, WAERK currency key. Summing across currencies is technically questionable (should group by currency or convert). For a demo, sum NETWR and note the caveat. Good to mention briefly — shows expertise. I'll add a short note.

Now the AMDP specifics:

1. Class definition:

```abap
CLASS zcl_vbap_top_materials DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.

    TYPES: BEGIN OF ty_top_material,
             matnr   TYPE matnr,
             umsatz  TYPE vbap-netwr,   " oder p DECIMALS 2
             waerk   TYPE waers,
             menge   TYPE vbap-kwmeng,
           END OF ty_top_material,
           tt_top_material TYPE STANDARD TABLE OF ty_top_material WITH EMPTY KEY.
```

Wait — AMDP parameter types: table types must be DDIC table types (defined in SE11) whose row type is a DDIC structure (flat, character-like? no — any flat structure?) — the rule: "The row type of the table type must be a DDIC structure whose components are elementary..." Actually the rule for AMDP: tabular parameters must be typed with DDIC table types; the row type must be a flat DDIC structure (no strings? strings are allowed? deep types are NOT allowed — no strings, no tables, no references). Elementary types are allowed for scalar parameters.

Hmm, but since ABAP 7.53? there's an option: "In AMDP methods, the tabular parameters can also be typed with table types of the class pool if..." I don't think so. Let me recall: The ABAP doc says: "The non-elementary input and output parameters of AMDP methods must be typed with table types from ABAP Dictionary." And: "Since ABAP 7.53? ... types defined in the class..." Hmm.

Actually, I recall: For AMDP, tabular parameters must use DDIC table types. BUT — there's an exception added later: "In AMDP methods, tabular parameters can be typed with table types defined in the class pool if their row type is a DDIC structure or a DDIC data element"? Hmm. I don't think that's allowed. Let me think...

ABAP doc "AMDP - Parameter": "The parameter types: Elementary ABAP types and table types from ABAP Dictionary can be used. The row type of a table type must be a flat structure from ABAP Dictionary or an elementary type." Also: "Structured parameters are not allowed" (structures as scalar parameters are not allowed? Actually structured parameters ARE not allowed for AMDP — only elementary and table types). Yes: AMDP method parameters can only be elementary or tabular (DDIC table types). No structures, no strings? Strings are allowed as elementary? Hmm — strings are allowed I think (they map to NVARCHAR). Deep types (table in table, references) not allowed.

Hmm wait, actually strings: "The following types are allowed: elementary types (including string and rawstring?)"... I believe string is allowed. Not critical here.

For the demo, to avoid requiring the reader to create DDIC objects, many blog examples define the table type in the class... but that's not allowed for AMDP! Common workaround in examples: use an existing DDIC table type or define one. Hmm, but many SAP doc examples use e.g. `TYPES flights_tab TYPE STANDARD TABLE OF demo_flshts WITH EMPTY KEY.` where demo_flshts is a DDIC structure... but is `flights_tab` defined in the class? Let me recall the actual doc example:

From ABAP doc example (CL_DEMO_AMDP_...):

```abap
CLASS cl_demo_amdp_select DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES: t_sflight TYPE STANDARD TABLE OF sflight WITH EMPTY KEY.
    CLASS-METHODS select_sflight
      IMPORTING VALUE(clnt)   TYPE abap.clnt
      EXPORTING VALUE(flights) TYPE t_sflight.
```

Hmm — is a local type `t_sflight` allowed as AMDP parameter type? The doc says table types from ABAP Dictionary... but I recall that local table types whose row type is a DDIC table/structure ARE allowed since some release. Let me think.

ABAP Keyword Documentation, "AMDP - Parameter": 

"Input and output parameters of AMDP methods must be passed by value. ... The following parameter types are possible:
- Elementary types
- Table types from ABAP Dictionary
..."

Hmm, but I also recall: "Since Release 7.50, the row type of the table type can also be a structure defined in the class..."? No...

Actually — I now recall more specifically: There was a change: "In AMDP methods, tabular parameters can be typed with table types that are defined in the same class (or interface) if the row type is a DDIC structure." Hmm... I really am not sure.

Let me think about what I know from practice: In SAP S/4HANA standard code, AMDP methods often use DDIC table types. In blog posts, people often write:

```abap
TYPES: tt_result TYPE STANDARD TABLE OF ty_result WITH DEFAULT KEY.
```

and use it as AMDP parameter — and I believe this actually works in newer releases? Hmm. There's a known restriction historically: "The type of the parameters must be defined in ABAP Dictionary" — this was relaxed at some point. Let me recall the ABAP doc for 7.52:

"AMDP - PARAMETERS: ... The typing of the parameters must follow the rules:
- Elementary types are allowed.
- For tabular parameters, table types from ABAP Dictionary must be used. The row type must be a flat DDIC structure or elementary.
..."

Hmm, and then: "As of ABAP Release 7.53, table types defined in class pools and interface pools can be used for tabular AMDP parameters, if their row type is..." — I think something like this was introduced. Actually yes! I recall now: ABAP 7.53 (or 7.52?) allowed AMDP parameters to be typed with table types declared in the class pool, as long as the row type is a DDIC structure (or CDS entity?). Let me recall the exact wording: 

From ABAP 7.53 release notes: "AMDP: Table types in class pools can be used for the typing of AMDP parameters" — I believe this is real. The ABAP doc "AMDP - Parameter" says: "Tabular parameters must be typed with table types from ABAP Dictionary or with table types defined in the class pool or interface pool of the AMDP class (as of Release 7.53?). The row type must be a flat structure from ABAP Dictionary or elementary."

Hmm, I think the actual rule (from current ABAP docs): "The tabular parameters of AMDP methods and function implementations must be typed with table types from ABAP Dictionary whose row type is a flat structure from ABAP Dictionary or elementary. As an alternative, table types defined in the class pool of the AMDP class can be used if their row type is a DDIC structure." Something like that. I believe local table types with DDIC structure row type are OK in modern releases (7.5x).

To be safe for a broad audience: I could define the result structure as a DDIC structure... but that requires SE11 work. For a code example in an answer, using a local type is more practical. I'll use a local table type and add a note: "Je nach Release müssen tabellarische AMDP-Parameter als DDIC-Tabellentypen angelegt sein (ältere Releases); ab 7.5x sind auch lokale Tabellentypen mit DDIC-Struktur als Zeilentyp erlaubt." Hmm, but if the row type is a local structure (BEGIN OF ... END OF), is that OK? If local table types are allowed only with DDIC structure row type, then a fully local structure wouldn't work.

Hmm. Let me think about what's definitely safe: Use existing DDIC structures? There's no perfect DDIC structure for "matnr + netwr + waerk". 

Option: Use `TYPE STANDARD TABLE OF vbap WITH EMPTY KEY`? Ugly.

Option: Define the row type as local structure and the table type locally — risk of not compiling on older releases but works on modern ones? I need to decide.

Let me try to recall the current ABAP documentation text precisely (ABAP 7.5x / cloud):

"AMDP - Parameter" (from ABAP Keyword Documentation):

"Rules for the parameter interface of AMDP methods:
- All parameters must be passed by value.
- The parameters can only be typed with elementary types or with table types. ...
- Tabular parameters must be typed with table types from ABAP Dictionary. The row type of these table types can be a flat structure from ABAP Dictionary or elementary. ...
- As of ABAP Release 7.53, tabular parameters can also be typed with table types from the class pool, if the row type is a DDIC structure or elementary? ..."

Hmm, I keep going back and forth. Let me approach from a different angle: I remember the SAP Community blog "AMDP – A Practical Guide" and similar. In many of those, they define:

```abap
TYPES: BEGIN OF ty_kna1,
         kunnr TYPE kna1-kunnr,
         name1 TYPE kna1-name1,
       END OF ty_kna1,
       tt_kna1 TYPE STANDARD TABLE OF ty_kna1 WITH DEFAULT KEY.
```

and use tt_kna1 as AMDP exporting parameter — and commenters sometimes note it doesn't work... Actually, I recall that this DOES produce a syntax error in older systems: "The type of the parameter must be a table type from ABAP Dictionary" or similar. And I recall that in newer releases (7.52+?), local types work. Hmm.

Actually — I now have a clearer memory: The ABAP doc says:

"AMDP methods: The typing of the parameters must observe the following rules:
- Elementary ABAP types can be used.
- Table types from ABAP Dictionary must be used for tabular parameters. The row type of the table type must be a flat structure from ABAP Dictionary or an elementary type.
- As from Release 7.53, table types defined in the class pool or interface pool of the AMDP class can also be used. The row type must be a flat structure from ABAP Dictionary or elementary."

Hmm, if the row type must be DDIC structure even for class-local table types, then a fully local BEGIN OF structure wouldn't be allowed. But I've definitely seen examples with fully local structures in AMDP parameters in recent SAP docs... 

Let me think about CL_DEMO_AMDP examples in the ABAP doc. Example "AMDP - Client Handling": uses `TYPES flights_tab TYPE STANDARD TABLE OF demo_flshts WITH EMPTY KEY.` — demo_flshts is a DDIC structure (created for demos). So the row type is DDIC, table type is local (class pool). That suggests: local table type + DDIC structure row type = OK (in that release). 

Another doc example: "CL_DEMO_AMDP_INSERT ..." uses DDIC table types.

And I recall the doc sentence: "The row type of the table type must be a flat structure from the ABAP Dictionary or elementary." — meaning the row type must be DDIC structure or elementary; the table type itself can be DDIC or (later) class-local.

So for my example: define a local table type whose row type is a DDIC structure. But which DDIC structure has matnr + umsatz? None standard. Options:
1. Tell the reader to create a DDIC structure (e.g., ZS_TOP_MATERIAL) and a table type (or local table type over it).
2. Use a fully local structure and note the release dependency.

For an educational answer, I think the cleanest is: define the DDIC structure and table type as a prerequisite, but show it compactly. OR use fully local types and add a note that on older releases a DDIC table type is required.

Hmm, actually, let me reconsider: maybe I'm overcomplicating. Let me check: is a fully local structure as row type allowed today? I recall the ABAP doc (current, 7.57/7.58):

"AMDP - Parameter: ... The following rules apply to the typing of the parameters of AMDP methods:
- All parameters must be passed by value.
- Elementary types can be used for the typing.
- Tabular parameters must be typed with table types. The table types can be defined in ABAP Dictionary or in the class pool of the AMDP class. The row type of the table types must be a flat structure from ABAP Dictionary or elementary."

Hmm — "flat structure from ABAP Dictionary". So the row type must be DDIC. A local BEGIN OF structure is NOT allowed as row type. I'm fairly confident about this restriction for AMDP methods (it's a classic gotcha). 

Wait, but is that still true in the ABAP Cloud / 7.5x? I believe yes — AMDP parameter row types must be DDIC structures (or elementary). Hmm, but actually, I have a vague memory that this was relaxed to allow CDS entities / structured types from the class... Let me not gamble.

Safe approach for the answer: 
- Define the result row as a DDIC structure? That requires SE11. In an answer, I can say: "Struktur ZS_TOP_MATERIAL (MATNR, UMSATZ, WAERK, MENGE) und Tabellentyp TT_TOP_MATERIAL im DDIC anlegen" and then use the DDIC table type in the class. That's the classically correct approach and compiles everywhere.

Alternatively, use existing DDIC structures cleverly? No good fit.

Hmm, but many readers just want copy-paste code. A hybrid: show the class with a local table type over a DDIC structure name, and clearly state the DDIC prerequisites. I'll do that: 

```abap
" DDIC-Voraussetzungen:
" Struktur  ZS_VBAP_TOP_MAT: matnr (MATNR), umsatz (NETWR bzw. P DEC 2), waerk (WAERS), menge (KWMENG)
" Tabellentyp ZTT_VBAP_TOP_MAT mit Zeilentyp ZS_VBAP_TOP_MAT
```

and in the class: `TYPES tt_top_material TYPE ztt_vbap_top_mat.` or directly use ztt_vbap_top_mat as parameter type.

Hmm, wait — but actually, let me reconsider using fully local types. I want to double-check the restriction once more because it determines the answer's code. 

Known AMDP parameter rules (from ABAP Keyword Documentation, "AMDP - Parameter"):

"Input and output parameters of AMDP methods and AMDP function implementations must be passed by value. ... The following types can be used:
- Elementary types (including enum? no)
- Table types from ABAP Dictionary
...

The row type of tabular parameters must be a flat structure from ABAP Dictionary or elementary. Deep types (strings? ...)"

Hmm, strings: I believe `string` is allowed as elementary type for AMDP parameters? There's a note: "Strings are allowed..." Actually for table row types, strings in DDIC structures are allowed (SSTRING/CHAR?). Whatever — not needed here.

And regarding class-local table types: I'm now recalling the ABAP doc more concretely. Current doc (7.5x) "AMDP - Parameter":

"Tabular input and output parameters must be typed with table types from ABAP Dictionary whose row type is a flat structure from ABAP Dictionary or elementary. ... As of Release 7.53, table types from the class pool can be used as well, if their row type is a flat structure from ABAP Dictionary or elementary."

Hmm, I keep producing this memory, which suggests it's real. Actually wait — I think the actual relaxation was different: I recall "As of ABAP 7.53, the row type of tabular AMDP parameters can also be a structured type defined in the class pool"? Hmm no...

Let me think about what I've seen in real S/4 code: e.g., CL_MM_PUR_PR_IR_MANAGE or similar AMDP classes... They typically use DDIC table types. In the ABAP docs for AMDP function implementations (CDS table function access), the example:

```abap
METHOD get_values_by_client BY DATABASE FUNCTION...
```

Hmm.

OK, decision: To maximize correctness across releases, I'll use a DDIC table type for the tabular parameter and clearly document the DDIC prerequisite. I'll ALSO mention that depending on release, local types may be possible. Actually — hmm, one more idea: I can make the example self-contained by using a generic-ish approach? No, AMDP parameters can't be generic.

Alternatively, I can sidestep: use `EXPORTING VALUE(et_top) TYPE ztt_vbap_top_material` and provide the DDIC definitions in text form (fields + types). That's fine and professional.

Hmm, wait. Actually, let me reconsider once more. I have a strong feeling that in current ABAP releases, this works:

```abap
CLASS zcl_... DEFINITION.
  PUBLIC SECTION.
    TYPES: BEGIN OF ty_result,
             matnr TYPE matnr,
             umsatz TYPE p LENGTH 15 DECIMALS 2,
             waerk TYPE waers,
           END OF ty_result,
           tt_result TYPE STANDARD TABLE OF ty_result WITH EMPTY KEY.
    ...
    METHODS get_top_materials
      IMPORTING VALUE(iv_vkorg) TYPE vkorg
      EXPORTING VALUE(et_top)   TYPE tt_result
      ...
```

Does the syntax check accept tt_result? Based on the doc rule "row type must be flat DDIC structure", NO — ty_result is a local structure. Unless the rule changed. 

Hmm, hold on, let me recall the ABAP release notes for 7.52: "AMDP: ... The restriction that the row type of tabular parameters must be a DDIC structure was lifted? ..." 

I recall there IS something in the 7.52 release notes about AMDP: "AMDP methods can now also be declared in interfaces"? No... 7.52 release notes AMDP: "AMDP function implementations can now be used as data source in ABAP SQL" (that was 7.50 for functions in general?). Hmm.

Let me try yet another angle: The ABAP doc "AMDP - Parameter" as I best remember it verbatim:

"Parameter typing:
- All parameters must be passed by value.
- The following parameter types are allowed:
  - Elementary ABAP types
  - Table types from ABAP Dictionary
- The row type of the table types must be a flat structure from ABAP Dictionary or an elementary type.
- Structured types and reference types are not allowed.
- As of Release 7.53, table types from the class pool of the AMDP class can be used in addition to table types from ABAP Dictionary."

Hmm, and does 7.53 also allow local structures as row type? I have a feeling the answer is: the row type must STILL be DDIC structure or elementary. Because the AMDP framework needs to map the type to HANA types, and it resolves DDIC structures. A local structure could in principle be resolved too... 

You know, I found it — I now clearly remember the current ABAP Keyword Documentation text for "AMDP - Parameter" (checked mentally against help.sap.com ABAP 7.5x):

"Typing of the parameters:
- All parameters must be passed by value.
- The following types can be used for typing:
  - Elementary types
  - Table types whose row type is elementary or a flat structure from ABAP Dictionary
- The table types themselves can be defined in ABAP Dictionary or in the class pool of the AMDP class (as of Release 7.53)."

Hmm, if this is the text, then the row type restriction is "elementary or flat DDIC structure" — local structures still not allowed. 

Ugh. OK, pragmatic solution: I'll define the row type as a DDIC structure in the explanation (brief SE11 instructions) and use a class-local table type over it (works 7.53+) or directly the DDIC table type (works everywhere). To keep it simple: use the DDIC table type directly as parameter type. And I'll add a note: "Ab Release 7.53 genügt auch ein im Class-Pool definierter Tabellentyp; der Zeilentyp muss weiterhin eine flache DDIC-Struktur oder elementar sein." — Hmm, but if I'm not 100% sure about the 7.53 part, maybe I should soften: "Je nach Release werden lokale Tabellentypen akzeptiert; klassisch sicher ist der DDIC-Tabellentyp." 

Hmm, hmm. Actually, let me just go with fully local types BUT flag it? No — if it doesn't compile, that's bad.

Let me make a final decision based on risk: 
- Using DDIC table type: definitely correct (all AMDP-capable releases). Requires reader to create 2 DDIC objects (structure + table type). Slight friction but professional and correct.
- Using local types: might not compile on some releases; I'm unsure.

Go with DDIC table type. I'll present the DDIC prerequisites compactly (maybe as a small table of fields). Also mention: "Falls euer Release lokale Typen erlaubt (ab 7.53), könnt ihr euch die DDIC-Objekte sparen" — hmm, I'd rather phrase: "In neueren Releases (ab 7.53) sind auch im Class-Pool definierte Tabellentypen zulässig; der Zeilentyp muss dann weiterhin eine flache DDIC-Struktur bzw. elementar sein." I'm reasonably confident in this statement. Actually, let me double check by recalling the 7.53 release notes... ABAP 7.53 (AS ABAP 7.53, S/4 1809?): AMDP news... I recall "AMDP: Table types in class pools" — hmm, I genuinely can't verify. 

Alternative: skip the release claim entirely and just say: "Klassisch (und in jedem Release sicher): DDIC-Struktur + DDIC-Tabellentyp. Neuere Releases erlauben auch lokale Tabellentypen — prüft das ggf. mit der Syntaxprüfung." That's honest and safe.

Hmm, OK wait — actually, I want to reconsider the whole thing once more. I've seen MANY recent SAP tutorials (e.g., ABAP Development Tutorials for 7.5x) with AMDP examples like:

```abap
CLASS cl_demo_amdp DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES: t_flights TYPE STANDARD TABLE OF sflight WITH EMPTY KEY.
    CLASS-METHODS get_flights
      IMPORTING VALUE(clnt) TYPE abap.clnt
      EXPORTING VALUE(flights) TYPE t_flights.
```

Here the row type is the DDIC table sflight itself (DDIC structure) and the table type is local. This compiles (I'm confident this pattern appears in SAP's own doc examples). So: local table type + DDIC structure row type = OK at least in 7.5x.

For my example, the row type needs to be a custom structure (matnr, umsatz, waerk, menge). If I must use a DDIC structure, the reader creates ZS_... in SE11. Fine. I'll do:

DDIC prerequisites:
- Struktur ZSD_TOP_MATERIAL: MATNR (DATS? no, MATNR data element), UMSATZ (type NETWR or P 15,2), WAERK (WAERS), MENGE (KWMENG) — hmm, or simpler: MATNR, UMSATZ, WAEHRUNG? Keep names: MATNR, UMSATZ, WAERS, MENGE.
- Tabellentyp ZSD_TT_TOP_MATERIAL with line type ZSD_TOP_MATERIAL.

Then class:

```abap
CLASS zcl_sd_top_materials DEFINITION PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    CLASS-METHODS get_top_materials
      IMPORTING VALUE(iv_vkorg) TYPE vkorg
                VALUE(iv_top)   TYPE i DEFAULT 10   " hmm, LIMIT with parameter?
      EXPORTING VALUE(et_top)   TYPE zsd_tt_top_material.
```

Wait — can I parameterize the LIMIT? In SQLScript: `LIMIT :iv_top` — yes, LIMIT accepts a variable: `LIMIT :iv_top`. That works in HANA SQLScript. Nice touch. But maybe keep it simple with fixed 10? The user said Top-10. I could add optional parameter iv_top TYPE i DEFAULT 10 and use LIMIT :iv_top. Hmm, DEFAULT values for AMDP parameters: allowed? AMDP parameters must be passed by value; optional parameters with DEFAULT — I believe optional parameters are allowed in AMDP methods (they're just ABAP methods). But careful: for AMDP, ALL parameters... hmm, are optional parameters allowed? I think yes, IMPORTING parameters can be optional. But there might be a restriction that AMDP parameters must be mandatory? Let me think... I don't recall a restriction against optional parameters. Actually, hmm, for AMDP function implementations used in CDS table functions, parameters must be... different story. For AMDP methods, I believe optional parameters are fine. But to be safe, maybe make it mandatory without default, or just hardcode 10. 

Simplest robust: hardcode TOP 10 via LIMIT 10, and mention that you could parameterize with LIMIT :iv_top. Actually, let me include the parameter but as mandatory `VALUE(iv_top) TYPE i` — hmm, the user asked specifically for Top-10; adding iv_top is a nice generalization but adds noise. I'll hardcode LIMIT 10 and add a one-line comment "LIMIT :iv_top geht auch, wenn ihr die Anzahl als Parameter übergebt". Good.

Now the SQLScript implementation:

```abap
METHOD get_top_materials BY DATABASE PROCEDURE
                         FOR HDB LANGUAGE SQLSCRIPT
                         OPTIONS READ-ONLY
                         USING vbak vbap.

  et_top = SELECT TOP 10
             vbap.matnr                AS matnr,
             SUM( vbap.netwr )         AS umsatz,
             -- Währung: hier vereinfacht; NETWR ist curcurrency-bezogen
             vbap.waerk                AS waerk,   -- hmm, waerk is per item; in GROUP BY it's fine if same currency
             SUM( vbap.kwmeng )        AS menge
           FROM vbap
           INNER JOIN vbak
             ON vbak.mandt = vbap.mandt
            AND vbak.vbeln = vbap.vbeln
           WHERE vbap.mandt = :clnt
             AND vbak.vkorg = :iv_vkorg
           GROUP BY vbap.matnr, vbap.waerk
           ORDER BY umsatz DESC   -- hmm, can ORDER BY use alias in SQLScript? 
           LIMIT 10;

ENDMETHOD.
```

Details to check:

1. `SELECT TOP 10` vs `LIMIT 10`: Both work in HANA. In SQLScript assignments, `SELECT TOP n ... LIMIT n` — both fine. I'll use LIMIT 10 (or TOP 10). Note: In HANA, ORDER BY ... LIMIT works in subqueries/assignments. Fine.

2. ORDER BY alias: In standard SQL, ORDER BY can reference select list aliases. In HANA, yes, ORDER BY alias is allowed. But careful: ORDER BY umsatz DESC where umsatz is alias of aggregate — allowed in HANA. Yes.

3. Client handling: `WHERE vbap.mandt = :clnt` — with implicit client handling, the clnt parameter must be used. Also join condition includes mandt equality (redundant given both filtered? vbap.mandt = :clnt and vbak.mandt = :clnt — better to filter both explicitly). I'll write `WHERE vbap.mandt = :clnt AND vbak.mandt = :clnt` or join on mandt + where on one. Cleaner: join ON vbak.mandt = vbap.mandt AND vbak.vbeln = vbap.vbeln, WHERE vbap.mandt = :clnt AND vbak.vkorg = :iv_vkorg. Since both mandts equal via join and vbap.mandt = :clnt, vbak.mandt = :clnt follows. Fine.

4. AMDP and DDIC table names: In AMDP, you reference DDIC tables by their name (uppercase). VBAK/VBAP exist as DDIC tables → accessible. Good. Note: For AMDP, the tables used must be listed in USING. Also, AMDP requires the DB objects to exist in the HANA DB (they do, as ABAP tables are replicated/created in HANA).

5. OPTIONS READ-ONLY: Since the method only reads, declare READ-ONLY. Good practice; also required if called during... it's a good practice. Note: READ-ONLY methods can only read; they can't call non-read-only procedures etc.

6. USING vbak vbap — correct syntax: `USING vbak vbap.`

7. The method implementation: `METHOD get_top_materials BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT OPTIONS READ-ONLY USING vbak vbap.` — correct order: BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT [OPTIONS READ-ONLY] [USING ...]. Yes.

8. Parameter passing: VALUE(...) for all AMDP parameters — mandatory. Yes: "All parameters of AMDP methods must be passed by value."

9. EXPORTING with VALUE: `EXPORTING VALUE(et_top) TYPE ...` — yes.

10. In SQLScript, the output table parameter et_top is assigned directly: `et_top = SELECT ...`. Correct.

11. Currency caveat: Summing NETWR across different WAERK is wrong if multiple currencies. Options: group by matnr + waerk (then "top 10" is per material+currency combo), or convert to a target currency (requires conversion — complex in SQLScript without proper function; there's CONVERT_CURRENCY function? HANA has a CONVERT_CURRENCY() function? There's the HANA function `CONVERT_CURRENCY` — yes, HANA has CONVERT_CURRENCY since SPS? It exists in HANA SQL: CONVERT_CURRENCY(...). Hmm, it exists but configuration-dependent (currency tables). For the demo, I'll group by MATNR and WAERK and note that if everything is in one currency (typical per sales org? not necessarily), you can drop WAERK. Or simpler: include waerk in GROUP BY and note the caveat. Alternatively use WAERS from... VBAP has WAERK (currency of the document item? VBAP-WAERK exists? Let me check: VBAP has field WAERK (currency) — yes, VBAP-WAERK exists (currency of sales document item? Actually VBAK has WAERK (document currency); VBAP also has WAERK). Hmm: VBAP fields: NETWR (net value), WAERK (SD document currency) — yes, VBAP-WAERK exists. Good.

Alternatively, to keep it clean: GROUP BY matnr only, and SUM(netwr), and mention the currency caveat in a note. But then selecting waerk requires an aggregate (MAX(waerk) or ANY_VALUE?). In HANA, selecting a non-aggregated column not in GROUP BY is an error. So either group by both, or use MAX(waerk). 

Cleanest pedagogically: GROUP BY vbap.matnr, vbap.waerk — and note: "Wenn ihr sicher seid, dass pro VKORG nur eine Währung läuft, könnt ihr WAERK aus der Gruppierung streichen; sonst ist die Gruppierung nach Material+Währung das korrekte Vorgehen (oder Währungsumrechnung)." Hmm, but then "Top 10 Materialien" could return the same material twice with different currencies. Acceptable with the note. Alternatively drop waerk from output and group by matnr only, with note about currency. Hmm.

I think I'll do: GROUP BY matnr, waerk; output includes waerk; note explains. Actually — for a cleaner "Top 10 Materialien" semantics, maybe better: assume single currency per sales org is NOT guaranteed, so the honest approach is group by material + currency. I'll keep it and explain.

Hmm, alternatively I could sum in document currency... no. Keep it.

Also: should I filter VBAK-VBTYP = 'C' (only orders, not quotations)? Real revenue would come from billing docs (VBRK/VBRP), but the user explicitly asked VBAP/VBAK. I'll add an optional comment line: `-- optional: AND vbak.vbtyp = 'C'  " nur Aufträge` — good touch showing domain knowledge. Note: field name is VBTYP in VBAK. Yes, VBAK-VBTYP (SD document category). 'C' = order.

12. Class must implement IF_AMDP_MARKER_HDB — yes, and the interface must be listed in the class definition. Also the class must be created... AMDP classes: any global class implementing IF_AMDP_MARKER_HDB. Note: AMDP classes can't be... they must not have... whatever.

13. Call from ABAP:

```abap
DATA(lo_top) = NEW zcl_sd_top_materials( ). " or static method

zcl_sd_top_materials=>get_top_materials(
  EXPORTING iv_vkorg = '1010'      " Verkaufsorganisation
  IMPORTING et_top   = DATA(lt_top) ).

cl_demo_output=>display( lt_top ).
```

With implicit client handling, clnt is not passed. I should make sure the call matches my signature decision.

Decision on client: Use implicit client handling (first parameter `clnt` TYPE abap.clnt, not passed in call). I'll explain this clearly. Also mention alternative: explicit parameter.

Hmm, wait — one more check on implicit client handling for AMDP methods: is it available in all relevant releases? It was introduced with 7.40 SP08? or 7.50? The feature "implicit client handling for AMDP methods" — I believe it exists since 7.40 SP... The doc section "AMDP - Client Handling" exists since 7.40 SP08 or so. Since the user presumably uses 7.5x (S/4), fine. I'll note "ab 7.40 SP08 bzw. 7.50" — maybe skip precise SP numbers to avoid errors; just say "modernen Releases".

Hmm, actually, let me reconsider whether to use implicit client handling once more. Risks: (a) if I misremember and the caller MUST pass clnt, my call example is wrong. (b) If implicit handling works as I remember, great.

Let me try to find a definitive memory... ABAP Keyword Documentation, "AMDP - Client Handling":

I recall the beginning: "For AMDP methods and AMDP function implementations, implicit client handling is not switched on automatically. It can be switched on by declaring a suitable input parameter." And then: "For AMDP methods, implicit client handling is switched on by declaring a mandatory input parameter clnt as first input parameter of the method. The parameter must be typed with abap.clnt or with a data element... When the method is called, the current client is passed automatically to the parameter clnt. The parameter clnt cannot be specified explicitly in the method call."

Hmm, "cannot be specified explicitly" — I'm now ~90% sure. Also I recall the doc for AMDP function implementations: "For AMDP function implementations, implicit client handling is switched on by declaring a mandatory input parameter clnt as first input parameter... When the function implementation is used as data source in ABAP SQL, the current client is passed automatically..." — same pattern. Yes.

Also, importantly: with implicit client handling, the AMDP framework ALSO checks/ensures? No. And there's a note: "In the procedure body, the parameter clnt must be used in the WHERE conditions for client-dependent tables; otherwise the results are not client-specific." The framework doesn't enforce it (I think there's a check in the AMDP procedure call? No). Fine.

Additionally: implicit client handling sets the session variable CDS_CLIENT? For AMDP methods, when called, the AMDP runtime sets the HANA session variable CDS_CLIENT to the current client — I believe yes, for AMDP with implicit client handling, CDS_CLIENT is set. But I'll use the parameter approach in the body anyway.

OK, going with implicit client handling. But hmm — one concern: if the reader's system is older (7.40 without the feature), the code won't compile. I'll add a fallback note: "Falls euer Release keine implizite Mandantenbehandlung unterstützt: Parameter einfach IV_MANDT nennen und im Aufruf sy-mandt übergeben."

Now, also the type abap.clnt: exists. `VALUE(clnt) TYPE abap.clnt`. Good.

14. Also: AMDP methods must be declared in the class definition with the AMDP option; the implementation must contain ONLY the SQLScript body (no ABAP). The method cannot have a `ENDMETHOD` with ABAP code. Also, no declarations. Correct.

15. Class-level: The class should implement IF_AMDP_MARKER_HDB. Also note: AMDP classes cannot be... they must be global? AMDP methods are only possible in global classes? Hmm: "AMDP methods can only be implemented in global classes" — I believe AMDP methods must be in global classes (class pools) of the ABAP Dictionary? Actually: "AMDP methods can only be implemented in global classes of the class library." Yes, I believe local classes cannot have AMDP methods. I'll make it a global class ZCL_...

16. Also worth noting: the DB objects (vbak, vbap) in USING are the DDIC table names; in the SQLScript body, you reference them directly as vbak/vbap (uppercase recommended). 

17. SQLScript specifics: scalar parameters are referenced with `:iv_vkorg`. Table parameters used directly. Assignment `et_top = SELECT ...;` with semicolon. Correct.

18. TOP vs LIMIT: `LIMIT 10` after ORDER BY. In HANA SQLScript, `SELECT ... FROM ... WHERE ... GROUP BY ... ORDER BY ... LIMIT 10;` — valid. Also `SELECT TOP 10 ...` valid. I'll use LIMIT 10.

Hmm, one subtlety: In SQLScript, when assigning to an output parameter, `et_top = SELECT TOP 10 ...` or with LIMIT — both fine.

19. Column name conflicts: alias `umsatz` — HANA allows lowercase identifiers unquoted; they become uppercase. Fine. But careful: ABAP field names in the DDIC structure must match (MATNR, UMSATZ, WAERK, MENGE). The SELECT column aliases must match the DDIC structure component names (case-insensitive). Good.

20. Should the method be static (CLASS-METHODS) or instance? Either works. Static is convenient. But note: AMDP methods can be instance or static. I'll use CLASS-METHODS for easy call. Hmm — one consideration: some prefer instance methods for injection/testing. Static is fine for demo.

21. Also add `RAISING`? AMDP methods can raise cx_amdp_error etc. Could add `RAISING cx_amdp_creation_error` — optional. Keep simple; maybe mention error handling briefly (AMDP errors → cx_amdp_error family / cx_sy_sql...? Actually database errors in AMDP raise CX_AMDP_ERROR subclasses, e.g., CX_AMDP_CREATION_ERROR, CX_AMDP_EXECUTION_ERROR, CX_AMDP_ERROR_DYN_SQL...). I could add `RAISING cx_amdp_execution_error` hmm — if the method declares RAISING, errors are propagated; otherwise they're wrapped? AMDP errors are always raised as CX_AMDP_* exceptions; declaring them in RAISING is optional (they're dynamic? no, they're... CX_AMDP_ERROR is static-checkable? I think AMDP exceptions are... hmm). Keep it simple: no RAISING, mention in notes that DB errors surface as CX_AMDP_* exceptions.

Now, additional content: "Erkläre, wann sich AMDP gegenüber ABAP-SQL lohnt." — When does AMDP pay off vs ABAP SQL (open SQL / modern ABAP SQL)?

Key points:
- Code pushdown: AMDP allows using HANA-specific features not available in ABAP SQL: e.g., complex procedural logic (imperative SQLScript: loops, IF/CASE logic, intermediate result tables, cursors), HANA-specific functions (window functions are now in ABAP SQL too, but e.g. hierarchical queries, spatial, text search, fuzzy search, predictive functions/PAL, graph engine, series data), UNION with different structures? etc.
- Multi-step calculations with intermediate results: In ABAP SQL you'd need multiple statements with intermediate tables transported between DB and AS ABAP; AMDP keeps everything in the DB in one call — avoids intermediate result shipping.
- Performance: When processing large volumes where the logic can't be expressed declaratively in a single SQL statement — SQLScript's imperative extensions let you do it set-based in the DB.
- Reuse: AMDP procedures can be consumed by other procedures, CDS table functions (via AMDP function implementations), AMDP function implementations usable in ABAP SQL as data source.
- Limitations of ABAP SQL: no procedural constructs; some HANA features not (yet) exposed; AMDP gives full SQLScript power.
- When NOT needed: If the requirement is expressible in a single ABAP SQL statement (SELECT with joins, aggregates, window functions), prefer ABAP SQL: better readability, portability (works on any DB), syntax checks at compile time, CDS integration, no HANA lock-in, easier testing, no DDIC type overhead. AMDP is HANA-only (FOR HDB) — portability loss; code is opaque to ABAP tooling (no where-used on DB objects? actually USING list helps), debugging harder (HANA debugger), transport of procedure sources handled by AMDP framework but versioning/analysis more complex.
- Rule of thumb (SAP recommendation): "Code pushdown" — first try to express in ABAP SQL/CDS; use AMDP when you need SQLScript-specific capabilities (procedural logic, HANA-specific functions, multiple steps with intermediate results, integration with HANA libraries like PAL/ AFL, geospatial, text/fuzzy search, hierarchy functions), or when existing HANA artifacts need wrapping.
- Also: AMDP for bottom-up? AMDP is the only way to create and call managed DB procedures from ABAP; needed for CDS table function implementations.
- Performance-wise: A single well-written ABAP SQL statement is typically as fast as an AMDP doing the same; AMDP wins when you'd otherwise need multiple round trips or application-server-side post-processing of large intermediate results.
- Also mention: READ-ONLY option, client handling, security (SQL injection not an issue since parameters are bound, not concatenated).
- Also: AMDP only on HANA (FOR HDB); ABAP SQL is DB-agnostic. In S/4HANA, HANA is the only supported DB anyway (mostly), so portability matters less — but for sidecar setups (secondary DB connections?) AMDP only runs on the primary HANA... AMDP runs on the primary database of the AS ABAP; with S/4 it's HANA.

Also worth explaining briefly how AMDP works: the SQLScript source is transported as part of the class; at first call, the AMDP framework creates the procedure in the HANA schema (SAP<SID> or _SYS_...?) — it's created in the ABAP schema; parameters mapped; USING ensures dependency management (where-used, deletion protection). Maybe a short "Wie AMDP funktioniert" intro.

Structure of the answer (in German):

1. Kurze Einleitung (1-2 Sätze).
2. DDIC-Voraussetzungen (Struktur + Tabellentyp) — kurz.
3. Klassendefinition (Code).
4. Implementierung (Code) — with comments.
5. Aufruf aus ABAP (Code).
6. Erläuterungen zu den AMDP-Spezifika (Marker-Interface, BY DATABASE PROCEDURE, USING, READ-ONLY, VALUE-Parameter, Mandantenbehandlung, Typen).
7. Wann lohnt sich AMDP vs. ABAP SQL (pro/contra, Faustregel).
8. Maybe a short note on currency caveat and VBTYP filter.

Format: Code blocks with abap syntax highlighting. Headers. Moderate length — this is a technical "write code + explain" request; the code is the core. The explanation should be substantive but not bloated. Use German throughout. Use markdown with ### headers, bullet lists for the "wann lohnt sich" part, maybe a small table for AMDP vs ABAP SQL? A table could be nice: Kriterium | ABAP SQL | AMDP. Or bullets. A compact table might be good for the decision criteria. Let me include a short table plus a Faustregel.

Let me now write the actual code carefully.

DDIC prerequisites:

Struktur ZSD_S_TOP_MATERIAL (flach):
- MATNR — Typ MATNR (CHAR 18) — Materialnummer
- WAERK — Typ WAERS — Währung
- UMSATZ — Typ NETWR (CURR 15/2)? Hmm, using NETWR as data element for the result component — NETWR is CURR with currency field reference? In a DDIC structure, a CURR component needs a reference currency field? For structure definitions, CURR fields need reference to currency key (in table they do; in structures, the currency reference is optional? In SE11 structures, CURR fields don't require a reference table (only tables do). Actually in DDIC structures, currency fields can be defined without reference — the reference is only checked for tables? Hmm, in SE11 structure, a CURR field requires... I believe in structures you can define CURR without reference table (it warns?). To keep it simple, define UMSATZ as `p DECIMALS 2` built-in type or use data element NETWR. NETWR domain is CURR 15,2? NETWR: CURR, length 15, decimals 2? Actually NETWR is CURR length 15 decimals 2? VBAP-NETWR: CURR 15/2? I think VBAP-NETWR is CURR(15,2)? Hmm, NETWR domain: data type CURR, length 15, decimal 2? Let me think: VBAP-NETWR is CURR 15 2? KWMENG is QUAN 13,3. NETWR — I believe length 15, decimals 2? Hmm, actually I recall NETWR being CURR 15,2? There's also NETWR in VBAK same. Fine — I'll just say "UMSATZ vom Typ NETWR (bzw. p LENGTH 15 DECIMALS 2)". For the DDIC structure, using data element NETWR is fine.

Hmm, wait: if I group by material+currency, the sum is per currency — fine with WAERK in structure.

- MENGE — Typ KWMENG (QUAN 13,3) — optional; sum of order quantities. Maybe include for context. Or keep result minimal: MATNR, UMSATZ, WAERK. Adding MENGE is nice. I'll include it.

Tabellentyp ZSD_TT_TOP_MATERIAL: Zeilentyp ZSD_S_TOP_MATERIAL, Standardtabelle.

Alternatively, to reduce DDIC friction, I could type the row as an existing DDIC structure? No good one. Keep custom.

Hmm, actually — wait. Let me reconsider the local-type question once more, because it significantly affects the example's usability. Let me try REALLY hard to recall the current ABAP doc on AMDP parameters.

From ABAP Keyword Documentation (latest), "AMDP - Parameter" (sql_ama_param or similar):

"Rules for the parameter interface of AMDP methods:

- All parameters must be passed by value.
- The parameters of AMDP methods can only be typed using elementary ABAP types or using table types. The table types can be defined in ABAP Dictionary or in the class pool of the AMDP class. Structured parameters are not possible.
- The row type of the table types must be a flat structure from ABAP Dictionary or elementary. Deep types are not possible. ..."

Hmm — "The table types can be defined in ABAP Dictionary or in the class pool of the AMDP class." — I do think this sentence exists in current docs (it was added around 7.53/7.54). And the row type restriction: "flat structure from ABAP Dictionary or elementary". Hmm, but wait — if the table type can be class-local, can its row type be a class-local structure? I believe the doc explicitly says the row type must be DDIC structure or elementary... but hmm, actually I have a nagging memory that at some point they allowed "structured types of the class pool" as row types too. 

Let me think about AMDP function implementations (used as CDS table function implementation): their parameters must be typed... For AMDP function implementations, the tabular return parameter must be typed with a DDIC table type? No wait — AMDP function implementations return... they have a RETURN parameter? No — AMDP function implementations are methods with `BY DATABASE FUNCTION` and they return a tabular result via... they must have a RETURNING parameter? Hmm, AMDP function implementations: "The return value... must be typed with a table type from ABAP Dictionary whose row type matches the CDS table function"? I recall: AMDP function implementations for CDS table functions have importing parameters matching the CDS parameters plus clnt, and the return parameter typed with a table type whose row type is the CDS entity's structure... which is a CDS-based type, not DDIC. Hmm, so for function implementations, the row type can be derived from the CDS entity ("The return parameter must be typed with a table type... or with #..."). There's special syntax for CDS entities. Not relevant here.

OK final decision: DDIC structure + DDIC table type. This is bulletproof. I'll present it compactly. And I'll add one sentence: "In neueren Releases sind auch im Class-Pool definierte Tabellentypen zulässig (Zeilentyp weiterhin flache DDIC-Struktur oder elementar) — dann entfällt der DDIC-Tabellentyp." Hmm, should I? If unsure, maybe phrase softly: "Je nach Release genügt auch ein lokaler Tabellentyp; sicher über alle Releases ist der DDIC-Tabellentyp." OK.

Hmm, actually, hmm, wait. Let me reconsider — maybe I'm overestimating the restriction. Let me recall a concrete counter-example: SAP's own ABAP doc example for AMDP (CL_DEMO_AMDP_SELECT?) — I recall:

```abap
REPORT demo_amdp_method.
CLASS demo_amdp DEFINITION.
  PUBLIC SECTION.
    INTERFACES if_amdp_marker_hdb.
    TYPES: BEGIN OF wa,
             carrid TYPE sflight-carrid,
             connid TYPE sflight-connid,
           END OF wa,
           itab TYPE STANDARD TABLE OF wa WITH EMPTY KEY.
    CLASS-METHODS get_data IMPORTING VALUE(clnt) TYPE abap.clnt
                           EXPORTING VALUE(data) TYPE itab.
```

Hmm — did the doc example use a local structure wa? I genuinely can't recall. I remember `demo_flshts` DDIC structure being used in some examples ("TYPES flights_tab TYPE STANDARD TABLE OF demo_flshts WITH EMPTY KEY"). The existence of demo_flshts (a demo DDIC structure created specifically for these examples) suggests that DDIC structures are needed as row types! Why else would SAP create a demo DDIC structure for flight demo data when they could define a local structure? That's decent evidence that local structures are NOT allowed as AMDP row types. 

OK: DDIC structure + table type it is. I'll clearly list the DDIC prerequisites.

Actually, hmm, one more alternative that avoids custom DDIC objects entirely: return the result as a table of an EXISTING DDIC structure... there isn't a fitting one. Or return VBAP lines? No. OK, custom DDIC objects, clearly documented. That's also realistic — in real projects you'd create them.

Now write the class:

```abap
CLASS zcl_sd_top_material_amdp DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    " Marker-Interface: kennzeichnet die Klasse als AMDP-fähig (HDB = HANA Database)
    INTERFACES if_amdp_marker_hdb.

    CLASS-METHODS get_top_materials
      " 1. Parameter 'clnt' => implizite Mandantenbehandlung:
      " wird beim Aufruf automatisch mit sy-mandt versorgt
      IMPORTING VALUE(clnt)    TYPE abap.clnt
                VALUE(iv_vkorg) TYPE vkorg
      EXPORTING VALUE(et_top)   TYPE zsd_tt_top_material.
```

Hmm wait — with implicit client handling, is the parameter order "clnt first" mandatory? Yes, first input parameter. OK.

Also: should I add RAISING cx_amdp_error? Optional. Skip, mention in notes.

Implementation:

```abap
CLASS zcl_sd_top_material_amdp IMPLEMENTATION.

  METHOD get_top_materials BY DATABASE PROCEDURE
                           FOR HDB LANGUAGE SQLSCRIPT
                           OPTIONS READ-ONLY
                           USING vbak vbap.

    et_top =
      SELECT vbap.matnr            AS matnr,
             vbap.waerk            AS waerk,
             SUM( vbap.netwr )     AS umsatz,
             SUM( vbap.kwmeng )    AS menge
        FROM vbap
        INNER JOIN vbak
           ON  vbak.mandt = vbap.mandt
           AND vbak.vbeln = vbap.vbeln
       WHERE vbap.mandt = :clnt
         AND vbak.vkorg = :iv_vkorg
         -- optional: nur Aufträge, keine Angebote/Kontrakte
         -- AND vbak.vbtyp = 'C'
       GROUP BY vbap.matnr,
                vbap.waerk
       ORDER BY umsatz DESC,
                matnr
       LIMIT 10;

  ENDMETHOD.

ENDCLASS.
```

Wait: ORDER BY umsatz DESC — alias reference in ORDER BY inside a SQLScript assignment. HANA allows ORDER BY on column aliases? In HANA SQL, ORDER BY can reference select list aliases — yes, HANA supports that (e.g., SELECT a+b AS s FROM t ORDER BY s). Yes, HANA supports ORDER BY alias. But to be extra safe, I could write `ORDER BY SUM(vbap.netwr) DESC` — also valid and unambiguous. Hmm, using the alias is cleaner. HANA definitely supports alias in ORDER BY (standard behavior). I'll use the alias but could mention. Actually, let me use `ORDER BY umsatz DESC, matnr` — fine.

Hmm, one more consideration: `LIMIT 10` vs `TOP 10`: both fine in HANA. LIMIT is more ANSI-ish. Keep LIMIT 10. Note: with LIMIT, ORDER BY must come before LIMIT — yes, syntax order: ... GROUP BY ... HAVING ... ORDER BY ... LIMIT. Correct.

Also: In SQLScript, should I worry that `et_top` assignment with a SELECT that returns fewer rows is fine — yes.

Also the join: VBAK-VBELN is CHAR 10, VBAP-VBELN CHAR 10 — join fine. MANDT join included — good practice (though with both filtered by clnt it's implied; including it helps the optimizer and is standard).

Should I use `:clnt` for both tables? WHERE vbap.mandt = :clnt AND vbak.vkorg = :iv_vkorg — since join equates mandts, vbak.mandt = :clnt transitively. OK. Some style guides filter both. I'll add both for clarity? It's redundant; keep one on vbap.mandt and join condition. Hmm, for correctness of implicit client handling, the doc says use clnt in WHERE conditions of client-dependent tables — one is enough given the join. I'll keep `vbap.mandt = :clnt` and the join on mandt. Fine.

Currency note: I'll add a comment in code and a note below.

Call from ABAP:

```abap
" Aufruf (z. B. in einem Report oder einer Handler-Klasse)
DATA(lt_top) = VALUE zsd_tt_top_material( ).

zcl_sd_top_material_amdp=>get_top_materials(
  EXPORTING iv_vkorg = CONV vkorg( '1010' )
  IMPORTING et_top   = lt_top ).

" clnt wird automatisch mit sy-mandt gefüllt (implizite Mandantenbehandlung)

LOOP AT lt_top INTO DATA(ls_top).
  WRITE: / ls_top-matnr, ls_top-umsatz, ls_top-waerk.
ENDLOOP.

" oder komfortabel:
" cl_demo_output=>display( lt_top ).
```

Hmm, `CONV vkorg( '1010' )` — vkorg is CHAR 4; passing '1010' literal to TYPE vkorg parameter works directly (literal conversion). Actually passing a character literal '1010' to a CHAR4 parameter is fine without CONV. Keep simple: `iv_vkorg = '1010'`.

Also mention: exceptions — wrap in TRY? AMDP raises CX_AMDP_* (e.g., CX_AMDP_EXECUTION_ERROR) — since I didn't declare RAISING, are they catchable? AMDP errors: The AMDP framework raises class-based exceptions of CX_AMDP_ERROR category. If the method doesn't declare them, can the caller still CATCH them? For exceptions not declared in RAISING, they can still be caught (they're just not declared; CX_AMDP_* inherit from CX_DYNAMIC_CHECK? or CX_STATIC_CHECK?). Hmm: CX_AMDP_ERROR inherits from CX_DYNAMIC_CHECK I believe. Dynamic check exceptions don't need RAISING declaration and can be caught anytime. So CATCH works. I'll show a TRY-CATCH optionally? Maybe just mention it in a bullet. Keep the call example clean, add a short note: "Datenbankfehler werden als CX_AMDP_*-Ausnahmen gemeldet (z. B. CX_AMDP_EXECUTION_ERROR), die sich per TRY...CATCH abfangen lassen."

Also worth noting in the call example: the AMDP procedure is created lazily on first call (in the ABAP schema of the HANA DB) and the source is transported with the class. Maybe mention in the "how it works" intro.

Now the explanation "wann lohnt sich AMDP gegenüber ABAP-SQL":

Structure:
- Grundsatz: "Code pushdown" — aber ABAP SQL kann heute schon sehr viel (Joins, Aggregate, Window Functions, CTEs, hierarchische Abfragen...). Faustregel: Was sich in EINER deklarativen ABAP-SQL-Anweisung ausdrücken lässt, gehört in ABAP SQL (oder CDS View) — nicht in AMDP.
- AMDP lohnt sich, wenn:
  1. Prozedurale/mehrschrittige Logik mit Zwischenergebnissen, die sonst auf den Applikationsserver müsste (mehrere Roundtrips / große Zwischentabellen). SQLScript erlaubt IF/WHILE/Cursors, lokale temporäre Tabellen, mehrere SELECTs in einem Procedure-Call.
  2. HANA-spezifische Funktionen, die ABAP SQL nicht (oder nicht effizient) abbildet: z. B. räumliche Funktionen (Spatial), Text-/Fuzzy-Search, Predictive Analysis Library (PAL/AFL), Graph, Seriendaten, HIERARCHY_*, Sprachfunktionen? Also: window functions exist in ABAP SQL now; but e.g. `SERIES`, `GRAPH`... Also UDFs.
  3. Wiederverwendung: AMDP function implementations als Implementierung von CDS-Table-Functions (die man in ABAP SQL/CDS nutzen kann); Aufruf von Prozeduren aus anderen Prozeduren.
  4. Bestehende HANA-Artefakte (Berechnungsmodelle? eher legacy) / Migration von Data Manager Logic.
  5. Performance bei komplexen Transformationen großer Datenmengen, die sich nicht in einen Satz deklarativen SQL fassen lassen.
- Gegenargumente / Wann ABAP SQL besser:
  1. Portabilität: AMDP läuft nur auf HANA (FOR HDB); ABAP SQL auf jeder DB.
  2. Lesbarkeit/Wartbarkeit: SQLScript ist aus ABAP-Sicht "black box"; keine ABAP-Syntaxprüfung des SQL-Texts (Fehler erst zur Laufzeit/Erzeugung), Debugging nur im HANA-Studio/HDI? (HANA debugger), Tooling schwächer.
  3. Typsicherheit/Boilerplate: DDIC-Typen nötig, Mandantenbehandlung manuell (bzw. clnt-Parameter), kein automatischer Client, keine Autoritätsprüfung? (Autorisierungen müssen selbst geprüft werden — ABAP SQL via CDS hat DCLS etc.)
  4. Testbarkeit, CDS-Integration (Annotations, DCL) fehlt.
  5. Wenn dieselbe Logik auch auf Nicht-HANA laufen muss.
- Faustregel (SAP-Empfehlung): 1. CDS Views / ABAP SQL (deklarativ), 2. AMDP für prozedurale Pushdown-Spezialfälle, 3. nur bei echtem Bedarf. "ABAP SQL first, AMDP when needed."
- Performance-Hinweis: Ein einzelner, gut geschriebener SELECT ist i. d. R. genauso schnell wie die gleiche Logik in AMDP — der Gewinn entsteht nicht durch "SQLScript an sich", sondern durch Vermeidung von Zwischenergebnissen auf dem Applikationsserver und durch Nutzung HANA-eigener Engine-Funktionen.

Also maybe a compact table:

| Kriterium | ABAP SQL / CDS | AMDP |
|---|---|---|
| DB-Unabhängigkeit | ja | nur HANA |
| Prozedurale Logik | nein | ja (SQLScript) |
| HANA-Spezialfunktionen | begrenzt | voll |
| Syntaxprüfung zur Kompilierzeit | ja | eingeschränkt (Fehler oft erst zur Laufzeit) |
| Mandantenbehandlung | automatisch | manuell/clnt-Parameter |
| CDS-Integration (DCL, Annotations) | ja | nein |
| Zwischenergebnisse ohne Roundtrips | nein (mehrere Statements → Transport) | ja |

That's a good table. Keep it concise.

Also mention specifics of the example: For THIS requirement (top 10 by revenue), plain ABAP SQL would suffice:

```abap
SELECT matnr, waerk, SUM( netwr ) AS umsatz, SUM( kwmeng ) AS menge
  FROM vbap
  ...
 GROUP BY matnr, waerk
 ORDER BY umsatz DESC
 LIMIT 10
 INTO TABLE @DATA(lt_top).
```

Actually — ABAP SQL supports LIMIT? Yes, ABAP SQL supports LIMIT since 7.40 SP08? Hmm: ABAP SQL has `UP TO n ROWS` and since 7.5x also `LIMIT`. Yes, ABAP SQL supports LIMIT (ABAP 7.52+? "SELECT ... LIMIT" was added with 7.52? I recall LIMIT in ABAP SQL introduced with ABAP 7.52? Hmm — ABAP SQL additions: UP TO n ROWS always; LIMIT was added in 7.52? Actually I think `LIMIT` in ABAP SQL came with 7.52 (or 7.51?). There's also `OFFSET`. I believe LIMIT/OFFSET were added to ABAP SQL in release 7.52. Yes: ABAP 7.52 news: "SQL: LIMIT, OFFSET". OK.) I can show this as the "alternative in pure ABAP SQL" to make the point that this specific task doesn't NEED AMDP — great pedagogical touch: the user asked for AMDP, but an honest expert notes that this particular query is expressible in ABAP SQL, and AMDP pays off for more complex cases. I'll include a short ABAP SQL equivalent snippet in the "wann lohnt" section.

Let me draft that ABAP SQL equivalent:

```abap
SELECT vbap~matnr,
       vbap~waerk,
       SUM( vbap~netwr )  AS umsatz,
       SUM( vbap~kwmeng ) AS menge
  FROM vbap
  INNER JOIN vbak ON vbak~vbeln = vbap~vbeln
                 AND vbak~mandt = vbap~mandt
 WHERE vbap~mandt = @sy-mandt
   AND vbak~vkorg = @iv_vkorg
 GROUP BY vbap~matnr, vbap~waerk
 ORDER BY umsatz DESC
 LIMIT 10
 INTO TABLE @DATA(lt_top).
```

Hmm, ORDER BY alias in ABAP SQL: allowed? In ABAP SQL, ORDER BY can use aliases? I believe ORDER BY in ABAP SQL can reference column aliases... Actually ABAP SQL ORDER BY: you can order by columns, column names of the result set... I recall that ABAP SQL allows ORDER BY with alias names? Hmm. In ABAP SQL, `ORDER BY` after aggregate SELECT — you can specify the alias? I believe yes: "ORDER BY can be used with the names of the columns in the result set" — hmm, historically ORDER BY in ABAP SQL could only use column names/positions... Let me recall: ABAP SQL ORDER BY sql_exp? As of 7.5x, ORDER BY can contain SQL expressions and aliases? I recall: "As of Release 7.5?, ORDER BY allows aggregate expressions and aliases"? Hmm.

To be safe in the snippet, use `ORDER BY SUM( vbap~netwr ) DESC` — is ORDER BY with aggregate expression allowed in ABAP SQL? I believe aggregates in ORDER BY are allowed when they appear in the SELECT list... ABAP SQL docs: "ORDER BY can be used to specify... aggregate expressions? " Hmm. Actually I recall ABAP SQL ORDER BY supports: columns, column selectors, positions (numbers), and SQL expressions (as of 7.5x?). To be safe, alternative: order by position: `ORDER BY 2 DESC`? Hmm, ordering by column index — ABAP SQL supports `ORDER BY` with literal numbers? Yes, ORDER BY 2 DESC historically works in ABAP SQL? Hmm, I think ABAP SQL does support numeric positions in ORDER BY? Hmm, not sure — native SQL does; ABAP SQL... I believe ABAP SQL ORDER BY accepts column names and... let me think. Old ABAP SQL: "ORDER BY col1 col2..." or "ORDER BY PRIMARY KEY". Positions? I don't think positions are allowed in ABAP SQL. Hmm.

Actually, I'm fairly confident modern ABAP SQL allows alias names in ORDER BY. From ABAP docs "SELECT, ORDER BY": "ORDER BY can be specified ... using the names or aliases of the columns in the result set"? Hmm... I recall the doc: "sql_exp ... aggregate expressions can be specified in ORDER BY if they are in the SELECT list"? 

Let me just recall real code: 

```abap
SELECT carrid, SUM( price ) AS sum_price
  FROM sflight
  GROUP BY carrid
  ORDER BY sum_price DESC
  INTO TABLE @DATA(result).
```

I'm quite sure I've seen this pattern and that it works (ORDER BY alias). Yes — ABAP SQL supports aliases in ORDER BY. I'm confident enough. (ABAP doc: "The alias names of the SELECT list can be specified after ORDER BY." — hmm, actually I recall that aliases in ORDER BY were NOT allowed historically and there was a change... In ABAP 7.5x with the new SQL syntax, ORDER BY alias works. I've written such code. OK.)

Also `LIMIT 10` — supported since 7.52. Fine, and I can note "ab 7.52; sonst UP TO 10 ROWS". Actually `UP TO 10 ROWS` works everywhere: `SELECT ... UP TO 10 ROWS ...` — but UP TO must come right after SELECT keyword: `SELECT UP TO 10 ROWS matnr, ...`? With comma syntax: `SELECT UP TO 10 ROWS matnr, waerk, ...` — yes valid. I'll use LIMIT 10 with a comment "(alternativ UP TO 10 ROWS)".

Hmm, wait: in ABAP SQL, when using GROUP BY + ORDER BY alias + LIMIT — all fine.

Also in the ABAP SQL snippet, joining on mandt: with implicit client handling in ABAP SQL, client is automatic — no need for `vbap~mandt = @sy-mandt` (ABAP SQL handles client automatically). So the snippet should NOT include mandt conditions — cleaner and shows the difference (automatic client handling!). Good teaching point: in ABAP SQL, client handling is automatic; in AMDP, you must handle it. So snippet:

```abap
SELECT vbap~matnr,
       vbap~waerk,
       SUM( vbap~netwr )  AS umsatz,
       SUM( vbap~kwmeng ) AS menge
  FROM vbap
  INNER JOIN vbak ON vbak~vbeln = vbap~vbeln
 WHERE vbak~vkorg = @iv_vkorg
 GROUP BY vbap~matnr, vbap~waerk
 ORDER BY umsatz DESC
 LIMIT 10
 INTO TABLE @DATA(lt_top).
```

Wait — join without mandt: ABAP SQL adds client conditions automatically for client-dependent tables (both vbap and vbak get mandt = sy-mandt implicitly, and the join is fine because both are filtered to the same client). Yes, implicit client handling in ABAP SQL adds `mandt = sy-mandt` to each client-dependent table. Correct.

INTO clause position: In ABAP SQL with comma syntax, INTO comes at the end: `... ORDER BY ... LIMIT 10 INTO TABLE @DATA(lt_top).` Hmm — clause order: SELECT ... FROM ... WHERE ... GROUP BY ... ORDER BY ... INTO TABLE. And LIMIT? Where does LIMIT go — before INTO? The ABAP SQL grammar: `SELECT ... [ORDER BY ...] [LIMIT ...] INTO ...`? Hmm. Actually in ABAP SQL, the INTO clause normally comes last, but there's the "strict mode" where INTO can be... Let me recall: `SELECT matnr FROM mara INTO TABLE @DATA(it) UP TO 10 ROWS.` — UP TO comes right after SELECT. For LIMIT: `SELECT FROM ... WHERE ... GROUP BY ... ORDER BY ... LIMIT 10 INTO TABLE @DATA(...)`? I believe LIMIT is placed after ORDER BY and before INTO? Hmm, or after INTO? 

ABAP doc for SELECT, LIMIT: "LIMIT ... The addition LIMIT must be placed after ORDER BY? or at the end?" I recall syntax diagrams: `SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... INTO ...` and LIMIT... Hmm, actually I think in ABAP SQL, LIMIT/OFFSET are specified AFTER the INTO clause? No wait...

Let me recall an example from ABAP docs (7.52 news, "LIMIT"):

```abap
SELECT FROM spfli
       FIELDS carrid, connid
       ORDER BY carrid, connid
       LIMIT 5
       INTO TABLE @DATA(result).
```

Hmm — with FIELDS keyword, INTO comes last. I believe the order is: ... ORDER BY ... [OFFSET ...] [LIMIT ...] INTO ...? Hmm, or INTO before LIMIT? 

I recall: In ABAP SQL strict mode 7.52, the INTO clause can be placed before or after other clauses? The rule: "In the strict modes from 7.40 SP05 on, INTO can be specified before ... " Hmm, historically INTO must be last. But I've definitely seen `LIMIT` after `ORDER BY` and before `INTO`. Let me think about the ABAP doc example for LIMIT:

From ABAP Keyword Documentation "SELECT, LIMIT":

```abap
SELECT FROM spfli
       FIELDS carrid,
              connid
       WHERE cityfrom = 'FRANKFURT'
       GROUP BY carrid, connid
       ORDER BY carrid, connid
       LIMIT 10
       INTO TABLE @DATA(result).
```

Hmm, I think LIMIT comes after ORDER BY and before INTO. Hmm, but actually I have a doubt: I recall the syntax diagram putting `LIMIT` at the very end, after INTO? No... Let me think about UP TO: `SELECT UP TO 10 ROWS ...` — UP TO is right after SELECT. LIMIT was introduced as part of the "new" SQL with placement... I'm fairly confident: `... ORDER BY ... LIMIT n OFFSET m INTO TABLE ...`? Hmm, or is OFFSET/LIMIT after INTO?

Let me recall the ABAP doc text: "SELECT, LIMIT: ... LIMIT limits the number of rows... The addition LIMIT must be specified after ORDER BY..." hmm. Actually you know what, I remember now more clearly: In ABAP SQL, the order is:

```
SELECT [DISTINCT] select_list
  FROM source
  [WHERE cond]
  [GROUP BY ...]
  [HAVING ...]
  [ORDER BY ...]
  [UP TO n ROWS | LIMIT n [OFFSET m]]
  INTO target...
```

Hmm no — UP TO n ROWS is after SELECT keyword. And LIMIT... I found it: ABAP doc example:

```abap
SELECT carrid, connid
       FROM spfli
       ORDER BY carrid, connid
       LIMIT 2
       INTO TABLE @DATA(result).
```

Hmm, I keep producing "LIMIT before INTO". But wait — can INTO really come after LIMIT? The general rule for ABAP SQL SELECT: "The INTO clause must be specified last" — in the strict modes... Actually the rule is: INTO must be the last clause of the SELECT statement (except for additions like... hmm). But then LIMIT before INTO would violate that unless LIMIT is part of the ordered clauses. I believe the syntax diagram for SELECT (7.52+) is:

SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... [OFFSET] [LIMIT] ... INTO ...? 

Hmm hmm. OK, alternative safe approach for the snippet: put INTO before LIMIT? `... ORDER BY umsatz DESC INTO TABLE @DATA(lt_top) LIMIT 10.`? That looks wrong too.

Safest: use UP TO 10 ROWS which has unambiguous placement:

```abap
SELECT UP TO 10 ROWS vbap~matnr, ...
```

Hmm, with comma lists: `SELECT UP TO 10 ROWS vbap~matnr, vbap~waerk, SUM(...) AS umsatz, ...` — valid? UP TO n ROWS comes directly after SELECT (before the select list). With the comma syntax, yes: `SELECT UP TO 10 ROWS carrid, connid FROM spfli...` — I believe that's valid. Yes.

But actually, I'm now recalling the ABAP news for 7.52: "SQL: LIMIT and OFFSET" — example:

```abap
SELECT FROM sflight
       FIELDS carrid, connid, fldate
       ORDER BY carrid, connid, fldate
       LIMIT 10
       INTO TABLE @DATA(result).
```

I'm going to trust this: LIMIT after ORDER BY, then INTO last. Hmm, but is INTO really after LIMIT? In this example with FIELDS, INTO is last. I believe the full clause order in strict mode allows INTO at the end, with LIMIT/OFFSET between ORDER BY and INTO. Hmm, wait, actually — I now genuinely recall the ABAP doc syntax diagram:

`SELECT [DISTINCT] {select_list | FIELDS ...} FROM ... [WHERE] [GROUP BY] [HAVING] [ORDER BY] [OFFSET] [LIMIT] INTO|APPENDING ...`

Hmm, no. Ugh.

Let me settle with a different approach: I'll write the ABAP SQL snippet with UP TO 10 ROWS (100% safe placement after SELECT) and mention "(ab 7.52 geht auch LIMIT)". Actually, hmm, but UP TO with comma-syntax select list — is `SELECT UP TO 10 ROWS a, b FROM ...` valid? UP TO n ROWS is an addition of SELECT and comes before the select list: `SELECT UP TO 10 ROWS matnr, waerk, ... FROM ...`. Yes, I'm confident that's valid.

Hmm, wait, actually, one more memory attempt on LIMIT placement: I'm now fairly sure the ABAP doc says: "LIMIT: ... can only be used after ORDER BY? ... The additions OFFSET and LIMIT must be specified after the ORDER BY clause? and before INTO?" — You know, I've seen real code like:

```abap
SELECT *
  FROM mara
  WHERE mtart = 'FERT'
  ORDER BY matnr
  INTO TABLE @DATA(lt)
  LIMIT 10.
```

Hmm?? That also rings a faint bell — LIMIT after INTO?! Because INTO must be last... no wait, if INTO must be last, LIMIT can't come after. Unless the rule changed: "As of 7.52, INTO can be specified before LIMIT/OFFSET"? 

I recall the ABAP doc for INTO clause: "The INTO clause must be specified after all other clauses of the SELECT statement... In the strict modes of the syntax check, INTO can also be specified before FROM? no..." 

OK, I'll avoid the ambiguity entirely: use UP TO 10 ROWS in the snippet. Done. Actually hmm, one more option: skip the ABAP-SQL-equivalent snippet's LIMIT entirely and use `UP TO 10 ROWS`. Yes.

Actually, let me reconsider including the ABAP SQL equivalent at all — it's valuable for the "wann lohnt sich AMDP" discussion (showing this task is doable in ABAP SQL). Keep it short with UP TO 10 ROWS.

Now — also think: should the AMDP example include something that ABAP SQL can't do, to justify itself? The user asked specifically for this task with AMDP, so I deliver AMDP, but in the explanation I honestly note that this specific query is also possible in ABAP SQL, and AMDP shines when logic gets more complex (e.g., multi-step: first aggregate per document, then rank, or use of window functions with procedural post-processing, currency conversion via HANA functions, etc.). Good.

Maybe I can make the AMDP example slightly more "AMDP-worthy" by showing a two-step SQLScript (intermediate table variable) — e.g., first aggregate per material+currency into a local table variable, then select top 10 from it. That demonstrates SQLScript's procedural strength (intermediate results) without overcomplicating:

```sql
  -- Zwischenergebnis: Umsatz je Material/Währung
  lt_agg = SELECT vbap.matnr AS matnr,
                  vbap.waerk AS waerk,
                  SUM(vbap.netwr) AS umsatz,
                  SUM(vbap.kwmeng) AS menge
             FROM vbap
             INNER JOIN vbak ON ...
            WHERE ...
            GROUP BY vbap.matnr, vbap.waerk;

  et_top = SELECT matnr, waerk, umsatz, menge
             FROM :lt_agg
            ORDER BY umsatz DESC, matnr
             LIMIT 10;
```

This shows table variables (`lt_agg` declared implicitly by assignment — in SQLScript, `lt_agg = SELECT ...` declares an implicit table variable; referencing via `:lt_agg`). This is nice SQLScript pedagogy. In AMDP, local variables can also be declared with `DECLARE lt_agg TABLE (...)` but implicit assignment is simpler. Note: In AMDP SQLScript, untyped table variables via assignment are allowed. Yes.

I'll include the two-step version — it demonstrates why AMDP/SQLScript is powerful (intermediate results stay in DB) and directly supports the explanation. 

Now, about `ORDER BY umsatz DESC` referencing alias in the second select from :lt_agg — since lt_agg has column umsatz, ordering by umsatz is a real column — no alias issue. 

Also in the second SELECT, `LIMIT 10` after ORDER BY — HANA syntax: SELECT ... FROM :lt_agg ORDER BY umsatz DESC LIMIT 10 — valid (ORDER BY before LIMIT). Yes.

Now, the DDIC structure fields must match the final select list: MATNR, WAERK, UMSATZ, MENGE. Good.

One more AMDP detail: the USING list — `USING vbak vbap` — DDIC tables referenced. Note: names in USING are the DDIC names; in the body you use the same names. Also, if the AMDP body references DDIC views/tables, they must be listed. Correct.

Another detail: AMDP methods and the class: the class must be... "AMDP classes" — the interface IF_AMDP_MARKER_HDB must be implemented; the class should not be abstract? It can be abstract? Whatever — FINAL CREATE PUBLIC is fine.

Also: For AMDP, the method must be implemented in the same class; AMDP methods cannot be redefined/abstract. Fine.

Also note: AMDP requires the ABAP system to be connected to HANA as primary DB (or secondary connection? AMDP runs on the primary HANA DB; "FOR HDB" refers to the primary database). With S/4HANA always HANA. Mention briefly.

Error handling note: CX_AMDP_* exceptions.

Transport/creation: The procedure is generated in the database schema of the ABAP schema at first use; source code is managed by ABAP (ADT). Mention ADT (Eclipse) recommended for AMDP development.

Now, about the client parameter type: `abap.clnt` — hmm, in the DDIC there's also MANDT data element. `TYPE abap.clnt` is the canonical choice from SAP examples. Keep.

Also, should clnt be `VALUE(clnt)`? All AMDP parameters must be VALUE. Yes.

Now let me also double check the AMDP method declaration syntax:

```abap
METHODS get_top_materials
  IMPORTING VALUE(clnt) TYPE abap.clnt
            VALUE(iv_vkorg) TYPE vkorg
  EXPORTING VALUE(et_top) TYPE zsd_tt_top_material.
```

Hmm — for AMDP methods, are EXPORTING parameters allowed to be specified as EXPORTING? Yes. Also could use RETURNING for single scalar; for tables, EXPORTING. OK.

And the implementation header:

```abap
METHOD get_top_materials BY DATABASE PROCEDURE
                         FOR HDB LANGUAGE SQLSCRIPT
                         OPTIONS READ-ONLY
                         USING vbak vbap.
```

Correct order per ABAP docs: `METHOD method BY DATABASE PROCEDURE FOR db LANGUAGE lang [OPTIONS ...] [USING ...].` Yes.

OPTIONS READ-ONLY — valid option. (Other options: DETERMINISTIC? READ-ONLY is the main one.)

Now the SQLScript body with two steps:

```abap
METHOD get_top_materials BY DATABASE PROCEDURE
                         FOR HDB LANGUAGE SQLSCRIPT
                         OPTIONS READ-ONLY
                         USING vbak vbap.

  -- Schritt 1: Umsatz je Material und Währung aggregieren
  lt_agg = SELECT vbap~... 
```

Wait — in SQLScript (HANA), no ABAP-style `~` selector; use `vbap.matnr` with dot. Correct: HANA uses dot notation for table columns: `vbap.matnr`. Yes.

```sql
  lt_agg =
      SELECT vbap.matnr           AS matnr,
             vbap.waerk           AS waerk,
             SUM( vbap.netwr )    AS umsatz,
             SUM( vbap.kwmeng )   AS menge
        FROM vbap
       INNER JOIN vbak
          ON  vbak.mandt = vbap.mandt
          AND vbak.vbeln = vbap.vbeln
       WHERE vbap.mandt = :clnt
         AND vbak.vkorg = :iv_vkorg
         -- optional: AND vbak.vbtyp = 'C'   " nur Aufträge
       GROUP BY vbap.matnr,
                vbap.waerk;

  et_top =
      SELECT matnr,
             waerk,
             umsatz,
             menge
        FROM :lt_agg
       ORDER BY umsatz DESC,
                matnr ASC
       LIMIT 10;

ENDMETHOD.
```

Comments in SQLScript: `--` for line comments and `/* */`. In AMDP, the SQLScript body — comments with `--` are fine. But careful: ABAP parser must tolerate them — yes, AMDP body is passed through; `--` comments are allowed in AMDP sources. Yes.

Hmm, one subtlety: within AMDP, can I use `--` comments? I believe yes (the body is SQLScript). Some early versions had issues with `--` because ABAP editor? No, it's fine. Alternatively use `/* */`. I'll use `--`.

Another subtlety: In AMDP SQLScript, string literals like 'C' — fine.

Also: implicit table variable lt_agg — in AMDP, is implicit declaration via assignment allowed, or must variables be DECLAREd? In SQLScript, `lt_agg = SELECT ...` creates an implicit table variable — allowed in AMDP too. Yes (SAP examples use this pattern). Good.

Now, is `LIMIT 10` allowed in the et_top assignment? Yes.

Potential issue: HANA requires `ORDER BY ... LIMIT` in subquery/assignment context — allowed. Yes.

Now the DDIC prerequisites text:

"Im DDIC (SE11) werden benötigt:
1. Struktur ZSD_S_TOP_MAT mit den Komponenten:
   - MATNR — MATNR — Materialnummer
   - WAERK — WAERS — Währung des Umsatzes
   - UMSATZ — NETWR — Summierter Nettoauftragswert
   - MENGE — KWMENG — Summierte Auftragsmenge
2. Tabellentyp ZSD_TT_TOP_MAT (Standardtabelle) mit Zeilentyp ZSD_S_TOP_MAT."

Hmm — WAERK data element: WAERS. In VBAP, the currency field is WAERK (data element WAERK? The data element for VBAP-WAERK is WAERK? Hmm: VBAP-WAERK has data element WAERK (domain WAERS). The component name in my structure: I'll name the component WAERK with data element WAERS? Data element WAERS exists (currency key). Data element WAERK also exists ("Währungscode des Vertriebsbelegkopfes"? hmm, WAERK is a data element too). To be safe: component WAERK TYPE waers. waers data element definitely exists. Good.

UMSATZ TYPE netwr — NETWR data element exists (CURR). In a DDIC structure, a CURR component without reference currency — allowed in structures? In SE11 structures, currency fields require a reference table only for transparent tables; in structures, you can specify CURR without reference? Hmm — actually, when activating a structure with CURR fields, the DDIC may require a reference field? I believe for structures, the reference table/field is optional (it's needed for tables). Hmm, actually I recall that in structures, CURR/QUAN fields also need a reference field? No — I'm fairly sure structures don't require it (e.g., many demo structures have CURR without reference). Hmm, actually I think the DDIC does NOT enforce reference fields in structures — correct, only transparent tables require reference tables for CURR/QUAN. OK fine.

Alternatively, to avoid any DDIC quirks: define UMSATZ as built-in `p DECIMALS 2 LENGTH 15`? In SE11 you'd use predefined type DEC 15,2? Hmm, CURR is basically DEC with semantics. Using NETWR is more semantic. Keep NETWR, mention "oder p 15,2".

Hmm, actually, maybe simpler: use data element NETWR for UMSATZ and KWMENG for MENGE. Fine.

Now — the class name: ZCL_SD_TOP_MATERIALS or ZCL_VBAP_TOP_MATERIALS. I'll use zcl_sales_top_materials? Let me pick `zcl_sd_top_materials`. Fine.

Now the call example — full mini report:

```abap
REPORT zsd_top_materials.

PARAMETERS p_vkorg TYPE vkorg OBLIGATORY DEFAULT '1010'.

START-OF-SELECTION.

  TRY.
      zcl_sd_top_materials=>get_top_materials(
        EXPORTING
          iv_vkorg = p_vkorg
        IMPORTING
          et_top   = DATA(lt_top) ).   " clnt wird automatisch gefüllt

      cl_demo_output=>display( lt_top ).

    CATCH cx_amdp_error INTO DATA(lx_amdp).
      cl_demo_output=>display( lx_amdp->get_text( ) ).
  ENDTRY.
```

Hmm — CX_AMDP_ERROR: does it exist as a catchable root? CX_AMDP_ERROR is the abstract root class of AMDP exceptions (CX_AMDP_CREATION_ERROR, CX_AMDP_EXECUTION_ERROR, ...). Yes, CX_AMDP_ERROR exists. And since these are dynamic-check? If CX_AMDP_ERROR inherits CX_DYNAMIC_CHECK, catching without RAISING declaration is fine. If it inherits CX_STATIC_CHECK, the syntax check would warn if not declared. Hmm. I believe AMDP exceptions are CX_DYNAMIC_CHECK descendants (DB errors are runtime situations). Let me not over-assert: I'll include TRY...CATCH and note. Actually, to be safe about static check complaints, I could add `RAISING cx_amdp_error` to the method signature? Hmm — is CX_AMDP_ERROR allowed in RAISING of AMDP methods? Sure, any CX_ class can be in RAISING. But adding RAISING changes nothing functionally for dynamic-check exceptions. I'll keep the method signature without RAISING (simpler) and the caller with TRY/CATCH — and if the static check complains (unlikely), it's just a warning. Actually, hmm, let me think: are AMDP exceptions static check? The ABAP doc "AMDP - Exceptions": "Errors in AMDP procedures are raised as exceptions of the classes CX_AMDP_... which inherit from CX_DYNAMIC_CHECK? ..." I believe: CX_AMDP_ERROR inherits from CX_DYNAMIC_CHECK. Yes, I'm fairly confident. So CATCH works without RAISING. Good.

Hmm, but wait: in my call example, `DATA(lt_top)` inline declared in IMPORTING — fine.

Also `cl_demo_output=>display` — fine for demos.

Now, additional explanatory bullets after the code (AMDP specifics):

- IF_AMDP_MARKER_HDB: markiert Klasse als AMDP-Klasse für HANA (HDB). Ohne dieses Interface keine AMDP-Methoden.
- BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT: Implementation ist reines SQLScript — zwischen METHOD und ENDMETHOD ist kein ABAP erlaubt.
- OPTIONS READ-ONLY: Methode nur lesend (empfohlen; erlaubt z. B. Aufruf in bestimmten Kontexten, Optimierung).
- USING vbak vbap: Abhängigkeiten — wichtig für Where-used, Transport/Erzeugung der Prozedur, Löschschutz.
- VALUE-Parameter: AMDP-Parameter immer by value; nur elementare Typen + (DDIC-)Tabellentypen; keine Strings? (skip), keine Strukturen/Referenzen.
- Mandantenbehandlung: Parameter clnt als erster Importing-Parameter → implizite Mandantenbehandlung (wird mit sy-mandt versorgt, im Aufruf nicht angeben). Im Body selbst WHERE mandt = :clnt. Alternative: eigener Parametername → explizit übergeben.
- Erzeugung: Prozedur wird beim ersten Aufruf in der ABAP-Datenbank (Schema SAP<SID>?) erzeugt; Quellcode wird mit der Klasse transportiert; keine manuelle HANA-Entwicklung nötig. ADT/Eclipse empfohlen.
- Fehler: CX_AMDP_*-Ausnahmen.

Then the "wann lohnt sich AMDP" section with the table + Faustregel + the ABAP SQL equivalent.

Also mention: AMDP ist Voraussetzung für CDS-Table-Functions (AMDP function implementations) — ein weiterer Grund.

Also: AMDP allows calling HANA built-in libraries (PAL, AFL), spatial, text search, etc.

Also: performance note — AMDP vs ABAP SQL for the SAME declarative logic: no significant difference; the DB optimizer handles both. The benefit comes from: avoiding multiple round trips, keeping intermediate results in DB, using HANA-only engines.

Also: portability caveat — AMDP only runs on HANA; in S/4HANA that's given, but e.g. for ECC on AnyDB it won't work. Also AMDP can't be used in... hmm.

Also worth noting: authorization checks (AUTHORITY-CHECK) can't run inside AMDP — do them in ABAP before the call. Good practical point.

Also: no implicit client handling unless clnt parameter — already covered.

Length/format: This is a "write code + explain" request. The answer will be moderately long — that's appropriate. Use German. Headers (###), code blocks (```abap), a table for the comparison, bullets. Keep prose tight.

Let me also double-check the SQLScript for correctness details:

- `SUM( vbap.netwr )` — NETWR is CURR(15,2)? stored as DEC — SUM fine.
- GROUP BY vbap.matnr, vbap.waerk — fine.
- Join VBAK-VBELN = VBAP-VBELN — fine.
- Filter: VBAK.VKORG = :iv_vkorg — parameter type vkorg (CHAR 4). Fine.
- LIMIT 10.

Edge: material numbers with leading zeros — fine.

One more consideration: Should the aggregate be based on NETWR (net value) — "Umsatz" from order data is really "Auftragswert" (net value of orders). I'll note: "Streng genommen ist das der Nettoauftragswert (NETWR), nicht der fakturierte Umsatz — der stünde in VBRK/VBRP. Für das Beispiel bleiben wir bei VBAP/VBAK." Good expert note, one line.

Now, about the implicit client handling claim — let me do a final sanity check because it's central to my code. Search memory: "AMDP clnt abap.clnt implicit client handling" ... I recall SAP Community threads: "For implicit client handling in AMDP, the first importing parameter must be named CLNT and typed with ABAP.CLNT. The caller must not pass this parameter; the AMDP runtime fills it with the current client." Hmm — actually wait, I now recall a CONTRARY memory: some threads say for AMDP methods you DO pass the client explicitly and implicit client handling means something else (that the AMDP framework sets the session variable CDS_CLIENT so that the body could use it)... 

Hmm. Let me think really carefully. There are two mechanisms:

1. CDS table functions: implemented by AMDP function implementations. The CDS table function has a parameter clnt (first parameter, type abap.clnt). When the table function is used in ABAP SQL, the client is passed automatically. In the AMDP function implementation, the method must have matching parameters including clnt. This is clear.

2. AMDP methods (procedures called directly from ABAP): The ABAP doc "AMDP - Client Handling" — I recall the text now with higher confidence:

"AMDP methods: For AMDP methods, implicit client handling is switched on by declaring a mandatory input parameter clnt as first input parameter of the method. The parameter must be typed with abap.clnt or with a data element whose... When the method is called, the current client is passed automatically to the parameter clnt. The parameter clnt cannot be specified explicitly in the method call. In the procedure body, the parameter clnt must be used in the WHERE conditions..."

Hmm, and I also recall a doc example where the call omits clnt. For instance, the ABAP doc example for "sql_ama" (AMDP methods) — CL_DEMO_AMDP... the demo report calls:

```abap
cl_demo_amdp=>get_scarr( IMPORTING carriers = DATA(carriers) ).
```

Hmm... I really do believe the clnt is auto-supplied. Additional support: The ABAP doc for AMDP methods states: "An AMDP method with implicit client handling cannot have the parameter clnt specified in the method call." — and the syntax check produces an error if you try: "Parameter CLNT is supplied implicitly and cannot be filled" or similar.

Hmm, also I recall Horst Keller's blog "AMDP – ABAP Managed Database Procedures" (2013-ish, before implicit client handling) where the client was passed explicitly. The implicit client handling for AMDP methods came later (7.40 SP08, 2015?) together with CDS table functions. 

I'm going with it: implicit client handling, clnt not passed in the call. And I'll explicitly document this behavior in a bullet so even if a reader's release differs, they understand and can adapt (fallback: rename parameter → explicit passing). This is the best balance.

Hmm, wait, actually — one more consideration. Let me reconsider: is it possible that for AMDP methods, the clnt parameter is auto-filled ONLY if... the method is called via the AMDP framework (which it always is)? Yes, AMDP methods are always called via the AMDP framework (the ABAP runtime intercepts the call). So auto-fill is feasible. OK.

Also note: with implicit client handling, the AMDP framework also sets the HANA session variable CDS_CLIENT for the procedure call — I believe yes. Not needed for the example.

Now — one more syntax check on the class definition: For AMDP methods in the class definition, do I need anything special in the declaration besides the parameter typing? No — the AMDP part appears only in the implementation (METHOD ... BY DATABASE PROCEDURE ...). The declaration is a normal method declaration with VALUE parameters. Correct.

But: the parameter TYPES must satisfy AMDP rules at declaration time (syntax check validates). OK.

Also: Can EXPORTING parameters be optional? Not needed.

Also: the class must be activated with ADT; AMDP development requires Eclipse (ADT) — SE80/SE24 can display but not edit AMDP method bodies? Correct: AMDP methods can only be edited in ADT (Eclipse). Worth a note.

Now let me also think about whether to include `CREATE PUBLIC` / `FINAL` — fine.

Also: should I show `PUBLIC SECTION` only — yes, keep minimal.

Now write the "wann lohnt sich AMDP" section properly. Content:

**Wann AMDP gegenüber ABAP SQL lohnt**

Grundregel: Sofern sich eine Aufgabe in (möglichst einer) deklarativen ABAP-SQL-Anweisung bzw. CDS-View ausdrücken lässt → ABAP SQL verwenden. AMDP ist kein generischer Performance-Turbo, sondern für Fälle, die ABAP SQL nicht abdecken kann:

Lohnt sich:
1. **Mehrschrittige, prozedurale Logik mit Zwischenergebnissen**: SQLScript erlaubt Tabellenvariablen, IF/WHILE, mehrere Schritte — alles bleibt in einem DB-Aufruf in der DB. In ABAP SQL müssten Zwischenergebnisse auf den Applikationsserver transportiert werden (Roundtrips, Speicher).
2. **HANA-spezifische Funktionen**, die ABAP SQL nicht bietet: Text-/Fuzzy-Search, Spatial, Predictive Analysis Library (PAL/AFL), Graph, Serien/Zeitreihen, eigene HANA-UDFs/Bibliotheken, HIERARCHY-Funktionen? (hierarchy functions are in ABAP SQL now via HIERARCHY... skip), FULLTEXT, etc.
3. **CDS-Table-Functions**: AMDP-Funktionsimplementierungen sind die einzige Möglichkeit, CDS-Table-Functions zu implementieren (parametrisierte, in ABAP SQL/CDS nutzbare "Views mit Logik").
4. **Wiederverwendung/Komposition**: Prozeduren können andere Prozeduren aufrufen; Ergebnisstrukturen... 
5. **Sehr komplexe Transformationen großer Datenmengen**, die deklarativ nicht (oder nur sehr umständlich mit riesigen JOINs/Subqueries) formulierbar sind.

Lohnt sich eher nicht:
- Einfache Selektionen/Joins/Aggregate/Window Functions → ABAP SQL ist äquivalent schnell, lesbarer, portabler, sicherer (automatische Mandantenbehandlung, Syntaxprüfung zur Kompilierzeit, CDS-Integration/DCL, Autorisierungen).
- Portabilität: AMDP läuft nur auf HANA (FOR HDB). In S/4HANA unkritisch, sonst schon.
- Wartbarkeit: SQLScript ist für den ABAP-Developer eine Blackbox; Fehler treten oft erst zur Laufzeit (Prozedurerzeugung), Debugging nur mit HANA-Tools; keine ABAP-Werkzeuge (Where-used nur über USING-Liste).
- Mandantenbehandlung/Autorisierungsprüfungen müssen explizit (clnt-Parameter / AUTHORITY-CHECK im ABAP) erfolgen.

Faustregel: "ABAP SQL first" — CDS/ABAP SQL für den Standardfall, AMDP gezielt für Pushdown, den ABAP SQL nicht hinbekommt. Performance kommt von der richtigen Verlagerung von Datenlogik in die DB, nicht vom Werkzeug: dieselbe deklarative Logik ist in ABAP SQL und AMDP ähnlich schnell.

Table (compact):

| Kriterium | ABAP SQL / CDS | AMDP (SQLScript) |
|---|---|---|
| Datenbank | beliebig | nur HANA |
| Deklarative Abfragen | ✔ voll | ✔ |
| Prozedurale Logik / Zwischenergebnisse in der DB | ✘ | ✔ |
| HANA-Spezialfunktionen (Text, Spatial, PAL, …) | ✘/teilweise | ✔ |
| Syntaxprüfung / Tooling | stark | eingeschränkt (ADT, Fehler oft zur Laufzeit) |
| Mandantenbehandlung | automatisch | manuell (clnt-Parameter) |
| CDS-Integration (DCL, VDM) | ✔ | ✘ |

Then the ABAP SQL equivalent snippet to show this task doesn't strictly need AMDP:

```abap
SELECT UP TO 10 ROWS vbap~matnr, vbap~waerk,
       SUM( vbap~netwr ) AS umsatz, SUM( vbap~kwmeng ) AS menge
  FROM vbap
  INNER JOIN vbak ON vbak~vbeln = vbap~vbeln
 WHERE vbak~vkorg = @iv_vkorg
 GROUP BY vbap~matnr, vbap~waerk
 ORDER BY umsatz DESC
 INTO TABLE @DATA(lt_top).
```

Hmm — ORDER BY alias `umsatz` in ABAP SQL: I said I'm fairly confident it works. Let me double-check: ABAP SQL ORDER BY — from ABAP docs: "After ORDER BY, you can specify: columns of the FROM clause? ... " Hmm. Historically (before 7.40), ORDER BY could specify column names from the database tables or positions? ABAP SQL ORDER BY: "ORDER BY {col1, col2...} | {PRIMARY KEY}" — the columns could be columns of the data source. With the new syntax, aliases... I recall the doc "SELECT, ORDER BY": "sql_exp: SQL expressions can be specified... The alias names of the SELECT list can be used"? 

Hmm, I have genuine uncertainty. Let me think of concrete known-working code: In many modern ABAP examples:

```abap
SELECT carrid, connid, SUM( seatsocc ) AS seats
  FROM sflight
  GROUP BY carrid, connid
  ORDER BY seats DESC
  INTO TABLE @DATA(r).
```

I'm quite sure I've seen this exact pattern in ABAP docs/blogs and it works. Actually — hmm, I recall there IS a restriction: "Aggregate expressions and aliases in ORDER BY are only allowed..."? I recall that in ABAP SQL, ORDER BY can reference the alias of an aggregate — yes, e.g., the doc example for GROUP BY: 

```abap
SELECT carrid, SUM( paymentsum ) AS sum_paymentsum
  FROM sflight
  GROUP BY carrid
  ORDER BY sum_paymentsum DESC? 
```

Hmm. Alternatively, avoid the risk: `ORDER BY SUM( vbap~netwr ) DESC`? Is an aggregate expression allowed directly in ORDER BY? I believe ABAP SQL allows aggregate expressions in ORDER BY if they also appear in SELECT list? Hmm.

Safest of all: avoid the issue — since I control the snippet, I can order by the alias and if unsure, note nothing. OR restructure: since I'm unsure, use the safest well-known form. What IS 100% safe in ABAP SQL? `ORDER BY` with column names of data sources — but for aggregates there's no source column. Positions? Not supported in ABAP SQL I think.

OK let me settle this with stronger memory: ABAP Keyword Documentation, "SELECT, ORDER BY": 

"ORDER BY ... lets you specify:
- Columns: col1, col2 ... — either as columns of the data source or as alias names of the SELECT list? ...
- SQL expressions: as of 7.4x? 'If the SELECT list contains aggregate expressions, they can be specified in ORDER BY'..."

I now recall specifically: "Aggregate expressions can be specified after ORDER BY only if they are also specified in the SELECT list" — and alias names: "The alias names defined in the SELECT list can be specified after ORDER BY." Hmm, I think both are true in modern ABAP SQL. I've personally seen `ORDER BY sum_price DESC` work. Going with alias. If someone's on a very old release, the whole comma-syntax snippet wouldn't work anyway.

Hmm, actually — you know what, I just remembered something concrete: The ABAP doc example for "SELECT, GROUP BY" includes:

```abap
SELECT carrid, connid, SUM( seatsocc ) AS seatsocc
       FROM sflight
       GROUP BY carrid, connid
       ORDER BY seatsocc DESC? 
```

I can't verify, but I'll go with alias — high confidence.

And `UP TO 10 ROWS` placement: `SELECT UP TO 10 ROWS vbap~matnr, ...` — hmm wait, with the comma syntax and INTO at the end: `SELECT UP TO 10 ROWS matnr, ... FROM ... WHERE ... GROUP BY ... ORDER BY ... INTO TABLE @DATA(...).` — UP TO n ROWS after SELECT keyword, before select list. Valid. Yes.

Hmm, but actually — with UP TO + GROUP BY + ORDER BY: allowed? UP TO n ROWS with GROUP BY: yes, allowed (limits result rows after grouping). OK.

Alternatively use LIMIT 10 — I'll mention "(ab Release 7.52 auch LIMIT 10 statt UP TO 10 ROWS)" — hmm, is LIMIT 7.52? I believe LIMIT/OFFSET in ABAP SQL came with 7.52. Let me just say "in neueren Releases auch LIMIT". Or omit. I'll add a brief parenthetical.

Now — one more thing about the AMDP example: the user asked "Top-10-Materialien nach Umsatz aus VBAP/VBAK". My solution groups by material AND currency. If I want strictly "top 10 materials", maybe I should present the simple version (group by matnr only) as primary and mention currency as caveat? Hmm. If I group by matnr only, I can't select waerk directly. Options: omit waerk from output entirely. Then the DDIC structure is MATNR, UMSATZ, MENGE. Cleaner semantics ("Top 10 Materialien nach Umsatz"), and I add a note: "Achtung: NETWR ist währungsabhängig; summiert über verschiedene Währungen hinweg ist der Wert nur informativ. In der Praxis entweder nach Währung gruppieren, in eine einheitliche Währung umrechnen (HANA CONVERT_CURRENCY) oder pro Währung auswerten."

Hmm, which is better pedagogically? Including WAERK in GROUP BY is technically more correct but muddies "top 10 materials". I'll go with group by matnr + waerk in the code (correct), and explain: "Gruppierung nach Material UND Währung, weil NETWR betraglich nur innerhalb einer Währung sinnvoll summierbar ist. Läuft in der VKORG konsequent eine Währung (oft so), kann WAERK entfallen." Hmm, but then the result could contain e.g. MATNR X twice (EUR + USD) and the "top 10 materials" becomes "top 10 material/currency combos". 

Alternatively: group by matnr only and use MAX(waerk) AS waerk? Ugly.

Decision: I'll keep WAERK in the group by and output, with the explanatory note. It demonstrates good data understanding. Actually hmm, wait — let me reconsider once more. The user's ask: "Top-10-Materialien nach Umsatz". Simplest faithful implementation: sum NETWR per MATNR, top 10. The currency issue is a real-world caveat worth a note. If I include waerk in the group by, the result is arguably NOT what was asked (could be >10 materials or duplicates). 

Better: primary solution groups by MATNR only, output MATNR, UMSATZ, MENGE. Note the currency caveat with options. This is cleaner and matches the ask. But then in the two-step SQLScript, step 1 groups by matnr. Fine.

Hmm, but including waerk shows more realistic thinking... I'll go with MATNR-only grouping + explicit caveat note. Simpler code, matches the requirement, caveat documented. 

Wait, but actually — one could argue that within one sales organization (VKORG), the document currency is usually the local/company currency but sales orders can be in any currency (customer abroad → USD). So the caveat is real. Note it.

Final structure of the result structure: ZSD_S_TOP_MAT with MATNR, UMSATZ, MENGE. Hmm, should I include MENGE? "Top-10 nach Umsatz" — menge is bonus context. Keep it (shows SUM of KWMENG). Or drop to keep minimal? Keep — 3 components, fine.

Hmm, actually, let me reconsider including WAERK once more... No. Final: MATNR, UMSATZ, MENGE. Note about currency.

Now the SQLScript body (two-step):

```sql
  -- Schritt 1: Auftragswert (NETWR) je Material aggregieren
  lt_agg =
      SELECT vbap.matnr         AS matnr,
             SUM( vbap.netwr )  AS umsatz,
             SUM( vbap.kwmeng ) AS menge
        FROM vbap
        INNER JOIN vbak
           ON  vbak.mandt = vbap.mandt
          AND vbak.vbeln = vbap.vbeln
       WHERE vbap.mandt = :clnt
         AND vbak.vkorg = :iv_vkorg
         -- optional: AND vbak.vbtyp = 'C'   -- nur Aufträge
       GROUP BY vbap.matnr;

  -- Schritt 2: Top 10 ermitteln
  et_top =
      SELECT matnr, umsatz, menge
        FROM :lt_agg
       ORDER BY umsatz DESC,
                matnr
       LIMIT 10;
```

Good. Note: `--` comments inside AMDP SQLScript — OK.

Hmm, one thing: in AMDP SQLScript, is `vbap.matnr` correct, or should it be `"VBAP"."MATNR"`? In AMDP, DDIC tables are exposed in the ABAP database schema with their names; unquoted lowercase identifiers are uppercased by HANA → VBAK/VBAP columns found. Standard AMDP examples use e.g. `sflight.carrid`. Good.

Also: the AMDP procedure is created in the ABAP schema, and vbak/vbap are synonyms/objects in that schema — the AMDP framework handles it. Fine.

Now, also mention: the method must be implemented in a global class; editing requires ADT (Eclipse). 

Let me also double check `OPTIONS READ-ONLY` implications: read-only AMDP can only contain read-only SQL (no INSERT/UPDATE/DDL), can't call non-read-only procedures. Good for our use. Also, read-only AMDP methods... there's a benefit: they can be used in... hmm, READ-ONLY is also required for AMDP methods called during e.g. ... whatever, just recommend it.

One more AMDP rule: AMDP methods cannot use... "The AMDP method must not be a... " also: AMDP methods can't have RETURNING parameters with tables? RETURNING must be a single value — tables allowed in RETURNING? For AMDP, RETURNING parameter must be elementary? Hmm — AMDP methods support RETURNING? I think AMDP methods support IMPORTING/EXPORTING/CHANGING/RETURNING with the type restrictions; RETURNING must be fully typed, could be a table? For safety I use EXPORTING. Fine.

Also: CHANGING parameters allowed in AMDP? I believe yes (tables). Not needed.

Now, the explanation bullets — let me also include a short "So funktioniert AMDP unter der Haube" (2-3 bullets): 
- Beim ersten Aufruf erzeugt die AMDP-Laufzeit die Prozedur CREATE PROCEDURE im ABAP-Schema der HANA-DB; der SQLScript-Quelltext wird mit der Klasse versioniert/transportiert (kein separates HANA-Deployment).
- Parameter werden gemappt (elementar ↔ Skalare, Tabellentyp ↔ Tabellenparameter).
- USING-Liste definiert Abhängigkeiten → Where-used list, Löschschutz, Neuerzeugung bei Änderungen.

OK. Also the note about ADT: "AMDP-Methoden können nur in ADT (Eclipse) gepflegt werden."

Now assemble the final answer in German. Structure:

# or ### headers. Let me draft:

---

## Voraussetzungen im DDIC

Kurz: AMDP-Parameter für Tabellen müssen mit Tabellentypen getypt sein, deren Zeilentyp eine flache DDIC-Struktur ist. Also:

- Struktur `ZSD_S_TOP_MAT`: MATNR (Datenelement MATNR), UMSATZ (NETWR), MENGE (KWMENG)
- Tabellentyp `ZSD_TT_TOP_MAT` (Standardtabelle, Zeilentyp ZSD_S_TOP_MAT)

(Hinweis: je nach Release gehen auch lokale Typen — DDIC ist die sichere Variante.)

## Die AMDP-Klasse

```abap
CLASS zcl_sd_top_materials DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC.

  PUBLIC SECTION.

    " Marker-Interface: macht die Klasse zur AMDP-Klasse für HANA (HDB)
    INTERFACES if_amdp_marker_hdb.

    CLASS-METHODS get_top_materials
      " Erster Parameter 'clnt' => implizite Mandantenbehandlung:
      " wird beim Aufruf automatisch mit sy-mandt versorgt und darf
      " im Aufruf NICHT übergeben werden.
      IMPORTING VALUE(clnt)     TYPE abap.clnt
                VALUE(iv_vkorg) TYPE vkorg
      " AMDP-Parameter immer 'by value'!
      EXPORTING VALUE(et_top)   TYPE zsd_tt_top_mat.

ENDCLASS.


CLASS zcl_sd_top_materials IMPLEMENTATION.

  METHOD get_top_materials BY DATABASE PROCEDURE
                           FOR HDB LANGUAGE SQLSCRIPT
                           OPTIONS READ-ONLY
                           USING vbak vbap.

    -- Schritt 1: Nettoauftragswert je Material aggregieren
    lt_agg =
      SELECT vbap.matnr         AS matnr,
             SUM( vbap.netwr )  AS umsatz,
             SUM( vbap.kwmeng ) AS menge
        FROM vbap
       INNER JOIN vbak
          ON  vbak.mandt = vbap.mandt
         AND vbak.vbeln  = vbap.vbeln
       WHERE vbap.mandt = :clnt
         AND vbak.vkorg = :iv_vkorg
         -- AND vbak.vbtyp = 'C'   " optional: nur Aufträge
       GROUP BY vbap.matnr;

    -- Schritt 2: Top 10
    et_top =
      SELECT matnr, umsatz, menge
        FROM :lt_agg
       ORDER BY umsatz DESC,
                matnr
       LIMIT 10;

  ENDMETHOD.

ENDCLASS.
```

Wait — mixing `--` comments: the comment `-- AND vbak.vbtyp = 'C'   " optional...` uses ABAP-style `"` comment inside SQLScript — NO! Inside SQLScript, `"` is not a comment (in HANA SQL, double quotes are identifiers!). Must use `--` or `/* */` only. Fix: `-- AND vbak.vbtyp = 'C'   -- optional: nur Aufträge`. Careful — good catch. All comments in the body must be SQLScript comments (`--` or `/* */`). I'll make sure.

## Aufruf aus ABAP

```abap
REPORT zsd_top_materials_demo.

PARAMETERS p_vkorg TYPE vkorg OBLIGATORY DEFAULT '1010'.

START-OF-SELECTION.

  TRY.
      zcl_sd_top_materials=>get_top_materials(
        EXPORTING iv_vkorg = p_vkorg          " clnt entfällt: implizite Mandantenbehandlung
        IMPORTING et_top   = DATA(lt_top) ).

      cl_demo_output=>write( lt_top ).
      cl_demo_output=>display( ).

    CATCH cx_amdp_error INTO DATA(lx_amdp).
      cl_demo_output=>display( lx_amdp->get_text( ) ).
  ENDTRY.
```

Hmm, cl_demo_output usage: `cl_demo_output=>display( lt_top )` directly is simpler. Use that.

Also note: if the release doesn't support implicit client handling → rename clnt to iv_mandt and pass sy-mandt.

## Was der Code im Einzelnen macht / AMDP-Bausteine

Bullets:
- IF_AMDP_MARKER_HDB ...
- BY DATABASE PROCEDURE FOR HDB LANGUAGE SQLSCRIPT ...
- OPTIONS READ-ONLY ...
- USING ...
- VALUE ...
- clnt / Mandanten

</details>
