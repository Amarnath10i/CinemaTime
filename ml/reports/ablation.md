# Ranker feature ablation (test fold)

Each feature group is removed, the LambdaRank model is retrained on the validation fold's candidates, and test NDCG@20 is compared with the full ranker on the same 5,396 users (paired bootstrap, 95% interval). A negative change means the group helps.

| removed                                 |   ndcg@20 | change                       | relative   |
|:----------------------------------------|----------:|:-----------------------------|:-----------|
| nothing (full ranker)                   |    0.1405 | -                            | -          |
| EASE score and rank                     |    0.1255 | -0.0150 (-0.0176 to -0.0127) | -10.7%     |
| ALS score and rank                      |    0.1371 | -0.0034 (-0.0054 to -0.0014) | -2.4%      |
| content score and rank                  |    0.1365 | -0.0041 (-0.0059 to -0.0024) | -2.9%      |
| popularity and freshness                |    0.1193 | -0.0212 (-0.0241 to -0.0179) | -15.1%     |
| user-movie fit (genre overlap, era gap) |    0.1414 | +0.0009 (-0.0007 to +0.0024) | +0.7%      |
| user history length                     |    0.1397 | -0.0008 (-0.0024 to +0.0007) | -0.6%      |
