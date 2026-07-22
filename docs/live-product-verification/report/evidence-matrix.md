# Report identity and applicability matrix

These rows exercise the frozen Contract V2 binding logic. “Contract verified”
means the local tests prove identity propagation and fail-closed state; it does
not mean every external source or predictor executed on this host.

| Gene | Transcript and cDNA | Protein | GRCh38 allele | Consequence | Contract expectation |
| --- | --- | --- | --- | --- | --- |
| RPE65 | `NM_000329.3:c.260A>G` | `p.Asp87Gly` | `1-68444869-T-C` | missense | Canonical binding; missense predictors applicable |
| ABCA4 | `NM_000350.3:c.5435T>A` | `p.Ile1812Asn` | `1-94014568-A-T` | missense | Canonical binding; missense predictors applicable |
| USH2A | `NM_206933.4:c.2276G>T` | `p.Cys759Phe` | `1-216247118-C-A` | missense | Canonical binding; missense predictors applicable |
| HBB | `NM_000518.5:c.20A>T` | `p.Glu7Val` | `11-5227002-T-A` | missense | Canonical binding; missense predictors applicable |
| TP53 | `NM_000546.6:c.215C>G` | `p.Pro72Arg` | `17-7676154-G-C` | missense | Canonical binding; missense predictors applicable |
| BRCA1 | `NM_007294.4:c.68_69delAG` | `p.Glu23ValfsTer17` | `NC_000017.11:g.43124028_43124029del` | frameshift | Canonical binding; missense predictors not applicable |
| CFTR | `NM_000492.4:c.1521_1523delCTT` | `p.Phe508del` | `NC_000007.14:g.117559592_117559594del` | in-frame deletion | Canonical binding; missense predictors not applicable |
| F8 | `NM_000132.4:c.6046C>T` | `p.Arg2016Trp` | `X-154902120-G-A` | missense | Canonical binding; missense predictors applicable |

The deletion rows use unambiguous genomic HGVS because left-normalized compact
indel strings may differ across representations. Canonical support in the test
is an identity-matched local VariantValidator record, never a fixture.

## Negative controls

| Control | Required result |
| --- | --- |
| Source identity belongs to another allele | No execution snapshot; bounded mismatch warning without either input echoed |
| Fixture is the only canonical source | No execution snapshot; canonical source unavailable |
| Local gnomAD query returns not found | Section is empty; disclosure says local execution plus `not_found` |
| Aggregate source is fallback but one predictor row has independent public source identity | Only that independent row is retained |
| Fallback classification, disease, molecular, frequency, ACMG, functional, or trial payload | Typed unavailable/empty result; scientific fields removed |
| One call-card source live and peers failed/missing | Aggregate status is `partial` |
| Fixture row has a recent timestamp | Currency status remains `unknown`, never `fresh` |

## Scope assertions

- Publication aggregation ignores weak sources and preserves its source tags
  and variant/gene scope counts.
- Trial rows preserve `variant_level`, `gene_level`, or `disease_level` and the
  query execution that produced them.
- Disease- or gene-level discovery remains useful discovery content but is not
  relabelled as exact-allele evidence.
