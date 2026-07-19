# CinemaTime Technical Report

This document details the architectural decisions, machine learning algorithms, and performance considerations underlying the CinemaTime recommendation engine.

## 1. Group Consensus Algorithm: Utilitarian vs. Egalitarian Approaches

When recommending content to a group of users with divergent tastes, the system must aggregate individual preferences into a single group decision. This falls under the domain of **Social Choice Theory**.

### The Problem with Pure Averaging (Utilitarian)
A naive approach is to calculate the average similarity score across all users (Utilitarian). However, our synthetic evaluation (`backend/eval_group_rec.py`) proves this leads to high variance in satisfaction. 
For example, if User A's score is 1.0 (Loves it) and User B's score is 0.0 (Hates it), the average is 0.5. The system might recommend a highly polarizing movie, leading to a poor group experience (the "Least Misery" problem).

### The CinemaTime Solution: Egalitarian Hybrid
We implemented a weighted hybrid approach that heavily penalizes "misery":
```python
group_score = (0.8 * min(user_scores)) + (0.2 * avg(user_scores))
```
By weighting the minimum score (Egalitarian/Least Misery) at 80%, the algorithm acts as a soft veto. A movie will only be recommended if *everyone* in the group finds it at least acceptable, enforcing a true compromise. The 20% average weight serves as a tie-breaker among acceptable movies.

## 2. Diversity-Aware Re-ranking (MMR)

Standard k-Nearest Neighbors (k-NN) using FAISS often suffers from the "filter bubble" effect, returning near-duplicate items (e.g., 5 identical superhero sequels). 

To solve this, CinemaTime implements **Maximal Marginal Relevance (MMR)**. MMR selects the next item $d_i$ by maximizing a combined objective function:

$$ MMR \propto \arg\max_{d_i \in D} \left[ (1 - \lambda) \cdot Sim(q, d_i) - \lambda \cdot \max_{d_s \in S} Sim(d_i, d_s) \right] $$

Where:
- $Sim(q, d_i)$ is the relevance of the movie to the query.
- $Sim(d_i, d_s)$ is the similarity to movies *already selected* in the result set $S$.
- $\lambda$ (Diversity penalty) is set to `0.5` in our API.

This ensures the recommendation list is both highly relevant and diverse.

## 3. Scale and Latency Considerations

### FAISS Vector Search
CinemaTime uses `faiss-cpu` with a flat inner-product index (`IndexFlatIP`). 
- **Scale**: At 10,000 items with 384 dimensions (`all-MiniLM-L6-v2`), the index size is approximately `10,000 * 384 * 4 bytes ≈ 15.3 MB`. This fits comfortably in RAM and allows exhaustive search in sub-milliseconds on modern CPUs.
- **Future Scale**: If the dataset grows beyond 1,000,000 items, the index should be migrated from `IndexFlatIP` to `IndexIVFPQ` (Inverted File with Product Quantization) to maintain sub-10ms query latency while reducing memory footprint.

### Lazy-Loading the NLP Model
Natural language semantic search requires encoding the user's text query into a 384-dimensional vector at runtime. 
Loading the `SentenceTransformer` model takes ~2-3 seconds and consumes ~400MB of RAM. To prevent cold-start delays on startup, the model is **lazy-loaded** using a Singleton pattern in `backend/main.py`. It is only instantiated in memory the *first time* a user triggers a `/api/search/vibe` query, keeping baseline API latency extremely low.
