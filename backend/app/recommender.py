"""
Content-based movie recommender.

Approach: treat each movie's combined genres + overview keywords as a
"document", vectorize all documents with TF-IDF, and recommend movies whose
vectors are most similar (cosine similarity) to either:
  - a user-selected set of movies they already like, or
  - a user-selected set of genres, or
  - both.

This is intentionally simple — no training, no model file, just vector math
over a static dataset. It's swappable later for a larger dataset or a
different vectorization scheme without changing the API surface.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from sqlalchemy.orm import Session

from app.models import Movie


class RecommenderEngine:
    def __init__(self):
        self.vectorizer: TfidfVectorizer | None = None
        self.tfidf_matrix = None
        self.movie_ids: list[int] = []
        self.movie_index: dict[int, int] = {}  # movie_id -> row index

    def build(self, db: Session):
        """Build the TF-IDF matrix from all movies currently in the DB.
        Call this once at startup, and again if movies are added/changed.
        """
        movies = db.query(Movie).order_by(Movie.id).all()
        documents = [
            f"{(m.genres or '')} {(m.genres or '')} {(m.overview or '')}"
            for m in movies
        ]
        # genres weighted 2x by repetition — genre overlap matters more
        # than incidental keyword overlap for this use case.

        self.movie_ids = [m.id for m in movies]
        self.movie_index = {m.id: i for i, m in enumerate(movies)}

        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)

    def is_ready(self) -> bool:
        return self.tfidf_matrix is not None and len(self.movie_ids) > 0

    def recommend(
        self,
        seed_movie_ids: list[int],
        seed_genres: list[str],
        top_n: int = 10,
    ) -> list[tuple[int, float]]:
        """Return list of (movie_id, score) sorted by descending similarity,
        excluding the seed movies themselves.
        """
        if not self.is_ready():
            return []

        if not seed_movie_ids and not seed_genres:
            return []

        # Build a single dense query vector by averaging together:
        #  - the TF-IDF vector of the genre text (if genres were given)
        #  - the TF-IDF vectors of each seed movie (if movies were given)
        dense_vectors: list[np.ndarray] = []

        if seed_genres:
            # repeat genres so they carry similar weight to a seed movie's profile
            genre_query = (" ".join(seed_genres) + " ") * 2
            genre_vec = self.vectorizer.transform([genre_query])
            dense_vectors.append(genre_vec.toarray()[0])

        valid_seed_rows = [
            self.movie_index[mid] for mid in seed_movie_ids if mid in self.movie_index
        ]
        if valid_seed_rows:
            seed_vecs = self.tfidf_matrix[valid_seed_rows].toarray()
            dense_vectors.append(seed_vecs.mean(axis=0))

        if not dense_vectors:
            return []

        query_vector = np.mean(dense_vectors, axis=0).reshape(1, -1)

        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

        ranked = sorted(
            zip(self.movie_ids, similarities), key=lambda x: x[1], reverse=True
        )

        exclude = set(seed_movie_ids)
        results = [(mid, float(score)) for mid, score in ranked if mid not in exclude]

        return results[:top_n]


# Singleton instance shared across the app
recommender = RecommenderEngine()
