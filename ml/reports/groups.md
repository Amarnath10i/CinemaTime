# Group recommendation strategies on real users (test fold)

600 random groups per size, drawn from the 5,396 test users; one shared top-10 list per group.

|   group size | member scores   | strategy                       |   member recall@10 |   members served |   worst member recall@10 |
|-------------:|:----------------|:-------------------------------|-------------------:|-----------------:|-------------------------:|
|            2 | EASE            | average (Borda)                |             0.0567 |           0.3617 |                   0.0127 |
|            2 | EASE            | least misery (min)             |             0.0498 |           0.3433 |                   0.0108 |
|            2 | EASE            | CinemaTime: 0.8 min + 0.2 mean |             0.0505 |           0.3442 |                   0.0106 |
|            2 | EASE            | most pleasure (max)            |             0.0651 |           0.3975 |                   0.0126 |
|            2 | content (SBERT) | average (Borda)                |             0.0011 |           0.0175 |                   0.0000 |
|            2 | content (SBERT) | least misery (min)             |             0.0012 |           0.0167 |                   0.0000 |
|            2 | content (SBERT) | CinemaTime: 0.8 min + 0.2 mean |             0.0012 |           0.0167 |                   0.0000 |
|            2 | content (SBERT) | most pleasure (max)            |             0.0013 |           0.0200 |                   0.0000 |
|            3 | EASE            | average (Borda)                |             0.0387 |           0.3189 |                   0.0020 |
|            3 | EASE            | least misery (min)             |             0.0335 |           0.2950 |                   0.0019 |
|            3 | EASE            | CinemaTime: 0.8 min + 0.2 mean |             0.0344 |           0.3006 |                   0.0020 |
|            3 | EASE            | most pleasure (max)            |             0.0512 |           0.3489 |                   0.0029 |
|            3 | content (SBERT) | average (Borda)                |             0.0015 |           0.0239 |                   0.0000 |
|            3 | content (SBERT) | least misery (min)             |             0.0020 |           0.0267 |                   0.0000 |
|            3 | content (SBERT) | CinemaTime: 0.8 min + 0.2 mean |             0.0018 |           0.0267 |                   0.0000 |
|            3 | content (SBERT) | most pleasure (max)            |             0.0013 |           0.0233 |                   0.0000 |
|            5 | EASE            | average (Borda)                |             0.0289 |           0.2490 |                   0.0001 |
|            5 | EASE            | least misery (min)             |             0.0241 |           0.2247 |                   0.0000 |
|            5 | EASE            | CinemaTime: 0.8 min + 0.2 mean |             0.0247 |           0.2257 |                   0.0000 |
|            5 | EASE            | most pleasure (max)            |             0.0376 |           0.2907 |                   0.0001 |
|            5 | content (SBERT) | average (Borda)                |             0.0009 |           0.0157 |                   0.0000 |
|            5 | content (SBERT) | least misery (min)             |             0.0009 |           0.0160 |                   0.0000 |
|            5 | content (SBERT) | CinemaTime: 0.8 min + 0.2 mean |             0.0009 |           0.0153 |                   0.0000 |
|            5 | content (SBERT) | most pleasure (max)            |             0.0010 |           0.0163 |                   0.0000 |
