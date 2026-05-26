import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import logging
import sys

# Configure logging
tlogging = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def main():
    try:
        # 1. Load CSV
        logger.debug("Loading CSV file: books.csv")
        df = pd.read_csv(r"dataset\Kaggle_7k_books\books.csv")
        logger.info(f"Loaded {len(df)} rows from CSV")

        # 2. Drop rows without description
        before_drop = len(df)
        df = df.dropna(subset=["description"])
        after_drop = len(df)
        logger.info(f"Dropped {before_drop - after_drop} rows without description; {after_drop} remain")

        # 3. Build text corpus for embeddings
        logger.debug("Building text corpus from title and description")
        texts = (df["title"].fillna("") + ". " + df["description"]).tolist()
        logger.info(f"Prepared {len(texts)} text entries for embedding")

        # 4. Load embedding model
        logger.debug("Loading embedding model: all-MiniLM-L6-v2")
        model = SentenceTransformer("all-MiniLM-L6-v2")

        # 5. Compute embeddings
        logger.info("Starting embedding computation...")
        embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        logger.info(f"Computed embeddings with shape {embeddings.shape}")

        # 6. Normalize embeddings for cosine similarity
        logger.debug("Normalizing embeddings")
        norms = np.linalg.norm(embeddings, axis=1)
        if np.any(norms == 0):
            logger.warning("Found zero-vector embedding(s), adding epsilon to avoid division by zero")
            norms[norms == 0] = 1e-6
        embeddings = embeddings / norms[:, np.newaxis]
        logger.info("Normalization complete")

        # 7. Build Faiss index
        dim = embeddings.shape[1]
        logger.debug(f"Creating Faiss index with dimension: {dim}")
        index = faiss.IndexFlatIP(dim)
        logger.debug("Adding embeddings to Faiss index")
        index.add(embeddings.astype('float32'))
        logger.info(f"Faiss index has {index.ntotal} vectors")

        # 8. Save index and metadata
        logger.debug("Saving Faiss index to book_index.faiss")
        faiss.write_index(index, "book_index.faiss")
        logger.debug("Saving metadata to books_metadata.pkl")
        with open("books_metadata.pkl", "wb") as f:
            pickle.dump(df.to_dict(orient="records"), f)
        logger.info("Data preparation complete: index and metadata saved")

    except Exception as e:
        logger.exception(f"An error occurred during data preparation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
