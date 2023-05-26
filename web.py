import os
import requests
from bs4 import BeautifulSoup

def get_search_results(query, num, start_index=0):
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")

    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": google_api_key,
        "cx": google_cse_id,
        "q": query,
        "num": num,
        "start": start_index,
        "hl": "ja",  # User interface language
        "cr": "countryJP"  # Search results from a certain country
    }

    response = requests.get(base_url, params=params)
    response.raise_for_status()

    return response.json()

def get_contents(links):
    contents = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
    }
    
    for link in links:
        try:
            response = requests.get(link, headers=headers, timeout=5)  # Use headers
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            html = response.text
        except requests.RequestException:
            html = "<html></html>"
            
        soup = BeautifulSoup(html, "html.parser")

        # Remove all 'a' tags
        for a in soup.findAll('a'):
            a.decompose()

        content = soup.select_one("article, .post, .content")

        if content is None or content.text.strip() == "":
            content = soup.select_one("body")

        if content is not None:
            text = ' '.join(content.text.split()).replace("。 ", "。\n").replace("! ", "!\n").replace("? ", "?\n").strip()
            contents.append(text)

    return contents

def summarize_contents(contents, question):
    extract_texts = []

    for i, content in enumerate(contents):
        if len(content) > 500:
            trimmed_content = content[:1024]
            if i == 0:  # 最初のコンテンツに対してのみ文言を追加
                m = f"以下の文章はインターネット検索を行って返ってきた情報です。「{question}」に関連する重要な情報を抽出します。\n{trimmed_content}"
            else:
                m = trimmed_content
            extract_texts.append(m)
    return ''.join(extract_texts)[:1500]

