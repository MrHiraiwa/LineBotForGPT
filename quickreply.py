def create_quick_reply(quick_reply, uri):
    if '🗺️地図で検索' in quick_reply:
        return {
            "type": "action",
            "action": {
                "type": "location",
                "label": '🗺️地図で検索',
            }
        }
    elif '💸支払い' in quick_reply:
        return {
            "type": "action",
            "action": {
                "type": "uri",
                "label": '💸支払い',
                "uri": uri
            }
        }
    else:
        return {
            "type": "action",
            "action": {
                "type": "message",
                "label": quick_reply,
                "text": quick_reply
            }
        }
