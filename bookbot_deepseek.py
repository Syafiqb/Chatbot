import pandas as pd
import random
import os
import re
import requests
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer

try:
    try:
        from config import DEEPSEEK_API_KEY
    except ImportError:
        DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    if not DEEPSEEK_API_KEY:
        raise ValueError("""
        Kunci API DeepSeek tidak ditemukan. Silakan:
        1. Buat file config.py dengan API key Anda, atau
        2. Atur environment variable DEEPSEEK_API_KEY
        """)
    
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_HEADERS = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    conversation_history = [
        {"role": "system", "content": "Anda adalah BookBot, asisten yang ramah dan membantu yang merekomendasikan buku dan bisa mengobrol tentang apa saja. Jaga respons Anda tetap ringkas dan ramah."},
        {"role": "assistant", "content": "Halo! Saya BookBot. Ada yang bisa saya bantu?"}
    ]
    
except Exception as e:
    print(f"Error saat inisialisasi DeepSeek: {e}")
    DEEPSEEK_API_KEY = None

BookBot = ChatBot(
    "BookBot",
    read_only=True,
    logic_adapters=[
        {
            "import_path": "chatterbot.logic.BestMatch",
            "default_response": "Maaf, saya tidak yakin bagaimana meresponsnya. Biar saya coba pikirkan...",
            "maximum_similarity_threshold": 0.9
        }
    ]
)

basic_convo = [
    "hi", "Halo! Saya BookBot. Saya bisa merekomendasikan buku.",
    "halo", "Hai! Ada yang bisa saya bantu?",
    "siapa namamu?", "Saya BookBot.",
    "apa yang kamu lakukan?", "Saya merekomendasikan buku dan menjawab pertanyaan Anda dengan bantuan DeepSeek AI.",
    "terima kasih", "Sama-sama! Senang bisa membantu!",
    "bye", "Sampai jumpa! Selamat membaca!",
    "apa kabar?", "Saya baik! Terima kasih sudah bertanya.",
    "kamu bisa apa?", "Saya bisa merekomendasikan buku dan menjawab pertanyaan seputar buku.",
    "buku apa yang bagus?", "Ada banyak! Misalnya 'Sapiens' untuk non-fiksi, atau 'Harry Potter' untuk fantasi.",
]


list_trainer = ListTrainer(BookBot)
list_trainer.train(basic_convo)
print("Pelatihan dasar selesai.")

try:
    books_df = pd.read_csv('books.csv', encoding='latin1', on_bad_lines='skip')
except FileNotFoundError:
    print("Peringatan: File 'books.csv' tidak ditemukan.")
    books_df = pd.DataFrame()

if not books_df.empty:
    books_df.columns = books_df.columns.str.strip().str.lower()
    required_cols = ['title', 'authors', 'average_rating', 'language_code']
    
    if all(col in books_df.columns for col in required_cols):
        books_df = books_df[required_cols].copy()
        books_df.dropna(inplace=True)
        books_df['average_rating'] = pd.to_numeric(books_df['average_rating'], errors='coerce')
        books_df.dropna(subset=['average_rating'], inplace=True)
        books_df = books_df[books_df['language_code'].str.contains('en', case=False, na=False)]
    else:
        print("Peringatan: Kolom yang dibutuhkan tidak lengkap.")
        books_df = pd.DataFrame()

def get_deepseek_response(user_input):
    if not DEEPSEEK_API_KEY:
        return "Maaf, koneksi ke DeepSeek API tidak tersedia."
    
    try:
        conversation_history.append({"role": "user", "content": user_input})
        
        payload = {
            "model": "deepseek-chat",
            "messages": conversation_history,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=DEEPSEEK_HEADERS)
        response.raise_for_status()
        
        response_data = response.json()
        reply = response_data["choices"][0]["message"]["content"]
        conversation_history.append({"role": "assistant", "content": reply})
        
        return reply
    except Exception as e:
        print(f"Error API: {e}")
        return "Maaf, terjadi kesalahan saat memproses permintaan Anda."

def get_book_recommendation(genre=None, author=None, min_rating=None):
    if books_df.empty:
        return "Maaf, database buku kosong."

    filtered = books_df.copy()
    

    # Filter berdasarkan author (jika ada)
    if author:
        filtered = filtered[filtered['authors'].str.contains(author, case=False, na=False)]
    
    # Filter berdasarkan rating (jika ada)
    if min_rating:
        filtered = filtered[filtered['average_rating'] >= float(min_rating)]
    
    # Jika masih ada hasil, kembalikan rekomendasi acak
    if not filtered.empty:
        # Ambil 3 buku acak dengan rating tertinggi
        recommended = filtered.nlargest(10, 'average_rating').sample(3)
        books_list = []
        for _, row in recommended.iterrows():
            books_list.append(
                f"- {row['title']} oleh {row['authors']} (Rating: {row['average_rating']}/5)"
            )
        return "Berikut beberapa rekomendasi untuk Anda:\n" + "\n".join(books_list)
    
    return "Maaf, tidak ada buku yang cocok dengan kriteria Anda."

def handle_recommendation(query):
    query = query.lower()
    
    rating = re.search(r'(?:rating|minimal)\s*([0-9.]+)', query)
    author = re.search(r'(?:oleh|karya)\s+([a-z .]+)', query)
    genres = ['fantasy', 'sci-fi', 'romance', 'mystery', 'non-fiction']
    genre = next((g for g in genres if g in query), None)
    
    return get_book_recommendation(
        genre=genre,
        author=author.group(1) if author else None,
        min_rating=float(rating.group(1)) if rating else None
    )

print("\nBookBot📚: Halo! Saya BookBot. Tanya apa saja!")
print("Contoh: 'Rekomendasikan buku fantasi rating 4.5' atau 'Jelaskan teori relativitas'")
print("Ketik 'quit' untuk keluar\n")

while True:
    try:
        user_input = input("Anda: ").strip()
        
        if user_input.lower() in ('quit', 'exit', 'bye'):
            print("BookBot📚: Sampai jumpa!")
            break
            
        if any(kw in user_input.lower() for kw in ['rekomendasi', 'buku', 'sarankan']):
            response = handle_recommendation(user_input)
        else:
            bot_response = BookBot.get_response(user_input)
            response = str(bot_response) if bot_response.confidence > 0.8 else get_deepseek_response(user_input)
        
        print(f"BookBot📚: {response}")
        
    except (KeyboardInterrupt, EOFError):
        print("\nBookBot📚: Sampai jumpa!")
        break
    except Exception as e:
        print(f"BookBot📚: Maaf, error: {str(e)}")