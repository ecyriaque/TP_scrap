import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import psycopg2
import re


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL n'est pas défini. Veuillez le définir dans un fichier .env.")

base_url = "https://books.toscrape.com/"
catalogue_url = "https://books.toscrape.com/catalogue/"

def scrape_all_books(start_url, catalogue_url):
    current_page = start_url
    all_books = []

    while current_page:
        response = requests.get(current_page)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            book_articles = soup.find_all("article", class_="product_pod")
            for book in book_articles:
                relative_link = book.find("div", class_="image_container").a["href"]
                if current_page == start_url:
                    full_link = requests.compat.urljoin(base_url, relative_link)
                else:
                    full_link = requests.compat.urljoin(catalogue_url, relative_link)
                all_books.append(full_link)

            next_page = soup.find("li", class_="next")
            if next_page:
                next_page_url = next_page.a["href"]
                if current_page == start_url:
                    current_page = requests.compat.urljoin(base_url, next_page_url)
                else:
                    current_page = requests.compat.urljoin(catalogue_url, next_page_url)
            else:
                current_page = None
        else:
            print(f"Erreur lors de la requête pour {current_page} : {response.status_code}")
            break

    return all_books

def clean_price(value):
    if value:
        cleaned_value = re.sub(r"[^\d.]", "", value)
        try:
            return float(cleaned_value)
        except ValueError:
            return 0.0
    return 0.0

def scrape_book_details(book_url):
    response = requests.get(book_url)
    if response.status_code != 200:
        print(f"Erreur lors de la requête pour {book_url} : {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    book_details = {}

    book_details["title"] = soup.find("h1").text.strip()

    price = soup.find("p", class_="price_color")
    if price:
        book_details["price"] = price.text.strip()

    availability = soup.find("p", class_="instock availability")
    if availability:
        book_details["availability"] = availability.text.strip()

    rating = soup.find("p", class_="star-rating")
    if rating:
        book_details["rating"] = rating["class"][1]

    description_section = soup.find("div", id="product_description")
    if description_section and description_section.find_next("p"):
        book_details["description"] = description_section.find_next("p").text.strip()

    product_info = soup.find("table", class_="table table-striped")
    if product_info:
        for row in product_info.find_all("tr"):
            key = row.find("th").text.strip()
            value = row.find("td").text.strip()
            book_details[key] = value

    breadcrumb = soup.find("ul", class_="breadcrumb")
    if breadcrumb:
        category_link = breadcrumb.find_all("a")[-1]
        category_href = category_link["href"]
        match = re.search(r"books/[^_]+_(\d+)/", category_href)
        if match:
            book_details["category_id"] = int(match.group(1)) + 1
        else:
            book_details["category_id"] = None

    image = soup.find("div", class_="thumbnail").find("img")
    if image:
        image_src = image["src"]
        book_details["image"] = requests.compat.urljoin("https://books.toscrape.com/", image_src)

    return book_details

def clean_availability(value):
    if value:
        digits = re.findall(r"\d+", value)
        if digits:
            return int(digits[0])
    return 0

def insert_book_into_db(book_details):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO public.book (upc, title, price_excl_tax, tax, availability, description, image, category_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            book_details.get("UPC"),
            book_details.get("title"),
            clean_price(book_details.get("Price (excl. tax)", "0")),
            clean_price(book_details.get("Tax", "0")),
            clean_availability(book_details.get("availability", "0")),
            book_details.get("description"),
            book_details.get("image"),
            book_details.get("category_id")
        ))
        conn.commit()
        print(f"Livre inséré avec succès : {book_details['title']}")
    except Exception as e:
        print(f"Erreur lors de l'insertion du livre : {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def main():
    start_url = base_url + "index.html"
    print("\n--- Scraping de tous les livres en cours ---")
    all_books_links = scrape_all_books(start_url, catalogue_url)
    print(f"\n--- Total de livres trouvés : {len(all_books_links)} ---")
    all_books_details = []
    for book_link in all_books_links:
        print(f"Scraping : {book_link}")
        book_details = scrape_book_details(book_link)
        if book_details:
            insert_book_into_db(book_details)
    for book in all_books_details:
        print("\n--- Détails du livre ---")
        for key, value in book.items():
            print(f"{key}: {value}")

if __name__ == "__main__":
    main()
