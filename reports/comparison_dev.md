# Topology comparison — dev

26 instances answered by all of single, sequential, hierarchical, parallel.

## All instances

| Topology | n | Acc@1 | Acc@3 | Acc@5 | MRR | Seconds | Tokens in | Tokens out | Cost $ |
|---|---|---|---|---|---|---|---|---|---|
| single | 26 | 0.88 | 0.92 | 0.92 | 0.90 | 23 | 51692 | 357 | 0.280 |
| sequential | 26 | 0.81 | 0.92 | 0.92 | 0.87 | 61 | 116286 | 1593 | 0.654 |
| hierarchical | 26 | 0.85 | 0.92 | 0.92 | 0.88 | 64 | 126079 | 2190 | 0.724 |
| parallel | 26 | 0.81 | 0.92 | 0.92 | 0.87 | 29 | 112876 | 2387 | 0.661 |

## Instances whose report names the gold file

| Topology | n | Acc@1 | Acc@3 | Acc@5 | MRR | Seconds | Tokens in | Tokens out | Cost $ |
|---|---|---|---|---|---|---|---|---|---|
| single | 11 | 0.91 | 1.00 | 1.00 | 0.95 | 16 | 38114 | 326 | 0.088 |
| sequential | 11 | 0.82 | 1.00 | 1.00 | 0.91 | 44 | 91576 | 1444 | 0.221 |
| hierarchical | 11 | 0.91 | 1.00 | 1.00 | 0.95 | 44 | 76681 | 1366 | 0.187 |
| parallel | 11 | 0.91 | 1.00 | 1.00 | 0.95 | 22 | 74482 | 2133 | 0.192 |

## Instances whose report does not

| Topology | n | Acc@1 | Acc@3 | Acc@5 | MRR | Seconds | Tokens in | Tokens out | Cost $ |
|---|---|---|---|---|---|---|---|---|---|
| single | 15 | 0.87 | 0.87 | 0.87 | 0.87 | 28 | 61648 | 380 | 0.192 |
| sequential | 15 | 0.80 | 0.87 | 0.87 | 0.83 | 74 | 134407 | 1703 | 0.434 |
| hierarchical | 15 | 0.80 | 0.87 | 0.87 | 0.83 | 78 | 162304 | 2795 | 0.537 |
| parallel | 15 | 0.73 | 0.87 | 0.87 | 0.80 | 34 | 141031 | 2573 | 0.469 |

## Rank of the gold file, per instance

| Instance | Hinted | single | sequential | hierarchical | parallel |
|---|---|---|---|---|---|
| astropy__astropy-14365 | yes | 1 | 1 | 1 | 1 |
| astropy__astropy-7746 | yes | 1 | 1 | 1 | 1 |
| django__django-11179 | yes | 1 | 1 | 1 | 1 |
| django__django-15902 | no | 1 | 1 | 1 | 2 |
| django__django-16255 | yes | 1 | 1 | 1 | 1 |
| matplotlib__matplotlib-24149 | yes | 1 | 1 | 1 | 1 |
| matplotlib__matplotlib-25498 | yes | 1 | 1 | 1 | 1 |
| mwaskom__seaborn-3190 | yes | 1 | 2 | 1 | 1 |
| mwaskom__seaborn-3407 | yes | 1 | 1 | 1 | 1 |
| pallets__flask-4045 | no | 1 | 1 | 1 | 1 |
| pallets__flask-5063 | no | 1 | 1 | 1 | 1 |
| psf__requests-2148 | yes | 2 | 2 | 2 | 2 |
| psf__requests-3362 | no | 1 | 2 | 1 | 2 |
| pydata__xarray-3364 | no | 1 | 1 | 1 | 1 |
| pydata__xarray-4248 | no | 1 | 1 | 1 | 1 |
| pylint-dev__pylint-5859 | no | 1 | 1 | 1 | 1 |
| pylint-dev__pylint-7228 | no | 1 | 1 | 1 | 1 |
| pytest-dev__pytest-6116 | no | 1 | 1 | 1 | 1 |
| pytest-dev__pytest-7490 | no | 1 | 1 | 1 | 1 |
| scikit-learn__scikit-learn-10508 | yes | 1 | 1 | 1 | 1 |
| scikit-learn__scikit-learn-11040 | no | 1 | 1 | 1 | 1 |
| sphinx-doc__sphinx-10325 | no | 1 | 1 | 1 | 1 |
| sphinx-doc__sphinx-11445 | no | 1 | 1 | 2 | 1 |
| sympy__sympy-19254 | yes | 1 | 1 | 1 | 1 |
| sympy__sympy-20322 | no | — | — | — | — |
| sympy__sympy-21612 | no | — | — | — | — |
