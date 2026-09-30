# Ml Based Digital-Library 
**Description**

Ml based Digital Library is an intelligent document management system. It uses Machine Learning and Natural Language Processing (NLP) to store, organize, and smartly search through large collections of PDF documents and books.

**Open Source**

This project is completely open-source. Anyone is free to use, modify, and distribute the code. Contributions, bug reports, and feature requests are always welcome!

**Requirements**

To run this project, you will need the following installed on your system:

Python 3.8 or higher

Web Framework: Django

Machine Learning & NLP: scikit-learn, NLTK, or spaCy

PDF Processing: PyPDF2, pdfplumber, or PyMuPDF

(Check the requirements.txt file for the exact library versions)

**Setup and Running Instructions**

Clone this repository to your local machine:
git clone https://github.com/SayanBanerjee09/Digital-Library.git

Navigate into the project folder:
cd Digital_Library_ML

Install the required dependencies using:
pip install -r requirements.txt

Create a folder named "media" in the root directory. Place your PDF files here (these are ignored by Git due to size limits).

Apply the database migrations:
python manage.py migrate

Start the local server:
python manage.py runserver

Open your web browser and go to:
http://127.0.0.1:8000/
