# Deep Evaluation Summary

Generated on `2026-06-18` from the upgraded DiasporaVote prototype.

## Scope

The upgraded prototype was evaluated across four areas:

- proof-engine throughput
- backend ballot acceptance throughput
- concurrent voting stress behavior
- public board and database scalability

The workstation was capped with safe runtime limits during this run, so larger benchmark targets were skipped when projected runtime exceeded the configured limit. The scripts themselves still support the larger requested scales for later reruns on stronger hardware or with a longer benchmark window.

## Proof Engine Volume Benchmark

Source: `benchmark_results/proof_volume_benchmark.json`

- Completed scale: `1,000` proofs
- Total proof generation time: `698.1476 ms`
- Average proof generation time: `0.698148 ms`
- Total proof verification time: `446.3921 ms`
- Average proof verification time: `0.446392 ms`
- Average proof size: `6309.662 bytes`
- Estimated storage for 1,000 proofs: `6,309,662 bytes`
- Success rate: `100%`
- Failure rate: `0%`
- Skipped scales in this run: `10,000`, `100,000`, `1,000,000`

## Backend Ballot Acceptance Benchmark

Source: `benchmark_results/backend_ballot_benchmark.json`

- Completed scale: `1,000` ballots
- Accepted ballots: `1,000`
- Failed ballots: `0`
- Average ballot acceptance time: `81.117444 ms`
- Minimum ballot acceptance time: `49.7251 ms`
- Maximum ballot acceptance time: `470.6978 ms`
- Throughput: `12.324884 ballots/second`
- Final tally correctness: `passed`
- Nullifier uniqueness correctness: `passed`
- Observed tally: `500 yes`, `500 no`
- Skipped scales in this run: `10,000`, `100,000`

## Concurrent Voting Stress Test

Source: `benchmark_results/concurrent_voting_stress_test.json`

- Completed concurrency level: `10`
- Average request latency: `1284.17472 ms`
- Minimum latency: `980.2744 ms`
- Maximum latency: `1469.3577 ms`
- Throughput: `5.366095 ballots/second`
- Success rate: `100%`
- Failure rate: `0%`
- Duplicate rejection correctness: `passed`
- Final tally correctness: `passed`
- Skipped concurrency levels in this run: `50`, `100`, `200`, `500`

## Public Board and Database Scalability Test

Source: `benchmark_results/public_board_scalability_test.json`

### Completed size: `1,000` ballots

- Database size: `1,499,136 bytes`
- Tally query time: `37.6041 ms`
- Public board first-page query time: `7.3563 ms`
- Paginated query time: `11.3399 ms`
- Ballot lookup time: `1.7843 ms`
- Chain verification time: `142.2365 ms`
- Chain verification result: `passed`

### Completed size: `10,000` ballots

- Database size: `14,651,392 bytes`
- Tally query time: `290.9437 ms`
- Public board first-page query time: `4.8644 ms`
- Paginated query time: `5.785 ms`
- Ballot lookup time: `1.2536 ms`
- Chain verification time: `1164.8683 ms`
- Chain verification result: `passed`

Skipped sizes in this run: `100,000`, `1,000,000`

## Independent CLI Verification Result

Bundle used: `benchmark_results/sample_verification_bundle.json`

Command:

```bash
python tools/verify_bundle.py benchmark_results/sample_verification_bundle.json
```

Observed result:

- proof verification: `passed`
- proof hash check: `passed`
- receipt consistency check: `passed`
- chain hash check: `passed`
- final result: `valid`

## Interpretation

- The proof engine is no longer decorative: the verifier now checks a public nullifier and a public vote commitment derived from private witness values, while the vote bit remains hidden.
- Duplicate-vote prevention is strengthened by event-scoped nullifiers and verified uniqueness checks.
- The public board now carries append-only hash-chain metadata that can be recomputed independently.
- Independent verification is no longer server-mediated only: a standalone CLI verifier validated the exported bundle successfully.
- The prototype remains honest about scale: the current machine comfortably completed the smaller safe scales, while the larger scales were skipped rather than guessed.
