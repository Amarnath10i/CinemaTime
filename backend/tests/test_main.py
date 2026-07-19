import pytest
from fastapi.testclient import TestClient
import json
import sys
import os

# Add backend to path so we can import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app, movies, get_encoder

client = TestClient(app)

def test_api_trending():
    response = client.get("/api/trending")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "id" in data[0]
        assert "title" in data[0]
        assert "media_type" in data[0]

def test_api_vibes():
    response = client.get("/api/vibes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_api_search_vibe():
    # If the model is not loaded (or taking too long), it might return an error dict,
    # but the endpoint should at least return 200
    response = client.get("/api/search/vibe?q=space adventure")
    assert response.status_code == 200
    data = response.json()
    if isinstance(data, dict) and "error" in data:
        pytest.skip("Semantic search model not available during test")
    else:
        assert isinstance(data, list)

def test_api_movie_titles():
    response = client.get("/api/movies/titles?q=test")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_api_group_recommend():
    payload = {
        "users": [
            ["tmdb_550"], # Fight Club
            ["tmdb_157336"] # Interstellar
        ],
        "n": 5
    }
    response = client.post("/api/group-recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
