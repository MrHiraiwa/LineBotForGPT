import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_search_results(query, num, start_index=0):
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")

    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": google_api_key,
        "cx": google_cse_id,
        "q": query,
        "num": num,
        "start": start_index
    }

    response = requests.get(base_url, params=params)
    response.raise_for_status()

    return response.json()


def get_contents(links):
    contents = []

    for link in links:
        try:
            response = requests.get(link)
            response.raise_for_status()
            html = response.text
        except requests.RequestException:
            html = "<html></html>"

        soup = BeautifulSoup(html, "html.parser")
        content = soup.select_one("article, .post, .content")

        if content is None or content.text.strip() == "":
            content = soup.select_one("body")

        if content is not None:
            text = ' '.join(content.text.split()).replace("。 ", "。\n").replace("! ", "!\n").replace("? ", "?\n").strip()
            contents.append(text)

    return contents


def summarize_contents(contents, question):
    extract_texts = []

    for content in contents:
        if len(content) > 500:
            trimmed_content = content[:1024]
            m = f"以下の文章はインターネット検索を行って返ってきた情報です。「{question}」に関連する重要な情報を抽出します。\n{trimmed_content}"
            extract_texts.append(m)

    return ''.join(extract_texts)[:2500]


@app.route("/search", methods=["POST"])
def search():
    question = request.json.get("question")
    search_result = get_search_results(question, 3)

    links = [item["link"] for item in search_result.get("items", [])]
    contents = get_contents(links)
    summary = summarize_contents(contents, question)

    if not summary:
        summary = "URLをあなたが見つけたかのようにリアクションして。\n"

    return jsonify({
        "userMessage": summary,
        "links": links
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
