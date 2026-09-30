from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
import spacy
import pymongo
import os

# --- DEEP LEARNING IMPORTS ---
from sentence_transformers import SentenceTransformer, util
import torch

# --- 1. GLOBAL SETUP ---

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["digital_library_db"]
books_col = db["books"]

# Path to Tesseract OCR on your Windows machine
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("Loading standard NLP Model...")
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

print("🧠 Loading Deep Learning Transformer (BERT)...")
model = SentenceTransformer('all-MiniLM-L6-v2') 
print("✅ AI Ready.")


# --- 2. SEARCH VIEW (Strict Hybrid Deep Learning) ---
def search_page(request):
    query = request.GET.get('q', '')
    results = []
    
    books = list(books_col.find())
    
    if query and books:
        corpus = []
        filenames = []
        
        for book in books:
            raw_keywords = book.get('keywords', [])
            clean_keywords = [w for w in raw_keywords if w.isalpha() and len(w) > 3]
            combined_text = f"{book['filename']} {' '.join(clean_keywords)}"
            corpus.append(combined_text)
            filenames.append(book['filename'])
        
        corpus.append("dummy book")
        filenames.append("dummy")
        
        # Encode Text
        query_embedding = model.encode(query, convert_to_tensor=True)
        corpus_embeddings = model.encode(corpus, convert_to_tensor=True)
        
        # Calculate Similarity
        cosine_scores = util.cos_sim(query_embedding, corpus_embeddings)[0]
        scores = cosine_scores.cpu().numpy()
        
        top_indices = scores.argsort()[::-1][:5]
        
        for index in top_indices:
            raw_score = float(scores[index])
            filename = filenames[index]
            
            if filename != "dummy":
                book_data = books_col.find_one({"filename": filename})
                
                # 1. Base AI Score (The raw math percentage)
                base_score = int(raw_score * 100)
                display_score = base_score
                
                # 2. Check for Exact Keyword Matches
                raw_keywords = book_data.get('keywords', [])
                clean_keywords_lower = [w.lower() for w in raw_keywords]
                query_words = query.lower().split()
                
                exact_match = False
                for word in query_words:
                    if len(word) > 2 and (word in clean_keywords_lower or word in filename.lower()):
                        exact_match = True
                        display_score += 40  # Big boost for physical matches
                
                # ----------------------------------------------------
                # 3. THE STRICT FILTER (Fixes your out-of-scope issue)
                # If the AI thinks it's a weak match (< 15%) AND the 
                # exact word is NOT in the book, SKIP IT entirely!
                # ----------------------------------------------------
                if base_score < 15 and not exact_match:
                    continue 
                
                # 4. Final Polish (Apply the curve safely)
                if exact_match:
                    display_score = min(display_score + 20, 98) # Cap at 98%
                else:
                    display_score = min(display_score * 2, 85)  # Cap semantic-only guesses at 85%
                
                # Append to results
                results.append({
                    'filename': filename,
                    'score': display_score,
                    'total_pages': book_data.get('total_pages', '?'),
                    'thumbnail': book_data.get('thumbnail'),
                    'category': book_data.get('category', 'Uncategorized'),
                })

    return render(request, 'catalog/search.html', {'query': query, 'results': results})# --- 2. SEARCH VIEW (Strict Hybrid Deep Learning) ---
def search_page(request):
    query = request.GET.get('q', '')
    results = []
    
    books = list(books_col.find())
    
    if query and books:
        corpus = []
        filenames = []
        
        for book in books:
            raw_keywords = book.get('keywords', [])
            clean_keywords = [w for w in raw_keywords if w.isalpha() and len(w) > 3]
            combined_text = f"{book['filename']} {' '.join(clean_keywords)}"
            corpus.append(combined_text)
            filenames.append(book['filename'])
        
        corpus.append("dummy book")
        filenames.append("dummy")
        
        # Encode Text
        query_embedding = model.encode(query, convert_to_tensor=True)
        corpus_embeddings = model.encode(corpus, convert_to_tensor=True)
        
        # Calculate Similarity
        cosine_scores = util.cos_sim(query_embedding, corpus_embeddings)[0]
        scores = cosine_scores.cpu().numpy()
        
        top_indices = scores.argsort()[::-1][:5]
        
        for index in top_indices:
            raw_score = float(scores[index])
            filename = filenames[index]
            
            if filename != "dummy":
                book_data = books_col.find_one({"filename": filename})
                
                # 1. Base AI Score (The raw math percentage)
                base_score = int(raw_score * 100)
                display_score = base_score
                
                # 2. Check for Exact Keyword Matches
                raw_keywords = book_data.get('keywords', [])
                clean_keywords_lower = [w.lower() for w in raw_keywords]
                query_words = query.lower().split()
                
                exact_match = False
                for word in query_words:
                    if len(word) > 2 and (word in clean_keywords_lower or word in filename.lower()):
                        exact_match = True
                        display_score += 40  # Big boost for physical matches
                
                # ----------------------------------------------------
                # 3. THE STRICT FILTER (Fixes your out-of-scope issue)
                # If the AI thinks it's a weak match (< 15%) AND the 
                # exact word is NOT in the book, SKIP IT entirely!
                # ----------------------------------------------------
                if base_score < 15 and not exact_match:
                    continue 
                
                # 4. Final Polish (Apply the curve safely)
                if exact_match:
                    display_score = min(display_score + 20, 98) # Cap at 98%
                else:
                    display_score = min(display_score * 2, 85)  # Cap semantic-only guesses at 85%
                
                # Append to results
                results.append({
                    'filename': filename,
                    'score': display_score,
                    'total_pages': book_data.get('total_pages', '?'),
                    'thumbnail': book_data.get('thumbnail'),
                    'category': book_data.get('category', 'Uncategorized'),
                })
    results = sorted(results, key=lambda x: x['score'], reverse=True)                

    return render(request, 'catalog/search.html', {'query': query, 'results': results})

# --- 3. UPLOAD VIEW (With OCR, Thumbnails & Explicit Classification) ---
@login_required
def upload_book(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        uploaded_file = request.FILES['pdf_file']
        fs = FileSystemStorage()
        
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)
        
        # 1. Generate Thumbnail
        thumbnail_name = None
        try:
            images = convert_from_path(file_path, first_page=1, last_page=1)
            if images:
                image = images[0]
                thumbnail_name = f"{filename}_thumb.jpg"
                thumb_path = os.path.join(fs.location, thumbnail_name)
                image.save(thumb_path, 'JPEG')
        except Exception as e:
            print(f"⚠️ Could not generate thumbnail: {e}")

        # 2. Extract Text (Standard PDF)
        text = ""
        total_pages = 0
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            for page in reader.pages[:15]: 
                extracted = page.extract_text()
                if extracted:
                    text += extracted + " "
        except Exception as e:
            print(f"Standard PDF reading failed: {e}")

        # 3. Extract Text (OCR Fallback)
        if len(text.strip()) < 50:
            print("🔍 No selectable text found. Activating AI OCR Engine...")
            try:
                ocr_images = convert_from_path(file_path, first_page=1, last_page=5)
                for img in ocr_images:
                    text += pytesseract.image_to_string(img) + " "
                print("✅ OCR Extraction Complete.")
            except Exception as e:
                print(f"⚠️ OCR failed: {e}")

        # 4. Generate Keywords
        if len(text.strip()) > 10:
            doc = nlp(text.lower())
            keywords = [
                token.lemma_ for token in doc 
                if token.pos_ in ['NOUN', 'PROPN', 'ADJ'] 
                and not token.is_stop 
                and token.is_alpha
                and len(token.text) > 2
            ]
            keywords = list(set(keywords))
        else:
            keywords = ["scanned", "document", "unreadable"]

       # ---------------------------------------------------------
        # 5. NEW: EXPLICIT DOCUMENT CLASSIFICATION (Improved Context)
        # ---------------------------------------------------------
        # We give the AI better "definitions" of what these subjects actually mean.
        CATEGORIES = {
            "Computer Science": "Computer science, programming, software, algorithms, artificial intelligence, data",
            "Mathematics": "Mathematics, algebra, calculus, geometry, probability, statistics, numbers, equations",
            "Physics": "Physics, mechanics, energy, thermodynamics, quantum, electricity, magnetism",
            "Chemistry": "Chemistry, organic, inorganic, reactions, molecules, atoms, laboratory",
            "Biology": "Biology, anatomy, genetics, cells, life sciences, zoology, medical",
            "History": "History, historical events, ancient civilization, world wars, humanity",
            "Literature": "Literature, fiction, poetry, novels, drama, english, essays",
            "Engineering": "Engineering, civil, mechanical, electrical, electronics, architecture, design",
            "Business & Finance": "Business, finance, economics, management, accounting, marketing, money"
        }
        
        category_names = list(CATEGORIES.keys())
        category_descriptions = list(CATEGORIES.values())
        
        print("🏷️ Classifying Document...")
        try:
            # Tell the AI to map the detailed descriptions, not just the single-word names
            category_embeddings = model.encode(category_descriptions, convert_to_tensor=True)
            
            # Clean up the filename to use as a massive clue (e.g., "Statistical-Methods.pdf" -> "Statistical Methods")
            clean_name = filename.replace("-", " ").replace("_", " ").replace(".pdf", "")
            
            # Build a natural sentence for the AI to read, combining the title and the top 50 keywords
            book_concept = f"This document is titled {clean_name}. It discusses concepts like: {', '.join(keywords[:50])}"
            
            book_embedding = model.encode(book_concept, convert_to_tensor=True)
            
            # Find the category with the highest semantic match
            cat_scores = util.cos_sim(book_embedding, category_embeddings)[0]
            best_cat_idx = cat_scores.argmax().item()
            
            # Add a strict threshold: If the AI is totally guessing (score < 15%), put it in a General bucket
            if cat_scores[best_cat_idx] > 0.15:
                assigned_category = category_names[best_cat_idx]
            else:
                assigned_category = "General / Multidisciplinary"
                
            print(f"✅ Classified as: {assigned_category} (Confidence: {cat_scores[best_cat_idx]:.2f})")
            
        except Exception as e:
            print(f"⚠️ Classification error: {e}")
            assigned_category = "Uncategorized"

        # 6. Save to MongoDB
        book_data = {
            "filename": filename,
            "thumbnail": thumbnail_name, 
            "total_pages": total_pages,
            "keywords": keywords,
            "category": assigned_category, # <--- NEW FIELD SAVED TO DB
            "uploaded_at": "Just now"
        }
        books_col.insert_one(book_data)

        return redirect('search')

    return render(request, 'catalog/upload.html')

# --- 4. DASHBOARD VIEW ---
@login_required
def dashboard(request):
    books = list(books_col.find())
    return render(request, 'catalog/dashboard.html', {'books': books})


# --- 5. DELETE BOOK ---
@login_required
def delete_book(request, filename):
    book = books_col.find_one({"filename": filename})
    if book:
        fs = FileSystemStorage()
        if fs.exists(filename):
            fs.delete(filename)
        if book.get('thumbnail') and fs.exists(book.get('thumbnail')):
            fs.delete(book.get('thumbnail'))
        books_col.delete_one({"filename": filename})
        
    return redirect('dashboard')