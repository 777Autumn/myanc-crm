# CRM preview spelling — bounded correction

Fix baseline: CRM `6044a434a52e00bf642fc81fac1d170e1640e07d`.
Scope: the shared external-text presentation function, not writes or approval
ownership. The Owner's fictional customer-update journey exposed halfwidth
parentheses in cards and model results despite a fullwidth requested name.

The offline reproduction confirms that staging and the fake backend retain the
original spelling but NFKC presentation changes it. This does not establish the
live model's exact submitted string or the live database spelling. A model must
not infer raw database mutations merely from a transformed display.

## Contract

- Preserve benign Unicode spelling (fullwidth punctuation/letters, circled
  numbers and combining characters) in customer creation/update previews,
  subsequent follow-up previews, fresh reads and newly generated receipts.
- Detect forged role/fence markup on an NFKC-normalized candidate, including
  ASCII, small and fullwidth angle brackets and composed combining sequences.
  Replace the dangerous candidate; preserve surrounding business spelling.
- Retain the existing control-character filtering, whitespace collapsing,
  2,000-character display limit and CRM_DATA fence. This is a safe display, not a
  byte-exact raw export when those protections apply. The fence quotes data; it
  is not itself an approval or a complete prompt-injection defense.
- Keep normalized customer matching separate from raw snapshot fingerprints.
  Compatibility-equivalent spelling drift must still stop a pending write.
- Do not normalize writes, migrate/rewrite saved previews or receipts, change
  approval identity/CAS/TTL, or add dependencies, services or recovery logic.
  Old stored receipts may still contain the former normalized presentation;
  use a fresh customer read for current spelling, not an old receipt.

## Checks and rollout

Unit and real controlled-CLI/SQLite journeys pair benign Unicode with poisoned
history; both reads remain non-mutating. The write journey has two separate host
approvals, one child write, stored receipts and fresh customer/history reads.
The standard suite also covers the unchanged old follow-up and approval guards.
These deterministic tests are not live-model semantic or Feishu UI acceptance.

Before rollout, replay the existing native Claude harness with paired benign
Unicode and compatibility-spelled poisoned text, and check actual tool arguments
and resulting state as well as the reply. A blocked/not-run model gate remains
explicit. Deploy only to an idle backed-up Owner Sandbox after review; never
refresh an existing pending card into approval of a different displayed value.
Real CRM cutover remains separately gated. Official Commerce Skills and reference
source stay unchanged; the CRM adapter normalizes the security probe rather than
the displayed business text.
