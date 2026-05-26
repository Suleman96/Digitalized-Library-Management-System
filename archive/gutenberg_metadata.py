from gutenberg.acquire import load_etext
from gutenberg.cleanup import strip_headers

book_id = 1342  # Example: Pride and Prejudice
text = strip_headers(load_etext(book_id)).strip()
print(text[:500])  # Print first 500 chars
