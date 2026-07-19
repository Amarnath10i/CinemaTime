import numpy as np
import pandas as pd

def simulate_group_recommendation():
    print("="*60)
    print(" 🧪 CinemaTime: Group Consensus Algorithm Evaluation")
    print("="*60)
    print("Comparing 'Pure Averaging' (Utilitarian) vs. 'Egalitarian Hybrid' (Least Misery)")
    print("Scenario: 3 users with highly divergent tastes.\n")

    # 1. Generate Synthetic Data
    # 10,000 movies, 384 dimensions (SentenceTransformer size)
    np.random.seed(42)
    num_movies = 10000
    dim = 384
    
    # Generate random movie vectors and normalize them (cosine similarity = dot product)
    movies = np.random.randn(num_movies, dim)
    movies = movies / np.linalg.norm(movies, axis=1, keepdims=True)
    
    # 2. Define Divergent Users
    # User A likes Sci-Fi, User B likes Rom-Com, User C likes Horror
    # We represent them as orthogonal vectors to simulate completely different tastes
    user_a = np.zeros(dim); user_a[0] = 1.0
    user_b = np.zeros(dim); user_b[1] = 1.0
    user_c = np.zeros(dim); user_c[2] = 1.0
    
    users = [user_a, user_b, user_c]
    
    # Let's inject two specific "candidate" movies to illustrate the math:
    # Movie 1: Highly polarizing. User A loves it (0.9), B and C are neutral (0.1)
    movie_polarizing = np.zeros(dim)
    movie_polarizing[0] = 0.9; movie_polarizing[1] = 0.1; movie_polarizing[2] = 0.1
    movie_polarizing = movie_polarizing / np.linalg.norm(movie_polarizing)
    
    # Movie 2: A true compromise. All users think it's pretty good (0.6)
    movie_compromise = np.zeros(dim)
    movie_compromise[0] = 0.6; movie_compromise[1] = 0.6; movie_compromise[2] = 0.6
    movie_compromise = movie_compromise / np.linalg.norm(movie_compromise)
    
    # Replace first two random movies with our injected ones
    movies[0] = movie_polarizing
    movies[1] = movie_compromise
    
    # 3. Compute Scores
    # Calculate similarity scores for all movies against all users
    # scores shape: (10000, 3)
    scores = np.dot(movies, np.array(users).T)
    
    # Pure Averaging (Utilitarian)
    avg_scores = np.mean(scores, axis=1)
    
    # Egalitarian Hybrid (80% Least Misery, 20% Average)
    min_scores = np.min(scores, axis=1)
    hybrid_scores = (min_scores * 0.8) + (avg_scores * 0.2)
    
    # 4. Evaluation Metrics
    print("--- 1. Pure Averaging (Utilitarian) ---")
    best_avg_idx = np.argmax(avg_scores)
    best_avg_user_scores = scores[best_avg_idx]
    
    print(f"Top Movie Index: {best_avg_idx}")
    print(f"User Scores: {best_avg_user_scores}")
    print(f"Average Score: {avg_scores[best_avg_idx]:.4f}")
    print(f"Lowest User Score (Misery): {np.min(best_avg_user_scores):.4f}")
    print(f"Variance in Satisfaction: {np.var(best_avg_user_scores):.4f}\n")
    
    print("--- 2. Egalitarian Hybrid (Current CinemaTime Algo) ---")
    best_hybrid_idx = np.argmax(hybrid_scores)
    best_hybrid_user_scores = scores[best_hybrid_idx]
    
    print(f"Top Movie Index: {best_hybrid_idx}")
    print(f"User Scores: {best_hybrid_user_scores}")
    print(f"Hybrid Score: {hybrid_scores[best_hybrid_idx]:.4f}")
    print(f"Lowest User Score (Misery): {np.min(best_hybrid_user_scores):.4f}")
    print(f"Variance in Satisfaction: {np.var(best_hybrid_user_scores):.4f}\n")
    
    print("--- 🏆 Conclusion ---")
    if np.min(best_hybrid_user_scores) > np.min(best_avg_user_scores):
        print("✅ The Egalitarian Hybrid successfully raised the worst-case satisfaction (less misery).")
    if np.var(best_hybrid_user_scores) < np.var(best_avg_user_scores):
        print("✅ The Egalitarian Hybrid resulted in a fairer, lower-variance outcome.")
        
    print("\nIn divergent groups, Pure Averaging often selects polarizing movies that one user loves")
    print("but others hate. The Hybrid model explicitly prevents this by acting as a 'veto'")
    print("against movies with a low minimum score, forcing a true compromise.")

if __name__ == "__main__":
    simulate_group_recommendation()
