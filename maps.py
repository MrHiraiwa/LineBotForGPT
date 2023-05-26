import requests
import os
import json

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

def find_place_by_geo_info(latitude, longitude, keyword1):
    places_api_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    parameters = {
        'keyword': keyword1,
        'types': 'food',
        'language': 'ja',
        'location': f'{latitude},{longitude}',
        'radius': 1000,
        'key': GOOGLE_API_KEY
    }

    response = requests.get(places_api_url, params=parameters)
    data = response.json()

    return data
