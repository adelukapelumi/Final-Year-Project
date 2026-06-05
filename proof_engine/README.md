# Proof Engine Spike

This spike is scoped to GitHub issue `#1`: verify whether the project can generate and verify a real local zk-STARK proof artifact for the binary referendum acceptance computation.

## Scope kept

Only the files requested in the issue were created under `proof_engine/`.

## MVP statement

The Cairo program models this acceptance computation:

```txt
vote_value * (vote_value - 1) = 0
registered_flag = 1
already_voted_flag = 0
accepted = registered_flag * (1 - already_voted_flag)
accepted = 1
```

Inputs are passed as three integers in this order:

```txt
[vote_value, registered_flag, already_voted_flag]
```

The `accepted` value is computed inside the Cairo executable and returned as the program output.

## Intended proof flow

This spike targets the current official Scarb executable/prove/verify flow for Cairo executable packages:

1. `scarb execute -p referendum_acceptance --target standalone --output standard --print-program-output --arguments-file inputs/<case>.json`
2. `scarb prove --execution-id 1`
3. Copy `target/execute/referendum_acceptance/execution1/proof/proof.json` to `artifacts/<case>.proof.json`
4. `scarb verify --proof-file artifacts/<case>.proof.json`
5. `./scripts/hash_proof.sh artifacts/<case>.proof.json`

## Current result on this machine

No real local proof artifact was generated in this session.

Reason:

- `scarb` is not installed on the current machine.
- `cairo-prove` is not installed on the current machine.
- The current host is Windows, and Scarb's proving docs currently state that the prover is not available on Windows.

Because of that, the spike stops honestly at the blocker boundary required by the issue instead of faking a proof file.

## Exact commands run

These commands were run locally on `2026-06-04` in this repository:

```powershell
scarb --version
```

```txt
scarb : The term 'scarb' is not recognized as the name of a cmdlet, function, script file, or operable program. Check
the spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:2 char:1
+ scarb --version
+ ~~~~~
    + CategoryInfo          : ObjectNotFound: (scarb:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
```

```powershell
cairo-prove --help
```

```txt
cairo-prove : The term 'cairo-prove' is not recognized as the name of a cmdlet, function, script file, or operable
program. Check the spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:2 char:1
+ cairo-prove --help
+ ~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (cairo-prove:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
```

```powershell
bash --version
```

```txt
Program 'bash.exe' failed to run: The file cannot be accessed by the systemAt line:2 char:1
+ bash --version
+ ~~~~~~~~~~~~~~.
At line:2 char:1
+ bash --version
+ ~~~~~~~~~~~~~~
    + CategoryInfo          : ResourceUnavailable: (:) [], ApplicationFailedException
    + FullyQualifiedErrorId : NativeCommandFailed
```

## What the scripts do

- `scripts/prove.sh` runs `scarb execute`, runs `scarb prove`, and copies the real generated `proof.json` into `artifacts/`.
- `scripts/verify.sh` verifies a proof file with `scarb verify --proof-file`.
- `scripts/hash_proof.sh` computes the SHA-256 hash of the proof artifact file itself.

## Expected success signal

On a supported Linux or WSL environment with `scarb` installed and proving enabled, success should look like:

```txt
Executing referendum_acceptance
Proving referendum_acceptance
Saving proof to: target/execute/referendum_acceptance/execution1/proof/proof.json
Proof copied to: proof_engine/cairo/artifacts/<case>.proof.json
```

and:

```txt
Verifying proof...
```

with exit code `0`.

## Expected failure signal

Invalid inputs should panic during execution and therefore never produce a proof file:

- `invalid_vote_value.json`
- `unregistered.json`
- `duplicate_vote.json`

## Required next step

Run this same `proof_engine/cairo` directory on a supported Linux or WSL host with current Cairo/Scarb proving support installed. That is the shortest path to determining whether the exact Cairo program here can generate and verify a real artifact under `proof_engine/cairo/artifacts/`.

## Issue report

```txt
TASK DONE:
Created the requested proof-engine-only spike files and verified the current blocker honestly.

OUTPUT PRODUCED:
Prepared Cairo executable source, five input files, three proof helper scripts, and a stable artifacts directory.
No real local proof artifact was produced on this Windows machine in this session.

FILES CREATED:
proof_engine/README.md
proof_engine/cairo/Scarb.toml
proof_engine/cairo/src/lib.cairo
proof_engine/cairo/src/main.cairo
proof_engine/cairo/inputs/valid_yes.json
proof_engine/cairo/inputs/valid_no.json
proof_engine/cairo/inputs/invalid_vote_value.json
proof_engine/cairo/inputs/unregistered.json
proof_engine/cairo/inputs/duplicate_vote.json
proof_engine/cairo/scripts/prove.sh
proof_engine/cairo/scripts/verify.sh
proof_engine/cairo/scripts/hash_proof.sh
proof_engine/cairo/artifacts/.gitkeep

COMMANDS RUN:
scarb --version
cairo-prove --help
bash --version

EXPECTED SUCCESS SIGNAL:
scarb execute succeeds, scarb prove writes proof.json, the proof is copied into proof_engine/cairo/artifacts/, scarb verify exits 0, and hash_proof.sh emits a SHA-256 digest for the proof file.

EXPECTED FAILURE SIGNAL:
Invalid inputs panic during execution and therefore do not produce proof.json.
Current machine also fails earlier because Cairo proving tooling is not installed and Scarb proving is documented as unavailable on Windows.

ASSUMPTIONS MADE:
The intended proof path is the official Scarb executable/prove/verify flow for Cairo executables.
The input files are serialized as argument arrays in the order [vote_value, registered_flag, already_voted_flag].

FACTS THAT NEED VERIFICATION:
Whether this exact Cairo source compiles unchanged with the target Scarb version once run on Linux or WSL.
Whether the selected Scarb version on the target host supports proof generation for this package without manifest changes.

WHAT YOU NEED NEXT:
A Linux or WSL environment with working Scarb/Cairo proving support to run the scripts and confirm real proof generation and verification.
```

## References

- Scarb executable package guide: https://docs.swmansion.com/scarb/docs/guides/creating-executable-package.html
- Scarb proving and verifying docs: https://docs.swmansion.com/scarb/docs/extensions/prove-and-verify.html
- Cairo book proving example: https://www.starknet.io/cairo-book/ch01-03-proving-a-prime-number.html
