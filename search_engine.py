
# PROTOTYPE SCRIPT: Final search logic is implemented in catalog/views.py
import pymongo
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import spacy

# --- 1. SETUP & CONNECTION ---
print("Loading Language Model...")
nlp = spacy.load("en_core_web_sm", disable=['ner', 'parser'])

print("Connecting to Digital Library...")
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["digital_library_db"]
    books_col = db["books"]
except Exception as e:
    print(f"Error connecting to DB: {e}")
    exit()

# --- 2. LOAD DATA ---
books = list(books_col.find())
if len(books) == 0:
    print("No books found! Run preprocess.py first.")
    exit()

print(f"Loaded {len(books)} book(s).")

# --- 3. SHOW ALL KEYWORDS (The New Feature) ---
all_keywords = set() # Use a 'set' to avoid duplicates

for book in books:
    # Add this book's keywords to our master list
    for k in book['keywords']:
        all_keywords.add(k)

# Sort them so they are easy to read
sorted_keywords = sorted(list(all_keywords))

print("\n" + "="*40)
print(f"TOTAL UNIQUE KEYWORDS FOUND: {len(sorted_keywords)}")
print("="*40)

# Ask user if they want to see the list
show_list = input("Do you want to see the full list of keywords? (y/n): ")

if show_list.lower() == 'y':
    print("\n--- KEYWORD INDEX ---")
    # Print them in rows of 10 to keep it clean
    for i in range(0, len(sorted_keywords), 10):
        print(", ".join(sorted_keywords[i:i+10]))
    print("-" * 40)


# --- 4. PREPARE THE SEARCH ENGINE ---
print("\nBuilding Search Index...")
corpus = []
filenames = []

for book in books:
    keyword_string = " ".join(book['keywords'])
    combined_text = f"{book['filename']} {keyword_string}"
    corpus.append(combined_text)
    filenames.append(book['filename'])

# Add dummy data
corpus.append("dummy book extra data")
filenames.append("Start Adding More Books")

vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(corpus)

print("\nSearch Engine is ready! (Type 'exit' to quit)")

# --- 5. SEARCH LOOP ---
while True:
    raw_query = input("\nSearch for a topic: ")
    if raw_query.lower() == 'exit':
        break
    
    # Clean the query
    doc = nlp(raw_query)
    clean_query = " ".join([token.lemma_.lower() for token in doc])
    
    try:
        query_vec = vectorizer.transform([clean_query])
        similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
        
        best_match_index = np.argmax(similarities)
        best_score = similarities[best_match_index]
        
        if best_score > 0.0: 
            best_book = filenames[best_match_index]
            if "Start Adding More Books" not in best_book:
                print(f"\n[FOUND] Best Match: '{best_book}'")
                print(f"Confidence Score: {best_score:.4f}")
            else:
                print("[no results] Try a keyword you saw in the list above.")
        else:
            print("[no results] No match found.")
            
    except Exception as e:
        print(f"Error: {e}")