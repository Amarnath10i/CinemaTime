# Hyperparameter selection (validation fold)

Train on likes before 2021-10-12, evaluate 5,619 users' likes until 2022-10-12. Selection by NDCG@20; the test fold is not touched.

| family   | model                                | fit (s)   |   recall@20 |   ndcg@20 |   coverage@10 |
|:---------|:-------------------------------------|:----------|------------:|----------:|--------------:|
| als      | ALS (k=64, alpha=20, lambda=10)      | cached    |      0.0740 |    0.0763 |        0.2020 |
| als      | ALS (k=128, alpha=20, lambda=10)     | cached    |      0.0734 |    0.0750 |        0.2213 |
| als      | ALS (k=128, alpha=40, lambda=50)     | cached    |      0.0688 |    0.0689 |        0.2465 |
| ease     | EASE (lambda=500, half-life 1y)      | 22        |      0.1111 |    0.1094 |        0.1078 |
| ease     | EASE (lambda=250, half-life 1y)      | 20        |      0.1084 |    0.1085 |        0.1257 |
| ease     | EASE (lambda=1000, half-life 1y)     | 20        |      0.1091 |    0.1078 |        0.0911 |
| ease     | EASE (lambda=500, half-life 6mo)     | 20        |      0.1074 |    0.1070 |        0.1089 |
| ease     | EASE (lambda=250, half-life 2y)      | 20        |      0.1059 |    0.1070 |        0.1319 |
| ease     | EASE (lambda=250, half-life 6mo)     | 25        |      0.1065 |    0.1068 |        0.1269 |
| ease     | EASE (lambda=500, half-life 2y)      | 19        |      0.1061 |    0.1067 |        0.1144 |
| ease     | EASE (lambda=2000, half-life 1y)     | 20        |      0.1070 |    0.1060 |        0.0753 |
| ease     | EASE (lambda=1000, half-life 2y)     | 20        |      0.1052 |    0.1060 |        0.0972 |
| ease     | EASE (lambda=1000, half-life 6mo)    | 19        |      0.1069 |    0.1059 |        0.0932 |
| ease     | EASE (lambda=2000, half-life 6mo)    | 19        |      0.1046 |    0.1041 |        0.0786 |
| ease     | EASE (lambda=2000, half-life 2y)     | 20        |      0.1034 |    0.1041 |        0.0806 |
| ease     | EASE (lambda=250, half-life 4y)      | 23        |      0.0997 |    0.1024 |        0.1430 |
| ease     | EASE (lambda=500, half-life 4y)      | 21        |      0.0998 |    0.1022 |        0.1264 |
| ease     | EASE (lambda=500, half-life 3mo)     | 20        |      0.1001 |    0.1017 |        0.1235 |
| ease     | EASE (lambda=1000, half-life 4y)     | 20        |      0.0991 |    0.1015 |        0.1089 |
| ease     | EASE (lambda=250, half-life 3mo)     | 25        |      0.0994 |    0.1011 |        0.1390 |
| ease     | EASE (lambda=1000, half-life 3mo)    | 21        |      0.0995 |    0.1010 |        0.1069 |
| ease     | EASE (lambda=2000, half-life 4y)     | 20        |      0.0980 |    0.1001 |        0.0940 |
| ease     | EASE (lambda=2000, half-life 3mo)    | 20        |      0.0959 |    0.0979 |        0.0910 |
| ease     | EASE (lambda=250)                    | 22        |      0.0879 |    0.0920 |        0.1768 |
| ease     | EASE (lambda=500)                    | 24        |      0.0865 |    0.0917 |        0.1652 |
| ease     | EASE (lambda=1000)                   | 19        |      0.0867 |    0.0916 |        0.1517 |
| ease     | EASE (lambda=2000)                   | 19        |      0.0867 |    0.0909 |        0.1363 |
| itemknn  | Item-kNN (cosine, k=200, shrink=50)  | 10        |      0.0659 |    0.0719 |        0.0921 |
| itemknn  | Item-kNN (cosine, k=500, shrink=100) | 11        |      0.0655 |    0.0715 |        0.0721 |

Chosen:

```json
{
  "ease": {
    "lam": 500,
    "half_life_days": 365
  },
  "itemknn": {
    "neighbors": 200,
    "shrink": 50.0
  },
  "als": {
    "factors": 64,
    "alpha": 20.0,
    "lam": 10.0
  }
}
```
