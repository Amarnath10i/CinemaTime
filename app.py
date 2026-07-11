import pickle
import requests
import streamlit as st
import faiss
import numpy as np

@st.cache_resource
def load_data():
    movies = pickle.load(open("movies.pkl", "rb"))
    index = faiss.read_index("movies.index")
    return movies, index

movies, index = load_data()

def fetch_poster(movie_id):
    API_KEY = "10e0997eacd8c14e60ef40b8a46f695b"
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    try:
        data = requests.get(url, timeout=5).json()
        if "poster_path" in data and data["poster_path"]:
            return "https://image.tmdb.org/t/p/w500/" + data["poster_path"]
        else:
            return "https://via.placeholder.com/500x750?text=No+Poster"
    except Exception:
        return "https://via.placeholder.com/500x750?text=Error"

def recommend(movie):
    movie_idx = movies[movies['title'] == movie].index[0]
    
    # Retrieve the pre-computed vector for the selected movie
    query_vector = index.reconstruct(int(movie_idx))
    query_vector = np.array([query_vector])
    
    # Search FAISS index for top 6 matches (top 1 is the movie itself)
    distances, indices = index.search(query_vector, 6)
    
    recommended_movies = []
    
    for i in indices[0][1:]:
        movie_row = movies.iloc[i]
        
        # safely handle missing data
        overview = movie_row.overview if hasattr(movie_row, 'overview') else "No description available."
        cast = movie_row.cast_display if hasattr(movie_row, 'cast_display') else "Unknown"
        genres = movie_row.genres_display if hasattr(movie_row, 'genres_display') else "Unknown"
        rating = movie_row.vote_average if hasattr(movie_row, 'vote_average') else "N/A"
        
        recommended_movies.append({
            "title": movie_row.title,
            "poster": fetch_poster(movie_row.id),
            "overview": overview,
            "cast": cast,
            "genres": genres,
            "rating": rating
        })
        
    return recommended_movies

st.set_page_config(
    page_title="Movie Recommendation System",
    layout="wide"
)

def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

st.markdown(
    "<h1 class='title'>🎬 Movie Recommendation System</h1>",
    unsafe_allow_html=True
)

selected_movie = st.selectbox(
    "Select a movie",
    movies['title'].values
)

if st.button("Recommend"):
    recommendations = recommend(selected_movie)
    cols = st.columns(5)
    for i in range(5):
        with cols[i]:
            rec = recommendations[i]
            st.image(rec["poster"])
            st.markdown(f"<div class='movie-card'><b>{rec['title']}</b><br/><span style='color:#FFD700'>⭐ {rec['rating']}</span></div>", unsafe_allow_html=True)
            with st.expander("Details & Synopsis"):
                st.caption(f"**Genres:** {rec['genres']}")
                st.caption(f"**Cast:** {rec['cast']}")
                st.write(f"{rec['overview']}")
