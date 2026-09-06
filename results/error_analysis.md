# Week 4 Error Analysis

## Miss rate by detector and identity type

| Detector | Human miss rate | Agent miss rate |
|---|---|---|
| baseline | 6.7% | 50.0% |
| classifier | 23.3% | 16.7% |
| iforest | 36.3% | 3.3% |

## Classifier feature importance (standardized coefficients)

Sign indicates direction: positive pushes toward 'compromised', negative toward 'normal'.

| Feature | Coefficient |
|---|---|
| tool_diversity | +2.032 |
| actions_per_session | +1.142 |
| batch_size_mean | -0.940 |
| session_duration | -0.419 |
| idle_ratio | -0.227 |
| inter_action_variance | +0.106 |

## Hardest cases (missed by 2+ detectors)

113 sessions missed by 2 or more detectors (out of 600 test sessions). Breakdown by identity type:

| identity_type   |   count |
|:----------------|--------:|
| human           |      62 |
| agent           |      51 |

## False negatives vs. true positives, by feature (agent identity)

Where the classifier's false negatives on agent-compromised sessions differ most from its true positives -- these features are where a missed compromise 'hides'.

| Feature | False-negative mean | True-positive mean |
|---|---|---|
| session_duration | 189.177 | 180.518 |
| inter_action_variance | 3.315 | 2.950 |
| actions_per_session | 44.453 | 56.009 |
| batch_size_mean | 9.055 | 6.476 |
| idle_ratio | 0.021 | 0.019 |
| tool_diversity | 5.394 | 9.228 |
