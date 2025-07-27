# Digitalized Library Management System

A modern, AI-powered library management system that enables efficient book search and recommendations using state-of-the-art natural language processing and vector search technologies.

## 🚀 Features

- **Semantic Book Search**: Find books using natural language queries
- **AI-Powered Recommendations**: Get personalized book recommendations
- **Efficient Indexing**: Fast search using FAISS (Facebook AI Similarity Search)
- **Modern Web Interface**: Built with Gradio for an interactive experience
- **Scalable Architecture**: Designed to handle large book collections

## 🛠️ Technologies Used

### FAISS (Facebook AI Similarity Search)
FAISS is a library developed by Facebook AI Research for efficient similarity search and clustering of dense vectors. In this project, FAISS is used to:
- Create an efficient index of book embeddings
- Enable fast similarity search across thousands of books
- Reduce search time complexity from O(n) to O(log n)

### Sentence Transformers
The system uses the `all-MiniLM-L6-v2` model from Sentence Transformers to:
- Convert book descriptions and titles into dense vector representations
- Enable semantic understanding of search queries
- Support natural language processing for better search results

### Gradio
Gradio provides the web interface for the application, offering:
- Easy-to-use UI components for book search and display
- Real-time interaction with the AI models
- Responsive design that works on different devices

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Digitalized-Library-Management-System.git
   cd Digitalized-Library-Management-System
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

1. Start the application:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:7860`

3. Use the search bar to find books using natural language queries

## 🧠 How It Works

### 1. Data Processing
Text data from book titles and descriptions undergoes several preprocessing steps:
- **Text Normalization**: Convert to lowercase, remove special characters
- **Tokenization**: Split text into meaningful units (words, subwords)
- **Stopword Removal**: Filter out common words (the, is, at, etc.)
- **Lemmatization**: Reduce words to their base/dictionary form

### 2. Embedding Generation
#### Technical Implementation:
- **Model Architecture**: Utilizes `all-MiniLM-L6-v2` from Sentence Transformers
- **Vector Dimensions**: 384-dimensional dense vector space
- **Embedding Process**:
  1. Input text is tokenized using WordPiece tokenization
  2. Tokens are passed through 6 transformer layers
  3. Mean pooling generates a fixed-size vector representation
  4. Layer normalization and dense projection to final dimension
- **Key Characteristics**:
  - Captures semantic relationships between words and phrases
  - Handles out-of-vocabulary words through subword tokenization
  - Optimized for semantic similarity tasks
  - Inference runs efficiently on both CPU and GPU

### 3. Vector Indexing with FAISS
#### Technical Implementation:
- **Index Type**: Hierarchical Navigable Small World (HNSW) graph
- **Key Components**:
  - **Inverted File System (IVF)**: Partitions the vector space into clusters
  - **Product Quantization (PQ)**: Compresses vectors to reduce memory usage
  - **HNSW Graph**: Enables efficient approximate nearest neighbor search
- **Index Building Process**:
  1. Vectors are normalized to unit length (L2 normalization)
  2. Training data is used to learn the optimal clustering
  3. Vectors are assigned to their nearest clusters
  4. HNSW graph is constructed for efficient traversal
- **Search Process**:
  1. Query vector is embedded using the same model
  2. Approximate nearest neighbor search is performed
  3. Results are ranked by cosine similarity
  4. Top-k results are returned with their similarity scores

### 4. Search & Recommendation System
- **Query Processing**:
  - Natural language query is converted to embedding
  - Optional query expansion using related terms
- **Retrieval Pipeline**:
  1. First-stage retrieval using FAISS approximate search
  2. Optional re-ranking of top candidates
  3. Score normalization and fusion
- **Performance Characteristics**:
  - Sub-linear search time complexity: O(log n)
  - Memory-efficient storage of vector representations
  - Scalable to millions of book entries


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Hugging Face](https://huggingface.co/) for the Sentence Transformers library
- [Facebook Research](https://research.facebook.com/) for FAISS
- [Gradio](https://gradio.app/) for the web interface