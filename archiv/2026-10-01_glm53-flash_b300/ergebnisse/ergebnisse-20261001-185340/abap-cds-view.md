# ABAP: cds-view

## Aufgabe

Schreibe eine CDS View Entity (define view entity) ZI_SalesOrderItem auf I_SalesDocumentItem bzw. VBAP mit Assoziation zum Material (I_Product), Annotationen für UI (@UI.lineItem), einem berechneten Feld 'NetValuePerUnit' und @Semantics für Betrag und Währung. Erkläre die Annotationen.

## Antwort



---

<details><summary>Denkprozess (30842 Zeichen)</summary>

The user is asking in German for a CDS View Entity (define view entity) called ZI_SalesOrderItem based on I_SalesDocumentItem (or VBAP) with:
- Association to Material (I_Product)
- UI annotations (@UI.lineItem)
- A calculated field 'NetValuePerUnit'
- @Semantics annotations for amount and currency
- Explanation of the annotations

This is an ABAP CDS (Core Data Services) question, typical for SAP S/4HANA development. Let me write a proper CDS view entity.

Key considerations:
1. Modern syntax: `define view entity` (not `define view`)
2. Root view or regular view - for sales order items, typically based on I_SalesDocumentItem
3. Association to I_Product
4. UI annotations for line items (Fiori Elements)
5. Calculated field NetValuePerUnit = NetValue / Quantity (with care for division by zero)
6. @Semantics.amount.currencyOf and @Semantics.quantity.unitOf for currency/quantity handling
7. Data source: I_SalesDocumentItem is the released CDS view for VBAP in S/4HANA

Let me draft the code:

```abap
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Verkaufsbelegposition - Erweiterung'
@Metadata.allowExtensions: true
define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
{
      @UI.lineItem: [{ position: 10, label: 'Verkaufsbeleg' }]
      SalesDocument,

      @UI.lineItem: [{ position: 20, label: 'Position' }]
      SalesDocumentItem,

      @UI.lineItem: [{ position: 30, label: 'Material' }]
      @Consumption.valueHelpDefinition: [{ entity: { name: 'I_Product', element: 'Product' } }]
      Product,

      @UI.lineItem: [{ position: 40, label: 'Menge' }]
      @Semantics.quantity.unitOf: 'SalesOrderQuantityUnit'
      OrderQuantity,

      @UI.lineItem: [{ position: 50, label: 'Mengeneinheit' }]
      SalesOrderQuantityUnit,

      @UI.lineItem: [{ position: 60, label: 'Nettowert' }]
      @Semantics.amount.currencyOf: 'TransactionCurrency'
      NetAmount,

      @UI.lineItem: [{ position: 70, label: 'Währung' }]
      TransactionCurrency,

      @UI.lineItem: [{ position: 80, label: 'Nettowert pro Einheit' }]
      @Semantics.amount.currencyOf: 'TransactionCurrency'
      cast( NetAmount / ( case when OrderQuantity <> 0 then OrderQuantity else 1 end ) 
            as abap.dec(23,2) ) as NetValuePerUnit,

      // Assoziation zum Material
      _Product
}
where ... // optional

association [1..1] to I_Product as _Product
  on $projection.Product = _Product.Product
```

Wait — in view entities, associations must be declared in the header (after `define view entity ... as select from ... association ...`), not at the end of the field list like in the old `define view` DDIC-based syntax. Actually, in view entities, associations are declared in the header:

```abap
define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
  association [1..1] to I_Product as _Product on $projection.Product = _Product.Product
{
  ...
}
```

Yes, that's correct for view entities. In DDIC-based views, associations could be at the end of the field list, but in view entities they must be in the header after the data source.

Also important for view entities:
- No `key` keyword in non-root views unless it's a projection... Actually, in view entities, you can specify `key` for the fields. For a regular view entity (not root), key fields are optional but recommended. Actually in view entities, the KEY keyword can be used in any view entity. Let me include keys.

- Cast: In view entities, expressions are allowed. Division: NetAmount / OrderQuantity. Need to handle division by zero — in ABAP CDS, division by zero causes a runtime error? Actually in CDS views, division by zero results in... In ABAP SQL, division by zero raises an exception/dump. Better to use a CASE or division with safe divisor. Actually, in CDS there's `division( operand1, operand2, decimals )` built-in function which handles it better and allows specifying decimal places. Let me use `division( NetAmount, OrderQuantity, 2 )` — but division by zero still dumps? The SQL function DIVISION: "If the divisor is 0, an exception is raised"? Hmm. Actually for the SQL function `division`, dividing by zero raises an error too. Safer approach: use CASE:

```abap
case 
  when OrderQuantity is not null and OrderQuantity <> 0 
  then division( NetAmount, OrderQuantity, 2 ) 
  else cast( 0 as abap.dec(23,2) ) 
end as NetValuePerUnit
```

Hmm, but the type of the case branches must match. division returns dec... The `division` function: `division(operand1, operand2, decimals)` — result type depends. Let me think about types: NetAmount is likely abap.curr (CURR 23,2 or similar) or abap.dec. OrderQuantity is QUAN 13,3 maybe. Division of curr by quan...

Actually simpler and commonly used:

```abap
@Semantics.amount.currencyOf: 'TransactionCurrency'
cast( division( NetAmount, case when OrderQuantity = 0 then 1 else OrderQuantity end, 2 ) as abap.curr(23,2) ) as NetValuePerUnit
```

Hmm, casting to abap.curr might not be allowed directly? Cast expressions in CDS support: abap.dec(len,decimals), abap.curr(len,decimals), abap.quan(...), etc. Yes, casting to abap.curr is allowed.

But division by zero: if OrderQuantity = 0 we substitute 1, so no division by zero. That's a pragmatic approach. Alternatively use NULL IF... Actually there's `coalesce`. Let me keep it simple with CASE.

Wait, in CDS the CASE in the divisor: `case when OrderQuantity = 0 then 1 else OrderQuantity end` — types: 1 is int, OrderQuantity is quan. Might need cast( 1 as abap.quan... )? Hmm, type compatibility in case expressions... In the divisor position it's an operand of division, not a case result mixing. Actually the CASE itself is an operand; the branches must be type-compatible with each other: 1 (int4?) and OrderQuantity (abap.quan(13,3)). Mixed types in CASE branches: the rules say all operands must be type-compatible... Actually for CDS case expressions, the result types of the branches must be comparable? Let me recall: In CDS, CASE - "The result types of the THEN and ELSE branches must be either identical or the type must be convertible"... Hmm, I think it's strict: "Alle Operanden nach THEN bzw. ELSE müssen denselben Typ haben"? No wait.

From ABAP docs on CDS CASE (simple case and searched case): "The operands then and else must have a type for which a common type can be determined"? Actually I recall for SQL expressions in ABAP CDS: the result type of a CASE expression is determined from the branches, and the branches must be mutually compatible. Numeric types can be mixed — the platform (HANA) will use the most general type. I believe numeric mixing is allowed in HANA SQL. In ABAP CDS on HANA, CASE with mixed numeric types works (e.g., int and dec). To be safe, I could write `cast( 1 as abap.quan(13,3) )`? Hmm, but casting to abap.quan requires... cast to quan is allowed I think. But simpler: many real-world examples just write:

```abap
NetAmount / OrderQuantity as NetValuePerUnit
```

and mention the division-by-zero caveat. Actually, in ABAP CDS, the `/` operator between curr and quan: The arithmetic operators +, -, *, / are allowed with numeric operands. curr is treated as dec. Division of curr by quan gives dec? The result type of division: "If both operands are integer types, the result is... otherwise dec"? Actually in ABAP CDS: For `/`, the result type: if both operands are integer (int1, int2, int4, int8), result is... hmm, in ABAP CDS integer division `/` yields decimal? Let me recall: In ABAP CDS view entities, the division operator `/` — "The result type is dec(34, ...)"? Hmm.

Actually, in ABAP CDS (and ABAP SQL), the arithmetic operators: `+`, `-`, `*` result types follow rules; `/` division: "If one of the operands is a decimal type, the result is a decimal with..." For ABAP SQL: division of two integers is integer division (truncating)? In ABAP SQL, `/` with two integer types performs integer division? Hmm, I believe in ABAP SQL and CDS, `/` between int types is integer division (like DIV), and with decimal involvement it's decimal division. For curr/quan (which are dec internally), the result would be dec with some precision.

To be explicit and safe, using the built-in function `division( NetAmount, OrderQuantity, 2 )` is cleaner: it returns a value with 2 decimal places. But NetValuePerUnit as amount with currency semantics — currency amounts typically 2 decimals, fine.

Hmm, but there's a subtlety: @Semantics.amount.currencyOf on a calculated field — is that allowed? Yes, you can annotate calculated fields with @Semantics.amount.currencyOf pointing to the currency field. For Fiori, currency/quantity semantics on computed fields work.

However, there's a known caveat: for calculated amounts, the currency reference must exist in the result set — TransactionCurrency is selected, so fine.

Alternatively, avoid @Semantics on the calculated field and just cast to abap.dec(23,2). But the user explicitly asked for "@Semantics für Betrag und Währung", so annotate NetAmount with @Semantics.amount.currencyOf: 'TransactionCurrency', and the calculated field too.

Also quantity: OrderQuantity with @Semantics.quantity.unitOf: 'SalesOrderQuantityUnit'.

Field names in I_SalesDocumentItem: Let me recall the actual fields of I_SalesDocumentItem (released view for VBAP):
- SalesDocument
- SalesDocumentItem
- Product (there's also Product... in VBAP it's MATNR; I_SalesDocumentItem has field `Product`)
- OrderQuantity (KWMENG)
- SalesOrderQuantityUnit? Hmm. Let me think. In I_SalesDocumentItem, the quantity unit field is `SalesOrderQuantityUnit`? I recall fields: OrderQuantity, OrderQuantityUnit? Let me think carefully.

I_SalesDocumentItem fields (from S/4HANA released views):
- SalesDocument
- SalesDocumentItem
- SalesDocumentItemCategory
- Product
- OrderQuantity
- OrderQuantityUnit
- NetAmount
- TransactionCurrency
- RequestedDeliveryDate
- ItemGrossWeight, ItemNetWeight, etc.
- SoldToParty
- ...

I believe the unit field is `OrderQuantityUnit`. Hmm, but I've also seen `SalesOrderQuantityUnit` in some views. In I_SalesOrderItem (older naming) there was `SalesOrderQuantityUnit`? Let me think: I_SalesOrderItem (the older, non-released or released?) — Actually there are both I_SalesDocumentItem and I_SalesOrderItem views. In I_SalesOrderItem, fields include SalesOrder, SalesOrderItem, SalesOrderQuantity... Hmm.

For I_SalesDocumentItem (the current released one), I'm fairly confident about:
- SalesDocument
- SalesDocumentItem
- Product
- OrderQuantity (KWMENG)
- OrderQuantityUnit (VRKME)
- NetAmount (NETWR)
- TransactionCurrency (WAERK)

Yes, I've seen OData service API_SALES_ORDER_SRV with fields OrderQuantity, OrderQuantityUnit, NetAmount, TransactionCurrency. The CDS I_SalesDocumentItem mirrors that. Good.

Also `RequestedDeliveryDate`, `Plant`, etc. Not needed.

Association to I_Product: on $projection.Product = _Product.Product.

For the association to be exposed properly and usable in OData/Fiori, we might add @ObjectModel annotations, but keep it focused.

Also add @UI.lineItem annotations with position and label. Use @EndUserText.label for the view. Also @Metadata.allowExtensions: true is good practice for metadata extensions.

Also @AccessControl.authorizationCheck: #NOT_REQUIRED (or #CHECK). For sales data, #CHECK would require an access control; use #NOT_REQUIRED for the example and mention it.

Now the calculated field. Let me write:

```abap
@UI.lineItem: [{ position: 80, label: 'Nettowert pro Menge' }]
@Semantics.amount.currencyOf: 'TransactionCurrency'
case
  when OrderQuantity is not initial and OrderQuantity <> 0
    then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec(23,2) )
    else cast( 0 as abap.dec(23,2) )
end as NetValuePerUnit
```

Hmm, `is not initial` — in CDS, `IS INITIAL` is supported in view entities? There's `IS INITIAL` condition in CDS view entities? I recall `... IS INITIAL` is allowed in CDS conditions (yes, in view entities, `IS INITIAL` is available; in old DDIC-based views it wasn't? Actually `IS INITIAL` is supported in CDS). To be safe, use `OrderQuantity <> 0` and handle null via coalesce? If OrderQuantity is null, comparison yields unknown → case goes to else? In SQL, NULL <> 0 is UNKNOWN, so the WHEN is not satisfied → else branch → 0. That's fine behavior.

But type mixing in CASE branches: division(...) returns dec(…)? The division function signature: division(operand1, operand2, decimals) where decimals is a numeric literal ≥ 0. Result type: df34_dec? Hmm — in ABAP CDS, `division` returns type... The docs: "The result has the data type DEC(31,decimals)"? Actually I recall: division returns a decimal float? No — division(1,3,2) = 0.33. The result type of division: "df34_dec"? Let me think. ABAP CDS built-in functions: DIVISION(arg1, arg2, dec) — "The decimal places of the result are specified by dec. The result has type df34_dec"? Hmm, I'm not 100% sure. I recall for ABAP SQL function DIVISION: "The result is of type df34_dec"? Or dec? 

From ABAP Keyword Documentation: "DIVISION(operand1, operand2, decimals) ... The result type is df34_dec"? Hmm, actually I think I remember: division returns a decimal with `decimals` decimal places, but internally df34_dec? There's a note: "The result has the type DF34_DEC" — hmm no wait.

Let me think about CAST: casting df34_dec to abap.dec(23,2) is allowed? Cast between numeric types is allowed generally (dec <-> df34_dec? df16_dec/df34_dec are decimal floats). Casting from df34_dec to dec should be fine.

Alternatively, avoid the function and use the `/` operator with explicit cast:

```abap
cast( NetAmount / OrderQuantity as abap.dec(23,2) ) as NetValuePerUnit
```

But division by zero risk. In CDS, `/` by zero → runtime error (SQLTYPE division by zero on HANA raises error). Hmm, actually on HANA, division by zero returns NULL? No — in HANA SQL, division by zero... I believe HANA returns an error for division by zero? Actually HANA: `SELECT 1/0 FROM DUMMY` → error "division by zero"? I think HANA returns NULL for division by zero in some cases... Let me recall: SAP HANA: division by zero yields an error? Hmm. In HANA SQL, `1/0` raises "division by zero" error (error 314?). Actually I recall that in HANA, integer division by zero is an error, but decimal division by zero returns NULL? There's a known behavior: In SAP HANA, `SELECT 1/0` returns... I believe it's an error "division by zero not allowed". Hmm, but many CDS examples guard against it.

Safest, well-readable approach used in many blogs:

```abap
@Semantics.amount.currencyOf: 'TransactionCurrency'
NetAmount / cast( OrderQuantity as abap.dec(15,3) ) as NetValuePerUnit
```

Hmm, that doesn't guard zero.

I'll go with the CASE-guarded division and note the rationale. To reduce type-mixing concerns, use `coalesce`? Alternative:

```abap
cast( division( NetAmount, coalesce( nullif( OrderQuantity, 0 ), 1 ), 2 ) as abap.dec(23,2) )
```

Too clever. Keep it simple:

```abap
case
  when OrderQuantity is not null and OrderQuantity <> 0
  then division( NetAmount, OrderQuantity, 2 )
  else cast( 0 as abap.dec(23,2) )
end as NetValuePerUnit
```

Hmm, but then the two branches: division returns (per docs) type... If division returns df34_dec and else is abap.dec(23,2), are they compatible in CASE? The docs for CASE: "The data types of the result... must be comparable"? For searched CASE in CDS: "The operands of THEN and ELSE must be type-compatible"? I recall the rule: "Die Ergebnisse der THEN- und ELSE-Zweige müssen in denselben Datentyp umwandelbar sein" — a common result type is determined. df34_dec and dec(23,2) — common type would be df34_dec. Then the CASE result is df34_dec, and we cast the whole thing:

```abap
cast( case when ... then division(...) else 0 end as abap.dec(23,2) ) as NetValuePerUnit
```

Hmm, `else 0` — integer literal; mixing df34_dec and int → common type df34_dec, fine.

Actually, let me simplify and be pragmatic. A very common pattern in real SAP examples:

```abap
@Semantics.amount.currencyOf: 'TransactionCurrency'
cast( NetAmount / OrderQuantity as abap.curr(23,2) ) as NetValuePerUnit
```

But I want to handle zero. Let me write:

```abap
@UI.lineItem: [{ position: 80, label: 'Nettowert pro Einheit' }]
@Semantics.amount.currencyOf: 'TransactionCurrency'
cast( division( NetAmount,
                case when OrderQuantity <> 0 then OrderQuantity
                     else cast( 1 as abap.quan(13,3) )
                end,
                2 ) as abap.dec(23,2) ) as NetValuePerUnit
```

Hmm, cast(1 as abap.quan(13,3)) — casting int literal to quan... allowed? Cast to abap.quan is allowed from numeric types. But quan requires a unit reference semantically; technically cast works. But then division's second operand type quan(13,3) vs NetAmount curr(23,2)... division accepts numeric operands. OK.

Honestly, simpler and cleaner: use NULLIF + COALESCE:

```abap
division( NetAmount, coalesce( nullif( OrderQuantity, cast( 0 as abap.quan(13,3) ) ), cast( 1 as abap.quan(13,3) ) ), 2 )
```

Too convoluted for a teaching example.

Let me reconsider: Maybe simplest robust version:

```abap
case
  when OrderQuantity is not initial and OrderQuantity <> 0
    then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec(23,2) )
    else cast( 0 as abap.dec(23,2) )
end as NetValuePerUnit
```

Regarding `IS INITIAL` in view entities: Yes, `IS INITIAL` is supported in CDS view entities (it was added; in old DDIC views it wasn't supported, but in view entities it is). Actually let me verify: ABAP docs "CDS DDL - ddlexpr, IS INITIAL"? Hmm. There is `IS INITIAL` condition in ABAP CDS: "sql_cond: ... IS INITIAL" — I believe this is supported in view entities since 7.55 or so. Yes: "CDS DDL - CDS View Entity, sql_cond: IS INITIAL" exists. But to be version-safe, `IS NOT NULL` is universally supported. I'll use `IS NOT NULL AND OrderQuantity <> 0`? But if the field is not null and 0, we go to else. If null → else. Good.

Hmm wait, actually there's subtlety: if OrderQuantity is NULL, `OrderQuantity <> 0` is UNKNOWN → not true → else → 0. So just `when OrderQuantity <> 0 then ... else ...` suffices. But explicit is nicer for teaching. I'll keep `OrderQuantity <> 0` only, with a comment, or include both. I'll write:

```abap
case
  when OrderQuantity is not null and OrderQuantity <> 0
    then division( NetAmount, OrderQuantity, 2 )
    else cast( 0 as abap.dec(23,2) )
end as NetValuePerUnit
```

And cast the whole? The result type of the CASE: division returns... Let me just check my memory of DIVISION: ABAP docs: "DIVISION(operand1, operand2, decimals): Division of operand1 by operand2. The result is rounded to decimals decimal places. The result type is df34_dec." Hmm, I genuinely recall something like: "The result has the data type DF34_DEC" — no wait, I think that's for the function `division` in ABAP SQL: "The result type is df34_dec"? 

Hmm, alternatively I recall: "division: ... decimals must be between 0 and 6? (or 0 and 14?)... The result type is dec(31,decimals)"? 

Let me think about what's documented: ABAP CDS Built-In Functions - Mathematical functions: DIVISION(arg1, arg2, dec): "Division von arg1 durch arg2. ... Das Ergebnis hat den SQL-Datentyp DF34_DEC"? I'm fairly sure the docs say the result type is df34_dec for DIVISION? Hmm, no — I think DIVISION returns "dec" with the specified decimals... 

Actually, from the ABAP Keyword Documentation (SQL Expressions, sql_func): "DIVISION(operand1, operand2, dec) — Division of operand1 by operand2. The result is rounded to dec decimal places. dec must be a numeric literal between 0 and 6? ... The data type of the result is df34_dec." Hmm, I've seen "df34_dec" mentioned in context of division because HANA's division function returns var decimal. I'll go with casting the result to be safe — casting df34_dec to abap.dec(23,2) is explicitly allowed per cast matrix (df16_dec/df34_dec → dec: yes, allowed).

To make the CASE branches type-consistent, cast both branches to abap.dec(23,2):

```abap
case
  when OrderQuantity is not null and OrderQuantity <> 0
    then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec(23,2) )
    else cast( 0 as abap.dec(23,2) )
end as NetValuePerUnit
```

This is clean, type-safe, and guards division by zero. 

Hmm, one more consideration: `cast( 0 as abap.dec(23,2) )` — casting an integer literal to dec is allowed. Yes.

Alternatively use `else cast( 0 as abap.curr(23,2) )`? Since we annotate with @Semantics.amount.currencyOf, the field should ideally be curr or dec. abap.dec(23,2) is fine for a calculated amount; many examples use abap.dec. Actually for currency fields, ABAP dictionary domain CURR vs DEC: calculated amounts often typed as abap.dec(23,2) with currency semantics annotation — that works in Fiori. But hmm, there's a subtlety: for OData V2 currency handling, the property type Edm.Decimal with SAP:currency... fine.

Actually, wait: should NetValuePerUnit be an amount per unit? Semantically it's "price per unit" — amount with currency is fine.

Now, also the user said "auf I_SalesDocumentItem bzw. VBAP" — so base it on I_SalesDocumentItem (released view). I'll use I_SalesDocumentItem and mention that VBAP fields are behind it (MATNR → Product, KWMENG → OrderQuantity, NETWR → NetAmount, WAERK → TransactionCurrency, VRKME → OrderQuantityUnit).

Also add association usage: maybe demonstrate usage of _Product in a field, e.g., ProductName via association? Could add `@UI.lineItem` for _Product.ProductName? Exposing association fields: In view entities you can select association fields: `_Product.ProductType` etc. But careful: adding product text requires I_ProductText with language filter. Keep it simple: just expose the association `_Product` and maybe show one usage example like `_Product.ProductType` commented out. Actually, to demonstrate association usage, I could add a field `ProductType` via `_Product.ProductType`? Hmm, that requires the association path in the field list — allowed in view entities: `_Product.ProductType as ProductType`. But path expressions in the SELECT list of view entities are allowed (with cardinality considerations). I'll include it as an optional commented line or include it for demonstration. Let me include it commented to keep the example minimal but show how to use the association.

Also, for Fiori Elements with OData V4 / RAP, you'd typically need @ObjectModel.text.element or composition, but not necessary here.

Also add @UI.lineItem with label and maybe importance. Use German labels since user writes German.

Also @EndUserText.label for the view.

Also mention: view entity name max 16 chars? ZI_SalesOrderItem — that's 17 characters? Z I _ S a l e s O r d e r I t e m: "ZI_SalesOrderItem" = Z(1)I(2)_(3)S(4)a(5)l(6)e(7)s(8)O(9)r(10)d(11)e(12)r(13)I(14)t(15)e(16)m(17) = 17 characters. CDS view names can be up to 16 characters? DDL source names: The name of a CDS entity can be up to 16 characters? Hmm — actually CDS view names can be up to 16 chars? No wait: DDIC-based CDS views: the CDS entity name up to 16 characters? I recall CDS view/entity names are limited to 16 characters? Hmm, no — I think CDS entity names can be longer. Let me think: ABAP Dictionary table names: 16 chars max (for DDIC tables it's 16). CDS views: the DDL source name and entity name — I believe max 16 characters for the SQL view? The CDS entity itself can be up to 30? Hmm.

Actually: For DDIC-based views, the CDS entity name can be up to 16 characters? No... Let me recall real examples: I_SalesDocumentItem — that's 19 characters. I_Product = 9. I_SuplrInvcItemPurOrdRefAlgn... those are long. CDS view names in standard are often much longer than 16 (e.g., I_SalesDocumentItem = 19 chars). So CDS entity names can be up to 30 characters? Hmm, but there was a restriction: the DDIC SQL view (old) name max 16; the CDS entity name max 16 too? No — I_SalesDocumentItem is definitely a valid released CDS view name with 19 chars. So entity names up to 30? Actually I believe CDS entity names can be up to 30 characters (like other ABAP names), while the associated "SQL view" name (DDIC view) is max 16. For view entities there's no separate SQL view. So ZI_SalesOrderItem (17 chars) is fine.

Hmm wait, actually I need to double check: CDS entity names — "The name of a CDS entity can have a maximum of 16 characters"? No, definitely not, given standard views like I_SalesDocumentItem (19), I_CustomerSupplier... e.g., "I_SuplrInvcItemPurOrdRefAlgn" is 28 chars. So max is 30? Hmm, but I also recall that CDS view names were limited to 16 characters in older releases! Yes — that's right: In older ABAP releases (7.40), CDS view names were limited to 16 characters. The limit was lifted to 30 characters (7.51? or with view entities?). Standard views like I_SalesDocumentItem exist on newer releases. Since we're using `define view entity` (7.55+), 30 chars is fine. OK, ZI_SalesOrderItem is fine.

Now, keys: For a non-root view entity, KEY is optional but good. I'll mark SalesDocument and SalesDocumentItem as key.

Also add `where` clause? Not needed.

Also maybe add @ObjectModel.semanticKey? Optional; skip or mention.

Let me also think about whether to include `@Metadata.allowExtensions: true` — good practice so UI texts can be moved to a metadata extension. I'll include it and explain briefly.

Also `@AccessControl.authorizationCheck: #NOT_REQUIRED` — explain that in production you'd use #CHECK with an access control (e.g., based on sales org) — actually for sales order data, #CHECK would be typical with ZI access control. Mention it.

Now the full code:

```abap
@EndUserText.label: 'Verkaufsbelegposition'
@AccessControl.authorizationCheck: #NOT_REQUIRED
@Metadata.allowExtensions: true
@UI.headerInfo: { typeName: 'Position',
                  typeNamePlural: 'Positionen' }
define view entity ZI_SalesOrderItem
  as select from I_SalesDocumentItem
  association [1..1] to I_Product as _Product
    on $projection.Product = _Product.Product
{
      @UI.lineItem: [{ position: 10, label: 'Verkaufsbeleg' }]
  key SalesDocument,

      @UI.lineItem: [{ position: 20, label: 'Position' }]
  key SalesDocumentItem,

      @UI.lineItem: [{ position: 30, label: 'Material' }]
      @Consumption.valueHelpDefinition:
        [{ entity: { name: 'I_Product', element: 'Product' } }]
      Product,

      @UI.lineItem: [{ position: 40, label: 'Menge' }]
      @Semantics.quantity.unitOf: 'OrderQuantityUnit'
      OrderQuantity,

      @UI.lineItem: [{ position: 50, label: 'ME' }]
      OrderQuantityUnit,

      @UI.lineItem: [{ position: 60, label: 'Nettowert' }]
      @Semantics.amount.currencyOf: 'TransactionCurrency'
      NetAmount,

      @UI.lineItem: [{ position: 70, label: 'Währung' }]
      TransactionCurrency,

      @UI.lineItem: [{ position: 80, label: 'Nettowert / Menge' }]
      @Semantics.amount.currencyOf: 'TransactionCurrency'
      case
        when OrderQuantity is not null and OrderQuantity <> 0
          then cast( division( NetAmount, OrderQuantity, 2 ) as abap.dec(23,2) )
          else cast( 0 as abap.dec(23,2) )
      end as NetValuePerUnit,

      // Pfad über die Assoziation (Beispiel)
      _Product.ProductType as ProductType,

      _Product
}
```

Hmm, wait: `ProductType` field in I_Product — yes, I_Product has ProductType. Good as a demonstration. But adding it also adds a column; fine.

Actually, should I include `_Product.ProductType`? It demonstrates path expressions. But note: in view entities, path expressions in the field list are allowed. Also, exposing `_Product` at the end for OData association. Good.

One issue: In view entities, is `key` allowed in non-root views? Yes, KEY can be specified in any view entity ("The key fields ... KEY is optional for non-root"). Fine.

Another consideration: `division( NetAmount, OrderQuantity, 2 )` — NetAmount is of type abap.curr(23,2)? In I_SalesDocumentItem, NetAmount is CURR 23,2? Actually the released view has NetAmount as abap.curr(23,2)? Hmm, VBAP NETWR is CURR 15,2? VBAP-NETWR: CURR, length 15, decimals 2? Actually VBAP NETWR is CURR 15? Let me think: NETWR in VBAP is CURR(15,2)? Hmm, KZWEG... Standard: VBAP-NETWR is CURR length 15 decimals 2? I believe NETWR is CURR 15,2? Hmm, actually many SAP amount fields are CURR 13,2 or 15,2. VBAP-NETWR: data element NETWR, domain WERTV8? WERTV8 is CURR 15,2? Hmm, WERTV8: length 15? Not critical.

But wait — in the released I_SalesDocumentItem, NetAmount might be typed as abap.curr(23,2)? Some standard views extend curr to 23,2? Not sure. Doesn't matter much for the example; my cast to abap.dec(23,2) is explicit anyway.

Hmm, actually one more consideration on the CASE + division: The `division` function's third parameter must be a numeric literal — 2 is fine.

Also: is `division` allowed with curr operands? DIVISION accepts any numeric. Fine.

Alternatively, I could simplify to make the example more readable:

```abap
cast( NetAmount / OrderQuantity as abap.dec(23,2) ) as NetValuePerUnit
```

and mention the zero-division caveat separately. But better to show the robust version in code. I'll show the robust version.

Hmm, actually, let me reconsider the null check: `OrderQuantity is not null` — if OrderQuantity is always filled (KWMENG not null in VBAP), fine. Keep it.

Now annotations explanation. The user asks "Erkläre die Annotationen." So I need to explain:

1. `@EndUserText.label` — description shown in tools/Fiori.
2. `@AccessControl.authorizationCheck` — whether access control exists; #NOT_REQUIRED suppresses warning; #CHECK requires ZC access control.
3. `@Metadata.allowExtensions: true` — allows metadata extensions to move UI annotations to separate MDE object (clean architecture, key user flexibility).
4. `@UI.headerInfo` — type name for Fiori header.
5. `@UI.lineItem` — defines columns in tables/lists (Fiori Elements list report / line items), with position (column order) and label (column header). Note: label can be overridden via metadata extension / i18n.
6. `@Semantics.amount.currencyOf: 'TransactionCurrency'` — binds the amount field to its currency field; ensures correct decimal handling (currency-specific decimals like JPY with 0 decimals), display formatting, and OData currency annotation (Org.OData.Measures.V1.ISOCurrency). Without it, amounts are treated as plain decimals.
7. `@Semantics.quantity.unitOf: 'OrderQuantityUnit'` — analogous for quantities with unit of measure.
8. `@Consumption.valueHelpDefinition` — value help for the Product field in Fiori UIs.
9. Association to I_Product — on-demand join (only joined when path is used / association consumed), reusable, exposed in OData as navigation property `_Product`.
10. Calculated field via CASE + division + cast — computed at runtime in the database; explain division by zero guard; cast ensures proper

</details>
