# ABAP: rap

## Aufgabe

Skizziere ein RAP-Business-Objekt (managed, mit Draft) für eine einfache Reisekosten-Abrechnung: Tabelle, CDS-Root-View, Behavior Definition mit Validation (Betrag > 0), Determination (Status bei Anlage = 'O'), einer Action 'approve' und der zugehörigen Behavior-Implementation-Klasse. Nur die wesentlichen Codeteile.

## Antwort

# RAP BO „Reisekostenabrechnung" (managed + Draft)

### 1. Persistenz-Tabelle `ZRK_ABRECHNUNG`

```abap
@EndUserText.label : 'Reisekostenabrechnung'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #RESTRICTED
define table zrk_abrechnung {
  key client            : abap.clnt not null;
  key travel_uuid       : sysuuid_x16 not null;
  description           : abap.char(60);
  amount                : abap.curr(15,2);
  currency              : abap.cuky(5);
  status                : abap.char(1);   " O = Offen, A = Genehmigt
  created_by            : abp_creation_user;
  created_at            : abp_creation_tstmpl;
  last_changed_by       : abp_lastchange_user;
  last_changed_at       : abp_lastchange_tstmpl;
  local_last_changed_at : abp_locinst_lastchange_tstmpl;
}
```

### 2. Draft-Tabelle `ZRK_ABRECHNUNG_D` (per ADT-Quick-Fix generierbar)

```abap
define table zrk_abrechnung_d {
  key client      : abap.clnt not null;
  key travel_uuid : sysuuid_x16 not null;
  " ... identische Felder wie zrk_abrechnung ...
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;   " Draft-Verwaltungsfelder
}
```

### 3. CDS-Root-View `ZRK_C_TRAVEL`

```abap
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Reisekostenabrechnung'
define root view entity ZRK_C_Travel
  as select from zrk_abrechnung
{
  key travel_uuid           as TravelUUID,

      description           as Description,
      @Semantics.amount.currencyCode: 'Currency'
      amount                as Amount,
      @Semantics.currencyCode: true
      currency              as Currency,
      status                as Status,

      @Semantics.user.createdBy: true
      created_by            as CreatedBy,
      @Semantics.systemDateTime.createdAt: true
      created_at            as CreatedAt,
      @Semantics.user.lastChangedBy: true
      last_changed_by       as LastChangedBy,
      @Semantics.systemDateTime.lastChangedAt: true
      last_changed_at       as LastChangedAt,
      @Semantics.systemDateTime.localInstanceLastChangedAt: true
      local_last_changed_at as LocalLastChangedAt
}
```

### 4. Behavior Definition

```
managed implementation in class zbp_rk_c_travel unique;
strict ( 2 );
with draft;

define behavior for ZRK_C_Travel alias Travel
persistent table zrk_abrechnung
draft table zrk_abrechnung_d
etag master LocalLastChangedAt
lock master
total etag LastChangedAt
authorization master ( instance )   " leere get_instance_authorizations genügt
numbering:managed                   " UUID durch Framework (ältere Releases: early numbering)
{
  create;
  update;
  delete;

  field ( readonly )  TravelUUID, Status, CreatedBy, CreatedAt,
                      LastChangedBy, LastChangedAt, LocalLastChangedAt;
  field ( mandatory ) Description, Amount, Currency;

  determination setStatus on modify { create; }                 " Status = 'O' bei Anlage
  validation  validateAmount on save { field Amount; create; }  " Betrag > 0

  action approve result [1] $self;                              " Status -> 'A'

  mapping for zrk_abrechnung
  {
    TravelUUID         = travel_uuid;
    Description        = description;
    Amount             = amount;
    Currency           = currency;
    Status             = status;
    CreatedBy          = created_by;
    CreatedAt          = created_at;
    LastChangedBy      = last_changed_by;
    LastChangedAt      = last_changed_at;
    LocalLastChangedAt = local_last_changed_at;
  }
}
```

### 5. Behavior-Implementation `ZBP_RK_C_TRAVEL`

Global Class (Quick Fix):

```abap
CLASS zbp_rk_c_travel DEFINITION PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF zrk_c_travel.
ENDCLASS.
CLASS zbp_rk_c_travel IMPLEMENTATION.
ENDCLASS.
```

Local Types (CCIMP):

```abap
CLASS lhc_travel DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PRIVATE SECTION.

    METHODS get_instance_authorizations FOR INSTANCE AUTHORIZATION
      IMPORTING keys REQUEST requested_authorizations FOR Travel RESULT result.

    METHODS setStatus FOR DETERMINE ON MODIFY
      IMPORTING keys FOR Travel~setStatus.

    METHODS validateAmount FOR VALIDATE ON SAVE
      IMPORTING keys FOR Travel~validateAmount.

    METHODS approve FOR MODIFY
      IMPORTING keys FOR ACTION Travel~approve RESULT result.

ENDCLASS.

CLASS lhc_travel IMPLEMENTATION.

  METHOD get_instance_authorizations.
    " bewusst leer (Beispiel ohne Berechtigungsprüfung)
  ENDMETHOD.

  METHOD setStatus.
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Status ) WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    DELETE travels WHERE Status IS NOT INITIAL.   " nur neue Instanzen

    MODIFY ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR travel IN travels
                      ( %tky   = travel-%tky
                        Status = 'O' ) ).
  ENDMETHOD.

  METHOD validateAmount.
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Amount ) WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    LOOP AT travels INTO DATA(travel) WHERE Amount <= 0.
      APPEND VALUE #( %tky = travel-%tky ) TO failed-travel.
      APPEND VALUE #( %tky            = travel-%tky
                      %msg            = new_message_with_text(
                                          severity = if_abap_behv_message=>severity-error
                                          text     = 'Betrag muss größer als 0 sein' )
                      %element-Amount = if_abap_behv=>mk-on )
                      TO reported-travel.
    ENDLOOP.
  ENDMETHOD.

  METHOD approve.
    MODIFY ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR key IN keys
                      ( %tky   = key-%tky
                        Status = 'A' ) ).

    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        ALL FIELDS WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    result = VALUE #( FOR travel IN travels
                      ( %tky   = travel-%tky
                        %param = travel ) ).
  ENDMETHOD.

ENDCLASS.
```

**Für eine lauffähige Fiori-App fehlen noch** (hier ausgeklammert): Projection-View + BDEF-Projection (`use draft`, `use action approve`), Service Definition & Binding sowie ggf. Feature Control, um `approve` nur bei Status `O` anzubieten.

---

<details><summary>Denkprozess (69968 Zeichen)</summary>

The user is asking in German for a sketch of a RAP Business Object (RESTful Application Programming Model, ABAP) - managed with Draft - for a simple travel expense report (Reisekosten-Abrechnung). They want:

1. Table (DDIC table)
2. CDS Root View
3. Behavior Definition with:
   - Validation (Betrag > 0 - amount > 0)
   - Determination (Status = 'O' on creation)
   - Action 'approve'
4. Behavior Implementation class

Only essential code parts ("Nur die wesentlichen Codeteile").

This is a technical ABAP RAP question. I should respond in German since the question is in German. Let me write out the essential code components.

Let me structure this properly:

**1. Database Table (DDIC)**

```abap
@EndUserText.label : 'Reisekostenabrechnung'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #RESTRICTED
define table zrk_abrechnung {
  key client            : abap.clnt not null;
  key travel_id         : abap.numc(6) not null;  "or uuid
  description           : abap.char(60);
  amount                : abap.curr(15,2);
  currency              : abap.cuky(5);
  status                : abap.char(1);
  created_by            : abap.char(12);
  created_at            : timestampl;
  last_changed_by       : abap.char(12);
  last_changed_at       : timestampl;
  local_last_changed_at : timestampl;
}
```

Actually, for RAP it's common to use uuid as key. Let me use a simple approach: travel_id as key or uuid. For managed with draft, we need:
- `local_last_changed_at` for ETag (draft consistency)
- Admin fields

Let me use uuid for simplicity of draft handling, or a numc key. Actually typical examples (like the RAP100 workshop) use travel_id (numc) plus... Actually RAP100 uses `travel_id : /dmo/travel_id` type. For draft, the key must be stable. Let me use uuid — simpler for early numbering. Actually with managed + draft, if we use external numbering we'd need early numbering handling. Using uuid with `@Semantics.uuid` and letting the framework generate is easiest. But for a "Reisekosten-Abrechnung" a human-readable ID is nicer. To keep it simple and essential, I'll use uuid as key and maybe show travel_id as alternative. Hmm, "nur die wesentlichen Codeteile" — keep it minimal. I'll use uuid.

Actually, let me reconsider: many RAP examples use a semantic key with early numbering. But to keep the sketch minimal, uuid is the cleanest: the framework generates the UUID automatically for managed BOs. I'll go with uuid.

**2. CDS Root View Entity**

```abap
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Reisekostenabrechnung'
define root view entity ZRK_C_Travel
  as select from zrk_abrechnung
{
  key travel_uuid       as TravelUUID,
      description       as Description,
      @Semantics.amount.currencyCode: 'Currency'
      amount            as Amount,
      @Semantics.currencyCode
      currency          as Currency,
      status            as Status,
      @Semantics.user.createdBy
      created_by        as CreatedBy,
      @Semantics.systemDateTime.createdAt
      created_at        as CreatedAt,
      @Semantics.user.lastChangedBy
      last_changed_by   as LastChangedBy,
      @Semantics.systemDateTime.lastChangedAt
      last_changed_at   as LastChangedAt,
      @Semantics.systemDateTime.localInstanceLastChangedAt
      local_last_changed_at as LocalLastChangedAt
}
```

Wait — for draft-enabled BOs, the CDS view should be based on the table directly (the draft table is generated separately). Also need metadata extensions etc. but those aren't essential. Need `@Metadata.allowExtensions: true` if using MDE — not essential.

Also, for draft, the root view entity needs to be draft-enabled via the behavior definition, and the CDS needs... Actually the draft enablement is in the BDEF. The CDS view itself just needs the annotations for UI optionally. Keep it minimal.

**3. Behavior Definition**

```
managed implementation in class zbp_rk_c_travel unique;
strict ( 2 );
with draft;

define behavior for ZRK_C_Travel alias Travel
persistent table zrk_abrechnung
draft table zrk_abrechnung_d
etag master LocalLastChangedAt
lock master
total etag Status
authorization master ( instance )
{
  create;
  update;
  delete;

  field ( readonly ) Status, CreatedBy, ...;
  field ( mandatory ) Description, Amount, Currency;

  determination setStatus on modify { create; }

  validation validateAmount on save { field Amount; create; }

  action ( features : instance ) approve result [1] $self;

  mapping for zrk_abrechnung
  {
    TravelUUID = travel_uuid;
    Description = description;
    Amount = amount;
    Currency = currency;
    Status = status;
    ...
  }
}
```

Note: `strict(2)` is required for draft? Actually strict mode is required for managed BOs with draft in newer releases — `strict ( 2 )` is mandatory for new developments (with draft it's required). Yes, draft requires strict mode (since 2020 or so, draft requires strict(2) in newer releases; at minimum strict). I'll include `strict ( 2 );`.

Also `with draft;` at header level, then `draft table` in the entity body.

Total etag: often `total etag LastChangedAt` — used for draft action locking... The total etag is for the whole BO. Keep `total etag LastChangedAt` or omit. I'll include it briefly.

**Draft table**: Should I sketch it? The user asked for "Tabelle, CDS-Root-View, Behavior Definition..., Behavior-Implementation-Klasse". The draft table is technically needed. I could mention it briefly — maybe include a short note that a draft table is needed with `%admin` include: `include syc_draft_admin` or the standard fields. The draft table definition:

```abap
define table zrk_abrechnung_d {
  key client       : abap.clnt not null;
  key traveluuid   : abap.raw(16) not null;  "or sysuuid_char... 
  ...
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;  "Draft-specific admin fields
}
```

Hmm, the exact syntax: draft tables include `include syb_draft_admin`? Let me recall. In ADT, when you create a draft table, the template is:

```abap
@EndUserText.label : 'Draft Database Table for ...'
@AbapCatalog.enhancement.category : #EXTENSIBLE_ANY
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #LIMITED
define table zrk_travel_d {

  key mandt      : mandt not null;
  key traveluuid : abap.raw(16) not null;

  travelid     : /dmo/travel_id;
  ...
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;
}
```

Hmm, actually I believe the draft admin include is `include syc_draft_admin` — hmm. Let me think. The standard includes: `sysadmin` (created_by, created_at, last_changed_by, last_changed_at) and for draft: `syc_draft_admin`? I recall the draft table template includes:

```
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;
```

Hmm, I'm not 100% sure of the name. There's `syb_draft_admin`? Let me think... The draft administrative fields are: DRAFTENTITYOPERATIONCODE, DRAFTENTITYCONSISTENCSTAT, DRAFTENTITYINPROCESSBYUSER, DRAFTENTITYLASTCHANGEDATETIME, DRAFTADMINISTRATIVEUUID... These are in include... I believe it's `syc_draft_admin`. Hmm, actually I've seen `include syc_draft_admin` hmm or is it `syb_draft_admin`? 

Searching memory: In SAP tutorials (RAP100), the draft table ZRAP100_TRAV_D includes:

```abap
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;
```

Hmm, I genuinely am not sure. I recall "syc_draft_admin" hmm. Alternatively the fields are defined via `include syb_draft_admin`. Let me think about what I've seen in ADT-generated draft tables... The generated code:

```abap
define table zrap_atrav_d {
  key mandt            : mandt not null;
  key traveluuid       : sysuuid_x16 not null;
  travelid             : /dmo/travel_id;
  ...
  lastchangedat        : timestampl;
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;
}
```

I'm fairly confident it's `syc_draft_admin`. Hmm, but wait — there's also `sysdraftadmin`? Hmm. Actually I think newer templates use:

```
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;
```

Hmm, I've also seen `include sys_draft_admin`? No... Let me settle: I believe the correct include name is `syc_draft_admin`. Hmm, but actually I now recall seeing `include syb_draft_admin` in some contexts... "SYB" is SAP ASE (Sybase) related, so that seems wrong. "SYC" relates to... hmm. 

Actually, I'm now fairly sure: The draft table admin include is `syc_draft_admin`. Hmm wait, no. Let me think again. I remember reading RAP blogs: draft tables contain the fields DRAFTENTITYOPERATIONCODE etc. And the include is... In the ABAP docs for "DDIC draft tables": "The include SYC_DRAFT_ADMIN..." Hmm.

Alternatively, to be safe, I can just note that the draft table is generated via quick fix (ADT) and contains the same fields plus draft admin includes — and show it briefly with a comment. Since the user asked for "wesentliche Codeteile" (essential code parts), I can mention the draft table in one line with a comment "via Quick Fix generierbar". That avoids the risk of getting the include name wrong while still being complete. But showing it adds value. Let me include it but keep it short, and I'll use `syc_draft_admin` — hmm, risk.

Let me try to recall harder. From the SAP tutorial "Create an SAP Fiori Elements App Using RAP..." the draft table definition shown:

```abap
@EndUserText.label : 'Draft database table for travel data'
@AbapCatalog.enhancement.category : #EXTENSIBLE_ANY
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #LIMITED
define table zrap100_trav### {
  key mandt            : mandt not null;
  key traveluuid       : sysuuid_x16 not null;
  travelid             : /dmo/travel_id;
  agencyid             : /dmo/agency_id;
  ...
  localcreatedby       : abp_creation_user;
  localcreatedat       : abp_creation_tstmpl;
  locallastchangedby   : abp_locinst_lastchange_user;
  locallastchangedat   : abp_locinst_lastchange_tstmpl;
  lastchangedat        : abp_lastchange_tstmpl;

  "%admin"
  include sysadmin;

  "%admin"
  include syc_draft_admin;
}
```

Hmm, I keep coming back to `syc_draft_admin`. Hmm, actually wait — I think I might be confusing with `syb_draft_admin`. Let me think about what "syc" could stand for... In SAP naming, "SY" prefix = system tables/fields. There's SYSADMIN include for admin fields. For draft... I've definitely seen "syc_draft_admin" somewhere. Hmm, but I also have a vague memory of "syb_draft_admin"... 

OK here's another angle: The draft admin fields include DRAFTENTITYOPERATIONCODE (char1), DRAFTENTITYCONSISTENCSTAT (char1), DRAFTENTITYINPROCESSBYUSER, DRAFTENTITYLASTCHANGEDATETIME, DRAFTADMINISTRATIVEUUID, DRAFTFIELDCHANGES, DRAFTFIELDDELETED, DRAFTUUID... hmm no.

I'll write `include syc_draft_admin` — hmm. Actually, you know what, I found it: I'm quite sure the ADT quick-fix generates:

```
"%admin"
include sysadmin;
"%admin"
include syc_draft_admin;
```

Hmm, no wait. I recall now more specifically — it might be `include syc_draft_admin;` hmm. There's also the possibility it's `sys_draft_admin`? 

Let me just go with `syc_draft_admin` but add a comment that the draft table can be generated via ADT quick fix anyway. That hedges appropriately. Actually — I now genuinely recall from the openSAP RAP courses: "include syc_draft_admin". Hmm, hmm. OK going with that, plus noting quick-fix generation.

Hmm, actually, I want to double check by thinking about the field names in the draft include: DRAFTENTITYOPERATIONCODE, DRAFTENTITYCONSISTENCYSTATUS, DRAFTENTITYINPROCESSBYUSER, DRAFTENTITYLASTCHANGEDATETIME, DRAFTADMINISTRATIVEUUID, HASDRAFT... The include might be named `sy_draft_admin`? I'll present it with a caveat-free but short mention. Fine.

**4. Behavior Implementation Class**

```abap
CLASS lhc_travel DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PRIVATE SECTION.

    METHODS validateAmount FOR VALIDATE ON SAVE
      IMPORTING keys FOR Travel~validateAmount.

    METHODS setStatus FOR DETERMINE ON MODIFY
      IMPORTING keys FOR Travel~setStatus.

    METHODS approve FOR MODIFY
      IMPORTING keys FOR ACTION Travel~approve RESULT result.

ENDCLASS.

CLASS lhc_travel IMPLEMENTATION.

  METHOD validateAmount.
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Amount Currency )
        WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    DELETE travels WHERE Amount IS NOT INITIAL AND Amount >= 0. " hmm

    LOOP AT travels INTO DATA(travel).
      APPEND VALUE #( %tky = travel-%tky ) TO failed-travel.
      APPEND VALUE #( %tky = travel-%tky
                      %msg = new_message_with_text(
                               severity = if_abap_behv_message=>severity-error
                               text = 'Betrag muss größer 0 sein' )
                      %element-amount = if_abap_behv=>mk-on
                    ) TO reported-travel.
    ENDLOOP.
  ENDMETHOD.
```

Better: read all entities, loop over keys, check amount <= 0 → fail. Let me write it cleanly:

```abap
  METHOD validateAmount.
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Amount ) WITH CORRESPONDING #( keys )
      RESULT DATA(lt_travel).

    LOOP AT lt_travel INTO DATA(ls_travel).
      IF ls_travel-Amount <= 0.
        APPEND VALUE #( %tky = ls_travel-%tky ) TO failed-travel.
        APPEND VALUE #( %tky = ls_travel-%tky
                        %msg = new_message_with_text(
                                 severity = if_abap_behv_message=>severity-error
                                 text     = |Betrag muss größer 0 sein| )
                        %element-Amount = if_abap_behv=>mk-on ) TO reported-travel.
      ENDIF.
    ENDLOOP.
  ENDMETHOD.
```

Determination:

```abap
  METHOD setStatus.
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Status ) WITH CORRESPONDING #( keys )
      RESULT DATA(lt_travel).

    DELETE lt_travel WHERE Status = 'O'.  "nur neue Instanzen

    MODIFY ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR ls IN lt_travel
                      ( %tky = ls-%tky
                        Status = 'O' ) ).
  ENDMETHOD.
```

Action approve:

```abap
  METHOD approve.
    MODIFY ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR key IN keys
                      ( %tky = key-%tky
                        Status = 'A' ) ).

    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        ALL FIELDS WITH CORRESPONDING #( keys )
      RESULT DATA(lt_travel).

    result = VALUE #( FOR ls IN lt_travel
                      ( %tky = ls-%tky
                        %param = ls ) ).
  ENDMETHOD.
```

Note: result parameter — with `result [1] $self` hmm, actually in strict mode, actions can return result; the handler signature: `RESULT result`. With strict(2), result param is `result TYPE ...`. Fine.

Also the CCIMP class (local handler classes) — the behavior pool. The class definition generated:

```abap
CLASS lsc_zrk_c_travel DEFINITION INHERITING FROM cl_abap_behavior_saver.
  ...
ENDCLASS.
```

For managed BOs, the saver class is generated but usually empty (no need to show). The essential part is lhc_travel with the three methods.

Also need the class header: `CLASS zbp_rk_c_travel DEFINITION PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF zrk_c_travel.` — that's the global class created via quick fix; the implementation goes into CCIMP (local types). I should show:

```abap
CLASS zbp_rk_c_travel DEFINITION PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF zrk_c_travel.
ENDCLASS.

CLASS zbp_rk_c_travel IMPLEMENTATION.
ENDCLASS.
```

And then the local handler class in the CCIMP include.

Also, the behavior definition needs the `validation on save` and `determination on modify { create; }`.

Status values: 'O' = Open (neu), 'A' = Approved. Maybe use domain fixed values; keep simple char1.

Additional details worth including for correctness:

- `field ( readonly ) Status, CreatedBy, CreatedAt, LastChangedBy, LastChangedAt, LocalLastChangedAt;`
- `field ( mandatory ) Description, Amount, Currency;` — mandatory triggers... note: mandatory creates implicit validation? Mandatory fields check is framework-level. Fine.
- Numbering: with uuid key, managed handles it (late numbering not needed). Actually for uuid keys, the framework generates automatically? For managed with internal (late) numbering... Hmm: For managed scenarios, if the key is a UUID with `@Semantics.uuid`, hmm — actually the framework does NOT automatically generate UUIDs; you typically need early numbering (`early numbering`) with a numbering method, OR you use `numbering:managed` (newer releases support `numbering:managed` for uuid keys!). Since ABAP Cloud 2308-ish, `numbering:managed` exists for semantic keys? Let me recall: In BDEF, `numbering:managed` is allowed for keys of type raw16/uuid — yes, since release 2305 or so, `numbering:managed` can be used for UUID keys in managed BOs. But to keep the sketch release-agnostic, I could use `early numbering` with a handler method... that adds code. Alternatively, keep it simple: use uuid and add `numbering:managed`? Hmm, that might not compile on older systems.

Simplest robust approach for a sketch: keep the key as uuid and note that the framework assigns it (with numbering:managed in newer releases) — or just not dwell on numbering. Actually, for managed BOs, if you don't specify anything, the consumer must provide the key on create... For draft/Fiori apps with uuid keys, the common pattern in RAP100: they use `travel_id` with early numbering via `FOR NUMBERING` method. That's extra code. 

Given "nur die wesentlichen Codeteile", I'll include `numbering:managed` with a short comment "(ab 2308; sonst early numbering)". Hmm, that adds complexity. Alternative: skip numbering discussion entirely and just note in one comment line. I think a one-line comment is fine: `numbering:managed` — hmm, but if their system doesn't support it, the sketch breaks. Let me think about what's cleanest pedagogically.

Option A: key = uuid, BDEF includes `numbering:managed` (modern, minimal code). 
Option B: key = travel_id numc, `early numbering` + handler method `FOR NUMBERING` (more code, classic RAP100 style).

The user asked for essential parts only. Option A is less code. I'll go with A and add a brief comment that on older releases early numbering would be needed. Actually, hmm — is `numbering:managed` valid syntax? Yes: `numbering:managed` in the BDEF header or per entity: `numbering : managed`. It's used like:

```
managed implementation in class zbp_... unique;
strict ( 2 );
with draft;

define behavior for ZRK_C_Travel alias Travel
persistent table zrk_abrechnung
draft table zrk_abrechnung_d
etag master LocalLastChangedAt
lock master
total etag LastChangedAt
authorization master ( global )
numbering:managed
{
  ...
}
```

Hmm, I believe syntax is `numbering:managed` placed in the entity body before the braces, or `numbering : managed`. In BDL, examples show:

```
define behavior for ZC_RAP_Travel alias Travel
persistent table /dmo/a_travel_d ... 
```

For numbering:managed, docs show:

```
managed implementation in class cl_... unique;
strict(2);
define behavior for ROOT entity ...
numbering:managed
{
  create;
  ...
}
```

Yes, `numbering:managed` is placed after the entity clauses, before the braces. OK.

Hmm, but wait — does numbering:managed work with draft? I believe yes (draft requires uuid-like keys anyway for draft table; draft tables use the key as raw16). Draft requires the key to be... draft tables store the entity key; works with uuid. Fine.

Actually, let me reconsider whether to even include numbering. If I omit numbering entirely, the sketch is still valid ABAP — create would require the client to supply the UUID. For a Fiori draft app that's bad UX (user would need to enter a raw16 UUID). So including numbering:managed (with comment) is the right call for a functional sketch. I'll include it with a short comment.

Alternatively — simpler and universally compatible: use `early numbering` and implement `METHOD get_instance_features`... no, numbering method: `METHODS earlynumbering_create FOR NUMBERING IMPORTING entities FOR CREATE Travel`. That's ~10 lines more. The user said essential parts only; numbering:managed is the minimal-code option. Go with it, plus a one-line comment "(UUID wird vom Framework generiert; auf älteren Releases: early numbering)".

Hmm, actually let me reconsider once more. Maybe simplest: keep uuid key and just note in a comment. I'll include `numbering:managed` since it's one line.

**Projection?** The user didn't ask for a projection view or service definition/binding. They asked for: Tabelle, CDS-Root-View, BDEF, Validation, Determination, Action, Behavior-Implementation-Klasse. So no projection needed. Good — keep to what's asked. Maybe a one-line note that for Fiori you'd add projection + service definition/binding, but that's beyond scope. A brief closing note is fine.

**Message class**: Using `new_message_with_text` avoids needing a message class — good for a sketch.

**Currency check**: Validation only on Amount > 0 as requested. Keep it simple.

Let me also make sure the BDEF includes:

```
validation validateAmount on save { field Amount; create; }
```

Hmm — syntax: `validation validateAmount on save { create; field Amount; }`. Order: `on save { field Amount; create; }` — both forms work; typical: `validation validateAmount on save { field Amount; }` plus create? If you only list `field Amount`, the validation runs when Amount changes on save — for newly created instances, if Amount is provided at create, does it trigger? The field trigger covers create too when the field has a value in the create operation? Hmm. Common pattern in RAP100: `validation validateAgency on save { field AgencyId; create; }`? Actually RAP100 uses: `validation validateAgency on save { field AgencyId; create; }`? Let me recall... In RAP100 (generator output), it's:

```
validation validateCustomer on save { field CustomerId; create; }
```

Hmm, I've seen `create;` included in the trigger list. Actually the generated BDEF from the Fiori Elements generator includes:

```
validation validateTravelID on save { create; field TravelID; }
```

Hmm, I think both orders are fine. I'll write `validation validateAmount on save { field Amount; create; }`. Wait — is `create` a valid trigger for on save validation? Valid trigger artifacts for `on save`: `create`, `update`, `delete`, `field X`. Yes, `create` is valid. Good.

Determination: `determination setStatus on modify { create; }` — on modify with create trigger. Good. (Could also be `on save`, but on modify { create } is the classic pattern for defaulting status.)

Action: `action approve result [1] $self;` — with feature control? The user didn't ask for feature control; keep simple: `action approve result [1] $self;`. Hmm, maybe make it `action ( features : instance )` — that would require get_instance_features implementation, which is extra code. User said essential only → plain action. But maybe worth one comment line that feature control could restrict approve to status 'O'. Keep it as a brief note maybe. I'll add a short comment.

Also `lock master`, `etag master LocalLastChangedAt`, `authorization master ( instance )` — authorization master is required in strict mode? In strict mode, you must specify `authorization master` (global or instance) — yes, strict(2) requires authorization master to be defined. I'll include `authorization master ( instance )` (without implementing auth checks — but then instance auth check methods would be required? If you declare `authorization master ( instance )`, you must implement `get_instance_authorizations`? Hmm — if declared but no `authorization instance` actions specified... Actually `authorization master ( instance )` requires the handler to implement `FOR INSTANCE AUTHORIZATION` if any operations are listed with `authorization ( instance )` or `authorization:instance`. If no operations are marked with instance authorization, hmm — I think declaring `authorization master ( instance )` without any `authorization ( instance )` on operations means the framework calls get_instance_authorizations only for operations marked accordingly; with none marked, no auth handler calls happen, but the method may still need to exist? To be safe and minimal, use `authorization master ( global )` — that requires get_global_authorizations implementation... which also is code.

Hmm. In strict mode, `authorization master` is mandatory (either global or instance or ( global, instance )). The corresponding handler methods only need implementation if there are corresponding authorizations to check. For `authorization master ( global )`, you must implement `get_global_authorizations` in the handler? I believe yes — the behavior pool must implement it (it can just return nothing). Actually, the ADT quick fix generates the handler with empty `get_global_authorizations`. Hmm, for managed with `authorization master ( instance )` and no instance-auth-marked operations, I think no auth method is forced. Let me think: The rule is — for every declared authorization control, corresponding methods must be implemented? The docs: "authorization master ( global )" → implement `get_global_authorizations`. "authorization master ( instance )" → implement `get_instance_authorizations` (required only if instance authorization is relevant for operations... hmm).

To keep the sketch safe and complete, I could include `authorization master ( instance )` and not show the auth method, or include `authorization master ( global )` and show an empty get_global_authorizations? That adds noise. 

Alternative: Many minimal examples use `authorization master ( instance )` and the quick-fix generates `get_instance_authorizations` returning empty. Hmm.

Actually, let me check: is `authorization master` really mandatory with strict(2)? Yes — strict mode requires authorization master to be specified. And the handler: with `authorization master ( instance )`, you must implement `get_instance_authorizations` only if there are operations with `authorization ( instance )` or `authorization:update` etc.? Hmm, I believe the method is required whenever instance authorization control is declared... Not 100% sure. 

Pragmatic approach: include `authorization master ( instance )` in BDEF and add a comment "Auth-Checks hier nicht implementiert (leere Methode genügt)". Or simpler: use `authorization master ( global )` and show a tiny empty method? Hmm.

Hmm, actually — I recall that with `authorization master ( instance )` and no `auth` markers on operations, ADT still requires the `get_instance_authorizations` method? I've seen behavior pools where only `authorization master ( instance )` is declared and the handler class includes `METHODS get_instance_authorizations FOR INSTANCE AUTHORIZATION ...`. The quick fix generates it. To be safe, I could just not dive into auth: declare `authorization master ( instance )` and mention in a comment that the (empty) auth method is generated by quick fix. That's honest and keeps code minimal. Alternatively skip the auth method entirely in the listing — the user asked for essential parts; the auth method is boilerplate. I'll declare it and note it.

Hmm, wait. Let me reconsider: maybe simpler to write `authorization master ( global )`? Then get_global_authorizations must be implemented (empty). Either way there's a stub. I'll go with instance and a comment. Actually — you know, let me just include the empty-ish methods in the handler class as comments or brief stubs? The user wants "wesentliche Codeteile" — the three business methods are essential; auth stubs are noise. I'll declare `authorization master ( instance )` with a comment "→ leere get_instance_authorizations genügt (Quick Fix)". Good compromise.

Hmm, actually, let me simplify: I can write `authorization master ( instance )` and in the impl class show only the three methods, with a comment noting the empty auth method is omitted for brevity. Fine.

**Draft table**: include short version.

**Total etag**: `total etag LastChangedAt` — hmm, for draft BOs, total etag is used for... it's needed for draft? The `total etag` is optional; used for cross-instance consistency in draft activation. RAP100 uses `total etag LastChangedAt`. I'll include it.

Wait — in my table, LastChangedAt is `last_changed_at` with `@Semantics.systemDateTime.lastChangedAt`. For managed BOs, the framework maintains `last_changed_at` (whole-BO timestamp) automatically if annotated with `@Semantics.systemDateTime.lastChangedAt`. Yes. And `local_last_changed_at` with localInstanceLastChangedAt for etag master. Good.

Field names: I'll use camelCase CDS names mapping to snake_case table fields via mapping in BDEF. Or simpler: name CDS fields same as table fields to skip... no, the `mapping for` clause is needed anyway if names differ; if names are identical, mapping is optional. To reduce code, I could name CDS aliases identical to table field names and skip the mapping block! E.g., view fields: TravelUUID? If I skip aliases, field names default to table field names (travel_uuid etc.). Then no mapping needed. But typical style uses aliases. Hmm — "nur die wesentlichen Codeteile": skipping the mapping block by using identical names is a legit simplification and reduces error surface. But it looks less idiomatic. 

Trade-off: I'll use idiomatic aliases and include a compact mapping block — it's important for learners to see the mapping. Actually, mapping is quite essential knowledge for BDEF. Include it but compact (maybe omit admin fields from mapping? No — admin fields with semantics annotations are auto-handled by framework? For managed BOs, admin fields (created_by etc.) with the proper semantics annotations are handled automatically IF listed in mapping? Hmm: The framework fills admin fields automatically when they're annotated and included in the mapping. If not in mapping, they're not maintained. RAP100 includes them in mapping. I'll include all in mapping — it's a few lines.

Alternatively use `mapping for zrk_abrechnung corresponding;` — there's a shorthand: `mapping for zrk_abrechnung corresponding;`? Hmm, I don't think `corresponding` shorthand exists in BDEF mapping... Actually there IS: `mapping for table corresponding`? Let me recall BDL mapping syntax:

```
mapping for zrk_abrechnung
{
  TravelUUID = travel_uuid;
  ...
}
```

There's also `mapping for zrk_abrechnung corresponding` — hmm, I believe yes! BDL supports `mapping for <table> corresponding;` which maps fields with identical names automatically... Hmm, does it? I recall `mapping for ... corresponding` being valid BDL — hmm, actually I'm not sure. There's "mapping for ... { ... }" and I have some memory of `corresponding` being allowed. Hmm. In BDL documentation: "mapping for ddic_table [corresponding] { mapping_info }" — I do think `corresponding` is an option where only differing fields need listing. Hmm, risky. I'll write the explicit mapping — safe and instructive.

Let me now also double check the CDS: for draft-enabled BOs, the root CDS view entity selects from the persistent table (not the draft table). Correct.

Also `@Metadata.allowExtensions: true` optional. Skip.

Access control: `@AccessControl.authorizationCheck: #NOT_REQUIRED` — fine for sketch.

**Status domain**: use char1 with values O (Open), A (Approved), maybe R (Rejected). Keep comment.

Now the behavior implementation class. Full sketch:

```abap
CLASS zbp_rk_c_travel DEFINITION PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF zrk_c_travel.
ENDCLASS.
CLASS zbp_rk_c_travel IMPLEMENTATION.
ENDCLASS.
```

Then CCIMP (Local Types):

```abap
CLASS lhc_travel DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PRIVATE SECTION.

    METHODS setStatus FOR DETERMINE ON MODIFY
      IMPORTING keys FOR Travel~setStatus.

    METHODS validateAmount FOR VALIDATE ON SAVE
      IMPORTING keys FOR Travel~validateAmount.

    METHODS approve FOR MODIFY
      IMPORTING keys FOR ACTION Travel~approve RESULT result.

ENDCLASS.

CLASS lhc_travel IMPLEMENTATION.

  METHOD setStatus.
    " Status nur bei Neuanlage auf 'O' setzen
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Status ) WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    DELETE travels WHERE Status IS NOT INITIAL.

    MODIFY ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR travel IN travels
                      ( %tky      = travel-%tky
                        Status    = 'O' ) ).
  ENDMETHOD.
```

Hmm, `DELETE travels WHERE Status IS NOT INITIAL` — if Status is char1, initial is space; new instances have status initial → they stay in table and get 'O'. Existing with 'A' get deleted from list. Good.

Wait, one nuance: `MODIFY ENTITIES ... UPDATE` on instances whose Status is unchanged would be wasteful but fine. Also, in determination on modify with create trigger, better pattern: loop over keys, read, filter, update. Mine is fine.

Actually a subtlety: in `setStatus`, after READ in LOCAL MODE, for newly created (draft) instances, Status is initial → included. Good.

```abap
  METHOD validateAmount.
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Amount ) WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    LOOP AT travels INTO DATA(travel) WHERE Amount <= 0.
      APPEND VALUE #( %tky = travel-%tky ) TO failed-travel.
      APPEND VALUE #( %tky  = travel-%tky
                      %msg  = new_message_with_text(
                                severity = if_abap_behv_message=>severity-error
                                text     = 'Betrag muss größer als 0 sein' )
                      %element-Amount = if_abap_behv=>mk-on
                    ) TO reported-travel.
    ENDLOOP.
  ENDMETHOD.
```

Hmm: `LOOP AT travels INTO DATA(travel) WHERE Amount <= 0.` — Amount is curr type; comparison with 0 fine. But what about initial amount (no amount entered)? Initial = 0 → fails validation → good (amount must be > 0). But careful: with draft, validation on save runs at activation; empty amount should fail. Good.

Note: `new_message_with_text` — class `cl_abap_behavior_message`? The helper is `new_message_with_text( severity = ... text = ... )` — available in behavior handler context (method of cl_abap_behavior_handler base? It's from IF_ABAP_BEHV_MESSAGE... Actually `new_message_with_text` is a method available in the handler via inheritance from `cl_abap_behavior_handler`? Hmm: In behavior pools, you use `new_message_with_text( ... )` — it's a static method of `cl_abap_behv`? The base class cl_abap_behavior_handler inherits from cl_abap_behv which provides `new_message`, `new_message_with_text` etc. Yes, in RAP100 examples they call `new_message_with_text( severity = if_abap_behv_message=>severity-error text = '...' )` directly inside handler methods. Correct.

Also `%element-Amount = if_abap_behv=>mk-on` — correct for attributing the message to the field.

```abap
  METHOD approve.
    " Status auf 'A' (genehmigt) setzen
    MODIFY ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR key IN keys
                      ( %tky   = key-%tky
                        Status = 'A' ) ).

    " Aktuelle Daten zurücklesen und als Ergebnis liefern
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        ALL FIELDS WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    result = VALUE #( FOR travel IN travels
                      ( %tky   = travel-%tky
                        %param = travel ) ).
  ENDMETHOD.
```

Good. Note: with draft, action on draft instance — the MODIFY in LOCAL MODE handles draft too. Fine for sketch.

Also should the action check current status? Could add `IF travel-Status = 'O'` guard — but feature control is the proper place. Keep simple; maybe a comment.

Now BDEF full:

```
managed implementation in class zbp_rk_c_travel unique;
strict ( 2 );
with draft;

define behavior for ZRK_C_Travel alias Travel
persistent table zrk_abrechnung
draft table zrk_abrechnung_d
etag master LocalLastChangedAt
lock master
total etag LastChangedAt
authorization master ( instance )
numbering:managed
{
  create;
  update;
  delete;

  field ( readonly ) Status, CreatedBy, CreatedAt, LastChangedBy, LastChangedAt, LocalLastChangedAt;
  field ( mandatory ) Description, Amount, Currency;

  determination setStatus on modify { create; }

  validation validateAmount on save { field Amount; create; }

  action approve result [1] $self;

  mapping for zrk_abrechnung
  {
    TravelUUID         = travel_uuid;
    Description        = description;
    Amount             = amount;
    Currency           = currency;
    Status             = status;
    CreatedBy          = created_by;
    CreatedAt          = created_at;
    LastChangedBy      = last_changed_by;
    LastChangedAt      = last_changed_at;
    LocalLastChangedAt = local_last_changed_at;
  }
}
```

Wait: `total etag LastChangedAt` — hmm, is total etag allowed with draft? Yes, commonly used. Fine.

One more check: `numbering:managed` placement — I believe it goes in the entity body header area, i.e., after `authorization master ( instance )` and before `{`. Let me double-check BDL syntax for numbering:managed. From SAP docs example:

```
managed implementation in class cl_demo_abap_rap_managed_m unique;
strict(2);
define behavior for DEMO_MANAGED_ROOT alias Root
persistent table demo_tab_root
...
numbering:managed
{
  create;
  ...
}
```

Yes, `numbering:managed` right before the braces. 

Hmm, one concern: does `numbering:managed` require the key field to be typed as UUID (raw16)? Docs: numbering:managed is possible for keys of type "UUID" (raw16) or char... I recall: "numbering:managed" can only be used for primary key fields of type UUID (RAW16)... Actually I think it supports abap.raw(16)/sysuuid_x16 and also numc? Hmm. The feature (released ~2023) supports UUID keys. My table uses `travel_uuid : abap.raw(16)` — hmm wait, in the DDIC table I should type it `sysuuid_x16` (data element) or `abap.raw(16)`. RAP100 uses `traveluuid : sysuuid_x16`. I'll use `sysuuid_x16` — hmm, is sysuuid_x16 a data element usable in table definitions? Yes, `sysuuid_x16` is a DDIC data element (type raw16). Good.

Alternatively, to dodge numbering complexities entirely, use semantic key travel_id with early numbering... no, stick with uuid + numbering:managed + comment.

Hmm, wait — actually, let me reconsider `numbering:managed` + draft compatibility. Draft requires... I believe numbering:managed works with draft. Yes, examples exist. OK.

Also for draft: `with draft;` at BDEF header, `draft table zrk_abrechnung_d` in entity. Draft table must have same key. Good.

Also, in strict mode, `lock master` — required? `lock master` is mandatory for draft? For draft-enabled BOs, lock master is required (draft needs it). Yes include.

`authorization master` mandatory in strict(2) — include `( instance )`.

Also `etag dep`... no dependent entities here. Single root only — good, keeps it simple ("einfache Reisekosten-Abrechnung" — one entity: header with amount; no items. Fine.)

**Draft table sketch**:

```abap
@EndUserText.label : 'Entwurfstabelle Reisekostenabrechnung'
@AbapCatalog.enhancement.category : #EXTENSIBLE_ANY
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #LIMITED
define table zrk_abrechnung_d {
  key client            : abap.clnt not null;
  key travel_uuid       : sysuuid_x16 not null;
  description           : abap.char(60);
  amount                : abap.curr(15,2);
  currency              : abap.cuky(5);
  status                : abap.char(1);
  created_by            : abap.char(12);  -- hmm, better use abp types
  ...
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;
}
```

Hmm — in the persistent table, better to use ABP data elements: `abp_creation_user`, `abp_creation_tstmpl`, `abp_locinst_lastchange_user`, `abp_locinst_lastchange_tstmpl`, `abp_lastchange_tstmpl`. RAP100 uses those. Let me use them in the main table:

```abap
define table zrk_abrechnung {
  key client            : abap.clnt not null;
  key travel_uuid       : sysuuid_x16 not null;
  description           : abap.char(60);
  amount                : abap.curr(15,2);
  currency              : abap.cuky(5);
  status                : abap.char(1);
  created_by            : abp_creation_user;
  created_at            : abp_creation_tstmpl;
  last_changed_by       : abp_lastchange_user;
  last_changed_at       : abp_lastchange_tstmpl;
  local_last_changed_at : abp_locinst_lastchange_tstmpl;
}
```

Check data element names: 
- abp_creation_user ✓ (CreatedBy)
- abp_creation_tstmpl ✓ (CreatedAt)
- abp_lastchange_user? Hmm — LastChangedBy is `abp_lastchange_user`? I recall `abp_locinst_lastchange_user` for LocalLastChangedBy and `abp_lastchange_user` for LastChangedBy. Yes: ABP_LASTCHANGE_USER exists. And timestamps: `abp_lastchange_tstmpl` (LastChangedAt), `abp_locinst_lastchange_tstmpl` (LocalLastChangedAt). Good.

For draft table, include same fields + admin includes. To keep short, I can show draft table with a comment "gleiche Felder wie Persistenz-Tabelle" + the two includes. That's a good compression. Actually the draft table needs all fields (same as persistent). I'll write it compactly with a comment.

Also note: draft table key type must match (sysuuid_x16). Good.

**CDS view**: also add `@Semantics.amount.currencyCode: 'Currency'` on Amount and `@Semantics.currencyCode: true`? For currencyCode annotation: `@Semantics.currencyCode: true` on Currency field. Yes.

Status: maybe add value help / fixed values via domain — skip, comment only.

Let me also consider: should the CDS be a view entity `define root view entity ZRK_C_TRAVEL as select from zrk_abrechnung` — yes. Add `@EndUserText.label`. Add UI annotations? Not asked. Skip (maybe one comment that Fiori UI annotations come via metadata extension/projection).

**Response format**: German, code blocks per artifact with short headers. Keep prose minimal. Use headers like "1. DDIC-Tabelle", "2. CDS Root View Entity", "3. Behavior Definition", "4. Draft-Tabelle (kurz)", "5. Behavior Implementation (Behavior Pool)". Order: table, draft table, CDS, BDEF, class. Or table, CDS, BDEF (mentioning draft table), class. I'll put draft table right after main table since BDEF references it.

Length: This is a code-heavy request; the code itself is the content. Keep explanations to one-liners. Maybe a final short note about what's omitted (projection, service definition/binding, feature control) — one or two lines. 

Formatting: use ### headers or bold labels + abap code blocks. Markdown appropriate (will be rendered). Use ```abap code fences.

Let me also double check the validation trigger semantics: `validation validateAmount on save { field Amount; create; }` — hmm, actually is it `create;` inside validation trigger braces? Valid trigger artifacts for validations on save: `create`, `update`, `delete`, `field <field>`. Hmm, actually for `on save` validations, the trigger list can include `create`, `update`, `delete` and `field`. Yes. RAP100 example: `validation validateTravelID on save { create; field TravelID; }`? Hmm, I recall generator output: 

```
validation validateCustomer on save { field CustomerId; create; }
```

Hmm, honestly I've seen both orders. Either compiles. I'll write `{ field Amount; create; }`.

Hmm wait, actually — do I even need `create;` if `field Amount` is listed? When creating with Amount filled, the field trigger fires for create operations too (the field is "changed" from nothing to value). I believe field triggers fire on create if the field has a value in the create request. But adding `create;` explicitly ensures validation runs for every new instance even without Amount in the payload (e.g., amount initial → must fail). Keep both — safe.

Determination: `determination setStatus on modify { create; }` — fine.

One more consideration: In the determination, using `MODIFY ENTITIES ... IN LOCAL MODE` from within a determination — correct pattern.

Also in `approve` action: since draft — when action is executed on active instance, fine; on draft instance, LOCAL MODE modify updates draft. OK.

Result parameter name: `RESULT result` — with strict mode, `result` must be typed; the generated signature handles it. In the method implementation, `result` is a table of structure with %tky and %param. My VALUE assignment is right.

Also: `READ ENTITIES OF zrk_c_travel` — should reference the root entity CDS name. Yes.

Let me also double check `failed-travel` / `reported-travel` naming: in handler methods, the implicit parameters are `failed` and `reported` (TYPE RESPONSE FOR ...). Access via `failed-travel`, `reported-travel`. Correct.

For the determination, no failed/reported params (determinations on modify have only keys import). Correct — determinations don't have responses. Right: `FOR DETERMINE ON MODIFY IMPORTING keys FOR Travel~setStatus` — no failed/reported. Good.

Now the message: `new_message_with_text( severity = if_abap_behv_message=>severity-error text = |Betrag muss größer 0 sein| )`. Fine. Could also use `%msg = new_message( id = 'ZY' number = '001' ... )` — text version simpler.

Also maybe add `%%element`... no, `%element-Amount = if_abap_behv=>mk-on`. Correct.

Global class name: `zbp_rk_c_travel` for BDEF `zrk_c_travel`. Convention: ZBP_<CDS>. Good.

Let me write the final answer in German, compact.

Additional small things:
- In BDEF, `use draft`? No — that's for projections. Not needed.
- `strict ( 2 );` — with draft this is required (draft requires strict mode ≥ 2? Draft requires strict mode; strict(2) is current recommendation). Include.

Also should I show `define behavior for ... alias Travel` — yes.

One more: `field ( readonly ) Status, ...` — also `field ( readonly : update )`? Keep simple: readonly for Status and admin fields. Mandatory for Description, Amount, Currency. Note: making Amount mandatory + validation > 0 is coherent.

Hmm — `field ( mandatory ) Currency` — mandatory creates a check that field is filled; fine.

Also: `field ( suppress )`? No.

Now, is `total etag LastChangedAt` correct name? CDS alias LastChangedAt. Yes.

Also the CDS: include `@Semantics.systemDateTime.lastChangedAt: true` on LastChangedAt — annotation syntax: `@Semantics.systemDateTime.lastChangedAt: true`. And `@Semantics.systemDateTime.localInstanceLastChangedAt: true`. And `@Semantics.user.createdBy: true`, etc. Write with `: true`.

Table field for currency: `abap.cuky(5)` — better reference data element `waers` or `abap.cuky(5)`. Use `abap.cuky(5)` fine; or `/dmo/currency_id`? Keep generic: `abap.cuky(5)` and `abap.curr(15,2)`. Hmm, for currency key, `abap.cuky(5)` is valid (CUKY built-in type). OK.

Status: `abap.char(1)` with comment "O=Offen, A=Genehmigt".

Let me draft the final response:

---

**1) DDIC-Tabelle** (Persistenz)

```abap
@EndUserText.label : 'Reisekostenabrechnung'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #RESTRICTED
define table zrk_abrechnung {
  key client            : abap.clnt not null;
  key travel_uuid       : sysuuid_x16 not null;
  description           : abap.char(60);
  amount                : abap.curr(15,2);
  currency              : abap.cuky(5);
  status                : abap.char(1);      " O = Offen, A = Genehmigt
  created_by            : abp_creation_user;
  created_at            : abp_creation_tstmpl;
  last_changed_by       : abp_lastchange_user;
  last_changed_at       : abp_lastchange_tstmpl;
  local_last_changed_at : abp_locinst_lastchange_tstmpl;
}
```

**2) Draft-Tabelle** (per Quick Fix generierbar; gleiche Felder + Draft-Verwaltung)

```abap
define table zrk_abrechnung_d {
  key client      : abap.clnt not null;
  key travel_uuid : sysuuid_x16 not null;
  " ... identische Felder wie zrk_abrechnung ...
  "%admin"
  include sysadmin;
  "%admin"
  include syc_draft_admin;
}
```

**3) CDS Root View Entity**

```abap
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Reisekostenabrechnung'
define root view entity ZRK_C_Travel
  as select from zrk_abrechnung
{
  key travel_uuid           as TravelUUID,

      description           as Description,
      @Semantics.amount.currencyCode: 'Currency'
      amount                as Amount,
      @Semantics.currencyCode: true
      currency              as Currency,
      status                as Status,

      @Semantics.user.createdBy: true
      created_by            as CreatedBy,
      @Semantics.systemDateTime.createdAt: true
      created_at            as CreatedAt,
      @Semantics.user.lastChangedBy: true
      last_changed_by       as LastChangedBy,
      @Semantics.systemDateTime.lastChangedAt: true
      last_changed_at       as LastChangedAt,
      @Semantics.systemDateTime.localInstanceLastChangedAt: true
      local_last_changed_at as LocalLastChangedAt
}
```

**4) Behavior Definition**

```
managed implementation in class zbp_rk_c_travel unique;
strict ( 2 );
with draft;

define behavior for ZRK_C_Travel alias Travel
persistent table zrk_abrechnung
draft table zrk_abrechnung_d
etag master LocalLastChangedAt
lock master
total etag LastChangedAt
authorization master ( instance )   " leere get_instance_authorizations genügt
numbering:managed                    " UUID durch Framework (sonst early numbering)
{
  create;
  update;
  delete;

  field ( readonly ) Status, CreatedBy, CreatedAt, LastChangedBy, LastChangedAt, LocalLastChangedAt;
  field ( mandatory ) Description, Amount, Currency;

  determination setStatus on modify { create; }        " Status = 'O' bei Anlage
  validation  validateAmount on save { field Amount; create; }  " Betrag > 0

  action approve result [1] $self;                     " Status -> 'A'

  mapping for zrk_abrechnung
  {
    TravelUUID         = travel_uuid;
    Description        = description;
    Amount             = amount;
    Currency           = currency;
    Status             = status;
    CreatedBy          = created_by;
    CreatedAt          = created_at;
    LastChangedBy      = last_changed_by;
    LastChangedAt      = last_changed_at;
    LocalLastChangedAt = local_last_changed_at;
  }
}
```

**5) Behavior-Pool**

Global class + CCIMP:

```abap
" ZBP_RK_C_TRAVEL (Global Class, per Quick Fix)
CLASS zbp_rk_c_travel DEFINITION PUBLIC ABSTRACT FINAL FOR BEHAVIOR OF zrk_c_travel.
ENDCLASS.
CLASS zbp_rk_c_travel IMPLEMENTATION.
ENDCLASS.
```

```abap
" Local Types (CCIMP)
CLASS lhc_travel DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PRIVATE SECTION.

    METHODS setStatus FOR DETERMINE ON MODIFY
      IMPORTING keys FOR Travel~setStatus.

    METHODS validateAmount FOR VALIDATE ON SAVE
      IMPORTING keys FOR Travel~validateAmount.

    METHODS approve FOR MODIFY
      IMPORTING keys FOR ACTION Travel~approve RESULT result.

ENDCLASS.

CLASS lhc_travel IMPLEMENTATION.

  METHOD setStatus.
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Status ) WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    DELETE travels WHERE Status <> ''.   " nur noch offene/initial Instanzen

    MODIFY ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR travel IN travels
                      ( %tky   = travel-%tky
                        Status = 'O' ) ).
  ENDMETHOD.
```

Hmm — `DELETE travels WHERE Status <> ''` keeps only initial ones. If Status = 'O' already (redetermination), it would also be updated to 'O' — harmless. Simpler: `DELETE travels WHERE Status IS NOT INITIAL.` — for char, `IS NOT INITIAL` works? For character fields, `IS INITIAL` means spaces — yes, `IS NOT INITIAL` valid. Use that.

Wait, careful: `DELETE travels WHERE Status IS NOT INITIAL.` — keeps rows with initial status. Good.

  METHOD validateAmount.

```abap
  METHOD validateAmount.
    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        FIELDS ( Amount ) WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    LOOP AT travels INTO DATA(travel) WHERE Amount <= 0.
      APPEND VALUE #( %tky = travel-%tky ) TO failed-travel.
      APPEND VALUE #(
        %tky   = travel-%tky
        %msg   = new_message_with_text(
                   severity = if_abap_behv_message=>severity-error
                   text     = 'Betrag muss größer als 0 sein' )
        %element-Amount = if_abap_behv=>mk-on )
        TO reported-travel.
    ENDLOOP.
  ENDMETHOD.
```

Hmm, the APPEND VALUE #( ... ) TO reported-travel syntax — need parentheses right: 

```abap
APPEND VALUE #( %tky            = travel-%tky
                %msg            = new_message_with_text(
                                     severity = if_abap_behv_message=>severity-error
                                     text     = 'Betrag muss größer als 0 sein' )
                %element-Amount = if_abap_behv=>mk-on ) TO reported-travel.
```

Good.

  METHOD approve:

```abap
  METHOD approve.
    MODIFY ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        UPDATE FIELDS ( Status )
        WITH VALUE #( FOR key IN keys
                      ( %tky   = key-%tky
                        Status = 'A' ) ).

    READ ENTITIES OF zrk_c_travel IN LOCAL MODE
      ENTITY Travel
        ALL FIELDS WITH CORRESPONDING #( keys )
      RESULT DATA(travels).

    result = VALUE #( FOR travel IN travels
                      ( %tky   = travel-%tky
                        %param = travel ) ).
  ENDMETHOD.

ENDCLASS.
```

Closing note: for a runnable Fiori app you'd add projection view + BDEF projection + service definition/binding — one line mention.

Also maybe a note: validation on save blocks activation/save; determination on modify sets status at create; action approve sets 'A'.

Should I add `%element-Amount`? Yes done.

One thing: in `validateAmount`, using LOCAL MODE read — for on save validation, reading with LOCAL MODE is standard (reads from draft/active incl. changes). Good.

Also, in approve, maybe guard: only approve if Status <> 'A'. Skip for brevity; mention feature control in a one-liner comment? I'll add a tiny comment in BDEF: `action approve result [1] $self; // optional: ( features : instance ) + get_instance_features`. Hmm, keep comments lean. Maybe one short bullet after code blocks listing omitted parts.

Also check: `READ ENTITIES OF zrk_c_travel IN LOCAL MODE ENTITY Travel ALL FIELDS WITH CORRESPONDING #( keys ) RESULT DATA(travels).` — syntax OK.

Potential issue: in `setStatus` determination triggered on create — `keys` contains the created instances. READ in LOCAL MODE returns current (draft) data. Fine.

Another subtle point: for draft-enabled BOs, determinations/validations run on both draft and active instances; fine.

Also the BDEF header could include `with draft;` — yes included. Note: `with draft` must come before `define behavior`. Also `strict ( 2 );` before define behavior. Order: managed implementation..., strict, with draft — all fine at header.

Hmm, one more check on `numbering:managed`: I want to be careful because if the user is on an older release this fails. I'll add comment "(ab Release ~2308; sonst early numbering)". Actually the release: `numbering:managed` was released with ABAP Cloud 2305? I recall it's available since 2023 ("numbering:managed" for late numbering of UUID keys — released in ABAP Cloud 2308? or on-prem 2023). I'll just say "neuere Releases; sonst early numbering". Safe.

Alternatively — hmm, let me reconsider using early numbering with a numbering method to be release-safe... It's ~8 extra lines:

```abap
early numbering
{
  ...
}
```
plus handler:
```abap
METHODS earlynumbering_cba... no:
METHODS earlynumbering_create FOR NUMBERING
  IMPORTING entities FOR CREATE Travel.
...
METHOD earlynumbering_create.
  LOOP AT entities INTO DATA(entity) WHERE TravelUUID IS INITIAL.
    entity-TravelUUID = ... cl_uuid=>create... 
```

Hmm, `cl_abap_uuid=>create_c36`? For x16: `cl_system_uuid=>create_uuid_x16_static( )`. That's the RAP100 pattern:

```abap
METHOD earlynumbering_create.
    DATA: entity type structure ...
    LOOP AT entities INTO DATA(entity) WHERE TravelUUID IS INITIAL.
      entity-TravelUUID = cl_system_uuid=>create_uuid_x16_static( ).
      APPEND entity TO mapped-travel.
    ENDLOOP.
    " rest without change
    APPEND ... 
```

Actually full pattern needs mapping all entities to mapped. More code. numbering:managed is cleaner. Keep numbering:managed with comment. Good.

Also, hmm: is `sysuuid_x16` the right DDIC data element for raw16 uuid? Yes, SYSUUID_X16 exists (byte16). RAP100 draft tables use `traveluuid : sysuuid_x16`. Good.

Now — one more consideration on the CDS root view for draft: it's recommended that the root view entity selects directly from the persistent table (yes). Also `@Metadata.allowExtensions: true` optional — skip.

Double-check BDEF: for draft, `draft table zrk_abrechnung_d` — yes. Also need `draft` enabled in projection for service — not in scope.

Also: should `update` be `update ( features : instance )`? No, keep plain.

I think also worth adding `field ( readonly ) TravelUUID;`? With numbering:managed, key is set by framework; typically you'd mark it readonly? The generator marks key fields... hmm, for uuid keys with numbering:managed, the field is automatically not editable? Adding `field ( readonly ) TravelUUID` is safe and sensible. But wait — can the key field be declared readonly with numbering:managed? Yes. Hmm, but actually with numbering:managed I think the framework handles it. I'll include TravelUUID in the readonly list — hmm, is that allowed (key field readonly)? For managed BOs, key fields are implicitly readonly on update (key can't be changed). Declaring `field ( readonly ) TravelUUID` explicitly is fine. I'll add it to be explicit. Actually to keep the field list shorter, maybe skip. Eh — include it; it's one word.

Hmm wait, actually there might be a syntax consideration: `field ( readonly ) TravelUUID, Status, ...;` — fine.

Let me also reconsider `authorization master ( instance )`: with strict(2), is a handler method mandatory? Checking my memory of the quick-fix behavior: when you declare `authorization master ( instance )`, ADT quick fix offers "add method get_instance_authorizations". I believe the runtime requires the method to exist if instance authorization is declared — actually the rule: "For authorization master ( instance ), the handler method get_instance_authorizations must be implemented." Hmm. I think yes, it must exist (can be empty). To be safe, I'll note it in a comment: "→ leere Methode get_instance_authorizations im Handler genügt (Quick Fix)". And optionally show the stub? I could add the stub as a comment line in the class. Let me add the method declaration+empty impl as a brief mention in text rather than code, or include it in code as empty method — it's 3 lines. Hmm, "nur die wesentlichen Codeteile" — I'll include it as empty stub with comment, since otherwise the class won't compile. Actually wait — will it compile without? If BDEF declares authorization master ( instance ), the behavior pool must implement get_instance_authorizations? I'm fairly confident that the check requires implementation of the auth method when instance auth is declared... Hmm, actually I recall that get_instance_authorizations is only required if there are `authorization ( instance )` marked operations or `authorization:instance` — no wait.

Let me think about RAP100: its BDEF has `authorization master ( instance )` and `update ( features : instance )` etc. The handler includes `METHODS get_instance_authorizations FOR INSTANCE AUTHORIZATION IMPORTING keys REQUEST requested_authorizations FOR Travel RESULT result.` — yes it's there. And I believe it's required by the framework (else dump/syntax error at BDEF activation? The BDEF activation checks behavior pool completeness? Actually BDEF activation doesn't check the class; errors surface at runtime or in class validation). Hmm — the behavior implementation must implement all declared handlers; missing methods cause a syntax error in the behavior pool? I believe the behavior definition references the class; the class must define methods matching the BDEF — missing ones cause errors when... hmm, actually the BDEF is the contract; the handler class methods are checked against it when the class is activated? There's a check "behavior implementation doesn't match definition". 

Safest: include the empty stub in the code. It's small:

```abap
METHODS get_instance_authorizations FOR INSTANCE AUTHORIZATION
  IMPORTING keys REQUEST requested_authorizations FOR Travel RESULT result.
...
METHOD get_instance_authorizations.
ENDMETHOD.
```

Hmm, that's 5 lines. OK, include — it makes the sketch actually complete/compilable. Hmm, but wait: does `authorization master ( instance )` alone (without any operation marked with instance auth) even require it? To avoid this rabbit hole entirely, alternative: use `authorization master ( global )` — then get_global_authorizations is definitely required. Same problem.

OK decision: include `authorization master ( instance )` and the empty `get_instance_authorizations` stub. That's correct and complete.

Hmm, actually hold on — let me reconsider. Is `authorization master` truly mandatory under strict(2)? Yes: "strict(2) requires ... authorization master to be defined" — I'm quite sure strict mode requires authorization master (and lock master for draft). So include it. And the stub. Fine.

Actually, one simplification: I could write `authorization master ( global )` and stub `get_global_authorizations` — equally long. Instance is more typical in examples. Keep instance.

Now — also `lock master` mandatory for draft: yes.

Let me also double check `total etag LastChangedAt` — optional but good with draft (protects against parallel draft activation). Keep.

Now assemble the final answer. Structure:

Intro sentence (one line). Then sections:

**1. DDIC-Tabelle `ZRK_ABRECHNUNG`** (code)
**2. Draft-Tabelle `ZRK_ABRECHNUNG_D`** (code, compressed)
**3. CDS-Root-View `ZRK_C_TRAVEL`** (code)
**4. Behavior Definition `ZRK_C_TRAVEL`** (code)
**5. Behavior-Implementation `ZBP_RK_C_TRAVEL`** (global class + local handler code)
Closing: 2-3 bullets on what's left out for a full app (projection, service definition/binding, feature control für approve, ggf. Metadate-Extension/UI-Annotations).

Keep prose minimal. German language. Use ### headings maybe, or bold. I'll use ### headings with short names. Code fences with `abap` and `bdl` language hints (bdl for BDEF — rendering may not know it, but fine; could use plain). I'll use `abap` for ABAP and `bdl`/none for BDEF. Maybe just use `abap` for all to be safe? BDEF isn't ABAP; using no language or `text` is fine. I'll use ```abap for ABAP code and ``` for BDEF (plain). Hmm, minor. I'll do ```abap for tables/CDS/class and plain fence for BDEF.

Length check: This will be a fairly long answer due to code, but that's appropriate for the request. Keep comments in code concise.

One more detail in the CDS: `define root view entity ZRK_C_Travel as select from zrk_abrechnung` — CDS names usually all caps in examples; fine either way.

Also in BDEF mapping — the mapping block: `mapping for zrk_abrechnung { ... }`. Correct.

Also — hmm, `field ( mandatory )` — syntax `field ( mandatory ) Description, Amount, Currency;` correct.

Also for draft + mandatory: mandatory fields are checked on draft save too. Fine.

Double-check `DELETE travels WHERE Status IS NOT INITIAL.` — travels is RESULT DATA(travels) — inline declared table of Travel structures with %tky etc. plus fields. WHERE on Status works. Good.

In approve: `FOR key IN keys` — keys is the importing table with %tky. Good.

Also, in approve, after MODIFY, the READ returns updated status; result mapping `%param = travel` — the whole instance as parameter (since result is $self). Good.

Potential nuance: `result = VALUE #( FOR travel IN travels ( %tky = travel-%tky %param = travel ) ).` — correct.

Also should approve set Status only if currently 'O'? Add WHERE guard in the UPDATE table? e.g. only for keys where status = 'O'. For brevity skip; maybe comment "// ggf. Prüfung Status = 'O' via Feature Control". I'll put that as a short comment in the method or in closing notes.

Final check on the handler method signatures:

- Determination: `METHODS setStatus FOR DETERMINE ON MODIFY IMPORTING keys FOR Travel~setStatus.` ✓
- Validation: `METHODS validateAmount FOR VALIDATE ON SAVE IMPORTING keys FOR Travel~validateAmount.` ✓ (failed/reported implicit)
- Action: `METHODS approve FOR MODIFY IMPORTING keys FOR ACTION Travel~approve RESULT result.` ✓ (failed/reported implicit too)

Auth: `METHODS get_instance_authorizations FOR INSTANCE AUTHORIZATION IMPORTING keys REQUEST requested_authorizations FOR Travel RESULT result.` ✓

Now write it. Also brief note at top: "Managed, draft-enable BO mit einer Root-Entität". Keep it tight.

Regarding the draft table include name — final decision: I'll write `include syc_draft_admin;` hmm... one more memory attempt: I'm now recalling ADT draft table template:

```
  "%admin"
  include sysadmin;

  "%admin"
  include syc_draft_admin;
```

Hmm, hmm. I also recall seeing `include syb_draft_admin` — no... "SYB" = Sybase ASE system table naming? There are DDIC include structures: SYSADMIN? Actually the admin include is `SYADMIN`? In table definitions you write `include sysadmin;` — hmm, is it `sysadmin` or `syadmin`? I've definitely seen `include sysadmin;` in RAP tutorials for persistent tables? Hmm, actually for persistent tables you don't include sysadmin — you define the admin fields explicitly (created_by etc.). The `include sysadmin` appears in *draft* tables. Let me recall the RAP100 draft table:

```abap
define table zrap100_trav### {
  key mandt            : mandt not null;
  key traveluuid       : sysuuid_x16 not null;
  travelid             : /dmo/travel_id;
  ...
  localcreatedby       : abp_creation_user;
  localcreatedat       : abp_creation_tstmpl;
  locallastchangedby   : abp_locinst_lastchange_user;
  locallastchangedat   : abp_locinst_lastchange_tstmpl;
  lastchangedat        : abp_lastchange_tstmpl;

  "%admin"
  include sysadmin;

  "%admin"
  include syc_draft_admin;
}
```

Yes — I'm now confident this is the pattern from the SAP tutorial (the "%admin" comments and the two includes). The draft include name `syc_draft_admin`... I keep flip-flopping. Let me try to recall the actual field list of the draft admin include: DRAFTENTITYOPERATIONCODE, DRAFTENTITYCONSISTENCSTAT (note truncated name), DRAFTENTITYINPROCESSBYUSER, DRAFTENTITYLASTCHANGEDATETIME, DRAFTADMINISTRATIVEUUID, DRAFTFIELDCHANGES, DRAFTFIELDDELETED, HASDRAFT? and the include name... In the ABAP source I've seen: `include syc_draft_admin`. Hmm, alternatively `include syb_draft_admin`... 

You know, I have decent confidence in `syc_draft_admin` from multiple tutorial sightings. Also, since I'm compressing the draft table anyway ("identische Felder wie Persistenztabelle" + includes), even if the include name were slightly off, I'll add "(per Quick-Fix in ADT generierbar)" so the user knows the canonical way. That mitigates the risk. Good.

Actually, let me reduce risk further: present the draft table as: "wird per Quick Fix generiert; im Wesentlichen:" and show the skeleton. Fine.

Also note: draft table needs `@AbapCatalog.dataMaintenance : #LIMITED` etc. — skip such details, it's generated anyway.

Now, the closing note: mention that for Fiori you'd add: projection view `ZRK_C_TravelProjection`, BDEF projection `projection; use draft; use action approve; ...`, service definition + binding. One compact bullet list or sentence. Keep to 2 lines.

Let me also sanity check the BDEF `with draft;` placement: header lines:

```
managed implementation in class zbp_rk_c_travel unique;
strict ( 2 );
with draft;
```

Yes, that's the standard order.

And `numbering:managed` — hmm, one more check: with draft + numbering:managed — I believe there was a restriction that numbering:managed requires... it works with draft. OK.

Alternatively, I could avoid the numbering question by noting: "Wenn TravelUUID vom Framework generiert werden soll: numbering:managed (neuere Releases), sonst early numbering." — put as comment in BDEF. Good.

Write final answer now. Keep it in German. Use minimal prose. I'll number the artifacts. Also make sure to mention Status values O/A consistently ('O' offen, 'A' genehmigt).

One more consideration on `%element-Amount`: the field name in the entity is `Amount` — correct casing as in BDEF/CDS alias. Good.

Also in validateAmount, should I also validate currency? Not asked. Skip.

Edge: `LOOP AT travels INTO DATA(travel) WHERE Amount <= 0.` — inline DATA in LOOP with WHERE — fine.

Also `failed-travel` — for validation, entries in failed cause the save to be rejected. Good.

Final structure:

Kurze Einleitung (1 Satz).

### 1. Persistenz-Tabelle
code

### 2. Draft-Tabelle
code (compressed)

### 3. CDS-Root-View
code

### 4. Behavior Definition
code

### 5. Behavior-Implementation
code (global + CCIMP)

### Hinweise / was fehlt noch für lauffähige Fiori-App
2-3 bullets.

That's it. Write it.

</details>
