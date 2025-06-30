from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from chatterbot.trainers import ChatterBotCorpusTrainer
import pandas as pd
import random
import os

# Robust CSV loading with multiple fallbacks
try:
    # Try loading with different encodings and error handling
    books_df = pd.read_csv('books.csv', encoding='latin1', on_bad_lines='skip')
except Exception as e:
    print(f"Error loading CSV: {str(e)}")
    try:
        books_df = pd.read_csv('books.csv', encoding='utf-8', on_bad_lines='skip')
    except:
        try:
            books_df = pd.read_csv('books.csv', encoding='ISO-8859-1', error_bad_lines=False)
        except:
            books_df = pd.DataFrame()
            print("Could not load book dataset. Using empty fallback.")

# Preprocess the data if available
if not books_df.empty:
    # Clean up column names (case-insensitive matching)
    books_df.columns = books_df.columns.str.strip().str.lower()
    
    # Select available columns
    available_cols = []
    for col in ['title', 'authors', 'average_rating', 'language_code', 'ratings_count']:
        if col in books_df.columns:
            available_cols.append(col)
    
    if available_cols:
        books_df = books_df[available_cols].dropna()
        
        # Filter English books if possible
        if 'language_code' in books_df.columns:
            books_df = books_df[books_df['language_code'].str.contains('en', case=False, na=False)]
else:
    print("Book database is empty. Recommendations will be limited.")

# Create chatbot instance
BookBot = ChatBot("BookBot", 
    read_only=False,
    logic_adapters=[
        {
            "import_path": "chatterbot.logic.BestMatch",
            "default_response": "Sorry, I don't understand book requests. Try something like 'Recommend a fantasy book'",
            "maximum_similarity_threshold": 0.85
        }
    ],
    storage_adapter='chatterbot.storage.SQLStorageAdapter',
    database_uri='sqlite:///database.sqlite3'
)

# Basic conversation training
basic_convo = [
    "hi", "Hello! I'm BookBot. I recommend books. What genre do you like?",
    "hello", "Hi there! Tell me your favorite book genre.",
    "what's your name?", "I'm BookBot, your book recommendation assistant!",
    "how old are you?", "I was just born digitally, but I know thousands of books!",
    "what do you do?", "I recommend books. Try asking: 'Recommend a sci-fi book'",
    "recommend me a book", "Sure! What genre? (fiction, fantasy, sci-fi, romance, etc.)",
    "what genres do you have?", "I recommend: fiction, fantasy, sci-fi, mystery, romance, thriller, non-fiction",
    "thank you", "You're welcome! Happy reading!",
    "bye", "Goodbye! Come back for more book recommendations!"
]

# Train the bot
list_trainer = ListTrainer(BookBot)
list_trainer.train(basic_convo)

# Fallback recommendation books in case dataset fails
FALLBACK_BOOKS = [
    {"title": "The Hobbit", "authors": "J.R.R. Tolkien", "genre": "fantasy"},
    {"title": "Dune", "authors": "Frank Herbert", "genre": "sci-fi"},
    {"title": "Pride and Prejudice", "authors": "Jane Austen", "genre": "romance"},
    {"title": "The Da Vinci Code", "authors": "Dan Brown", "genre": "mystery"},
    {"title": "Atomic Habits", "authors": "James Clear", "genre": "non-fiction"}
]

def get_book_recommendation(genre=None, author=None):
    """Get a book recommendation with fallback"""
    result = ""
    
    # Try to use dataset if available
    if not books_df.empty:
        filtered = books_df.copy()
        
        if genre:
            # Simple genre matching in title/author (since dataset doesn't have genre column)
            filtered = filtered[
                filtered['title'].str.contains(genre, case=False) | 
                filtered['authors'].str.contains(genre, case=False)
            ]
        
        if author:
            filtered = filtered[filtered['authors'].str.contains(author, case=False)]
        
        if not filtered.empty:
            book = filtered.sample(1).iloc[0]
            result = f"I recommend '{book['title']}' by {book['authors']}"
            
            # Add rating if available
            if 'average_rating' in book and not pd.isna(book['average_rating']):
                result += f" (⭐ {book['average_rating']}/5)"
            return result
    
    # Fallback to hardcoded books
    if genre:
        genre_books = [b for b in FALLBACK_BOOKS if genre.lower() in b['genre']]
        if genre_books:
            book = random.choice(genre_books)
            return f"I recommend '{book['title']}' by {book['authors']} ({book['genre']})"
    
    book = random.choice(FALLBACK_BOOKS)
    return f"I recommend '{book['title']}' by {book['authors']} ({book['genre']})"

def handle_book_recommendation(query):
    """Handle book recommendation requests"""
    query = query.lower()
    
    # Detect request types
    if 'author' in query or 'by ' in query:
        authors = ['stephen king', 'jk rowling', 'jane austen', 'ernest hemingway']
        return f"Try asking about authors like: {random.choice(authors)}"
    
    # Detect genres
    genres = {
        'fantasy': ['fantasy', 'magic', 'dragon'],
        'sci-fi': ['sci-fi', 'science fiction', 'space', 'future'],
        'romance': ['romance', 'love', 'relationship'],
        'mystery': ['mystery', 'thriller', 'crime', 'detective'],
        'non-fiction': ['non-fiction', 'history', 'biography', 'real']
    }
    
    found_genre = None
    for genre, keywords in genres.items():
        if any(kw in query for kw in keywords):
            found_genre = genre
            break
    
    return get_book_recommendation(genre=found_genre)

# Main conversation loop
exit_conditions = (":q", "quit", "exit", "bye")
print("BookBot📚: Hello! I recommend books. Ask me things like:")
print("BookBot📚: - 'Recommend a fantasy book'")
print("BookBot📚: - 'Suggest a mystery novel'")
print("BookBot📚: Type 'quit' to exit\n")

while True:
    try:
        user_input = input("You: ").strip()
        
        if user_input.lower() in exit_conditions:
            print("BookBot📚: Happy reading! Goodbye!")
            break
        
        # Handle book recommendations
        if any(kw in user_input.lower() for kw in ['recommend', 'suggest', 'book', 'read']):
            response = handle_book_recommendation(user_input)
        else:
            response = BookBot.get_response(user_input)
        
        print(f"BookBot📚: {response}")
        
    except (KeyboardInterrupt, EOFError):
        print("\nBookBot📚: Goodbye!")
        break
    except Exception as e:
        print(f"BookBot📚: Sorry, I encountered an error. Please try asking differently.")
        # print(f"[Debug] Error: {str(e)}")  # Uncomment for debugging