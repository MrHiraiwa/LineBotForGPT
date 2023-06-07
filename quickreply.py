def create_quick_reply(quick_reply, uri="", qreply_opt=""):
    if qreply_opt =="map":
        return {
            "type": "action",
            "action": {
                "type": "location",
                "label": '🗺️地図で検索',
            }
        }
    elif qreply_opt == "pay":
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
