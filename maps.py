from flask import Blueprint, request, jsonify
import requests
import json
import os

maps = Blueprint('maps', __name__)

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')


def find_place_by_geo_info(latitude, longitude, keyword):
    places_api_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    parameters = {
        'keyword': keyword,
        'types': 'food',
        'language': 'ja',
        'location': f'{latitude},{longitude}',
        'radius': 1000,
        'key': GOOGLE_API_KEY
    }

    response = requests.get(places_api_url, params=parameters)
    data = response.json()
    return data


def maps_search(latitude, longitude, keyword):
    data = find_place_by_geo_info(latitude, longitude, keyword)
    shop_info_texts = []
    map_urls = []

    for i, result in enumerate(data['results']):
        if i >= 20:
            break
        place_name = result['name']
        types = result['types']
        like = result.get('rating', 'N/A')
        user_ratings_total = result.get('user_ratings_total', 'N/A')
        price_level = result.get('price_level', 'N/A')
        vicinity = result['vicinity']
        map_url = f"https://www.google.com/maps/search/?api=1&query={result['geometry']['location']['lat']},{result['geometry']['location']['lng']}&query_place_id={result['place_id']}"
        shop_info_text = f"場所名: {place_name}\nタイプ: {types}\n評価: {like}\nレビュー数: {user_ratings_total}\n価格レベル: {price_level}\n住所: {vicinity}\n"
        shop_info_texts.append(shop_info_text)
        if i < 3:
            map_urls.append(map_url)

    user_message = f"下記の一覧は場所とキーワード「{keyword}」を条件に場所を検索を行って返ってきた情報です。おすすめの場所を教えて。\n" + '\n'.join(shop_info_texts)
    links = "\n❗参考\n" + '\n'.join(map_urls)

    return {'message': user_message, 'links': links}

