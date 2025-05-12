import streamlit as st
import requests
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# ------------------ MongoDB Setup ------------------ #
client = MongoClient("mongodb://localhost:27017/")
db = client["movie_dashboard"]
collection = db["search_history"]

# ------------------ OMDb API Setup ------------------ #
OMDB_API_KEY = "f5bd16ba"
OMDB_API_URL = "http://www.omdbapi.com/"

# ------------------ API Query ------------------ #
def show_query(title, year=None, genre=None, page=1):
    try:
        params = {
            "apikey": OMDB_API_KEY,
            "t": title,
            "y": year,
            "genre": genre,
            "page": page
        }
        response = requests.get(OMDB_API_URL, params=params)
        if response.status_code != 200:
            st.error("Could not connect to movie database.")
            return None
        data = response.json()
        if data.get("Response") == "False":
            st.error(f"Movie not found: {title}")
            return None
        return data
    except Exception as e:
        st.error(f"Something went wrong. Error: {str(e)}")
        return None

# ------------------ Save to MongoDB ------------------ #
def save_to_mongo(movie_data):
    doc = {
        "title": movie_data.get("Title"),
        "timestamp": datetime.now(),
        "data": movie_data
    }
    result = collection.insert_one(doc)
    print("Saved to MongoDB with ID:", result.inserted_id)  # Debug print

# ------------------ Sidebar: Recent Searches ------------------ #
def load_recent_searches():
    st.sidebar.subheader("\U0001F550 Recent Searches")
    recent = list(collection.find().sort("timestamp", -1).limit(5))
    for i, item in enumerate(recent):
        if st.sidebar.button(f"{item['title']} ({item['timestamp'].strftime('%H:%M:%S')})", key=f"recent_{i}"):
            st.session_state.selected_movie = item["data"]
            st.rerun()

# ------------------ Display Movie Details ------------------ #
def display_movie_details(movie):
    title = movie.get("Title", "Unknown Title")
    director = movie.get("Director", "Unknown")
    plot = movie.get("Plot", "No plot available")
    cast = movie.get("Actors", "")
    year = movie.get("Year", "Unknown")
    rating = movie.get("imdbRating", "Not rated")
    poster = movie.get("Poster")
    imdb_url = f"https://www.imdb.com/title/{movie.get('imdbID')}"

    if poster and poster != "N/A":
        st.image(poster)
    st.title(title)
    st.subheader(f"Directed by: {director}")

    df = pd.DataFrame({
        "Title": [title],
        "Director": [director],
        "Year": [year],
        "Rating": [rating],
        "Cast": [cast]
    })
    st.dataframe(df)

    if plot == "N/A" or not plot:
        st.subheader("Plot")
        st.write("Plot not available.")
    else:
        st.subheader("Plot")
        st.write(plot)

    if st.button("Watch Movie on IMDb"):
        st.markdown(f"[Click here to watch on IMDb]({imdb_url})")

# ------------------ Display Multiple Results ------------------ #
def display_multiple_results(movies, page, total_pages):
    for movie in movies:
        title = movie.get("Title", "Unknown Title")
        year = movie.get("Year", "Unknown")
        poster = movie.get("Poster", "N/A")
        st.subheader(title)
        st.write(f"Year: {year}")
        if poster != "N/A":
            st.image(poster)
        st.write("---")

    if page > 1:
        if st.button("Previous Page"):
            st.session_state.page -= 1
            st.rerun()
    if page < total_pages:
        if st.button("Next Page"):
            st.session_state.page += 1
            st.rerun()

# ------------------ Main App ------------------ #
def main():
    st.set_page_config(page_title="Movie Analytics", layout="wide")
    st.title("\U0001F3A5 Movie Analytics")

    load_recent_searches()

    if 'selected_movie' not in st.session_state:
        st.session_state.selected_movie = None
    if 'page' not in st.session_state:
        st.session_state.page = 1

    year_filter = st.sidebar.selectbox("Filter by Year", [None] + [str(i) for i in range(1900, 2024)])
    genre_filter = st.sidebar.selectbox("Filter by Genre", [None, "Action", "Comedy", "Drama", "Horror", "Thriller", "Romance"])

    title = st.text_input("Enter the movie title")
    search_button = st.button("Search")

    if search_button and title:
        st.session_state.selected_movie = None
        with st.spinner("Fetching movie data..."):
            movie_data = show_query(title, year=year_filter, genre=genre_filter, page=st.session_state.page)
            if movie_data:
                st.session_state.selected_movie = movie_data
                save_to_mongo(movie_data)

    if st.session_state.selected_movie:
        display_movie_details(st.session_state.selected_movie)
        if st.button("Back to search"):
            st.session_state.selected_movie = None
            st.rerun()

if __name__ == '__main__':
    main()
