# Topology comparison — heldout

11 instances answered by all of single, sequential, hierarchical, parallel.

## All instances

| Topology | n | Acc@1 | Acc@3 | Acc@5 | MRR | Seconds | Tokens in | Tokens out | Cost $ |
|---|---|---|---|---|---|---|---|---|---|
| single | 11 | 1.00 | 1.00 | 1.00 | 1.00 | 17 | 39876 | 312 | 0.092 |
| sequential | 11 | 0.91 | 1.00 | 1.00 | 0.95 | 31 | 64580 | 1314 | 0.159 |
| hierarchical | 11 | 1.00 | 1.00 | 1.00 | 1.00 | 38 | 75477 | 1985 | 0.192 |
| parallel | 11 | 0.91 | 1.00 | 1.00 | 0.95 | 20 | 83016 | 2030 | 0.209 |

## Instances whose report names the gold file

| Topology | n | Acc@1 | Acc@3 | Acc@5 | MRR | Seconds | Tokens in | Tokens out | Cost $ |
|---|---|---|---|---|---|---|---|---|---|
| single | 5 | 1.00 | 1.00 | 1.00 | 1.00 | 15 | 27864 | 275 | 0.030 |
| sequential | 5 | 0.80 | 1.00 | 1.00 | 0.90 | 28 | 48745 | 1279 | 0.056 |
| hierarchical | 5 | 1.00 | 1.00 | 1.00 | 1.00 | 26 | 35758 | 1335 | 0.044 |
| parallel | 5 | 0.80 | 1.00 | 1.00 | 0.90 | 18 | 59787 | 1924 | 0.071 |

## Instances whose report does not

| Topology | n | Acc@1 | Acc@3 | Acc@5 | MRR | Seconds | Tokens in | Tokens out | Cost $ |
|---|---|---|---|---|---|---|---|---|---|
| single | 6 | 1.00 | 1.00 | 1.00 | 1.00 | 19 | 49885 | 343 | 0.062 |
| sequential | 6 | 1.00 | 1.00 | 1.00 | 1.00 | 33 | 77776 | 1344 | 0.103 |
| hierarchical | 6 | 1.00 | 1.00 | 1.00 | 1.00 | 49 | 108577 | 2527 | 0.148 |
| parallel | 6 | 1.00 | 1.00 | 1.00 | 1.00 | 21 | 102373 | 2119 | 0.138 |

## Rank of the gold file, per instance

`—` means the topology answered but none of its candidates was the gold file. An instance missing from a run appears under *Excluded* instead.

| Instance | Hinted | single | sequential | hierarchical | parallel |
|---|---|---|---|---|---|
| astropy__astropy-14182 | no | 1 | 1 | 1 | 1 |
| django__django-12915 | yes | 1 | 1 | 1 | 1 |
| mwaskom__seaborn-3010 | yes | 1 | 1 | 1 | 1 |
| pallets__flask-4992 | yes | 1 | 1 | 1 | 1 |
| psf__requests-2317 | yes | 1 | 2 | 1 | 2 |
| pydata__xarray-5131 | no | 1 | 1 | 1 | 1 |
| pylint-dev__pylint-7993 | yes | 1 | 1 | 1 | 1 |
| pytest-dev__pytest-8365 | no | 1 | 1 | 1 | 1 |
| scikit-learn__scikit-learn-13241 | no | 1 | 1 | 1 | 1 |
| sphinx-doc__sphinx-8506 | no | 1 | 1 | 1 | 1 |
| sympy__sympy-22840 | no | 1 | 1 | 1 | 1 |

## Excluded

Answered by some topologies but not all, so left out of every table above:

- `matplotlib__matplotlib-26011`
