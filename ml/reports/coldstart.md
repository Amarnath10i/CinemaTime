# Cold start: ranking movies with no ratings yet (test fold)

877 catalog movies released by 2023-10-14 had no likes before 2022-10-12, yet they make up 8.8% of the likes held out for evaluation; 2,525 test users liked at least one of them. Each method ranks only those cold movies for each such user; 95% bootstrap intervals over users.

| method                                | recall@20              | ndcg@20                |
|:--------------------------------------|:-----------------------|:-----------------------|
| random order                          | 0.0007 (0.0003-0.0012) | 0.0005 (0.0002-0.0009) |
| newest first                          | 0.1050 (0.0957-0.1145) | 0.0347 (0.0320-0.0373) |
| content similarity (CinemaTime today) | 0.0225 (0.0183-0.0271) | 0.0129 (0.0104-0.0156) |
| hybrid: content -> ALS space (mu=1)   | 0.1510 (0.1400-0.1615) | 0.0795 (0.0740-0.0851) |

Ridge strength chosen on the validation fold (NDCG@20 there): mu=0.1: 0.1106, mu=1: 0.1122, mu=10: 0.0942, mu=100: 0.0691
