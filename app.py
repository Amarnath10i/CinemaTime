import pickle
import requests
import streamlit as st

@st.cache_data
def load_data():
    movies = pickle.load(open("movies.pkl", "rb"))
    similarity = pickle.load(open("similarity.pkl", "rb"))
    return movies, similarity

movies, similarity = load_data()

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
    index = movies[movies['title'] == movie].index[0]
    distances = similarity[index]
    movie_list = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1]
    )[1:6]
    recommended_movies = []
    recommended_posters = []
    for i in movie_list:
        movie_id = movies.iloc[i[0]].id
        recommended_movies.append(movies.iloc[i[0]].title)
        recommended_posters.append(fetch_poster(movie_id))
    return recommended_movies, recommended_posters

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
    names, posters = recommend(selected_movie)
    cols = st.columns(5)
    for i in range(5):
        with cols[i]:
            st.image(posters[i])
            st.markdown(names[i])
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
