# ABAP: cds-view

## Aufgabe

Schreibe eine CDS View Entity (define view entity) ZI_SalesOrderItem auf I_SalesDocumentItem bzw. VBAP mit Assoziation zum Material (I_Product), Annotationen für UI (@UI.lineItem), einem berechneten Feld 'NetValuePerUnit' und @Semantics für Betrag und Währung. Erkläre die Annotationen.

## Antwort

# CDS View Entity `ZI_SalesOrderItem`

```abap
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Vertriebsbelegposition'
@Metadata.allowExtensions: true

define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
  association [0..1] to I_Product as _Product
    on $projection.Product = _Product.Product
{
      @UI.lineItem: [ { position: 10, label: 'Vertriebsbeleg' } ]
      @UI.selectionField: [ { position: 10 } ]
  key SalesDocument,

      @UI.lineItem: [ { position: 20, label: 'Position' } ]
  key SalesDocumentItem,

      @UI.lineItem: [ { position: 30, label: 'Material' } ]
      @Consumption.valueHelpDefinition: [{ entity: { name: 'I_Product', element: 'Product' } }]
      @ObjectModel.foreignKey.association: '_Product'
      Product,

      @UI.lineItem: [ { position: 40, label: 'Menge' } ]
      @Semantics.quantity.unitOfMeasureField: 'OrderQuantityUnit'
      OrderQuantity,

      @UI.hidden: true
      OrderQuantityUnit,

      @UI.lineItem: [ { position: 50, label: 'Nettowert' } ]
      @Semantics.amount.currencyField: 'TransactionCurrency'
      NetAmount,

      @UI.hidden: true
      TransactionCurrency,

      @UI.lineItem: [ { position: 60, label: 'Nettowert pro ME' } ]
      @EndUserText.label: 'Nettowert pro Mengeneinheit'
      @Semantics.amount.currencyField: 'TransactionCurrency'
      case
        when OrderQuantity <> 0
          then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec( 15, 2 ) )
        else cast( 0 as abap.dec( 15, 2 ) )
      end as NetValuePerUnit,

      // Assoziation nach außen exponieren (OData-Navigation)
      _Product
}
```

## Erläuterungen

### `define view entity`
Seit ABAP Platform 2020 (7.56) bzw. ABAP Environment der Nachfolger der klassischen `define view`-Syntax: strengere Regeln, Ausdrücke (Arithmetik, `CASE`, Funktionen) sind direkt in der Elementliste erlaubt. Für Neuentwicklungen ist die view entity die empfohlene Technologie.

### Assoziation `_Product`
- `association [0..1] to I_Product ... on $projection.Product = _Product.Product` – `$projection` verweist auf das Feld in der eigenen SELECT-Liste.
- **Kardinalität `[0..1]`**: Material kann fehlen (z. B. Textpositionen) → verhält sich bei Nutzung wie ein LEFT OUTER JOIN; `[1..1]` würde wie INNER JOIN wirken und Positionen ausschließen.
- **Lazy/On-demand**: Der Join wird nur erzeugt, wenn der Konsument tatsächlich Felder über die Assoziation liest (z. B. `_Product.ProductType` in einer Konsum-View). Die View bleibt dadurch schlank und wiederverwendbar.
- `_Product` am Ende der Elementliste exponiert die Assoziation → erscheint als *Navigation Property* im OData-Service.

### `@UI.lineItem`
- Definiert die **Spalten der Tabelle** im Fiori Elements List Report bzw. in Object-Page-Tabellen.
- `position` = Spaltenreihenfolge, `label` = Spaltentitel (überschreibt das geerbte Feldlabel).
- `@UI.selectionField` macht das Feld zusätzlich zum Filter in der Filterleiste.
- Best Practice: UI-Annotationen in eine **Metadata Extension** auslagern – dafür ist `@Metadata.allowExtensions: true` gesetzt.

### `@Semantics.amount.currencyField` / `@Semantics.quantity.unitOfMeasureField`
- Verknüpft Betrag ↔ Währungsschlüssel bzw. Menge ↔ Mengeneinheit.
- Fiori Elements rendert Betrag und Währung **zusammen** („1.234,56 EUR“) und berücksichtigt die Dezimalstellen der Währung (z. B. JPY ohne Nachkommastellen).
- Ohne diese Annotation würde der Betrag als „nackte“ Zahl ohne Einheit erscheinen.
- Deshalb sind `TransactionCurrency` und `OrderQuantityUnit` mit `@UI.hidden` markiert: Sie brauchen **keine eigene Spalte**, da Währung/ME automatisch neben dem Betrag bzw. der Menge angezeigt werden.

### Berechnetes Feld `NetValuePerUnit`
- In view entities sind Ausdrücke direkt als Element erlaubt – kein Hilfsview nötig.
- `division(NetAmount, OrderQuantity, 2)`: SQL-Funktion mit **fixer Nachkommastellenzahl** – deterministischer als der `/`-Operator, dessen Ergebnistyp sonst „unkontrolliert“ viele Dezimalstellen haben kann.
- `CASE ... <> 0`: Schutz vor **Division durch 0** (sonst Laufzeitfehler); `cast(... as abap.dec(15,2))` fixiert den Ergebnistyp.
- Das Feld ist fachlich ein Preis (Betrag pro Einheit) und erhält daher dieselbe Währungsannotation wie `NetAmount`.

### Sonstige Annotationen
- `@AccessControl.authorizationCheck: #CHECK` – es wird ein Access-Control-Objekt (DCL) erwartet; für Tests `#NOT_REQUIRED`, sonst Aktivierungswarnung.
- `@EndUserText.label` – Beschreibung der View (ADT, OData-Metadaten).
- `@Consumption.valueHelpDefinition` – Value Help für das Materialfeld im Fiori-UI.
- `@ObjectModel.foreignKey.association` – deklariert `Product` über die Assoziation als Fremdschlüssel.

## Hinweis: `I_SalesDocumentItem` vs. `VBAP`

`I_SalesDocumentItem` ist die **freigegebene VDM-View** (stabile API, upgrade-sicher) – direkter Zugriff auf `VBAP` ist in S/4HANA für kundeneigene Entwicklung nicht released. Falls doch `VBAP` nötig (z. B. ECC): Mapping `VBELN→SalesDocument`, `POSNR→SalesDocumentItem`, `MATNR→Product`, `KWMENG→OrderQuantity`, `VRKME→OrderQuantityUnit`, `NETWR→NetAmount`, `WAERK→TransactionCurrency`. Die genauen Feldnamen von `I_SalesDocumentItem` am besten per Code-Vervollständigung in ADT prüfen.

In einer RAP-Architektur exponiert man diese Interface-View (`ZI_`) typischerweise über eine Konsum-View (`ZC_... as projection on ZI_...`), in der die UI-Annotationen für den OData-Service liegen.

---

<details><summary>Denkprozess (53869 Zeichen)</summary>

The user is asking in German for a CDS View Entity (define view entity) called ZI_SalesOrderItem based on I_SalesDocumentItem (or VBAP) with:
1. Association to Material (I_Product)
2. UI annotations (@UI.lineItem)
3. A calculated field 'NetValuePerUnit'
4. @Semantics annotations for amount and currency
5. Explanation of the annotations

This is a SAP ABAP CDS (Core Data Services) development question. Let me write a proper CDS view entity.

Key points for modern CDS view entities:
- `define view entity` syntax (not the old `define view`)
- Associations instead of joins
- `@AccessControl.authorizationCheck` annotation
- `@EndUserText.label` annotation
- Root view or not? Since it's an item view, probably not root, but could be a projection or standalone
- Calculated fields: In CDS view entities, you can use expressions directly in the element list (unlike old views where you needed extension views or computed via case). Arithmetic expressions are allowed directly.
- Currency semantics: `@Semantics.amount.currencyField: 'Currency'`
- For NetValuePerUnit: NetValue / Quantity — need to be careful about division by zero, and the result semantics. The result would be an amount per unit — semantically it's still an amount (currency) per quantity unit. Typically you'd annotate it as amount with currency field.

Let me draft the view:

```abap
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Vertriebsbelegposition'
@Metadata.allowExtensions: true
define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
{
      @UI.lineItem: [{ position: 10, label: 'Vertriebsbeleg' }]
  key SalesDocument,
      @UI.lineItem: [{ position: 20, label: 'Position' }]
  key SalesDocumentItem,

      @UI.lineItem: [{ position: 30, label: 'Material' }]
      @Consumption.valueHelpDefinition: [{ entity: { name: 'I_Product', element: 'Product' } }]
      Product,

      // Association zum Material
      @Consumption.semanticObject: 'Product'
      _Product,

      @UI.lineItem: [{ position: 40, label: 'Menge' }]
      @Semantics.quantity.unitOfMeasureField: 'SalesDocumentItemUnit'
      OrderQuantity,

      @UI.lineItem: [{ position: 50, label: 'Mengeneinheit' }]
      SalesDocumentItemUnit,

      @UI.lineItem: [{ position: 60, label: 'Nettowert' }]
      @Semantics.amount.currencyField: 'TransactionCurrency'
      NetAmount,

      @UI.lineItem: [{ position: 70, label: 'Währung' }]
      TransactionCurrency,

      // Berechnetes Feld
      @UI.lineItem: [{ position: 80, label: 'Nettowert pro Einheit' }]
      @Semantics.amount.currencyField: 'TransactionCurrency'
      cast( NetAmount / OrderQuantity as abap.dec(15,2) ) as NetValuePerUnit,

      _Product
}
```

Wait — associations must be listed at the end (or they can be anywhere, but conventionally at the end). Also, in view entities, the association exposure: `_Product` at the end exposes the association.

Also need to define the association itself. In view entities, associations are defined in the header:

```abap
define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
  association [0..1] to I_Product as _Product
    on $projection.Product = _Product.Product
{
```

Actually, for I_SalesDocumentItem, there's already an association to I_Product? Let me think. I_SalesDocumentItem (released CDS view for VBAP) — it has associations like _SalesDocument, _Product? Hmm. Actually I_SalesDocumentItem does have an association `_Product` I believe. But the user wants us to define the association, so we can either reuse or define our own. To be safe and instructive, define the association explicitly with `association [0..1] to I_Product as _Product on $projection.Product = _Product.Product`.

Note: In CDS view entities, association targets must be... any CDS entity (view entity, table, etc.). I_Product is fine.

Calculated field: In view entities, arithmetic expressions are allowed directly in the element list. `NetAmount / OrderQuantity` — division by zero: if OrderQuantity is 0, the result is... in ABAP CDS, division by zero leads to an error/dump? Actually in CDS, division by zero results in an error. There's `division()` function? In CDS there are built-in functions: `division(operand1, operand2, decimals)` — actually `division` is a SQL function in ABAP CDS: `DIVISION(1,2,2)`? Hmm. In ABAP SQL and CDS there's `DIV` (integer division), `DIVISION(arg1, arg2, dec)` — yes, `DIVISION` is available in ABAP SQL expressions and CDS view entities: `division(operand1, operand2, scale)`. Also `ddiv`? Let me recall.

ABAP CDS built-in functions:
- `DIV` — integer division
- `MOD` — remainder
- `DIVISION(n, d, dec)` — decimal division with specified decimals
- `ROUND(n, dec)`
- `CURR_ROUND`? no...
- `division` is available since 7.40? In view entities definitely.

Also `FLTP_TO_DEC`, `DEC_TO_FLTP`? There's `fltptodec`? Hmm.

For a robust example, use division with zero check:

```abap
case OrderQuantity
  when 0 then cast( 0 as abap.dec(15,2) )
  else division( NetAmount, OrderQuantity, 2 )
end as NetValuePerUnit
```

Hmm, but case with `when 0` — OrderQuantity is a quantity field of type QUAN (dec). Comparing to 0 is fine.

Actually simpler: `division( NetAmount, OrderQuantity, 2 )` — but division by zero would cause runtime error. Better to guard. Or use `coalesce`? Not for zero check.

Alternatively use `NetAmount / OrderQuantity` with cast. In view entities, the `/` operator is allowed for arithmetic. The result type of division: decimal? The precision might be an issue. Using `division(...,2)` gives controlled decimals.

Let me write:

```abap
@Semantics.amount.currencyField: 'TransactionCurrency'
@UI.lineItem: [{ position: 80, label: 'Nettowert pro ME' }]
@EndUserText.label: 'Nettowert pro Einheit'
case when OrderQuantity <> 0
     then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec(15,2) )
     else cast( 0 as abap.dec(15,2) )
end as NetValuePerUnit
```

Hmm, `division(NetAmount, OrderQuantity, 2)` — division expects decimal operands; NetAmount is CURR (dec 16,2 or similar), OrderQuantity is QUAN. Should be fine.

Actually, is `<>` allowed in CDS case? Yes: `case when condition then ... else ... end`. Conditions support `=, <>, <, >, <=, >=`, BETWEEN, LIKE, IS NULL, boolean AND/OR/NOT.

Alternatively simpler for teaching purposes:

```abap
NetAmount / OrderQuantity as NetValuePerUnit
```

with a note about division by zero. But better to show the robust version. Maybe show the simple version in main code with division() and mention the guard.

Let me also consider: should the view be based on I_SalesDocumentItem or directly on VBAP? The user says "auf I_SalesDocumentItem bzw. VBAP" — meaning "on I_SalesDocumentItem or VBAP". Best practice: use the released I_SalesDocumentItem. I can mention the alternative of using VBAP directly (for custom tables or when released views aren't available), maybe show a variant header.

Also annotations:
- `@AccessControl.authorizationCheck: #CHECK` (or #NOT_REQUIRED for demo)
- `@Metadata.allowExtensions: true` so metadata extensions can be used
- `@EndUserText.label`
- `@UI.lineItem` with position and label
- `@Semantics.amount.currencyField` for amounts
- `@Semantics.quantity.unitOfMeasureField` for quantities
- `@Consumption.valueHelpDefinition` for value help on Product
- `@ObjectModel.text.element`? Not needed.
- Maybe `@UI.hidden`? Not needed.

Also for the association: `@Consumption.semanticObject: 'Product'`? That's for Fiori semantic object linking. Could include.

Also `@UI.fieldControl`? Not necessary.

Also might add `@UI.selectionField` for filter fields — nice to mention.

Let me think about the actual fields in I_SalesDocumentItem:
- SalesDocument
- SalesDocumentItem
- Product (there's `Product` field)
- OrderQuantity (type QUAN) — actually in I_SalesDocumentItem, the field is `OrderQuantity` with unit `OrderQuantityUnit`? Let me recall. In I_SalesDocumentItem: SalesDocumentItemUnit? Hmm.

I_SalesDocumentItem fields (from SAP released view): SalesDocument, SalesDocumentItem, SalesDocumentItemCategory, Product, OrderQuantity, OrderQuantityUnit, RequestedDeliveryDate, ... NetAmount, TransactionCurrency, ItemGrossAmount, ... The unit field: I believe it's `OrderQuantityUnit`. Hmm, or `SalesDocumentItemUnit`. Let me think.

In I_SalesDocumentItem, I recall fields:
- SalesDocument
- SalesDocumentItem
- SalesDocumentItemCategory
- SalesDocumentItemType?
- Product
- OrderQuantity
- OrderQuantityUnit
- TransactionCurrency
- NetAmount
- ItemNetAmount? 

Actually the standard view I_SalesDocumentItem has: `OrderQuantity`, `OrderQuantityUnit`, `NetAmount`, `TransactionCurrency`, `Product`, `RequestedDeliveryDate`, `HigherLevelItem`, ... I'm fairly confident about `OrderQuantity` and `OrderQuantityUnit`. Hmm, but there's also `SalesDocumentItemUnit`? In some views like I_SalesDocumentItemBasic? Let me think about I_SalesOrderItem — that one is deprecated/replaced by I_SalesDocumentItem. In I_SalesOrderItem (old), fields: SalesOrder, SalesOrderItem, Material (older name), OrderQuantity, OrderQuantityUnit, NetAmount, TransactionCurrency.

For I_SalesDocumentItem (the newer released one), I believe the fields include:
- SalesDocument
- SalesDocumentItem
- Product
- OrderQuantity
- OrderQuantityUnit
- NetAmount
- TransactionCurrency
- SalesDocumentItemCategory

I'll go with OrderQuantity and OrderQuantityUnit, and note that field names may vary. Actually to be safe, I could mention "Feldnamen können je nach Release leicht abweichen". That's honest.

Alternatively, base on VBAP directly: VBELN, POSNR, MATNR, KWMENG, VRKME, NETWR, WAERK. If using VBAP, the association to I_Product would be on VBAP~MATNR = _Product.Product. But VBAP is not a released API; better practice is I_SalesDocumentItem. I'll show the I_SalesDocumentItem version as primary and mention VBAP variant briefly.

Let me also handle currency: TransactionCurrency in I_SalesDocumentItem — yes, that exists.

Now the association definition:

```abap
define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
  association [0..1] to I_Product as _Product
    on $projection.Product = _Product.Product
{
```

Cardinality [0..1] because Product might not exist (or product field could be empty). Could also use [1..1] but [0..1] is safer for left outer join semantics.

Note: In view entities, you can also just reuse an existing association from the source: `_Product` might already exist in I_SalesDocumentItem. Then you could do `association [0..1] to I_Product as _Product on ...` anyway or redirect. Simpler to define our own.

Full code:

```abap
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Vertriebsbelegposition - Grunddaten'
@Metadata.allowExtensions: true
@UI.headerInfo: [{ typeName: 'Position', typeNamePlural: 'Positionen' }]

define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
  association [0..1] to I_Product as _Product
    on $projection.Product = _Product.Product
{
      @UI.lineItem: [ { position: 10, label: 'Beleg' } ]
      @UI.selectionField: [ { position: 10 } ]
  key SalesDocument,

      @UI.lineItem: [ { position: 20, label: 'Position' } ]
  key SalesDocumentItem,

      @UI.lineItem: [ { position: 30, label: 'Material' } ]
      @Consumption.valueHelpDefinition:
        [ { entity: { name: 'I_Product', element: 'Product' } } ]
      Product,

      @UI.lineItem: [ { position: 40, label: 'Menge' } ]
      @Semantics.quantity.unitOfMeasureField: 'OrderQuantityUnit'
      OrderQuantity,

      @UI.lineItem: [ { position: 50, label: 'ME' } ]
      OrderQuantityUnit,

      @UI.lineItem: [ { position: 60, label: 'Nettowert' } ]
      @Semantics.amount.currencyField: 'TransactionCurrency'
      NetAmount,

      @UI.lineItem: [ { position: 70, label: 'Währung' } ]
      TransactionCurrency,

      @UI.lineItem: [ { position: 80, label: 'Nettowert / ME' } ]
      @Semantics.amount.currencyField: 'TransactionCurrency'
      case OrderQuantity
        when 0 then cast( 0 as abap.dec(15,2) )
        else division( NetAmount, OrderQuantity, 2 )
      end as NetValuePerUnit,

      // Assoziation zum Material
      _Product
}
```

Wait — `case OrderQuantity when 0 then ...` — simple case syntax: `case operand when value then result ... else ... end`. That works in CDS. But OrderQuantity is QUAN dec — comparing with 0 literal fine.

Hmm, one issue: `division(NetAmount, OrderQuantity, 2)` — the DIVISION function signature: `DIVISION(arg1, arg2, scale)` where scale is the number of decimal places, must be a literal or typed literal between 0 and 6? Actually scale can be 0-6? I think division's third parameter is the number of decimal places, an integer literal. Yes.

Result type of division: dec with the specified decimals? The result type is determined... For division(arg1, arg2, dec), result has dec decimal places. Casting to abap.dec(15,2) is then somewhat redundant but harmless. Actually maybe skip the cast in else branch and just do:

```abap
case when OrderQuantity <> 0 then division( NetAmount, OrderQuantity, 2 ) else 0 end as NetValuePerUnit
```

Hmm, mixing types in case branches — the else 0 would be int, might cause type conflict. Better cast: `cast( 0 as abap.dec(15,2) )`? Actually the case result type is determined by all branches; a literal 0 might be fine and get converted. To be safe, keep the cast.

Alternatively simpler and commonly seen:

```abap
@Semantics.amount.currencyField: 'TransactionCurrency'
NetAmount / OrderQuantity as NetValuePerUnit,
```

But division by zero risk. In CDS, division by zero raises an exception at runtime? In ABAP SQL, division by zero causes a runtime error (CX_SY_ZERODIVIDE? in Open SQL it's a dump / SQL error). Actually for `/` in ABAP SQL/CDS: "If the divisor is 0, the result is... error"? I believe division by zero leads to a runtime error in ABAP SQL expressions. Hmm, actually in HANA SQL, division by zero returns NULL? No — in HANA, 1/0 gives error "division by zero" (error 304). HANA has `NULLIF` to guard. In ABAP CDS, there's no automatic null handling; you'd use `case`.

I'll show the guarded version with `division()` and explain why. Also mention `NULLIF`? HANA supports NULLIF; ABAP CDS doesn't have NULLIF as built-in? Actually ABAP CDS doesn't support NULLIF directly I think. Use case.

Also, semantically, "NetValuePerUnit" is amount per unit — annotating with @Semantics.amount.currencyField is right (it's a currency amount). Some might argue it's a "quantity per..." no, it's value per unit = price. So amount annotation is correct.

Should I also add `@Semantics.amount.currencyCode`? No — `currencyField` is correct for CDS. (`currencyCode` is for BW/other contexts.) In CDS: `@Semantics.amount.currencyField: 'CurrencyField'`.

Also add `@ObjectModel.foreignKey.association: '_Product'` on Product? That's a nice touch:

```abap
@ObjectModel.foreignKey.association: '_Product'
Product,
```

Hmm, foreign key association requires the association target to have the key. I_Product.Product is the key. This is valid and commonly used. Could include but might complicate. I'll include it as optional or just mention.

Also, if this view is meant for a Fiori Elements list report, `@UI.lineItem` is what matters. Also `@Search.defaultSearchElement` etc. — skip, keep focused.

Also should I make it a root view for RAP? The name ZI_SalesOrderItem suggests an interface view (I = interface). Could add `define root view entity` if used in RAP BO. But the user just asked for a view on I_SalesDocumentItem with association — not necessarily RAP. I'll keep non-root but mention that for RAP you'd add `root` and composition etc. Maybe briefly.

Explanations (in German since the question is German):

1. **define view entity** — modern syntax since ABAP 7.55/7.56 (actually view entities since 7.52, on-prem 1902+? View entities available since ABAP 7.52? No — CDS view entities since ABAP Platform 2020 / 7.56? Let me recall: CDS view entities were introduced with ABAP 7.52? Hmm. CDS view entities introduced in ABAP Platform 1902? Actually: CDS view entities available since ABAP 7.52? I think view entities came with 7.52 (S/4 1709?) no...

Let me get this right: CDS view entities were introduced with ABAP Platform 2020 (7.56)? Hmm. I recall "CDS view entities" introduced in ABAP 7.52? Checking memory: The ABAP keyword documentation: "CDS view entities are available since ABAP release 7.52"? I believe view entities were introduced in ABAP 7.52 (on-prem) — no wait, 7.52 introduced "CDS view entities"? 

Timeline: 
- 7.40: CDS views (define view), annotations
- 7.50: ...
- 7.51: ...
- 7.52 (2018, S/4 1809): CDS table functions, ... hmm
- ABAP Platform 2020 / 7.56 (S/4 2020): CDS view entities introduced? 

I recall the SAP blog "CDS View Entities — What's New" from 2019/2020 saying view entities are available "as of ABAP Platform 2020" i.e., 7.56, S/4HANA 2020. Hmm, but also there was an earlier introduction in the cloud (ABAP Cloud / Steampunk 1905+). I'm fairly confident: CDS view entities introduced with ABAP Platform 2020 (S/4HANA 2020, ABAP 7.56), and in BTP ABAP Environment earlier (1908+?). For the answer, I can just say "ab ABAP Platform 2020 (7.56) bzw. ABAP Environment" — or keep it vague: "moderner Nachfolger der klassischen CDS Views". I'll say available since ABAP 7.56 / S/4HANA 2020 — that's the commonly cited fact. Yes, DDL source "define view entity" — since ABAP Platform 2020. Good.

2. **Association [0..1] to I_Product as _Product on ...** — lazy join, only joined when accessed; $projection refers to element in the SELECT list. Cardinality.

3. **@UI.lineItem** — defines columns in Fiori Elements list report tables; position = column order; label = column header. Also mention that labels can/should be maintained via metadata extension (@Metadata.layer) and @Metadata.allowExtensions.

4. **@Semantics.amount.currencyField** — links amount field to currency key field so Fiori/UI renders currency symbol and correct decimals; also relevant for OData $metadata (V2: sap:unit? Actually currency code mapping). Similarly @Semantics.quantity.unitOfMeasureField for quantities.

5. **Calculated field** — expressions allowed directly in view entities element list (unlike old views where you could also do expressions? Actually old CDS views also allowed expressions in element list since 7.40 SPxx; but view entities allow more, e.g., expressions in associations, etc.). division() function with 2 decimals; guard against division by zero with case; cast for result type.

6. **@AccessControl.authorizationCheck** — #CHECK means DCL must exist; #NOT_REQUIRED for demo.

7. **@Metadata.allowExtensions: true** — allows METADATA EXTENSION to move UI annotations out of the base view.

8. **@Consumption.valueHelpDefinition** — value help for Product field.

9. Why I_SalesDocumentItem instead of VBAP: released CDS view = stable API, VDM; VBAP direct access not recommended (not released for custom development in S/4; "released objects" concept). Mention that if you must use VBAP (e.g., ECC), the fields map: VBELN→SalesDocument, POSNR→SalesDocumentItem, MATNR→Product, KWMENG→OrderQuantity, VRKME→OrderQuantityUnit, NETWR→NetAmount, WAERK→TransactionCurrency.

Also note: association to I_Product — in the SELECT list, exposing `_Product` at the end. Also could add fields from _Product like `_Product.ProductType`? Not needed; but I could show that association fields can be selected: e.g., `_Product.ProductText[1].ProductName`? Hmm, path expressions with default filter... Keep simple. Maybe show one example: select `_Product.ProductType` as ProductType? That would turn association into join when used. Could mention that.

Actually, to demonstrate association usage, I could include a field from the association:

```abap
_Product.ProductType as ProductType,  // would trigger join
```

But better to keep association unjoined (pure association) and explain that it's only joined when the consumer requests fields. Maybe mention both options. I'll keep the association exposed but not used, and explain the benefit (lazy evaluation, reuse in consumers/other views via association redirection).

Also, is `TransactionCurrency` the right field name in I_SalesDocumentItem? I believe yes. And NetAmount — yes, I_SalesDocumentItem has NetAmount. OrderQuantity — yes. OrderQuantityUnit — I think so. Let me double check mentally: I_SalesDocumentItem in S/4: fields include SalesDocument, SalesDocumentItem, SalesDocumentItemCategory, SalesDocumentItemText?, Product, ProductDescription? (maybe via association _ProductText), OrderQuantity, OrderQuantityUnit, RequestedDeliveryDate, ItemBillingBlockReason, ... NetAmount, TransactionCurrency, ... I'm reasonably confident. I'll add a note that field names should be checked in ADT (code completion).

Also add `@EndUserText.label` per element? The @UI.lineItem label covers column headers. Could also add @EndUserText.label on elements — redundant. Skip.

Maybe also add @UI.lineItem importance? `@UI.lineItem: [{ position: 10, importance: #HIGH }]` — importance is used for search results. Optional; keep simple.

Also for currency field TransactionCurrency maybe add @UI.hidden? Some hide the currency column since the amount shows it. Could mention as tip: currency/unit fields often hidden in lineItem because the amount displays them. I'll annotate TransactionCurrency and OrderQuantityUnit with @UI.hidden: true? Hmm — if hidden, they still exist for semantics. That's a common pattern. But then the user sees less. I could show it and explain. Let me include @UI.hidden on the unit/currency fields with explanation — that's a nice practical touch. Actually, careful: In Fiori Elements, the currency is displayed with the amount automatically when the currency field is part of the entity. Marking it @UI.hidden removes the standalone column. I'll include it and explain.

Hmm, but if I hide them, the example shows fewer lineItem annotations... It's fine, I'll include hidden annotations and explain.

Let me also think about whether `division` exists in CDS view entities: Yes — ABAP CDS built-in functions in view entities include: DIVISION(arg1, arg2, dec), ROUND, ... Actually the SQL function is `division`. In ABAP SQL: `division( expr1, expr2, dec )`. Yes, available in CDS view entities and ABAP SQL since 7.54? The SQL function DIVISION is available since release 7.54? Hmm. Let me recall: ABAP SQL functions: `div`, `mod`, `division` — DIVISION introduced in 7.54? I think `division` SQL function was added with 7.54 (or 7.53). For view entities (7.56+) it's definitely available. Fine.

Alternatively, to be maximally safe, use plain `/` with cast:

```abap
cast( NetAmount / OrderQuantity as abap.dec(15,2) ) as NetValuePerUnit
```

But division-by-zero. The case guard handles it. With `/` the result type rules: for decimal operands, result type is determined by... could have many decimals. division(...,2) is cleaner. I'll use division and mention the simple `/` alternative.

Actually, hmm: does `division()` require both arguments to be decimal? NetAmount is CURR → treated as dec. OrderQuantity is QUAN → dec. OK.

One more consideration: `case OrderQuantity when 0 then ...` — simple case compares equality; with dec type and literal 0, fine. But what about NULL? If OrderQuantity is null, simple case → else branch? In SQL, NULL = 0 is unknown → goes to else. Good, else gives 0. Fine.

Alternatively searched case: `case when OrderQuantity <> 0 then ... else ... end`. If OrderQuantity is NULL, condition is unknown → else → 0. Good either way.

Let me also consider adding `@Semantics.amount.currencyField` needs the currency field to be in the same view — yes, TransactionCurrency is selected.

Now, about `@AccessControl.authorizationCheck: #CHECK` — if no DCL exists, activation gives warning/error? With #CHECK, at runtime authorization check is performed if DCL exists; activation warns if no DCL. For a demo, `#NOT_REQUIRED` avoids warnings. I'll use #CHECK and mention alternatives, or use #NOT_REQUIRED with comment. I'll use #CHECK and explain. Hmm, for copy-paste friendliness, #NOT_REQUIRED might be smoother. I'll use #CHECK but explain that you need a DCL or switch to #NOT_REQUIRED for tests. Actually let me use `#CHECK` with a comment — good practice teaching. Or `#NOT_REQUIRED` with comment "für Demo; im Produktivbetrieb #CHECK + DCL". I'll go with #CHECK and note.

Also `@Metadata.allowExtensions: true` — then suggest MDE example briefly? Maybe just mention.

Should I show a short metadata extension example? Could be nice but adds length. The user asked to explain the annotations — a brief MDE mention is enough.

Also mention: view entity names ZI_... convention: Z + I (interface view). 

Also the association: name `_Product` with underscore convention.

Now structure of the answer (in German):

1. Short intro sentence.
2. Code block with full view entity.
3. Explanation sections:
   - View entity vs. classic view (define view entity, associations, expressions)
   - Association to I_Product (cardinality, $projection, lazy join)
   - @UI.lineItem (list report columns, position, label; @UI.selectionField; @UI.hidden)
   - @Semantics.amount.currencyField / quantity.unitOfMeasureField (currency/quantity handling in UI + OData)
   - Calculated field NetValuePerUnit (expression, division(), case guard, cast)
   - Other annotations: AccessControl, EndUserText, Metadata.allowExtensions, Consumption.valueHelpDefinition
4. Variant note: VBAP direct (field mapping) and released-views best practice.
5. Maybe note on metadata extension.

Keep it reasonably concise but thorough. Use headers and code blocks. German language. Format: markdown with ## headers, abap code fences.

Let me write the final code carefully:

```abap
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Vertriebsbelegposition'
@Metadata.allowExtensions: true

define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
  association [0..1] to I_Product as _Product
    on $projection.Product = _Product.Product
{
      @UI.lineItem: [ { position: 10, label: 'Vertriebsbeleg' } ]
      @UI.selectionField: [ { position: 10 } ]
  key SalesDocument,

      @UI.lineItem: [ { position: 20, label: 'Position' } ]
  key SalesDocumentItem,

      @UI.lineItem: [ { position: 30, label: 'Material' } ]
      @Consumption.valueHelpDefinition: [{ entity: { name: 'I_Product', element: 'Product' } }]
      @ObjectModel.foreignKey.association: '_Product'
      Product,

      @UI.lineItem: [ { position: 40, label: 'Menge' } ]
      @Semantics.quantity.unitOfMeasureField: 'OrderQuantityUnit'
      OrderQuantity,

      @UI.hidden: true
      OrderQuantityUnit,

      @UI.lineItem: [ { position: 50, label: 'Nettowert' } ]
      @Semantics.amount.currencyField: 'TransactionCurrency'
      NetAmount,

      @UI.hidden: true
      TransactionCurrency,

      @UI.lineItem: [ { position: 60, label: 'Nettowert pro ME' } ]
      @Semantics.amount.currencyField: 'TransactionCurrency'
      case OrderQuantity
        when 0 then cast( 0 as abap.dec( 15, 2 ) )
        else division( NetAmount, OrderQuantity, 2 )
      end as NetValuePerUnit,

      _Product
}
```

Wait: division result type — division(NetAmount, OrderQuantity, 2) returns dec like... The result of division(arg1, arg2, dec): type is dec with dec decimals? Actually the result type of DIVISION: "The result has the data type DEC with the number of decimal places specified by dec"? Hmm, I recall the result type of division is determined: if both operands are dec, result is dec with length... The docs: "DIVISION(arg1, arg2, dec): ... The result is rounded to dec decimal places. The data type of the result is..." I believe for decimal operands the result is DEC with dec decimals. So the cast isn't strictly needed in the then-branch consistency: then-branch cast(0 as abap.dec(15,2)) vs else division result dec(?,2). Type unification: case branches must have compatible types; they'll be merged. Should be OK. Actually to be safe, wrap division in cast too:

```abap
case OrderQuantity
  when 0 then cast( 0 as abap.dec( 15, 2 ) )
  else cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec( 15, 2 ) )
end as NetValuePerUnit
```

Hmm, casting a dec to dec(15,2) — cast between dec types allowed? CAST in CDS: allowed casts between numeric types... casting dec to dec is allowed? CAST supports conversions among numeric types (int, dec, fltp, etc.). Casting DEC(16,2) to DEC(15,2) — I think cast between DEC types is allowed (it's a "lossless"? no, but allowed). Actually ABAP CDS CAST rules: conversions allowed between numeric types including dec→dec? The cast matrix: INT1/INT2/INT4/INT8, DEC, CURR, QUAN, FLTP, DECFLOAT... DEC to DEC is allowed I believe. Hmm, is casting CURR to DEC allowed? Yes, numeric to numeric generally allowed except some restrictions (e.g., FLTP to DEC allowed? there are some restrictions like FLTP→DEC allowed? I recall FLTP can be cast to DEC? Actually the CAST matrix in ABAP CDS: from FLTP to DEC is allowed? Let me think... The documentation "CDS DDL - CAST, conversion matrix": FLTP → DEC/ CURR/ QUAN: allowed? I believe FLTP→DEC is allowed. And DEC→DEC allowed.)

To reduce risk, maybe simpler: use the plain division operator with case:

```abap
case when OrderQuantity <> 0
     then NetAmount / OrderQuantity
     else cast( 0 as abap.dec(15,2) )
end as NetValuePerUnit
```

But then result type of NetAmount / OrderQuantity: for `/` with decimal operands, the result type is... In ABAP SQL, division of two decimals: result type DEC with length 16 and... hmm, the rules: "The result type of / for decimal operands is DEC(16, ...)"? Actually for ABAP SQL arithmetic with decimal: result of division has type DEC(16, 14)? No...

ABAP SQL arithmetic rules: For `/` with decimal operands, the result has decimal places... The documentation: "If both operands are decimal, the result is decimal with 16 digits? and the number of decimal places is..." I recall: division of two DEC: result DEC with p = 16? and s = s1 - s2 + something? There's a defined rule. The result might have too many decimals for currency display, hence cast to dec(15,2) is good.

I think using division(...,2) is cleaner and well-documented. Let me keep division with cast on both branches for type consistency. Actually, is `cast( 0 as abap.dec(15,2) )` fine? Yes, casting integer literal to dec is allowed.

Hmm, one more consideration: in the simple-case syntax `case OrderQuantity when 0 then ...`, comparing QUAN with 0 — allowed. OK.

Alternatively use searched case for clarity. I'll use searched case:

```abap
case
  when OrderQuantity <> 0
    then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec( 15, 2 ) )
  else cast( 0 as abap.dec( 15, 2 ) )
end as NetValuePerUnit
```

Wait — can `cast` wrap a function call? Yes, cast operand where operand can be an expression? In CDS view entities, CAST argument can be any expression? In classic CDS views, cast argument had to be an elementary expression/field? In view entities, cast can contain expressions? Hmm. In CDS view entities, "CAST" operand can be an expression? I believe in view entities, the argument of CAST can be any expression (including function calls) — yes, view entities allow expressions in more places. Actually let me think: In view entities, `cast( division(...) as ...)` — I'm fairly sure this is allowed since view entities support nesting of expressions. In classic views, cast argument could be a field, literal, case, or expression? Classic: "cast_expr: CAST( expr AS dtype)" where expr could be field, literal, case expression, arithmetic expression... I think it worked too. OK.

Alternatively avoid cast on division: division(NetAmount, OrderQuantity, 2) returns DEC with 2 decimals — then case type unification with cast(0 as dec(15,2))... The merged type would be fine. But to be safe, keep both casts. Hmm, actually there might be an issue: cast of division result to dec(15,2) — if NetAmount is dec(16,2) and division result is dec(?,2), casting to dec(15,2) could overflow if NetAmount huge — unlikely, fine.

Actually, maybe simpler and more robust: skip the else-branch zero and just document? No — division by zero dump is a real concern; keep the guard. Good teaching point.

Alternatively use `nullif`? Not available. Use case. Fine.

Also, should NetValuePerUnit get @EndUserText.label? The @UI.lineItem label covers the column; for other usages (e.g., OData), a label helps. Could add `@EndUserText.label: 'Nettowert pro Mengeneinheit'`. I'll add it on the calculated field since it has no DDIC label.

Also for other fields, labels come from the underlying I_SalesDocumentItem element labels (they propagate). Good to mention: labels are inherited from the source fields; @UI.lineItem label overrides for the list report.

Now the explanation part. Let me structure:

**Der Code** — code block.

**Erläuterungen:**

1. `define view entity` statt `define view`
   - modern syntax, since ABAP Platform 2020 (7.56) / ABAP Environment
   - advantages: stricter syntax, expressions allowed everywhere, associations more flexible, better performance (no implicit "select *" issues?), summary: view entities are the recommended technology; classic CDS views are deprecated for new development.

2. Association `_Product`
   - `association [0..1] to I_Product as _Product on $projection.Product = _Product.Product`
   - Cardinality [0..1]: product may not exist / Product can be empty → left outer join semantics, no rows lost
   - `$projection` refers to the field as selected in the element list
   - Lazy: join only executed when consumer requests fields of _Product (e.g., Fiori Element navigates, or another view selects _Product.X)
   - Exposing `_Product` at the end of the element list publishes it in the OData service ($metadata → navigation property)
   - Reuse: other views can redirect/extend

3. `@UI.lineItem`
   - Defines the columns of a table in Fiori Elements (list report / object page table)
   - `position`: column order; `label`: column caption (overrides inherited label)
   - Works together with `@UI.selectionField` (filter fields in the filter bar)
   - Best practice: keep UI annotations in a metadata extension (@Metadata.layer: #CORE) — enabled by @Metadata.allowExtensions: true

4. `@Semantics.amount.currencyField` / `@Semantics.quantity.unitOfMeasureField`
   - Links amount ↔ currency code and quantity ↔ unit
   - Fiori Elements renders the currency/unit with the value (e.g., "1.234,56 EUR"), correct decimal handling per currency (e.g., JPY 0 decimals)
   - In OData metadata the fields are flagged (sap:unit), so the UI knows
   - Without this annotation, amounts/quantities display as plain numbers
   - That's why currency/unit fields are often `@UI.hidden` — they appear alongside the amount automatically

5. Calculated field `NetValuePerUnit`
   - View entities allow expressions (arithmetic, case, functions) directly in the element list
   - `division(NetAmount, OrderQuantity, 2)`: SQL function with fixed 2 decimals — better control than `/` (which can produce many decimals / type surprises)
   - `case` guards against division by zero (runtime error otherwise)
   - `cast(... as abap.dec(15,2))` fixes the result type
   - Annotated as amount with the same currency → semantically a price
   - Note: calculated fields are computed at runtime of the view; for large data volumes consider whether it belongs in the view or in the consumer

6. Weitere Annotationen
   - `@AccessControl.authorizationCheck: #CHECK`: CDS access control (DCL) expected; #NOT_REQUIRED for demo; #NOT_ALLOWED forbids
   - `@EndUserText.label`: description shown in ADT, OData, etc.
   - `@Consumption.valueHelpDefinition`: value help for the Product field in Fiori
   - `@ObjectModel.foreignKey.association: '_Product'`: declares Product as foreign key via association (input validation, value help derivation)

7. Hinweis zu VBAP vs. I_SalesDocumentItem
   - I_SalesDocumentItem is the released VDM view — stable contract, upgrade-safe
   - Direct access to VBAP is not released (C1) in S/4HANA; only if necessary (e.g., ECC system without VDM), mapping: VBELN/POSNR/MATNR/KWMENG/VRKME/NETWR/WAERK
   - Field names in I_SalesDocumentItem can be checked via ADT code completion

Maybe also a tiny note: for RAP, add `root` and provider contract if needed. Keep short.

Length: This is a technical request; a fairly complete answer with code + explanations is appropriate. Use German. Use headers and bullet lists. Avoid excessive length — keep explanations crisp.

Let me double-check syntax details:

- Annotation placement above elements with proper indentation — fine.
- `@UI.lineItem: [ { position: 10, label: 'Vertriebsbeleg' } ]` — correct array syntax.
- `@UI.selectionField: [ { position: 10 } ]` — correct.
- `@Consumption.valueHelpDefinition: [{ entity: { name: 'I_Product', element: 'Product' } }]` — correct.
- `@ObjectModel.foreignKey.association: '_Product'` — correct.
- `@Semantics.quantity.unitOfMeasureField: 'OrderQuantityUnit'` — correct.
- `@UI.hidden: true` — correct (or `@UI.hidden: [ { value: true } ]`? No, `@UI.hidden: true` is valid).
- Association on-clause with `$projection.Product` — correct for view entities (in classic views also allowed).
- Key fields: `key SalesDocument, key SalesDocumentItem` — the view should have keys; I_SalesDocumentItem keys are SalesDocument, SalesDocumentItem. Good.
- Exposing `_Product` at end without semicolon — correct, last element no comma.

One subtlety: If I annotate `@ObjectModel.foreignKey.association: '_Product'` on Product, the association must be defined — it is. OK.

Another subtlety: `division` — in CDS, function name is `division` lowercase; fine.

Also: does `case ... end as NetValuePerUnit` need the alias? Yes, `end as NetValuePerUnit` — correct syntax: `case ... end as NetValuePerUnit`.

Also the element list in view entities: expressions like case are allowed as elements. Yes.

Potential issue: `when OrderQuantity <> 0` — `<>` is valid in CDS conditions. Yes.

Also, should I use `OrderQuantity` vs `OrderQuantity`? In I_SalesDocumentItem the quantity field... Let me reconsider. Searching memory of I_SalesDocumentItem (CDS view, released for C1? It's released): Fields include:
- SalesDocument
- SalesDocumentItem
- SalesDocumentItemCategory
- SalesDocumentItemType?
- SalesDocumentItemProcessType?
- Product
- ProductCharacteristic1? no...
- OrderQuantity
- OrderQuantityUnit
- ItemVolume? ...
- NetAmount
- TransactionCurrency
- ItemGrossAmount
- TaxAmount
- RequestedDeliveryDate
- ItemDeliveryPriority?
- ...

I'm fairly confident about OrderQuantity, OrderQuantityUnit, NetAmount, TransactionCurrency, Product. There's also `SalesDocumentItemUnit`? Hmm, in I_SalesDocumentItem there might be both OrderQuantityUnit and... Actually I recall in I_SalesDocumentItem: `OrderQuantityUnit` — yes. And `TargetQuantity`? whatever. I'll add a note: "Feldnamen ggf. per Code-Completion in ADT prüfen".

Alternatively, to be extra safe, I could base the example on I_SalesDocumentItem but note the alternative VBAP mapping. Good.

Also worth noting: I_SalesDocumentItem already contains an association `_Product`? If it does, one could simply reuse it by selecting `_Product` — but defining our own is explicit and works regardless. Actually if I_SalesDocumentItem already has _Product, defining our own association with the same target is still fine (different name _Product in our view... wait, if we define `association ... as _Product` on our view, that's our own; no conflict with source's association since we reference source's fields via $projection.Product). Fine.

Hmm, one more: In view entities, association targets: I_Product is a view entity? I_Product is a CDS view (classic) or view entity depending on release; either way it's a valid association target (any CDS entity). Fine.

Also: `@Metadata.allowExtensions: true` — correct annotation name.

Also maybe add `@ObjectModel.representativeKey`? Not needed.

Also `@UI.headerInfo` — optional; skip or include? I'll skip to keep focus, or include briefly. The user asked specifically for @UI.lineItem; I'll keep headerInfo out to reduce noise. Maybe mention in one line.

Now write the explanation of annotations clearly and compactly. The user explicitly asked "Erkläre die Annotationen." So explanations are required — good structure with a table or bullets. A table could work nicely: Annotation | Wirkung. But detailed explanations per group with short bullets might be better. I'll do grouped bullets with bold annotation names.

Also explain the calculated field and association (not annotations per se, but asked).

Format plan:
- Brief intro (1 sentence)
- Code block (the view)
- "Erläuterung" section with subsections:
  - **Grundgerüst / view entity**
  - **Assoziation _Product**
  - **@UI.lineItem (+ selectionField, hidden)**
  - **@Semantics.amount / quantity**
  - **Berechnetes Feld NetValuePerUnit**
  - **Sonstige Annotationen** (AccessControl, EndUserText, Metadata.allowExtensions, Consumption.valueHelp, ObjectModel.foreignKey)
- **Hinweis: I_SalesDocumentItem vs. VBAP** (short, with field mapping line)

Keep each subsection 2-5 bullets. Total moderate length. German throughout.

Let me also double check `division` parameter order: `division(dividend, divisor, decimals)` — yes: DIVISION(arg1, arg2, dec) = arg1 / arg2 rounded to dec decimal places.

One more check: In the case expression, `cast( 0 as abap.dec( 15, 2 ) )` — literal 0 cast to dec — allowed. Yes.

Also, is `NetValuePerUnit` a good name? Yes as requested.

Also currency field for NetValuePerUnit: TransactionCurrency — correct since NetAmount is in that currency.

Edge: If OrderQuantity is NULL (not initial), case goes to else → 0. Good.

Also mention: `@Semantics.amount.currencyField` on calculated field ensures the UI formats it as currency amount.

Now, about `@AccessControl.authorizationCheck: #CHECK` — when activating without DCL, you get a warning (not error). I'll note: "für erste Tests #NOT_REQUIRED setzen, sonst Warnung ohne DCL".

Write the VBAP mapping compactly:

VBAP: VBELN, POSNR, MATNR, KWMENG (Menge), VRKME (ME), NETWR (Nettowert), WAERK (Währung).

Also mention: in ECC there are no view entities? View entities require ABAP 7.56+; on older systems use `define view`. One line.

Also maybe mention that in the Fiori Elements context, this view would typically be exposed via a projection view (ZC_...) for consumption — one line at the end. Good practice note.

Let me finalize the code. Also consider adding `@UI.lineItem` importance? skip.

Final code:

```abap
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Vertriebsbelegposition'
@Metadata.allowExtensions: true

define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
  association [0..1] to I_Product as _Product
    on $projection.Product = _Product.Product
{
      @UI.lineItem: [ { position: 10, label: 'Vertriebsbeleg' } ]
      @UI.selectionField: [ { position: 10 } ]
  key SalesDocument,

      @UI.lineItem: [ { position: 20, label: 'Position' } ]
  key SalesDocumentItem,

      @UI.lineItem: [ { position: 30, label: 'Material' } ]
      @Consumption.valueHelpDefinition: [{ entity: { name: 'I_Product', element: 'Product' } }]
      @ObjectModel.foreignKey.association: '_Product'
      Product,

      @UI.lineItem: [ { position: 40, label: 'Menge' } ]
      @Semantics.quantity.unitOfMeasureField: 'OrderQuantityUnit'
      OrderQuantity,

      @UI.hidden: true
      OrderQuantityUnit,

      @UI.lineItem: [ { position: 50, label: 'Nettowert' } ]
      @Semantics.amount.currencyField: 'TransactionCurrency'
      NetAmount,

      @UI.hidden: true
      TransactionCurrency,

      @UI.lineItem: [ { position: 60, label: 'Nettowert pro ME' } ]
      @EndUserText.label: 'Nettowert pro Mengeneinheit'
      @Semantics.amount.currencyField: 'TransactionCurrency'
      case
        when OrderQuantity <> 0
          then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec( 15, 2 ) )
        else cast( 0 as abap.dec( 15, 2 ) )
      end as NetValuePerUnit,

      // Assoziation wird nach außen exponiert (OData-Navigation)
      _Product
}
```

Hmm — `@UI.hidden: true` on OrderQuantityUnit: but then the unit is not shown as separate column; the Menge column shows "10 EA" automatically due to unitOfMeasureField. Good, explain that.

Wait, one concern: `@UI.hidden: true` — is the syntax `@UI.hidden: true` valid? Yes, UI.hidden is a boolean annotation; in Fiori metadata it maps to hidden. Fine.

Also: should TransactionCurrency be hidden? Same logic. OK.

Explanations — let me draft in German:

### Warum `define view entity`?
- Seit ABAP Platform 2020 (ABAP 7.56) bzw. ABAP Environment der Nachfolger der klassischen CDS-View (`define view`). Strengere Syntax, bessere Performance bei manchen Operationen, Ausdrücke (Berechnungen, CASE, Funktionen) sind direkt in der Elementliste erlaubt. Klassische CDS Views gelten für Neuentwicklungen als obsolet ("deprecated").

### Assoziation `_Product`
- `association [0..1] to I_Product as _Product on $projection.Product = _Product.Product`
- Kardinalität [0..1]: Das Produkt kann fehlen (oder `Product` ist leer) → Verhalten wie LEFT OUTER JOIN, es gehen keine Positionen verloren. [1..1] würde wie INNER JOIN wirken? Actually [1..1] with missing target → also left outer? Hmm. In CDS, associations are translated to joins based on the join cardinality and usage; [1..1] vs [0..1] affects whether inner or left outer join is used when the association is used in a path: [1..1] → inner join, [0..1] → left outer join. Yes that's the rule for path expressions. So explain: [0..1] → left outer join bei Pfadnutzung; [1..1] → inner join.
- `$projection.Product` verweist auf das Feld in der SELECT-Liste dieser View.
- Lazy: Der Join wird nur erzeugt, wenn der Konsument tatsächlich Felder über die Assoziation liest (z. B. `_Product.ProductType` in einer Konsum-View oder Fiori-Element-Navigation). Dadurch bleibt die View schlank und wiederverwendbar.
- `_Product` am Ende der Elementliste exponiert die Assoziation → erscheint als Navigation Property im OData-Service.

### `@UI.lineItem`
- Definiert Spalten einer Tabelle in Fiori Elements (List Report, Object-Page-Tabellen).
- `position`: Reihenfolge der Spalten; `label`: Spaltentitel (überschreibt das geerbte DDIC-Label des Feldes).
- `@UI.selectionField` macht das Feld zusätzlich zum Filter in der Filterleiste.
- Felder ohne lineItem erscheinen nicht als Spalte (aber als Felder auf der Object Page, sofern @UI.identifier etc.).
- Best Practice: UI-Annotationen in eine Metadata Extension auslagern (`@Metadata.allowExtensions: true` ermöglicht das; dann `@Metadata.layer: #CORE` in der MDE).

### `@Semantics.amount.currencyField` / `@Semantics.quantity.unitOfMeasureField`
- Verknüpft Betrag ↔ Währungsschlüssel bzw. Menge ↔ Mengeneinheit.
- Fiori Elements rendert Betrag und Währung zusammen ("1.234,56 EUR"), berücksichtigt Währungsdezimalstellen (z. B. JPY ohne Nachkommastellen) und Mengeneinheiten.
- Im OData-Metadaten werden die Felder entsprechend markiert (sap:unit/sap:currency? In OData V2: sap:unit on the amount pointing to currency field). 
- Deshalb sind Währungs-/Einheitsfelder oft `@UI.hidden` — sie werden automatisch neben dem Betrag/zur Menge angezeigt, brauchen keine eigene Spalte.
- Ohne die Annotation würde der Betrag als "nackte" Zahl gerendert.

### Berechnetes Feld `NetValuePerUnit`
- View Entities erlauben Ausdrücke direkt in der Elementliste — kein separates Erweiterungs-View nötig.
- `division(NetAmount, OrderQuantity, 2)`: SQL-Funktion mit fester Nachkommastellenzahl (hier 2) — deterministischer als der `/`-Operator, dessen Ergebnistyp sonst je nach Operanden viele Nachkommastellen haben kann.
- `case ... when <> 0`: Schutz vor Division durch 0 (sonst Laufzeitfehler).
- `cast(... as abap.dec(15,2))`: fixiert den Ergebnistyp.
- Das Feld wird mit derselben Währung annotiert — fachlich ist es ein Preis (Betrag pro Einheit).
- Hinweis: Die Berechnung läuft zur Laufzeit der View (pushdown auf die DB). Für sehr große Datenmengen ggf. prüfen, ob das Feld in die Konsum-Schicht gehört.

### Sonstige Annotationen
- `@AccessControl.authorizationCheck: #CHECK`: Es wird ein Access-Control-Objekt (DCL) erwartet/benutzt. Für Spielwiesen: `#NOT_REQUIRED` (keine Prüfung, keine Warnung), `#NOT_ALLOWED` (Zugriffskontrolle explizit verboten).
- `@EndUserText.label`: Beschreibungstext der View (ADT, OData $metadata).
- `@Consumption.valueHelpDefinition`: Value Help für das Produktfeld im Fiori-UI.
- `@ObjectModel.foreignKey.association: '_Product'`: deklariert `Product` über die Assoziation als Fremdschlüssel (Grundlage für Value Help/Validierung).

### I_SalesDocumentItem vs. VBAP
- `I_SalesDocumentItem` ist die freigegebene (released, C1) Standard-View aus dem VDM — stabile Vertrags-API, upgrade-sicher. Direkter Zugriff auf `VBAP` ist in S/4HANA für kundeneigene Entwicklung nicht freigegeben.
- Falls doch VBAP (z. B. ECC/älteres Release): Feld-Mapping `VBELN→SalesDocument`, `POSNR→SalesDocumentItem`, `MATNR→Product`, `KWMENG→OrderQuantity`, `VRKME→OrderQuantityUnit`, `NETWR→NetAmount`, `WAERK→TransactionCurrency`; Assoziation dann `on $projection.Product = _Product.Product` mit MATNR.
- Feldnamen in I_SalesDocumentItem ggf. per Code-Vervollständigung in ADT prüfen (kleine Release-Unterschiede möglich).

Maybe a final line: In einer RAP-Architektur würde man diese Interface-View (ZI_) über eine Konsum-View (ZC_) mit UI-Annotationen für Fiori Elements exponieren; die lineItem-Annotationen könnten dann dorthin wandern.

I think that's comprehensive. Let me also double-check the case syntax once more:

```
case
  when OrderQuantity <> 0
    then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec( 15, 2 ) )
  else cast( 0 as abap.dec( 15, 2 ) )
end as NetValuePerUnit
```

Valid CDS searched case expression. Good.

One thing: `division` function — is it `division(operand1, operand2, decimals)`? Yes. Available in CDS view entities and ABAP SQL (since 7.54 for SQL functions? division since 7.54? I believe the SQL function DIVISION was introduced in ABAP 7.54? Hmm, actually I recall `division` being available in CDS for a while. For view entities (7.56+) definitely fine.)

Also, is `cast` around `division(...)` allowed? In view entities, cast argument can be an expression — yes, view entities allow arbitrary expressions inside cast. (In classic views, cast argument could also be an expression? The classic docs: "CAST( expr AS dtype)" where expr is "SQL expression"? I think in classic views cast argument could be field, literal, parameter, case, or expression too. Either way, fine for view entities.)

Also `abap.dec( 15, 2 )` — correct type syntax: `abap.dec(15,2)`. Yes.

Potential nitpick: For currency amounts, DEC(15,2) fine.

Also — should the view have `@Search` annotations? Not asked. Skip.

Also, `@UI.lineItem` label with German umlauts fine.

Now about `@UI.selectionField` — correct spelling: `@UI.selectionField: [ { position: 10 } ]`. Yes.

Also, in the code, I put `@UI.hidden: true` — could also write `@UI.hidden: true` — fine.

I should double check `@ObjectModel.foreignKey.association` annotation name: It's `@ObjectModel.foreignKey.association: '_Product'`. Yes.

Also `@Consumption.semanticObject: 'Product'` — optional; skip to avoid clutter, or include? Skip; value help is enough.

One more consideration on the association: Should I use `[0..1]` or `[1..1]`? For I_Product lookup by Product key, [1..1] would be semantically right if Product always exists (referential integrity via foreign key). But Product could be empty in VBAP (e.g., text items, service items without material). So [0..1] is safer. Explain that.

Also note: since ABAP 7.58? there's `WITH PRIVILEGED ACCESS`? Not needed.

Also, maybe mention that in view entities you can't use `key` on calculated fields — keys must be from... not relevant.

Also: The user wrote "ZI_SalesOrderItem" — keep that exact name.

Format: I'll write in German, use ## headers, code block with abap syntax highlighting, bullet lists. Reasonable length — this is a "write code + explain" task, so a thorough answer is expected. I'll aim for a well-structured answer without excessive padding.

Let me also reconsider: should `NetValuePerUnit` maybe be annotated with `@Semantics.amount.currencyField` — yes done. Could also add `@Measures`? No.

Also the note about labels inherited: In Fiori Elements, if no label given in lineItem, the element's label (from @EndUserText.label of source field or DDIC) is used.

Alright, compose the final answer.

Also small detail: In the element list, annotation lines before `key SalesDocument` — annotations must come before the `key` keyword? Order: annotations, then `key`, then element name. Yes: `@UI...` then `key SalesDocument`. Correct.

Also blank lines between elements fine.

Also, the association clause placement: after `as select from I_SalesDocumentItem`, before `{`. Multiple associations allowed. Correct.

One more: Should I add `,` after `_Product`? No, last element no comma. Correct as drafted.

Also, in view entities, exposing association at end: `_Product` — yes.

Also mention: the view name ZI_ prefix suggests interface layer; for OData exposure you'd create a projection/consumption view ZC_SalesOrderItem as `define view entity ZC_SalesOrderItem as projection on ZI_SalesOrderItem` with UI annotations there. One or two lines at the end.

Now write it. Keep explanations tight. Use German technical terms.

Length check: The code is ~45 lines; explanations ~40-50 lines of bullets. That's appropriate for the request. Headers help scanning.

</details>
