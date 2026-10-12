# CinemaTime ML

Offline training and evaluation for CinemaTime's personalized recommender.
MovieLens 32M ratings are joined to the app's catalog through TMDB ids. Models
are trained on the past and judged on what users liked in the following year.
The winning model is exported as NumPy arrays that the API serves without any
ML framework, and a replay of the test users through the API's code checks
that what ships is what was measured.

## Results

Test fold: models see likes before 2022-10-12 and rank all 8,926 catalog
movies for 5,396 users, who are scored on the 87,958 movies they liked in the
following year. 95% bootstrap intervals over users. All tables:
[`reports/`](reports/).

| model | NDCG@20 | Recall@20 | Hit@10 |
|---|---|---|---|
| Content: SBERT profile (CinemaTime before) | 0.0062 (0.0056–0.0070) | 0.0064 | 0.042 |
| Popularity, last 12 months | 0.0851 (0.0814–0.0887) | 0.0956 | 0.346 |
| Item-kNN | 0.0760 (0.0725–0.0797) | 0.0688 | 0.298 |
| Implicit ALS (k = 64) | 0.0805 (0.0770–0.0844) | 0.0792 | 0.325 |
| EASE | 0.0985 (0.0946–0.1026) | 0.0916 | 0.375 |
| EASE, recency-weighted (1-year half-life) | 0.1240 (0.1194–0.1284) | 0.1257 | 0.465 |
| **Two-stage: 4 retrievers → LambdaRank** | **0.1405 (0.1364–0.1452)** | **0.1428** | **0.512** |
| *the same, served by the API's NumPy engine* | *0.1405 (0.1363–0.1451)* | *0.1427* | |

- **The two-stage model beats the best single model** by +0.0166 NDCG@20
  (paired 95% interval +0.0129 to +0.0198, +13%). It reaches 23× the NDCG
  of the content model CinemaTime used before.
- **Serving is exact.** Replaying every test user through the API's engine
  changes NDCG@20 by −0.0000 (−0.0005 to +0.0004). One request takes about
  17 ms at the median (`reports/serving.md`).
- **Cold start.** 8.8% of held-out likes went to movies nobody had rated
  before the cutoff. Ranking only those movies, mapping SBERT vectors into the
  ALS space gives NDCG@20 0.080. Content similarity gives 0.013 and newest
  first gives 0.035 (`reports/coldstart.md`).
- **Visitors with few likes.** Replaying each user's last 3, 5, 10 or 20 likes,
  the two-stage model beats every single retriever from 3 likes on. With a
  single like, last year's popularity is just as good (`reports/serving.md`).
- **What the ranker needs.** Retraining without each feature group shows:
  - popularity and freshness: −15% NDCG;
  - EASE: −11%;
  - content: −3%;
  - ALS: −2%;
  - genre overlap and era gap: no measurable gain (`reports/ablation.md`).
- **Findings that changed the app:**
  - **Recommending unreleased films.** A quarter of the catalog was
    released after the ratings data ends; without a release-date mask, content
    models were scored on recommending films that did not exist yet.
  - **Training-serving skew.** A ranker trained on the dense EASE but served the
    pruned one lost 0.0025 NDCG@20 (−0.0046 to −0.0008), so the ranker is
    now trained on exactly what is served.
  - **Group Watch.** On real users, Group Watch's least-misery rule serves
    members worse than plain "most pleasure" (`reports/groups.md`).


## The problem, as the app has it

A visitor hearts a few movies; the For You page has to rank 8,926 catalog
movies for them. Three things make that harder than a textbook benchmark:

1. **The interaction data is old and the catalog is new.** MovieLens 32M ends
   in October 2023, but a quarter of the catalog was released after that, and
   8.8% of the likes in the test year went to movies with no ratings at all
   before the cutoff. Collaborative filtering alone cannot recommend them.
2. **Visitors are not MovieLens users.** A MovieLens user has rated hundreds of
   films over years; a visitor has liked five, a minute ago. The model has to
   work with short, fresh histories and no trained user vector.
3. **It has to run on a small serverless function.** No PyTorch, no LightGBM,
   no SciPy at request time.

## Evaluation protocol

Defined once in [`cinemaml/config.py`](cinemaml/config.py).

- **Likes.** A rating of 4 stars or more is a like. Everything is implicit
  feedback: which movies a user likes, not how many stars.
- **Temporal folds.** The validation fold trains on likes before 2021-10-12
  and evaluates the next year; the test fold trains on likes before
  2022-10-12 and evaluates until the data ends. Hyperparameters and the
  ranker are chosen on validation only. A random split would let a model
  learn from a user's 2023 likes to "predict" their 2015 ones.
- **Evaluated users.** Users with at least 5 likes before the cutoff and at
  least one new like inside the window. Truth is what they liked inside the
  window, excluding anything they had already liked.
- **Full-catalog ranking.** Every model ranks all catalog movies for every
  user. Metrics on 100 sampled negatives can reverse the order of models
  (Krichene & Rendle, KDD 2020), so they are not used.
- **Only released movies.** A movie released after the window closes cannot
  be recommended in that fold (`Fold.unavailable`). Without this, content
  models were penalized for recommending 2025 films to people in 2022.
- **Uncertainty.** 95% intervals come from a bootstrap over users, and
  comparisons between models use a paired bootstrap over the same users.
- **Metrics.** NDCG@K and Recall@K (K = 10, 20, 50), Hit@10, plus catalog
  coverage, novelty (self-information of recommended items), intra-list
  diversity (1 − mean pairwise SBERT cosine) and recall on cold movies.

## Models

Every model ranks the whole catalog from a user's likes. The non-trivial ones
are implemented from their papers in NumPy/SciPy and tested against their
definitions on small data (`tests/test_models.py`).

| model | idea | file |
|---|---|---|
| Popularity | most-liked movies overall or over the last year | [`baselines.py`](cinemaml/models/baselines.py) |
| Content (CinemaTime before) | cosine between a movie's Sentence-BERT vector and the mean of the user's likes | [`baselines.py`](cinemaml/models/baselines.py) |
| Item-kNN | shrunk cosine over co-likes, top-k neighbours per item | [`itemknn.py`](cinemaml/models/itemknn.py) |
| EASE (Steck 2019) | closed-form linear item-item model, `B = −P / diag(P)` with `P = (XᵀX + λI)⁻¹`, zero diagonal; likes weighted by recency `2^(−age / half-life)` | [`ease.py`](cinemaml/models/ease.py) |
| Implicit ALS (Hu, Koren & Volinsky 2008) | weighted matrix factorization; each half-step solved with warm-started conjugate gradient for all users at once (Takács et al. 2011) | [`als.py`](cinemaml/models/als.py) |
| Hybrid ALS | ridge map from SBERT vectors to ALS item factors, fitted on well-rated movies, gives unrated movies a place in the taste space | [`hybrid.py`](cinemaml/models/hybrid.py) |
| Two-stage | union of EASE, hybrid ALS, popularity and content candidates, re-ranked by LightGBM LambdaRank on 14 features | [`ranker.py`](cinemaml/models/ranker.py), [`features.py`](../backend/recsys/features.py) |

The tests check, among other things, that:
- each EASE column is the ridge regression of that item on all the others;
- CG converges to the exact ALS normal-equation solution;
- the ALS loss never increases;
- folding in a user reproduces the training step;
- the content map recovers a planted linear relationship.

### The ranker's features

Shared by training and the API ([`backend/recsys/features.py`](../backend/recsys/features.py)), so a feature cannot mean one thing offline and another in production:

- **Retriever signals:** each retriever's score and rank. EASE and ALS scores are divided by the user's best score, because raw scores grow with history length, which differs wildly between a MovieLens veteran and a visitor.
- **Popularity:** log likes overall and over the last year, and the last year's share of all likes.
- **Freshness:** whether the movie had any likes at all, and its age.
- **Fit to the user:** genre overlap with the user's likes, and the distance between the movie's year and the mean year of their likes.
- **History:** the user's history length.

One feature was removed on purpose: "share of the user's likes from the last year". It varies across MovieLens users but is 1 for every visitor, which would make it a training/serving mismatch.

## Serving

`uv run cinemaml export` writes `backend/recsys/artifacts/`:
- **`model.npz`:** pruned EASE as CSR arrays, hybrid ALS item factors with the ALS Gram matrix, item popularity, genres and release dates, and the LightGBM trees flattened into arrays.
- **`meta.json`:** hyperparameters, the ranker's feature list and the offline results.

At request time, [`backend/recsys/engine.py`](../backend/recsys/engine.py) does the following:
- **EASE:** sums the liked movies' rows of the pruned matrix.
- **ALS:** solves the visitor's vector in closed form against the item factors (fold-in), with no retraining.
- **Content and popularity:** scored the same way as offline.
- **Ranking:** builds the shared features and scores them with [`trees.py`](../backend/recsys/trees.py), a NumPy LightGBM evaluator tested to match LightGBM exactly, including its missing-value rules.

Explanations are exact rather than post-hoc. An EASE score is a sum of one contribution per liked movie, so *"Because you liked X"* names the largest contribution.

Three checks guard training-serving skew:
1. **`tests/test_serving.py`:** trains a two-stage model on synthetic data, exports it, loads the engine, and requires identical candidates and scores to 1e-5.
2. **The engine refuses artifacts** whose feature list differs from the code's.
3. **The `export` experiment replays every test user** through the engine built from exported arrays and compares the result with the offline model (`reports/serving.md`).

## Reproduce

```bash
cd ml
uv sync
mkdir -p data/raw && curl -o data/raw/ml-32m.zip https://files.grouplens.org/datasets/movielens/ml-32m.zip
unzip data/raw/ml-32m.zip -d data/raw/

uv run cinemaml tune        # validation fold: EASE, item-kNN and ALS grids -> reports/best_params.json
uv run cinemaml compare     # test fold: every model, bootstrap intervals, the two-stage ranker
uv run cinemaml coldstart   # ranking movies with no ratings yet
uv run cinemaml diversity   # MMR lambda sweep
uv run cinemaml groups      # group recommendation strategies on real users
uv run cinemaml ablation    # retrain the ranker without each feature group
uv run cinemaml export      # replay through the API engine, then write backend/recsys/artifacts/
uv run pytest               # 25 tests on synthetic data; no download needed
```

On a 16 GB laptop the whole sequence takes about two hours, most of it ALS
fits (cached under `data/cache/`) and the EASE grid, where each fit inverts an
8,926 × 8,926 matrix.

## Layout

```
cinemaml/
  config.py          paths and the evaluation protocol
  data.py            catalog join, likes, temporal folds, release-date availability
  metrics.py         full-catalog Recall/NDCG/Hit, bootstrap, beyond-accuracy
  evaluate.py        rank every movie for every evaluated user
  models/            popularity, content, item-kNN, EASE, ALS, hybrid ALS, two-stage ranker
  experiments/       one module per report in reports/
  export.py          writes the serving artifacts
tests/               models vs. definitions, metrics, NumPy trees vs. LightGBM, engine vs. offline
reports/             every table quoted here, generated by the experiments
```

## Limitations

- **MovieLens users are not CinemaTime visitors.** The short-history replay is
  the closest offline proxy; there is no online A/B test.
- **Old ratings data.** It ends in October 2023. Retrievers are refitted on
  all of it and the ranker on its last year, but newer films can only be placed
  through their plot embeddings.
- **Movies only.** MovieLens covers movies, so TV and anime likes are ignored
  by For You.
- **Candidate recall caps the ranker.** The four retrievers' candidates
  contain 40% of users' future likes, which is the ceiling for stage 2. Larger
  pools or a sequence model for visitors (SASRec) are the next step.

