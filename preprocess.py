import pytesseract
from pdf2image import convert_from_path
import spacy
import nltk
import os
from pymongo import MongoClient
import datetime

# --- 1. CONFIGURATION ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Your Poppler path
POPPLER_PATH = r"C:\Program Files\poppler-25.12.0\Library\bin"

# --- 2. DATABASE CONNECTION ---
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["digital_library_db"]
    books_collection = db["books"]
    print("Connected to MongoDB.")
except Exception as e:
    print(f"Database Error: {e}")
    exit()

# --- 3. SETUP NLP (STRICTER MODE) ---
print("Loading language models...")
nltk.download('stopwords', quiet=True)
# Note: We keep 'tagger' enabled now so we can check for Nouns/Verbs
nlp = spacy.load("en_core_web_sm", disable=['ner', 'parser'])
nlp.max_length = 3000000 

# Define "Meaningful" Parts of Speech
# NOUN = Object (e.g., "Battery"), PROPN = Name (e.g., "Tesla"), ADJ = Description (e.g., "Electric")
ALLOWED_POS = {'NOUN', 'PROPN', 'ADJ', 'VERB'}

def process_and_save(pdf_path):
    filename = os.path.basename(pdf_path)
    print(f"\n--- Processing: {filename} ---")
    
    # --- AUTO-CLEANUP: Delete old version if it exists ---
    existing_book = books_collection.find_one({"filename": filename})
    if existing_book:
        print(f"Found older version of '{filename}'. Deleting it to make room for cleaner data...")
        books_collection.delete_one({"filename": filename})

    print("Step 1: Converting PDF to images...")
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    except Exception as e:
        print(f"Poppler Error: {e}")
        return

    print(f"Step 2: extracting meaningful keywords from {len(images)} pages...")
    
    full_text = ""
    all_keywords = []

    for i, img in enumerate(images):
        try:
            page_text = pytesseract.image_to_string(img)
            full_text += page_text + " "
        except:
            continue
        
        # --- IMPROVED FILTERING ---
        if len(page_text) > 10:
            doc = nlp(page_text)
            
            for token in doc:
                # 1. Must be a real word (letters only, no numbers/symbols)
                if not token.is_alpha: 
                    continue
                # 2. Must be longer than 2 characters (removes "tl", "fi")
                if len(token.lemma_) < 3: 
                    continue
                # 3. Must be a Noun, Verb, or Adjective (removes "however", "therefore")
                if token.pos_ not in ALLOWED_POS:
                    continue
                # 4. Must not be a stopword
                if token.is_stop:
                    continue
                    
                # If it passes all checks, keep it!
                all_keywords.append(token.lemma_.lower())
        
        if (i+1) % 10 == 0:
            print(f"  -> Processed page {i+1}/{len(images)}")

    # Remove duplicates and sort
    unique_keywords = sorted(list(set(all_keywords)))

    print(f"Step 3: Saving {len(unique_keywords)} clean keywords...")
    
    book_data = {
        "filename": filename,
        "upload_date": datetime.datetime.now(),
        "total_pages": len(images),
        "keywords": unique_keywords,  # Save ALL valid keywords
        "full_text_preview": full_text[:1000] 
    }
    
    books_collection.insert_one(book_data)
    print("SUCCESS! Cleaned book saved to MongoDB.")

# --- RUN ---
if __name__ == "__main__":
    pdf_filename = "DOC-20241202-WA0002.pdf" 
    if os.path.exists(pdf_filename):
        process_and_save(pdf_filename)
    else:
        print(f"File '{pdf_filename}' not found.")