import pymongo
from sentence_transformers import SentenceTransformer, util

# --- 1. SETUP ---
print("Loading Database and AI Model for Evaluation...")
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["digital_library_db"]
books_col = db["books"]
model = SentenceTransformer('all-MiniLM-L6-v2') 

# --- 2. GROUND TRUTH DATASET (Customized for your Library) ---
# We define exactly which files SHOULD be returned for specific queries.
GROUND_TRUTH = {
    # Testing a specific math concept
    "number system": [
        "R S Agarwal Quantitativ Aptitude_compressed (1).pdf"
    ],
    # Testing a broad subject match (Should grab both physics books)
    "physics": [
        "ERRORLESS PHYSICS (2)_q3Cal1a.pdf",
        "DOC-20241202-WA0002.pdf"
    ],
    # Testing a highly specific physics concept
    "alternating current": [
        "DOC-20241202-WA0002.pdf"
    ],
    # Testing a broad math concept (Should grab both stats and aptitude)
    "mathematics": [
        "R S Agarwal Quantitativ Aptitude_compressed (1).pdf",
        "613872906-Statistical-Methods-Vol-2-N-G-Das_K4uq38n.pdf"
    ],
    # Testing a specific statistical concept
    "data analysis": [
        "613872906-Statistical-Methods-Vol-2-N-G-Das_K4uq38n.pdf"
    ]
}

# --- 3. REPLICATE THE SEARCH LOGIC ---
def run_search(query):
    books = list(books_col.find())
    corpus = []
    filenames = []
    
    for book in books:
        raw_keywords = book.get('keywords', [])
        clean_keywords = [w for w in raw_keywords if w.isalpha() and len(w) > 3]
        combined_text = f"{book['filename']} {' '.join(clean_keywords)}"
        corpus.append(combined_text)
        filenames.append(book['filename'])
        
    query_embedding = model.encode(query, convert_to_tensor=True)
    corpus_embeddings = model.encode(corpus, convert_to_tensor=True)
    cosine_scores = util.cos_sim(query_embedding, corpus_embeddings)[0].cpu().numpy()
    
    top_indices = cosine_scores.argsort()[::-1][:5]
    
    retrieved_files = []
    for index in top_indices:
        raw_score = float(cosine_scores[index])
        filename = filenames[index]
        book_data = books_col.find_one({"filename": filename})
        
        base_score = int(raw_score * 100)
        raw_keywords = book_data.get('keywords', [])
        clean_keywords_lower = [w.lower() for w in raw_keywords]
        query_words = query.lower().split()
        
        exact_match = any(len(w) > 2 and (w in clean_keywords_lower or w in filename.lower()) for w in query_words)
        
        # Apply our strict filter (Must be >15% OR an exact keyword match)
        if base_score >= 15 or exact_match:
            retrieved_files.append(filename)
            
    return retrieved_files

# --- 4. CALCULATE METRICS ---
def evaluate_system():
    total_precision = 0
    total_recall = 0
    total_queries = len(GROUND_TRUTH)
    
    print("\n" + "="*60)
    print("🚀 RUNNING INFORMATION RETRIEVAL EVALUATION METRICS")
    print("="*60)

    for query, expected_files in GROUND_TRUTH.items():
        retrieved_files = run_search(query)
        
        # Calculate True Positives, False Positives, False Negatives
        true_positives = len(set(retrieved_files).intersection(set(expected_files)))
        false_positives = len(retrieved_files) - true_positives
        false_negatives = len(expected_files) - true_positives
        
        # Precision: Out of all retrieved, how many were relevant?
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        
        # Recall: Out of all expected relevant files, how many did we find?
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        
        total_precision += precision
        total_recall += recall
        
        print(f"\n🔍 Query: '{query}'")
        print(f"  🎯 Expected Ground Truth: {expected_files}")
        print(f"  🤖 AI Retrieved:          {retrieved_files}")
        print(f"  📈 Score -> Precision: {precision:.2f} | Recall: {recall:.2f}")

    # Mean Average Precision & Recall
    map_score = total_precision / total_queries
    mean_recall = total_recall / total_queries
    
    # F1-Score: Harmonic mean of Precision and Recall
    if map_score + mean_recall > 0:
        f1_score = 2 * (map_score * mean_recall) / (map_score + mean_recall)
    else:
        f1_score = 0

    print("\n" + "="*60)
    print("📊 FINAL SYSTEM PERFORMANCE ")
    print("="*60)
    print(f"Mean Precision (MAP): {map_score:.2f} ({int(map_score*100)}%)")
    print(f"Mean Recall:          {mean_recall:.2f} ({int(mean_recall*100)}%)")
    print(f"Overall F1-Score:     {f1_score:.2f} ({int(f1_score*100)}%)")
    print("="*60 + "\n")

if __name__ == "__main__":
    evaluate_system()