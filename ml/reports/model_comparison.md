# Model comparison (test fold)

Models train on likes (ratings >= 4) before 2022-10-12 and rank all 8,926 catalog movies for 5,396 users, who are scored on the 87,958 movies they liked in the following year. Full ranking, no sampled negatives. Point estimate with a 95% bootstrap interval over users.

| model                                                                            | recall@20              | ndcg@20                | hit@10                 | recall@50              |   cold recall@50 |   coverage@10 |   novelty (bits) |   diversity@10 |
|:---------------------------------------------------------------------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------|-----------------:|--------------:|-----------------:|---------------:|
| Popularity (all time)                                                            | 0.0421 (0.0392-0.0449) | 0.0481 (0.0453-0.0509) | 0.2135 (0.2035-0.2242) | 0.0853 (0.0812-0.0895) |           0      |         0.015 |             1.87 |          0.779 |
| Popularity (last 12 months)                                                      | 0.0956 (0.0909-0.0998) | 0.0851 (0.0814-0.0887) | 0.3458 (0.3329-0.3595) | 0.1613 (0.1555-0.1668) |           0      |         0.013 |             3.28 |          0.767 |
| Content: SBERT profile (current CinemaTime)                                      | 0.0064 (0.0055-0.0075) | 0.0062 (0.0056-0.0070) | 0.0424 (0.0372-0.0483) | 0.0149 (0.0134-0.0167) |           0.01   |         0.067 |            12.05 |          0.479 |
| Item-kNN (cosine, k=200, shrink=50)                                              | 0.0688 (0.0650-0.0730) | 0.0760 (0.0725-0.0797) | 0.2984 (0.2869-0.3102) | 0.1261 (0.1210-0.1313) |           0      |         0.091 |             2.87 |          0.771 |
| EASE (lambda=500)                                                                | 0.0916 (0.0872-0.0961) | 0.0985 (0.0946-0.1026) | 0.3747 (0.3624-0.3876) | 0.1694 (0.1644-0.1752) |           0      |         0.166 |             3.58 |          0.777 |
| EASE (lambda=500, half-life 1y)                                                  | 0.1257 (0.1209-0.1314) | 0.1240 (0.1194-0.1284) | 0.4646 (0.4501-0.4780) | 0.2159 (0.2096-0.2221) |           0      |         0.1   |             4.35 |          0.766 |
| EASE (lambda=500, half-life 1y), top 200 weights per item                        | 0.1227 (0.1177-0.1285) | 0.1210 (0.1164-0.1253) | 0.4581 (0.4427-0.4718) | 0.2134 (0.2064-0.2199) |           0      |         0.097 |             4.27 |          0.765 |
| ALS (k=64, alpha=20, lambda=10)                                                  | 0.0792 (0.0753-0.0832) | 0.0805 (0.0770-0.0844) | 0.3249 (0.3123-0.3375) | 0.1518 (0.1466-0.1574) |           0      |         0.206 |             4.14 |          0.77  |
| Hybrid ALS: ALS (k=64, alpha=20, lambda=10) + content map for cold movies (mu=1) | 0.0793 (0.0753-0.0833) | 0.0806 (0.0771-0.0844) | 0.3254 (0.3128-0.3379) | 0.1517 (0.1466-0.1571) |           0.0005 |         0.206 |             4.15 |          0.77  |
| Two-stage: EASE + hybrid ALS + popularity + content -> LambdaRank                | 0.1428 (0.1379-0.1486) | 0.1405 (0.1364-0.1452) | 0.5115 (0.4988-0.5262) | 0.2340 (0.2278-0.2404) |           0.002  |         0.135 |             5.82 |          0.746 |

## Two-stage ranker vs. alternatives (paired bootstrap over the same users)

| metric | compared with | difference (95% interval) | relative |
|---|---|---|---|
| recall@20 | current CinemaTime (content) | +0.1364 (+0.1310 to +0.1425) | +2144% |
| recall@20 | best single model (EASE) | +0.0170 (+0.0126 to +0.0216) | +14% |
| ndcg@20 | current CinemaTime (content) | +0.1343 (+0.1301 to +0.1389) | +2156% |
| ndcg@20 | best single model (EASE) | +0.0166 (+0.0129 to +0.0198) | +13% |

The ranker re-orders candidates from ease (150), als (100), popularity (50), content (50); on the validation fold those candidates contained 40.0% of users' future likes, the ceiling for stage 2.

## What the ranker relies on (share of split gain)

| feature | share |
|---|---|
| ease_rank | 0.242 |
| ease_rel | 0.127 |
| share_last_year | 0.108 |
| age_years | 0.100 |
| als_rank | 0.078 |
| als_rel | 0.065 |
| log_likes_last_year | 0.056 |
| log_likes | 0.049 |
| genre_overlap | 0.046 |
| content_rank | 0.037 |
| content_score | 0.033 |
| user_log_likes | 0.032 |
| year_gap | 0.026 |
| is_cold | 0.000 |
