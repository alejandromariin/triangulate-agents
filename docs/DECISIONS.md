# Decision log

Design decisions and course corrections, newest first.
Format: what was decided, what was considered instead, and why.

---

### D-010 · Splits are stratified by whether the statement names the gold file
**2026-08-03**

42% of the selected instances have the gold file's path written somewhere in the
problem statement — almost always in a pasted stack trace:

```
File ".../django/contrib/staticfiles/handlers.py", line 86, in __call__
```

Those instances are markedly easier: the answer is in the input. Repository-only
stratification left them at **46% of `dev` against 8% of `heldout`**. Both splits
are now stratified on this property as well, bringing them to 42% each.

- **Considered:** excluding hinted instances from the golden set. Rejected —
  pasted stack traces are how bug reports actually look, and a locator should
  exploit them exactly as a developer would. Removing them would measure a
  cleaner but less real task.
- **Considered:** trying seeds until the split looked balanced. Rejected — that
  selects the evaluation set by inspecting a property of its outcome, and no
  honest answer exists to "why this seed?".
- **Why stratify:** a drop from `dev` to `heldout` is the project's main warning
  signal for overfitting. With unequal difficulty across the splits, overfitting
  and a harder sample produce the same symptom and cannot be told apart. The
  reasoning is identical to stratifying by repository: a variable known to move
  the result is controlled rather than left to the draw.
- **Detection** is lexical: the gold path, its bare file name, or its dotted
  module form appearing in the statement. All 16 matches were inspected by hand
  and none was a false positive, but the rule is a heuristic and can miss
  paraphrased mentions, so treat the share as approximate.
- **Kept as a field**, not just used for splitting: `statement_names_gold_file`
  lets results be reported separately for hinted and unhinted instances. Whether
  topologies converge when the answer is given and diverge when it is not is a
  sharper question than any aggregate, and an aggregate would hide it.

### D-009 · Per-repository quotas instead of a cap; split is 26 dev / 12 held-out
**2026-08-03**

Each of the 12 repositories contributes a fixed quota of instances — 3, plus one
extra for the two largest — and within a repository the specific instances are
drawn with the seed. Exactly one instance per repository goes to `heldout`.

- **Considered:** a `max_per_repo = 5` cap followed by a random draw over the
  surviving pool of 57.
- **Why:** a cap sets a ceiling but no floor. A random draw under a cap can
  legitimately return five Django instances, five sympy instances and *zero*
  Flask instances — nothing prevents a repository from vanishing from the golden
  set. Quotas make repository coverage a property of the design rather than an
  outcome of the draw. Randomness still decides *which* instances, just not *how
  many* per repository.
- **Arithmetic:** 12 repositories × 3 = 36, plus one extra to each of the two
  largest = 38. One instance per repository is held out ⇒ **26 dev / 12
  held-out**, superseding the 25/13 of D-005 and D-006, which were chosen before
  the repository distribution was measured. 26/12 falls out of the structure
  instead of being rounded to a target; the effect on the margin of error is
  ±27 → ±28 points, i.e. cosmetic, while the regularity is not.
- **Property gained:** the held-out split contains exactly one bug from every
  repository. The reported headline number cannot be dominated by whichever
  projects happened to land there, and no project is absent from it.
- **Cost, stated plainly:** equal quotas deliberately depart from the real
  distribution of bugs. Django supplies 114 of the 300 upstream instances and
  contributes 4 here; Flask supplies 3 and contributes 3. The reported numbers
  therefore answer "how does this behave averaged evenly across projects?", not
  "how does this behave on the real-world mix of bugs?". The former is the right
  question for a comparison of topologies, which is about robustness across
  codebases, but it is a choice and not a neutral default.
- **Side benefit:** with every repository guaranteed at least three instances,
  per-repository error analysis is possible at all. Under a random draw,
  repositories with zero or one instance would make that question unanswerable.

### D-008 · Every SWE-bench Lite instance touches exactly one file
**2026-08-03**

Measured before writing the build script: all 300 instances of the `test` split
survive every filter, and all 300 have exactly one gold file. No file was
dropped as a test, a non-Python file or a deletion — SWE-bench Lite is already
curated down to single-file, product-code fixes.

- **Filters are kept anyway**, as safeguards rather than filters: they cost
  nothing, they document what the task assumes, and they are what keeps the
  pipeline safe to point at a less curated dataset. `meta.filters` will
  legitimately report zeros.
- **Consequence for metrics:** with a single gold file per instance, Precision@k
  is degenerate — a perfect answer inside a 5-candidate list scores 0.2. The
  meaningful metrics are Accuracy@k (is the gold file in the top k?) and MRR (how
  high was it ranked?). F1 is not reportable until function-level ground truth
  reintroduces multi-target instances.
- **Consequence for scope:** the benchmark only covers single-file bugs.
  Multi-file bugs — arguably where a team of specialists should have the largest
  advantage over a single agent — are absent from the dataset. Any conclusion
  about topologies holds for single-file localization and must be stated that way.
  Addressing it means moving beyond SWE-bench Lite.
- **Method note:** this was found by measuring the funnel before implementing it.
  Written blind, the script would have carried three filters that never fire and
  a metric that cannot express the result.

### D-007 · OpenAI models rather than Anthropic
**2026-08-03**

- **Considered:** the Anthropic API.
- **Why:** existing API access and familiarity, which removes friction from the
  fastest-moving part of the project.
- **Scope:** the choice of provider is orthogonal to the research question. The
  comparison is between *topologies* under a fixed model, not between models. A
  cross-model replication is planned precisely to test whether the topology
  conclusions hold independently of the model.
- **Open:** the specific cheap/expensive model pair is deferred until the first
  agent runs and the real cost per instance can be measured.

### D-006 · Golden set fixed at 38 instances
**2026-08-03**

38 instances (26 dev / 12 held-out, see D-009), with the cost question
deliberately answered somewhere other than the size of the dataset.

- **Considered:** 15-24 instances to reduce API spend.
- **Why:** building the golden set costs zero tokens — it downloads a public
  dataset and filters JSON. Dataset size and number of executed instances are
  independent: the runner takes a limit, so a 38-instance file can be run on 5.
  Meanwhile the project's claim is comparative ("topology A beats topology B"),
  and comparative claims need sample size. At N=10 the margin of error on a rate
  is roughly ±31 points, which is wider than any plausible difference between
  topologies — the experiment would be unable to conclude anything.
- **Cost is controlled elsewhere:** iterate on a 5-instance subset; run the full
  set rarely; hard dollar cap in the runner; bounded `max_iter` per agent;
  persisted per-instance results so a failed run resumes instead of restarting.
- **Revisit:** after measuring real token cost on a single instance.
  Regenerating a smaller set is one command.

### D-005 · Dev / held-out split from day one
**2026-08-03**

26 instances for iteration, 12 reserved (see D-009 for how those figures arise).
Prompts, parameters and architecture are tuned looking only at `dev`. The
held-out split is run rarely and produces the reported numbers.

- **Considered:** a single pool, simpler to manage.
- **Why:** tuning against the same instances you report on silently optimizes for
  those specific instances. The resulting numbers describe the dataset, not the
  system. A split that is never inspected is the only honest headline figure.
- **If contaminated:** resample a fresh held-out set from the remaining SWE-bench
  Lite pool and record it here.

### D-004 · `gold_functions` derived heuristically, and marked as such
**2026-08-03**

Function-level ground truth is extracted from the section heading git writes into
each diff hunk header, not from parsing the source.

- **Considered:** cloning every repository at `base_commit` and resolving hunk
  line numbers to enclosing definitions with `ast`.
- **Why:** the accurate method requires checkouts that the build script does not
  have, and file-level scoring does not need it. The heuristic is free and good
  enough to inspect.
- **Cost:** it is wrong for some nested definitions and absent for hunks with no
  heading — both are observable on `django__django-11099`. `data/SCHEMA.md`
  states explicitly that the field is not reportable ground truth; scoring uses
  `gold_files` only.

### D-003 · The gold patch is never stored in the golden set
**2026-08-03**

`gold_files` is derived from SWE-bench's `patch` field at build time, and the
patch itself is discarded. `hints_text` is stored but never reaches the agent.

- **Considered:** keeping the patch for convenience and filtering it out at
  prompt construction time.
- **Why:** the patch is literally the answer. Filtering relies on remembering to
  filter, every time, in every topology. Not storing it makes the leak
  structurally impossible rather than merely unlikely — a stronger guarantee for
  a one-line cost. Same reasoning for `hints_text`, which frequently names the
  faulty file outright.

### D-002 · Dependencies added incrementally, pinned exactly
**2026-08-03**

`pyproject.toml` declares only what is actually used, at exact versions.

- **Considered:** declaring the full intended stack up front.
- **Why:** exact pins keep reported numbers reproducible. Adding dependencies
  only when something needs them keeps install times short and makes the git
  history show what each one was added for.

### D-001 · The repository is not an installable package
**2026-08-03**

Top-level directories with `package = false`; entry points run as
`uv run python -m scripts.build_golden_set` from the root.

- **Considered:** a conventional `src/triangulate/` layout.
- **Why:** the flat layout keeps the directory names identical to the
  architecture they represent, with no packaging indirection to explain. Nothing
  here is consumed as a library.
- **Revisit:** if the eval harness is ever extracted for reuse elsewhere, real
  packaging becomes necessary.
