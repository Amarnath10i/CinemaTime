# Serving: is what ships what was evaluated?

Test fold: models see likes before 2022-10-12; 5,396 users are scored on what they liked until 2023-10-14. 95% bootstrap intervals over users; differences are paired over the same users.

## 1. Pruning EASE for serving

The dense item-item matrix is too big for a small serverless function. Keeping each movie's strongest weights (by magnitude, sign preserved), EASE alone:

| model                                                     | ndcg@20                | recall@20              | recall@50              |   weights (MB) |
|:----------------------------------------------------------|:-----------------------|:-----------------------|:-----------------------|---------------:|
| EASE (lambda=500, half-life 1y)                           | 0.1240 (0.1194-0.1284) | 0.1257 (0.1209-0.1314) | 0.2159 (0.2096-0.2221) |          319   |
| EASE (lambda=500, half-life 1y), top 50 weights per item  | 0.1159 (0.1113-0.1201) | 0.1174 (0.1123-0.1224) | 0.2054 (0.1987-0.2116) |            2.3 |
| EASE (lambda=500, half-life 1y), top 100 weights per item | 0.1183 (0.1138-0.1226) | 0.1197 (0.1145-0.1251) | 0.2088 (0.2020-0.2155) |            4.6 |
| EASE (lambda=500, half-life 1y), top 200 weights per item | 0.1210 (0.1164-0.1253) | 0.1227 (0.1177-0.1285) | 0.2134 (0.2064-0.2199) |            9.3 |
| EASE (lambda=500, half-life 1y), top 500 weights per item | 0.1229 (0.1183-0.1273) | 0.1246 (0.1194-0.1302) | 0.2156 (0.2095-0.2216) |           23.2 |

## 2. Replaying the test users through the API's engine

Artifacts exported from the 2022-10-12 cutoff, ranker trained on the validation fold with the same pruned EASE; every test user sent as a visitor with their full history. What remains different is ALS: the engine solves each visitor's vector at request time, the offline model uses the trained one.

| model                                             | ndcg@20                | recall@20              | recall@50              | vs offline                   |
|:--------------------------------------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------------|
| offline two-stage, EASE top 200 (LightGBM, SciPy) | 0.1405 (0.1364-0.1452) | 0.1428 (0.1379-0.1486) | 0.2340 (0.2278-0.2404) | -                            |
| served: API engine on exported arrays (NumPy)     | 0.1405 (0.1363-0.1451) | 0.1427 (0.1377-0.1485) | 0.2341 (0.2281-0.2407) | -0.0000 (-0.0005 to +0.0004) |
| served, likes sent without recency weights        | 0.1341 (0.1299-0.1385) | 0.1275 (0.1224-0.1323) | 0.2172 (0.2107-0.2239) | -0.0064 (-0.0087 to -0.0042) |

## 3. Training-serving skew, measured

An earlier version trained the ranker on features from the dense EASE and served the pruned one. Pruning to the top 200 weights changes EASE's own NDCG@20 by -0.0029. A ranker trained on the dense EASE's features but served the pruned EASE changes the two-stage NDCG@20 by -0.0026: its thresholds on `ease_rank` and `ease_rel` were learned on the dense distribution, which pruning shifts (thousands of small weights become exactly zero). The loss is small but avoidable: the ranker trained on the pruned EASE it is served with matches the dense pipeline.

| model                                                          | ndcg@20                | recall@20              | recall@50              | vs consistent served         |
|:---------------------------------------------------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------------|
| ranker trained on dense-EASE features, offline with dense EASE | 0.1405 (0.1359-0.1449) | 0.1433 (0.1382-0.1491) | 0.2325 (0.2261-0.2393) | -                            |
| same ranker served with EASE top 200 (skew)                    | 0.1379 (0.1334-0.1426) | 0.1410 (0.1359-0.1466) | 0.2301 (0.2235-0.2365) | -0.0025 (-0.0046 to -0.0008) |
| ranker trained on EASE top 200 features, served the same       | 0.1405 (0.1363-0.1451) | 0.1427 (0.1377-0.1485) | 0.2341 (0.2281-0.2407) | -                            |

## 4. Visitors with only a few likes

Each test user replayed with only their *m* most recent likes before the cutoff (users with fewer give all of theirs). NDCG@20 against the same held-out year.

|   likes given |   popularity (last year) |   content (CinemaTime before) |   EASE alone |   ALS fold-in alone |   two-stage engine |
|--------------:|-------------------------:|------------------------------:|-------------:|--------------------:|-------------------:|
|        1.0000 |                   0.0447 |                        0.0087 |       0.0449 |              0.0405 |             0.0443 |
|        3.0000 |                   0.0450 |                        0.0100 |       0.0588 |              0.0464 |             0.0612 |
|        5.0000 |                   0.0453 |                        0.0085 |       0.0664 |              0.0498 |             0.0697 |
|       10.0000 |                   0.0461 |                        0.0080 |       0.0732 |              0.0556 |             0.0820 |
|       20.0000 |                   0.0477 |                        0.0073 |       0.0780 |              0.0605 |             0.0925 |

## 5. Latency

One request (10 likes, top 20 with explanations), engine only, in-process: p50 16.5 ms, p95 18.2 ms over 300 requests on a laptop CPU.

## 6. Shipped artifacts

Retrievers refitted on every like until 2023-10-14; ranker trained on the 2022-10-12 to 2023-10-14 window (69 trees).

- `backend/recsys/artifacts/meta.json`: 0.0 MB
- `backend/recsys/artifacts/model.npz`: 9.0 MB
