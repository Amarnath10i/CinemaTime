# CinemaTime ML

Offline training and evaluation for CinemaTime's recommender. MovieLens 32M
ratings are joined to the app's catalog through TMDB ids, models are trained
on the past and evaluated on the following year, and the winners are exported
as small NumPy artifacts the API serves without any ML framework.

```bash
cd ml
uv sync
curl -O https://files.grouplens.org/datasets/movielens/ml-32m.zip   # into data/raw/
```
