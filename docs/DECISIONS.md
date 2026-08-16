# Decision log

Design decisions and course corrections, newest first.
Format: what was decided, what was considered instead, and why.

Recorded here only when a decision constrains how the data is handled or how the
reported numbers must be read. Tooling preferences and layout conventions are
left to the code.

---

### D-012 · The system is stochastic, and differences of one instance are not read as differences
**2026-08-16**

Two runs of the same topology, with the same prompts and the same code, are not
guaranteed to produce the same answers. This was observed rather than assumed:
on `django__django-15902` the sequential topology ranked the gold file first in
one run and second in the next, with nothing changed between them but a field
being recorded.

- **Mitigated** by fixing `temperature=0` for every agent of every topology,
  which narrows the variation. It does not eliminate it: tool call ordering and
  provider-side non-determinism remain.
- **Considered:** running each instance several times and averaging, which is the
  direct answer to sampling noise, and not adopted. The consequence is stated
  rather than hidden: every reported figure comes from a single run per topology
  and carries that noise.
- **How to read the numbers:** a gap of one or two instances between two
  topologies is not evidence that they differ. With 26 dev instances, one
  instance moves accuracy by ~4 points, so only differences of several points
  are discussed as differences. Per-instance comparisons are read the same way —
  a single bug that one topology wins is a lead to investigate in its recorded
  stages, not a result.
- **Practical consequence:** results cannot be reproduced exactly from the same
  command. Reproducing the *conclusions* is the claim; reproducing the JSON byte
  for byte is not.

### D-011 · Results are cached per instance, and a run can stop early
**2026-08-16**

Each answered instance is written to `reports/runs/<topology>_<split>/` on its
own. A later run of the same topology and split reuses those files instead of
asking the model again, and stops before starting an instance once the run's
spend passes `--max-usd`.

- **Why cache:** a run over a split is a sequence of paid, independent calls. A
  failure in the middle would otherwise discard every answer before it, and the
  natural response — rerunning the whole split — would pay for them twice. The
  cost of the experiment should be proportional to the instances that still need
  answering, not to the number of times something went wrong.
- **Why the cap is checked before an instance rather than after:** a limit
  enforced after the call has already spent the money it exists to prevent.
- **How to read the numbers:** a summary reports `n`, and `n` may be smaller than
  the split — because of `--limit`, or because the cap stopped the run. A row is
  only comparable with another row of the same `n` over the same instances, which
  is why `--limit` selects instances in a fixed order rather than at random.
- **The cache is keyed by topology and split only**, not by prompt or budget. It
  therefore cannot tell that a stored answer was produced under different
  conditions, and mixing them would silently average two systems into one row.
  Changing a prompt, a candidate cap or an iteration cap means deleting the run
  directory; the alternative — hashing the configuration into the key — was
  rejected as machinery guarding a step that is one command.

### D-010 · The repository is exposed at `base_commit`, and nothing after it
**2026-08-06**

Clones contain the full history, including the commit that fixes the bug. Before
each instance the checkout is parked on `base_commit`, and every history tool is
anchored at `HEAD`, which git only walks backwards from. Options that traverse
other branches (`--all`, explicit revisions) are never passed.

- **What would happen otherwise:** `git_log` would list the fixing commit, whose
  message and touched paths are the answer. Accuracy would go *up*, which makes
  this the most dangerous kind of failure — it looks like success.
- **Verified, not assumed:** on `django__django-15902` the clone holds 3,935
  commits after `base_commit`; none of them appears in the tool's output. The
  same property is what `scripts/setup_repos.py` checks when it confirms every
  `base_commit` and gold file exists.
- **Checkout uses `--force`:** a dirty working tree would otherwise leave an
  instance silently evaluated against a different revision, which is the same
  class of error in the other direction.
- **How to read the numbers:** they describe a system that saw the repository
  exactly as it stood when the bug was reported. Any change to how the checkout
  is prepared has to preserve that, or the results stop being comparable with
  earlier runs.

### D-009 · A hit requires the full repository-relative path
**2026-08-06**

Scoring compares paths verbatim after normalising separators, a leading `./` or
`/`, and surrounding whitespace. Case is not normalised, and partial paths do not
count: `formsets.py` and `forms/formsets.py` are misses even when the gold file
is `django/forms/formsets.py`.

- **Considered:** accepting any suffix of the gold path, or the bare file name.
- **Why not:** naming a file is not locating it. Django contains many `utils.py`,
  `base.py` and `models.py`; a topology that emitted bare file names without ever
  finding where they live would score almost as well as one that investigated,
  and the benchmark would stop measuring what it claims to measure.
- **Why case is left alone:** on a case-sensitive filesystem `Utils.py` and
  `utils.py` are different files, so folding case would accept an answer that
  does not exist in the repository.
- **Paired with the prompt:** the required format is stated explicitly in the
  task, with examples of what is rejected, and the wording is identical across
  topologies. A metric may only penalise what the prompt asked for — otherwise
  the experiment partly measures whether a model guessed the expected format,
  which is not the subject of the comparison.
- **How to read the numbers:** a malformed answer counts as a miss, exactly like
  a wrong one. Runs therefore also record how many answers contained no
  well-formed path at all, so a topology failing on format rather than on
  reasoning is visible instead of silently penalised.

### D-008 · Every topology answers with at most five files and a bounded budget
**2026-08-06**

Each topology returns a ranked list capped at 5 candidates, and each agent is
capped at 15 tool-using iterations.

- **Why the cap on candidates:** with a single gold file per instance, an
  unbounded list would let a topology hedge — naming twenty files guarantees a
  hit and makes Accuracy@k meaningless. Five is enough for MRR to discriminate
  between ranks while keeping the answer a commitment rather than a sweep.
- **Why the cap on iterations:** it bounds the cost of a single instance, and it
  bounds it *equally* for every topology. Without it, the topologies would differ
  in how long they are allowed to run, and any difference in accuracy could be
  bought with tokens rather than with structure.
- **How to read the numbers:** both caps are part of the measurement. A reported
  Accuracy@5 is "accuracy under a 5-candidate, 15-iteration budget", and a
  topology that would do better with more room is recorded as doing worse here.
  Raising either cap invalidates comparison with earlier runs.
- **Reported alongside results:** elapsed time and token usage per instance, so
  the accuracy of a topology is never read without its cost.

### D-007 · Splits are stratified by whether the statement names the gold file
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

### D-006 · Per-repository quotas instead of a cap; split is 26 dev / 12 held-out
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
  held-out**, superseding the 25/13 of D-003 and D-004, which were chosen before
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

### D-005 · Every SWE-bench Lite instance touches exactly one file
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

### D-004 · Golden set fixed at 38 instances
**2026-08-03**

38 instances (26 dev / 12 held-out, see D-006), with the cost question
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

### D-003 · Dev / held-out split from day one
**2026-08-03**

26 instances for iteration, 12 reserved (see D-006 for how those figures arise).
Prompts, parameters and architecture are tuned looking only at `dev`. The
held-out split is run rarely and produces the reported numbers.

- **Considered:** a single pool, simpler to manage.
- **Why:** tuning against the same instances you report on silently optimizes for
  those specific instances. The resulting numbers describe the dataset, not the
  system. A split that is never inspected is the only honest headline figure.
- **If contaminated:** resample a fresh held-out set from the remaining SWE-bench
  Lite pool and record it here.

### D-002 · `gold_functions` derived heuristically, and marked as such
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

### D-001 · The gold patch is never stored in the golden set
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
