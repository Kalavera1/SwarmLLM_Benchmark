# ABAP: rap

## Aufgabe

Skizziere ein RAP-Business-Objekt (managed, mit Draft) für eine einfache Reisekosten-Abrechnung: Tabelle, CDS-Root-View, Behavior Definition mit Validation (Betrag > 0), Determination (Status bei Anlage = 'O'), einer Action 'approve' und der zugehörigen Behavior-Implementation-Klasse. Nur die wesentlichen Codeteile.

## Antwort



---

<details><summary>Denkprozess (33022 Zeichen)</summary>

The user is asking in German for a sketch of a RAP Business Object (RESTful Application Programming Model) for a simple travel expense report (Reisekosten-Abrechnung). They want:
- managed scenario with Draft
- Table (database table)
- CDS root view
- Behavior Definition with:
  - Validation (amount > 0)
  - Determination (status on create = 'O' — probably 'O' for "Open")
  - Action 'approve'
- Behavior implementation class
- Only essential code parts

This is a technical ABAP RAP question. I should respond in German since the question is in German. Let me write out the essential code parts.

Let me structure this:

1. **Database table** (ZRK_ABRECHNUNG or similar)
```abap
@EndUserText.label : 'Reisekostenabrechnung'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #RESTRICTED
define table zrk_abrechnung {
  key client            : abap.clnt not null;
  key reise_id          : sysuuid_x16 not null;
  mitarbeiter           : abap.char(12);
  reisezweck            : abap.char(80);
  betrag                : abap.dec(15,2);
  waehrung              : abap.cuky;
  status                : abap.char(1);
  created_at            : timestampl;
  created_by            : abap.char(12);
  last_changed_at       : timestampl;
  last_changed_by       : abap.char(12);
  local_last_changed_at : timestampl;
}
```

2. **CDS Root View** (with draft)
```abap
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Reisekostenabrechnung'
@Metadata.allowExtensions: true
define root view entity ZRK_C_Abrechnung
  as select from zrk_abrechnung
{
  key reise_id            as ReiseId,
      mitarbeiter         as Mitarbeiter,
      reisezweck          as Reisezweck,
      betrag              as Betrag,
      waehrung            as Waehrung,
      status              as Status,
      @Semantics.systemDateTime.lastChangedAt: true
      last_changed_at     as LastChangedAt,
      @Semantics.systemDateTime.localInstanceLastChangedAt: true
      local_last_changed_at as LocalLastChangedAt
}
```

Wait, for draft you need the draft table and the view needs to be draft-enabled. The draft enablement is defined in the behavior definition, not in the CDS view itself (in newer releases). Actually the `@Metadata.allowExtensions: true` is for metadata extensions. For draft, the BDEF defines `draft table zrk_abrechn_d`.

3. **Behavior Definition**
```
managed implementation in class zbp_rk_abrechnung unique;
strict ( 2 );
with draft;

define behavior for ZRK_C_Abrechnung alias Abrechnung
persistent table zrk_abrechnung
draft table zrk_abrechn_d
etag master LocalLastChangedAt
lock master total etag LastChangedAt
authorization master ( instance )
{
  create;
  update;
  delete;

  draft action Edit;
  draft action Activate optimized;
  draft action Discard;
  draft action Resume;
  draft determine action Prepare;

  field ( readonly ) ReiseId, Status;
  field ( mandatory ) Betrag, Mitarbeiter;

  determination setStatusOnCreate on modify { create; }
  validation validateBetrag on save { field Betrag; }

  action ( features : instance ) approve result [1] $self;

  mapping for zrk_abrechnung
  {
    ReiseId = reise_id;
    Mitarbeiter = mitarbeiter;
    Reisezweck = reisezweck;
    Betrag = betrag;
    Waehrung = waehrung;
    Status = status;
    ...
  }
}
```

4. **Behavior Implementation Class**

```abap
CLASS lhc_abrechnung DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PRIVATE SECTION.
    METHODS get_instance_features FOR INSTANCE FEATURES
      IMPORTING keys REQUEST requested_features FOR Abrechnung RESULT result.

    METHODS validateBetrag FOR VALIDATE ON SAVE
      IMPORTING keys FOR Abrechnung~validateBetrag.

    METHODS setStatusOnCreate FOR DETERMINE ON MODIFY
      IMPORTING keys FOR Abrechnung~setStatusOnCreate.

    METHODS approve FOR MODIFY
      IMPORTING keys FOR ACTION Abrechnung~approve RESULT result.
ENDCLASS.

CLASS lhc_abrechnung IMPLEMENTATION.

  METHOD approve.
    " Status auf 'A' (genehmigt) setzen
    MODIFY ENTITIES OF zrk_c_abrechnung IN LOCAL MODE
      ENTITY Abrechnung
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR key IN keys ( %tky = key-%tky
                                        Status = 'A' ) )
      MAPPED DATA(mapped)
      FAILED DATA(failed)
      REPORTED DATA(reported).

    READ ENTITIES OF zrk_c_abrechnung IN LOCAL MODE
      ENTITY Abrechnung
        ALL FIELDS WITH CORRESPONDING #( keys )
      RESULT DATA(abrechnungen).

    result = VALUE #( FOR abr IN abrechnungen
                      ( %tky = abr-%tky
                        %param = abr ) ).
  ENDMETHOD.

  METHOD validateBetrag.
    READ ENTITIES OF zrk_c_abrechnung IN LOCAL MODE
      ENTITY Abrechnung
        FIELDS ( Betrag ) WITH CORRESPONDING #( keys )
      RESULT DATA(abrechnungen).

    LOOP AT abrechnungen INTO DATA(abr).
      IF abr-Betrag IS INITIAL OR abr-Betrag <= 0.
        APPEND VALUE #( %tky = abr-%tky ) TO failed-abrechnung.
        APPEND VALUE #( %tky = abr-%tky
                        %msg = new_message_with_text(
                                 severity = if_abap_behv_message=>severity-error
                                 text = 'Betrag muss größer 0 sein' )
                        %element-Betrag = if_abap_behv=>mk-on ) TO reported-abrechnung.
      ENDIF.
    ENDLOOP.
  ENDMETHOD.

  METHOD setStatusOnCreate.
    MODIFY ENTITIES OF zrk_c_abrechnung IN LOCAL MODE
      ENTITY Abrechnung
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR key IN keys ( %tky = key-%tky
                                        Status = 'O' ) ).
  ENDMETHOD.

  METHOD get_instance_features.
    READ ENTITIES OF zrk_c_abrechnung IN LOCAL MODE
      ENTITY Abrechnung
        FIELDS ( Status ) WITH CORRESPONDING #( keys )
      RESULT DATA(abrechnungen).

    result = VALUE #( FOR abr IN abrechnungen
                      ( %tky = abr-%tky
                        %action-approve = COND #( WHEN abr-Status = 'O'
                                                  THEN if_abap_behv=>fc-o-enabled
                                                  ELSE if_abap_behv=>fc-o-disabled ) ) ).
  ENDMETHOD.

ENDCLASS.
```

Also need the class definition wrapper:
```abap
CLASS zbp_rk_abrechnung DEFINITION PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF zrk_c_abrechnung.
ENDCLASS.

CLASS zbp_rk_abrechnung IMPLEMENTATION.
ENDCLASS.
```

And the local handler class (lhc_...) goes in the CCIMP (local types) of the behavior implementation class.

Also the draft table:
```abap
@EndUserText.label : 'Reisekostenabrechnung - Draft'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
define table zrk_abrechn_d {
  key mandt      : mandt not null;
  key reise_id   : sysuuid_x16 not null;
  ...same fields...
  "%admin"
  include sych_bdl_draft_admin_inc;
}
```

Actually the draft table includes the same fields plus `include sych_bdl_draft_admin_inc;` and `draftentityoperationcode`, etc. The standard is:

```abap
define table zrk_abrechn_d {
  key client     : abap.clnt not null;
  key reise_id   : sysuuid_x16 not null;
  mitarbeiter    : abap.char(12);
  ...
  "%admin"
  include sych_bdl_draft_admin_inc;
}
```

Also a message class might be needed for the validation, but I can use new_message_with_text for simplicity.

Let me also think about naming conventions. Common pattern: ZI_ or ZC_ or ZRK_C_. For managed BOs, the root view often named ZI_Travel (interface view) or ZC_ (consumption). Since they asked for "CDS-Root-View", I'll use one view to keep it simple — ZRK_C_REISEKOSTEN or ZI_Reisekosten. Let me use `ZRK_C_Reisekosten` or simpler: `ZI_REISEKOSTEN`. I'll go with `ZRK_C_REISEABRECHNUNG` — hmm, keep it short: `ZI_REISEKOSTEN`. Actually let me use consistent naming:

- Table: `zreisekosten` or `zrk_abrechnung`
- Draft table: `zrk_abrechn_d`
- CDS view: `ZRK_C_Abrechnung` (root view entity)
- BDEF: `ZRK_C_Abrechnung`
- Behavior impl class: `zbp_rk_abrechnung`

Status codes: 'O' = Open (neu/offen), 'A' = Approved (genehmigt). The user said status at creation = 'O', so 'O' likely means "Offen".

Let me also mention the field ( readonly ) for Status — since the determination sets it, it should probably be readonly: `field ( readonly ) Status;` — but then the determination can still modify it in local mode. Yes, that's the standard pattern.

Also note: `strict(2)` requires draft actions to be explicitly listed. With `strict ( 2 )` and draft, you must define draft actions Edit, Activate, Discard, Resume, and draft determine action Prepare.

Let me also add the `authorization master ( instance )` — actually to keep it minimal, maybe skip authorization. The user said "nur die wesentlichen Codeteile" (only essential code parts). So keep it lean but complete enough to be correct.

For the mapping, it's needed for managed BOs with persistent table. I'll include a compact mapping.

Let me think about the total etag / lock master. For draft:
```
lock master total etag LastChangedAt
```
and
```
etag master LocalLastChangedAt
```

That's standard.

Now the validation: `validation validateBetrag on save { field Betrag; }` — with create; implied? In strict mode, `on save { create; field Betrag; }` — actually validations trigger on save for the specified operations. The syntax: `validation validateBetrag ON SAVE { FIELD Betrag; }` — this triggers whenever the field Betrag is changed and on create. Actually to be precise: a validation on save with `field Betrag` triggers when the field is modified; to also trigger on create you may need `create;` in the trigger list? Let me recall: 

Syntax: `validation ... on save { field <fields>; create; }` — Hmm. In RAP BDL, the trigger operations for validations: `on save { field f1; create; }` — yes, you can list `create` as a trigger. Actually the standard is: `validation validateBetrag on save { field Betrag; }` — the validation is executed when the specified fields are changed. On create, all fields are "changed", so it triggers on create too. Hmm, is that right?

From SAP documentation: "A validation is executed ... if the specified fields are included in the operations' fields". For create operations, the fields are part of the create, so the validation triggers. Actually, I recall that for create you may explicitly add `create;`. Let me check: In the RAP BDL docs, validation trigger: `on save { field; create; }` — I've seen examples like:

```
validation validateCustomer on save { field CustomerId; create; }
```

Hmm, actually I believe the syntax allows `create` and `update` as triggers. From SAP: `validation Valid_... on save { create; field FieldName; }`. Yes, that's valid. Many SAP examples include `create;` explicitly. To be safe I'll write `on save { create; field Betrag; }`. Hmm wait — actually I need to double check. The BDL syntax for validations:

```
validation <name> on save { <trigger_operations> }
```
where trigger operations can be `create`, `update`, `delete`, `field <f>`. 

From SAP docs example:
```
validation validateTravel on save { create; field TravelID; }
```
Hmm, I've definitely seen `{ field BeginDate; }` alone. The default: "If no trigger operation is specified, the validation is executed for all operations"? No...

Let me recall the actual BDL grammar: 

```
validation ValidationName on save { field1; field2; create; }
```

I believe both field triggers and create/update triggers can be listed. In the ABAP RAP examples from SAP (e.g., RAP100), the validation is:

```
validation validateTravel on save { create; field TravelID; field BeginDate; field EndDate; }
```

Hmm, actually in RAP100 it's:
```
validation validateTravel on save { field TravelID; field BeginDate; field EndDate; }
```

Hmm. Let me think about what's correct. From the ABAP Keyword Documentation (BDL - VALIDATION):

> `validation ... on save { field ...; create; }` — The validation is executed ... when the specified fields are modified. 

The doc says: Trigger operation options: `create`, `update`, `field`. If `create` is specified, validation runs on create operations. Fields specified trigger on modify of those fields. I'm fairly confident `create;` can be listed. In many SAP tutorials (e.g., "Develop a RAP business service"), they write:

```
validation validateStatus on save { create; field Status; }
```

Hmm, actually I recall the determination syntax: `determination setStatus on modify { create; }` — that's definitely valid, create as trigger for determinations. For validations, similar. I'll include `create; field Betrag;` to be safe — it's valid syntax and ensures the validation runs on create.

Wait, actually — for determinations on modify: `determination setStatusOnCreate on modify { create; }` — yes, that's the standard trigger for "on create".

For the determination, the user wants "Status bei Anlage = 'O'" (status on creation = 'O'). So `determination setStatusOnCreate on modify { create; }`.

Implementation: in the determination, MODIFY ENTITIES ... IN LOCAL MODE UPDATE FIELDS ( Status ) WITH VALUE #( FOR key IN keys ( %tky = key-%tky Status = 'O' ) ). Note: since Status is readonly, we need LOCAL MODE. Yes.

For the action approve: set status to 'A' (approved). Also add feature control: only enabled when status = 'O'. The user asked for "einer Action 'approve'" — feature control is optional but nice. I'll include it briefly since it's common practice, but keep it compact. Actually "nur die wesentlichen Codeteile" — maybe include the feature control as it's a one-liner in BDEF plus a method. I'll include it but keep it short. Hmm, it adds a method get_instance_features. It's good practice. I'll include it briefly.

Alternatively, skip feature control to keep minimal. I think including it makes the sketch more realistic and it's only a few lines. I'll include it.

Message class: For the validation, use `new_message_with_text` to avoid needing a message class. Or use a message class with `%msg = new_message( id = 'ZRK_MSG' number = '001' severity = ... )`. new_message_with_text is simpler for a sketch.

Let me also remember: in the validation, append to `failed-abrechnung` and `reported-abrechnung`. The alias name is used: `failed-Abrechnung`. The derived types: `failed-late_numbering` etc. With alias `Abrechnung`, the components are `failed-abrechnung` (lowercase alias). In ABAP, component names in the derived structures are based on the alias: `%tky` etc., structure name = alias in lowercase. So `APPEND ... TO failed-abrechnung.`

Now the draft table — I should show it briefly since draft was requested. The draft table is generated via a quick fix in ADT, but I can sketch it:

```abap
@EndUserText.label : 'Draft-Tabelle Reisekosten'
define table zrk_abrechn_d {
  key client            : abap.clnt not null;
  key reiseid           : sysuuid_x16 not null;
  mitarbeiter           : abap.char(12);
  reisezweck            : abap.char(80);
  betrag                : abap.dec(15,2);
  waehrung              : abap.cuky;
  status                : abap.char(1);
  lastchangedat         : timestampl;
  locallastchangedat    : timestampl;
  "%admin"
  include sych_bdl_draft_admin_inc;
}
```

Note: draft table field names must match the mapping? Actually the draft table fields are mapped via the same `mapping` in the BDEF? No — the draft table is handled automatically; the field names in the draft table should ideally match the CDS aliases or the mapping. Actually, the draft table structure is derived; the BDEF mapping applies to the persistent table. For the draft table, the field names must match the CDS view element names? Hmm. In practice, when you generate the draft table via ADT quick fix, it creates fields with the names of the CDS view elements (aliases). So draft table fields should be named like the aliases: REISE_ID? No — like the alias names: ReiseId → REISEID? The generated draft table uses the alias names of the CDS view. E.g., for /DMO/I_Travel with alias TravelID, draft table /DMO/D_TRAVEL_A has field TRAVEL_ID? Let me recall... /DMO/D_TRAVEL_A has fields like TRAVEL_ID, AGENCY_ID... Hmm, those match the persistent table names.

Actually, I believe the draft table field names must correspond to the CDS element names (aliases) because the draft handling maps automatically based on... hmm. Let me think. The managed runtime reads/writes the persistent table using the `mapping` in the BDEF. For the draft table, the mapping is... there's no separate mapping for the draft table. I believe the draft table fields must have the same names as the CDS view's element names (the aliases). Let me verify with an example: In the RAP100 workshop, CDS view /DMO/R_Travel_D (or ZRAP100_R_TravelTP_###) has elements like TravelID, AgencyID, ... and the draft table ZRAP100_DTRAV### has fields TRAVELID, AGENCYID, ... — yes! The draft table fields are named after the CDS aliases (concatenated, uppercase). E.g., TRAVELID not TRAVEL_ID. I remember the draft tables generated have fields like "TRAVELID" — yes, in RAP100 the draft table ZRAP100_DTRAV### contains TRAVELID, AGENCYID, BOOKING_FEE (hmm, BookingFee → BOOKINGFEE). I'm fairly sure the draft table uses the alias names.

So in my sketch, draft table fields: REISEID, MITARBEITER, REISEZWECK, BETRAG, WAEHRUNG, STATUS, LASTCHANGEDAT, LOCALLASTCHANGEDAT + include sych_bdl_draft_admin_inc.

Hmm wait, but LastChangedAt is the total etag — is it included in the draft table? The draft table should contain all fields of the CDS view, including LastChangedAt. Yes, generated draft tables include all fields. OK.

To keep it simple, maybe I'll note that the draft table can be generated via ADT (quick fix) and show a compact version. The user said "Nur die wesentlichen Codeteile" — so I can show the draft table compactly or just mention it. I'll show it briefly.

Also the CDS view needs `@Semantics.systemDateTime.lastChangedAt: true` on LastChangedAt and `localInstanceLastChangedAt` on LocalLastChangedAt for etag handling. Also for create: `@Semantics.systemDateTime.createdAt` etc. — optional, skip for brevity but maybe include created_by/created_at in table. Keep table lean: reise_id, mitarbeiter, reisezweck, betrag, waehrung, status, local_last_changed_at, last_changed_at. Maybe skip created_at/by to keep minimal. Actually including them is realistic but adds lines. I'll keep a couple admin fields minimal.

Currency: waehrung as abap.cuky with @Semantics.currencyCode — for simplicity, maybe skip currency semantics annotations. Actually a Betrag without currency is odd; but to keep minimal, I could drop the currency field entirely. Hmm, "Reisekosten-Abrechnung" with Betrag — a currency field is realistic. I'll keep Waehrung but without heavy annotations, or add `@Semantics.amount.currencyField: 'Waehrung'` on Betrag and `@Semantics.currencyCode: true` on Waehrung. That's two lines, fine.

Now, the BDEF in detail:

```
managed implementation in class zbp_rk_abrechnung unique;
strict ( 2 );
with draft;

define behavior for ZRK_C_Abrechnung alias Abrechnung
persistent table zrk_abrechnung
draft table zrk_abrechn_d
etag master LocalLastChangedAt
lock master total etag LastChangedAt
{
  create;
  update;
  delete;

  draft action Edit;
  draft action Activate optimized;
  draft action Discard;
  draft action Resume;
  draft determine action Prepare;

  field ( readonly ) ReiseId, Status;
  field ( mandatory ) Betrag, Mitarbeiter, Reisezweck;

  determination setStatusOnCreate on modify { create; }
  validation validateBetrag on save { create; field Betrag; }

  action ( features : instance ) approve result [1] $self;

  mapping for zrk_abrechnung
  {
    ReiseId = reise_id;
    Mitarbeiter = mitarbeiter;
    Reisezweck = reisezweck;
    Betrag = betrag;
    Waehrung = waehrung;
    Status = status;
    LastChangedAt = last_changed_at;
    LocalLastChangedAt = local_last_changed_at;
  }
}
```

Note: with `strict(2)`, `with draft` requires the draft actions to be listed explicitly. Also `authorization master ( global )` or instance is required in strict mode? In strict mode, `authorization master` is required? Let me recall: strict(2) requires... The strict mode requires explicit listing of draft actions, `lock master`, etc. I believe `authorization master` is optional. Hmm, actually with strict(2), you must specify authorization master? I don't think so. Many examples with strict(2) don't include authorization when not needed. Actually, in strict mode, "authorization master ( instance )" is required? Let me think... In RAP strict(2) mode, the following are mandatory: draft actions explicitly defined, etag master, lock master... I recall that `authorization master` is mandatory in strict mode. Hmm.

From ABAP docs on strict mode: "strict(2): ... requires that the behavior definition header includes ... " Let me recall the RAP100 example BDEF:

```
managed implementation in class zbp_... unique;
strict ( 2 );
with draft;

define behavior for ZRAP100_R_TravelTP_### alias Travel
persistent table zrap100_atrav###
draft table zrap100_dtrav###
etag master LocalLastChangedAt
lock master total etag LastChangedAt
authorization master ( instance )
{
  ...
}
```

Yes, RAP100 includes `authorization master ( instance )`. I believe in strict(2), authorization master is mandatory. To be safe, include `authorization master ( instance )`. But then, do I need an authorization control implementation? If `authorization master ( instance )` is specified, you must implement `get_instance_authorizations` method? If the authorization is declared but no method... Actually if you specify `authorization master ( instance )` without `authorization master ( instance, class )`, you must implement the authorization handling via... hmm.

In BDL: `authorization master ( instance )` means instance-based authorization control is active and must be implemented in the handler (get_instance_authorizations). If you don't want auth checks, you can use `authorization master ( global )` with... also needs implementation. There's also the option `authorization master ( global, class )`? Hmm.

Actually, there's a simpler option: `authorization master ( instance )` requires implementing `get_instance_authorizations`. If you want to skip, you could omit authorization entirely — but is that allowed in strict(2)? 

Checking my memory of the ABAP BDL docs for strict(2): "The following rules apply in strict mode: ... the authorization master must be specified..." I'm not 100% sure. Let me think about what SAP's own generated examples look like. When you use the "Manage ..." RAP generator or the ADT-based generation with strict(2), the BDEF includes `authorization master ( instance )` and `authorization master ( global )`? Hmm.

Actually, from the ABAP Keyword Documentation, strict mode (2): "Mandatory specifications: ... lock master, etag master, authorization master". I believe authorization master IS mandatory in strict(2). And if you specify `authorization master ( instance )`, you need the handler method `get_instance_authorizations` — but if it's empty/unimplemented, is that a syntax error? The method is generated by ADT quick fix; you can implement it returning nothing (no auth checks), which is fine.

Hmm, but including get_instance_authorizations adds lines. Alternative: `authorization master ( global )` requires `get_global_authorizations`. Either way a method.

Hmm wait — actually I recall that in strict(2), if you don't want authorization, you can... there's no "none" option. Let me check: BDL syntax `authorization master ( instance )` or `( global )` or `( instance, class )` etc. I think it's mandatory in strict mode. Hmm, but I've also seen strict(2) BDEFs without authorization... 

Let me think about the RAP Generator output: it generates `authorization master ( instance )` and `authorization master ( global )`? The generated BDEF from the RAP generator:

```
managed implementation in class zbp_... unique;
strict ( 2 );
with draft;
define behavior for Z... alias ...
persistent table ...
draft table ...
etag master LocalLastChangedAt
lock master total etag LastChangedAt
authorization master ( instance )
{
  ...
}
```

Yes, I'm fairly confident strict(2) mandates authorization master. From ABAP docs: "In strict mode, the following must be specified: ... authorization master". Hmm, actually I found in memory: "strict(2): The specification of the authorization master is mandatory." I'll include `authorization master ( instance )` and a minimal `get_instance_authorizations` that returns everything enabled (or just empty implementation). Actually, to keep the sketch minimal, I can implement it as an empty method with a comment "keine Einschränkungen". An empty implementation means no restrictions — wait, does an empty get_instance_authorizations mean all authorized? The default for requested features not set is... if you don't set the auth flags, the default is "authorized" (the framework assumes authorized unless restricted). Yes: unset = authorized. So an empty implementation works.

Hmm, but this adds complexity. Alternatively, I could use strict(1) or no strict... but modern practice is strict(2). The user asked for essential code; I'll include authorization master with a one-line empty implementation and a comment. Or I could just note it. Let me include it briefly to keep the sketch compilable.

Actually, let me reconsider: is `authorization master` really mandatory in strict(2)? From the ABAP Keyword Documentation (Behavior Definition, strict mode):

"strict(2) ... The following additions must be specified: ... lock master, etag master, authorization master..." 

I genuinely recall there being a rule that strict(2) requires `authorization master`. Let me go with including it — it's safer and realistic. I'll add the empty get_instance_authorizations method with a short comment.

Hmm, but wait — there's also `with draft` + strict(2) requiring `draft determine action Prepare` etc. Yes I have those.

Also `early numbering`? Not needed; managed with UUID key — for sysuuid_x16 keys, you often use `early numbering` or let the framework assign... For managed BOs with UUID primary key, the framework does NOT automatically fill the UUID; you need `early numbering` and implement `get_instance_features`... no wait, early numbering requires implementing numbering in the handler (`FOR NUMBERING`). Alternatively, use `@Semantics.uuid` hmm. Actually for managed scenarios, if the key field is of type sysuuid_x16 and you want automatic UUID generation, you add `early numbering` and implement method `FOR NUMBERING`... 

Hmm, actually there's a simpler approach: In the CDS view, annotate the key with `@Semantics.uuid: true`? I don't think that auto-generates. The common pattern in SAP examples (RAP100): they use `early numbering` and implement `get_instance_features`... no. Let me recall RAP100: 

In RAP100 (managed with draft), the BDEF has:
```
early numbering
```
Hmm, actually I don't remember RAP100 having early numbering. Let me think. The RAP100 BDEF:

```
managed implementation in class zbp_rap100_u_travel_### unique;
strict ( 2 );
with draft;

define behavior for ZRAP100_R_TravelTP_### alias Travel
persistent table zrap100_atrav###
draft table zrap100_dtrav###
etag master LocalLastChangedAt
lock master total etag LastChangedAt
authorization master ( instance )
{
  field ( readonly ) TravelId, OverallStatus;
  field ( mandatory ) AgencyId, CustomerId, BeginDate, EndDate;

  create;
  update;
  delete;

  draft action Edit;
  draft action Activate optimized;
  draft action Discard;
  draft action Resume;
  draft determine action Prepare {
    validation validateTravel;
    validation validateDates;
  }

  determination setInitialTravelStatus on modify { create; }
  determination calculateTravelID on modify { create; }

  validation validateTravel on save { create; field CustomerId; field AgencyId; }
  validation validateDates on save { field BeginDate; field EndDate; }

  action ( features : instance ) acceptTravel result [1] $self;
  action ( features : instance ) rejectTravel result [1] $self;
  ...
}
```

And the TravelID: they use `determination calculateTravelID on modify { create; }` to set the TravelID (a numeric field), while the actual key TravelUUID is... hmm, in /DMO the key is TravelUUID (sysuuid_x16) and they generate it... In RAP100, the table key is travel_uuid and there's a determination for travel_id (the human-readable ID). For the UUID key, the managed framework automatically fills UUID keys? 

Actually yes! I recall: For managed BOs, if the primary key field is of type RAW(16)/UUID, the RAP framework automatically assigns a UUID on create — no, wait. Hmm. I believe the managed runtime does NOT automatically generate UUIDs; you need early numbering. But in many SAP examples, create works without early numbering and the UUID gets filled... 

Let me think again. In the ABAP docs on "early numbering": "If the primary key is of type UUID ... the framework can automatically generate ... " Hmm. There's a concept: for managed BOs, number allocation can be done via `early numbering` (handler implementation) or `numbering : managed` (framework, with semantic keys)... 

Actually: `numbering: managed` is for late numbering? The options: early numbering (self-implemented), late numbering (self-implemented), and for managed: internal automatic numbering? I recall: "If the key field is annotated with @Semantics.uuid or typed as sysuuid_x16, the managed framework automatically generates a UUID when `early numbering` is NOT specified"? Hmm no.

Let me recall concretely from RAP docs: "Numbering: ... For managed business objects, the RAP framework can handle the number allocation automatically if the key field is of type UUID (raw16). This is the default. If you want to define your own numbering, use early numbering."

Hmm, I genuinely believe that for managed BOs with a raw16 UUID key, the framework assigns a UUID automatically on create. Evidence: In many simple RAP examples (e.g., the classic "ZXX_TRAVEL" tutorials), create works and the UUID is filled without any numbering implementation. Yes — I'm fairly confident: managed runtime auto-fills UUID keys (type raw16 / sysuuid_x16). The docs say: "For managed BOs, the key values are automatically generated if the key field is of type UUID." Hmm...

Actually, I now recall more precisely from the ABAP Keyword Documentation on BDL early numbering: "If the primary key field is typed with built-in type ... UUID ... then the managed RAP framework automatically provides a value" — I'm not fully certain, but the widespread pattern of simple managed BO tutorials working without early numbering strongly suggests automatic UUID generation. Yes, e.g., in the "ABAP RESTful Application Programming Model" book examples and many blogs, managed BOs with sysuuid_x16 keys get UUIDs automatically. I'll go with that (no early numbering needed). Good, keeps it minimal.

Now the behavior implementation class. Structure:

Global class:
```abap
CLASS zbp_rk_abrechnung DEFINITION PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF zrk_c_abrechnung.
ENDCLASS.
CLASS zbp_rk_abrechnung IMPLEMENTATION.
ENDCLASS.
```

Local handler (CCIMP):
```abap
CLASS lhc_abrechnung DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PRIVATE SECTION.
    METHODS get_instance_features FOR INSTANCE FEATURES
      IMPORTING keys REQUEST requested_features FOR Abrechnung RESULT result.

    METHODS get_instance_authorizations FOR INSTANCE AUTHORIZATION
      IMPORTING keys REQUEST requested_authorizations FOR Abrechnung RESULT result.

    METHODS setStatusOnCreate FOR DETERMINE ON MODIFY
      IMPORTING keys FOR Abrechnung~setStatusOnCreate.

    METHODS validateBetrag FOR VALIDATE ON SAVE
      IMPORTING keys FOR Abrechnung~validateBetrag.

    METHODS approve FOR MODIFY
      IMPORTING keys FOR ACTION Abrechnung~approve RESULT result.
ENDCLASS.
```

Implementations as sketched above.

For approve: check feature? The framework handles feature control. Implementation:

```abap
METHOD approve.
  " Status auf 'A' (genehmigt) setzen
  MODIFY ENTITIES OF zrk_c_abrechnung IN LOCAL MODE
    ENTITY Abrechnung
      UPDATE FIELDS ( Status )
      WITH VALUE #( FOR key IN keys ( %tky = key-%tky
                                      Status = 'A' ) )
    FAILED failed
    REPORTED reported.

  " Aktualisierte Daten als Ergebnis zurückgeben
  READ ENTITIES OF zrk_c_abrechnung IN LOCAL MODE
    ENTITY Abrechnung
      ALL FIELDS WITH CORRESPONDING #( keys )
    RESULT DATA(abrechnungen)
    FAILED failed.

  result = VALUE #( FOR abr IN abrechnungen
                    ( %tky = abr-%tky
                      %param = abr ) ).
ENDMETHOD.
```

Note: `FAILED failed` — in MODIFY ENTITIES within a handler, you can pass `FAILED DATA(failed)` inline or use the method's failed param? The method's `failed` param is for the action's own failed reporting. Common pattern: `MODIFY ENTITIES ... FAILED DATA(failed) REPORTED DATA(reported

</details>
