# Plant Name Expression Syntax

This document describes the project-specific Plant Name Expression Syntax used by the plant database. It is a compact internal format for parsing, validating, indexing, and rendering plant names.

It is not a replacement for botanical nomenclature, APNI/APC records, nursery labels, or horticultural registration systems. It is an internal canonical expression format designed for deterministic machine handling and readable display.

## Purpose

The syntax must be able to represent:

- species
- infraspecific taxa
- hybrids
- hybrid-of-hybrid parentage
- cultivar names
- common names

The syntax deliberately stays compact. It uses delimiters instead of verbose key/value attributes where possible.

## Delimiters

The current delimiter meanings are:

```text
.      separates genus and species
:      introduces an infraspecific rank
[]     contains hybrid parentage
|      separates hybrid parents
()     contains cultivar name
{}     contains common name
```

## Canonical structure

The canonical order is:

```text
TaxonExpression(Cultivar Name){Common Name}
```

Cultivar and common name are both optional. If both are present, the cultivar name comes first.

When the genus is known but parentage is unknown, use empty square brackets:

```text
Genus[](Cultivar Name){Common Name}
```

## Taxon expression forms

The syntax supports three taxon expression types:

- species
- infraspecific taxon
- hybrid

### Species

A species is written as:

```text
Genus.species
```

Examples:

```text
Banksia.ericifolia
Banksia.spinulosa
Grevillea.rosmarinifolia
Hakea.laurina
```

These correspond to the binomials:

```text
Banksia ericifolia
Banksia spinulosa
Grevillea rosmarinifolia
Hakea laurina
```

### Infraspecific taxa

Use `:` to introduce a rank below species:

```text
Genus.species:rank.epithet
```

Supported ranks:

```text
subsp   subspecies
var     variety
form    form
```

Examples:

```text
Banksia.integrifolia:subsp.integrifolia
Banksia.spinulosa:var.cunninghamii
Banksia.marginata:form.prostrata
```

Human-readable renderings:

```text
Banksia integrifolia subsp. integrifolia
Banksia spinulosa var. cunninghamii
Banksia marginata form. prostrata
```

Do not use a plain dot for the infraspecific rank. The colon separates the species-level name from the rank-qualified part.

When the subspecies epithet is the same as the species epithet, `:subsp.*` is acceptable shorthand in input. Canonical output should still render the repeated epithet explicitly.

Correct:

```text
Banksia.integrifolia:subsp.integrifolia
```

Acceptable shorthand:

```text
Banksia.integrifolia:subsp.*
```

Avoid:

```text
Banksia.integrifolia.subsp.integrifolia
```

### Hybrids

Use square brackets for hybrid parentage:

```text
Genus[parent|parent]
```

Example:

```text
Banksia[ericifolia|spinulosa]
```

Meaning:

```text
Banksia ericifolia x Banksia spinulosa
```

This form is used instead of `Banksia.ericifolia|spinulosa` because the latter becomes ambiguous once nested hybrids, cultivars, and common names are added.

### Genus inheritance in hybrid expressions

Inside a `Genus[...]` hybrid expression, bare species names inherit the outer genus.

Example:

```text
Grevillea[rosmarinifolia|thelemanniana]
```

Meaning:

```text
Grevillea rosmarinifolia x Grevillea thelemanniana
```

Preferred:

```text
Grevillea[rosmarinifolia|thelemanniana]
```

Avoid repeating the genus for same-genus parents unless the parser explicitly supports fully qualified parents:

```text
Grevillea[Grevillea.rosmarinifolia|Grevillea.thelemanniana]
```

### Hybrid of a hybrid

Nested square brackets represent recursive hybrid parentage.

Examples:

```text
Grevillea[rosmarinifolia|[juniperina|thelemanniana]]
Banksia[ericifolia|[spinulosa|marginata]]
Grevillea[[juniperina|thelemanniana]|rosmarinifolia]
```

Meanings:

```text
Grevillea rosmarinifolia x (Grevillea juniperina x Grevillea thelemanniana)
Banksia ericifolia x (Banksia spinulosa x Banksia marginata)
(Grevillea juniperina x Grevillea thelemanniana) x Grevillea rosmarinifolia
```

Each bracket level must contain exactly two parents.

### Cultivar-bearing hybrid parents

A hybrid parent may itself be a cultivar name in round brackets. When a cultivar is used as a parent, do not expand the underlying species of that cultivar in the hybrid expression.

Example:

```text
Genus[parent_species1|(Cultivar Name)]
```

Meaning:

```text
Genus parent_species1 x 'Cultivar Name'
```

This is an atomic cultivar-parent form inside `[]`. It does not use curly braces and does not list the underlying species of the cultivar parent.

## Cultivars

Cultivar names are placed in round brackets immediately after the taxon expression:

```text
TaxonExpression(Cultivar Name)
```

By default, each word in a cultivar name should start with a capital letter.

Examples:

```text
Banksia.spinulosa(Birthday Candles)
Banksia[ericifolia|spinulosa](Giant Candles)
Grevillea[rosmarinifolia|[juniperina|thelemanniana]](Example Cultivar)
Banksia[](Birthday Candles)
```

If the cultivar has no known parentage, keep the genus and use empty square brackets:

```text
Banksia[](Birthday Candles)
```

Human-readable renderings:

```text
Banksia spinulosa 'Birthday Candles'
Banksia ericifolia x Banksia spinulosa 'Giant Candles'
Grevillea rosmarinifolia x (Grevillea juniperina x Grevillea thelemanniana) 'Example Cultivar'
Banksia 'Birthday Candles'
```

Do not use single quotes inside the expression syntax. Round brackets already identify the cultivar name. Single quotes are used only in display rendering.

## Common names

Common names are placed in curly braces immediately after the taxon expression and after any cultivar name:

```text
TaxonExpression{Common Name}
TaxonExpression(Cultivar Name){Common Name}
Genus[](Cultivar Name){Common Name}
```

By default, each word in a common name should start with a capital letter.

Examples:

```text
Banksia.serrata{Saw Banksia}
Banksia.spinulosa(Birthday Candles){Hairpin Banksia}
Banksia[ericifolia|spinulosa](Giant Candles){Giant Candles Banksia}
Banksia[](Birthday Candles){Hairpin Banksia}
```

Human-readable renderings:

```text
Banksia serrata - Saw Banksia
Banksia spinulosa 'Birthday Candles' - Hairpin Banksia
Banksia ericifolia x Banksia spinulosa 'Giant Candles' - Giant Candles Banksia
Banksia 'Birthday Candles' - Hairpin Banksia
```

Common names are not unique. The database should treat common names as many-to-many data, not as a single authoritative field on a taxon.

If the supplied common name is exactly the same as the outer genus after whitespace normalization and case-insensitive comparison, omit the common-name part.

Canonical:

```text
Grevillea[banksii:form.white|bipinnatifida](Superb)
```

Avoid:

```text
Grevillea[banksii:form.white|bipinnatifida](Superb){Grevillea}
```

## Combined examples

Species only:

```text
Banksia.serrata
```

Species with common name:

```text
Banksia.serrata{Saw Banksia}
```

Species cultivar:

```text
Banksia.spinulosa(Birthday Candles)
```

Species cultivar with common name:

```text
Banksia.spinulosa(Birthday Candles){Hairpin Banksia}
```

Subspecies:

```text
Banksia.integrifolia:subsp.integrifolia
```

Variety:

```text
Banksia.spinulosa:var.cunninghamii
```

Form:

```text
Banksia.marginata:form.prostrata
```

Hybrid:

```text
Banksia[ericifolia|spinulosa]
```

Hybrid cultivar:

```text
Banksia[ericifolia|spinulosa](Giant Candles)
```

Hybrid cultivar with common name:

```text
Banksia[ericifolia|spinulosa](Giant Candles){Giant Candles Banksia}
```

Hybrid of hybrid:

```text
Grevillea[rosmarinifolia|[juniperina|thelemanniana]]
```

Hybrid of hybrid with cultivar and common name:

```text
Grevillea[rosmarinifolia|[juniperina|thelemanniana]](Example Cultivar){Example Grevillea}
```

Hybrid with a cultivar-bearing parent:

```text
Grevillea[rosmarinifolia|(Example Cultivar)]
```

## Informal grammar

```text
PlantExpression
  = TaxonExpression CultivarPart? CommonNamePart?

TaxonExpression
  = SpeciesExpression
  | InfraspecificExpression
  | HybridExpression

SpeciesExpression
  = Genus "." SpeciesEpithet

InfraspecificExpression
  = Genus "." SpeciesEpithet ":" Rank "." InfraspecificEpithet

HybridExpression
  = Genus "[" ParentExpression "|" ParentExpression "]"

ParentExpression
  = SpeciesEpithet
  | InfraspecificParentExpression
  | NestedHybridExpression
  | CultivarParentExpression

InfraspecificParentExpression
  = SpeciesEpithet ":" Rank "." InfraspecificEpithet

NestedHybridExpression
  = "[" ParentExpression "|" ParentExpression "]"

CultivarParentExpression
  = "(" CultivarName ")"

CultivarPart
  = "(" CultivarName ")"

CommonNamePart
  = "{" CommonName "}"

Rank
  = "subsp" | "var" | "form"
```

## Parsing notes

A parser should produce a structured representation rather than relying on the raw string alone.

Recommended parsed fields:

```text
raw_expression
canonical_expression
taxon_type: species | infraspecific | hybrid
outer_genus
species_epithet
infraspecific_rank
infraspecific_epithet
hybrid_parents
cultivar_name
common_name
```

Hybrid parents should be recursive nodes, not flat strings.

Example parse tree for:

```text
Grevillea[rosmarinifolia|[juniperina|thelemanniana]](Example Cultivar){Example Grevillea}
```

Conceptual structure:

```text
PlantExpression
  TaxonExpression: Hybrid
    genus: Grevillea
    parent_1:
      species: rosmarinifolia
      inherited_genus: Grevillea
    parent_2:
      Hybrid
        inherited_genus: Grevillea
        parent_1:
          species: juniperina
          inherited_genus: Grevillea
        parent_2:
          species: thelemanniana
          inherited_genus: Grevillea
  cultivar_name: Example Cultivar
  common_name: Example Grevillea
```

## Canonicalization rules

1. Preserve the genus capitalization as `Genus` with initial capital.
2. Store species and infraspecific epithets in lowercase unless a source requires otherwise.
3. Remove leading and trailing whitespace around the full expression.
4. Remove unnecessary whitespace around delimiters.
5. Preserve spaces inside cultivar and common names.
6. Do not add empty cultivar or common name delimiters.
7. If both cultivar and common name are present, cultivar must come first.
8. Omit the common-name part when the common name is exactly the same as the outer genus.
9. Use the shortest valid same-genus hybrid form with inherited genus.
10. By default, capitalize the first letter of each word in cultivar names and common names.

Canonical:

```text
Banksia[ericifolia|spinulosa](Giant Candles){Giant Candles Banksia}
```

Avoid:

```text
Banksia [ ericifolia | spinulosa ] ( Giant Candles ) { Giant Candles Banksia }
```

Canonical:

```text
Grevillea[rosmarinifolia|[juniperina|thelemanniana]]
```

Avoid:

```text
Grevillea[Grevillea.rosmarinifolia|Grevillea[Grevillea.juniperina|Grevillea.thelemanniana]]
```

## Validation rules

Reject or flag expressions with:

1. Empty genus.
2. Empty species epithet.
3. Empty hybrid parent.
4. Unbalanced square brackets.
5. Unbalanced round brackets.
6. Unbalanced curly braces.
7. More than one cultivar part.
8. More than one common-name part.
9. Common name before cultivar.
10. Unsupported infraspecific rank.
11. Hybrid expressions without exactly two parents at each bracket level.

Examples to reject or flag:

```text
Banksia.
Banksia[]
Banksia[ericifolia|]
Banksia[ericifolia|spinulosa
Banksia.spinulosa){Birthday Candles}
Banksia.spinulosa{Hairpin Banksia}(Birthday Candles)
Banksia.spinulosa:forma.prostrata
```

## Display rendering rules

When rendering to human-readable text:

1. Replace the first genus/species dot with a space.
2. Render infraspecific ranks with a trailing period if appropriate:
   - `subsp` -> `subsp.`
   - `var` -> `var.`
   - `form` -> `form.`
3. Render hybrid parentage using `x` or the multiplication sign depending on output context.
4. Render cultivar names in single quotes.
5. Render common names after the scientific/horticultural name, separated by a dash or stored separately in UI fields.
6. Do not render a common name when it is exactly the same as the outer genus.

Examples:

```text
Banksia.spinulosa(Birthday Candles){Hairpin Banksia}
```

Display:

```text
Banksia spinulosa 'Birthday Candles' - Hairpin Banksia
```

```text
Banksia[ericifolia|spinulosa](Giant Candles){Giant Candles Banksia}
```

Display:

```text
Banksia ericifolia x Banksia spinulosa 'Giant Candles' - Giant Candles Banksia
```

```text
Grevillea[rosmarinifolia|[juniperina|thelemanniana]]
```

Display:

```text
Grevillea rosmarinifolia x (Grevillea juniperina x Grevillea thelemanniana)
```

## Database design guidance

The expression should not be the only database representation. Store a parsed structure and generate the expression from fields where possible.

Recommended model concepts:

```text
Taxon
Name
HybridParentage
Cultivar
CommonName
TaxonCommonName
```

Important distinctions:

1. Taxon and name are not the same thing.
2. Accepted names and synonyms should be supported later.
3. Misapplied names may need separate handling later.
4. Common names are many-to-many.
5. Native status is regional, not inherent in the name string.
6. Cultivar names are horticultural selections, not botanical ranks.
7. Hybrid parentage should be represented recursively.

The expression syntax is useful as:

```text
canonical_expression
import/export representation
search token source
URL-safe identifier source after escaping/encoding
human-editable shorthand
```

It should not replace structured relational data.

## Search behavior guidance

Search should support:

```text
Banksia ericifolia
Banksia.ericifolia
ericifolia
Giant Candles
Banksia Giant Candles
Giant Candles Banksia
Banksia[ericifolia|spinulosa]
```

Search normalization should treat these as related where possible:

```text
Banksia.spinulosa(Birthday Candles)
Banksia spinulosa Birthday Candles
Banksia spinulosa 'Birthday Candles'
```

Common name search must not assume uniqueness.

## Scope exclusions

Do not implement syntax for the following unless explicitly requested later:

```text
PBR denomination
PBR synonym
trade name
trademark
marketing name
cultivar Group
grex
graft chimera
author citation
APNI/APC name status
accepted name vs synonym
misapplied name
regional native status
provenance / seed source
nursery stock SKU
```

These are important horticultural and botanical concepts, but they are intentionally outside the current compact expression syntax.

## Coding expectations

When modifying code for this project:

1. Preserve the Plant Name Expression Syntax exactly unless asked to change it.
2. Add parser tests before changing parser behavior.
3. Keep parser output structured and recursive.
4. Keep canonicalization deterministic.
5. Do not silently reinterpret ambiguous expressions.
6. Prefer explicit validation errors over guessing.
7. Keep cultivar and common name support separate.
8. Do not add PBR or trade-name fields to the syntax without a specific instruction.
9. Use examples from this document as test cases.
10. If adding renderers, ensure expressions round-trip where possible:

```text
parse(expression) -> structure -> canonical_expression
```

## Minimum parser test cases

Valid:

```text
Banksia.ericifolia
Banksia.integrifolia:subsp.integrifolia
Banksia.spinulosa:var.cunninghamii
Banksia.marginata:form.prostrata
Banksia[ericifolia|spinulosa]
Banksia[ericifolia|spinulosa](Giant Candles)
Banksia[ericifolia|spinulosa](Giant Candles){Giant Candles Banksia}
Banksia.serrata{Saw Banksia}
Grevillea[rosmarinifolia|[juniperina|thelemanniana]]
Grevillea[rosmarinifolia|[juniperina|thelemanniana]](Example Cultivar){Example Grevillea}
```

Invalid or warning-worthy:

```text
Banksia.
Banksia[]
Banksia[ericifolia|]
Banksia[ericifolia|spinulosa
Banksia.spinulosa{Hairpin Banksia}(Birthday Candles)
Banksia.spinulosa:forma.prostrata
Banksia.ericifolia|spinulosa(Giant Candles)
```

## Preferred vocabulary

Use these terms consistently:

```text
Plant Name Expression Syntax
PlantExpression
TaxonExpression
SpeciesExpression
InfraspecificExpression
HybridExpression
ParentExpression
CultivarPart
CommonNamePart
canonical expression
human-readable rendering
```

Avoid calling the expression itself the final scientific name. It is a parseable project expression that can be rendered into scientific, horticultural, or display names.
