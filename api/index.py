import random
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from firebase_admin import initialize_app, credentials, firestore
import datetime
import json
import base64
from dotenv import load_dotenv
import os
import socketio

#envのロード
load_dotenv()

app = Flask(__name__)

# 全てのオリジンに対して CORS を有効化
CORS(app)

# 環境変数からサービスアカウントキーを復元
encoded_key = os.getenv("FIREBASE_KEY_BASE64")
decoded_key = base64.b64decode(encoded_key).decode("utf-8")

# Firebase Admin SDKの初期化
# cred = credentials.Certificate("./key.json")  # サービスアカウントキーへのパスを指定
cred = credentials.Certificate(json.loads(decoded_key))
initialize_app(cred)

# Firebase Firestoreのデータベースへのアクセス
db = firestore.client()

# rooms collectionへの参照
rooms_ref = db.collection('rooms')

# 部屋ID初期化
def generate_id():
    return random.randint(1, 999999)

# IDの検証、1以上999999以下であることを確認
def validate_id(id_value):
    if not 1 <= id_value <= 999999:
        abort(400, description="Invalid ID. ID must be between 1 and 999999.")
        
        

def room_exists(room_id):
    """指定された room_id のルームが存在するかどうかを確認する。"""
    room = rooms_ref.document(str(room_id)).get()
    return room.exists

# 対戦部屋の一覧を取得する
@app.route('/rooms', methods=['GET'])
def get_rooms():
    try:
        rooms = [doc.id for doc in rooms_ref.stream()]
        print("GET: rooms")
        return jsonify({"rooms": rooms}), 200
    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"message": "500-Internal Server Error"}), 500

# 対戦部屋が存在するかどうかを確認する
@app.route('/rooms/<int:room_id>', methods=['GET'])
def room_exists(room_id):
    validate_id(room_id)
    try:
        room = rooms_ref.document(str(room_id)).get()
        if room.exists:
            return jsonify({"exists": True}), 200
        else:
            return jsonify({"exists": False}), 404
    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

# 対戦部屋を作成する
@app.route('/rooms', methods=['POST'])
def create_room():
    try:
        room_id = generate_id()
        new_room = rooms_ref.document(str(room_id))
        new_room.set({"players": []})
        print(f"部屋生成成功, ID={room_id}")
        return jsonify({"message": "OK", "room_id": room_id}), 200
    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"message": "500-Internal Server Error"}), 500

# 対戦部屋を削除する
@app.route('/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    validate_id(room_id)
    try:
        rooms_ref.document(str(room_id)).delete()
        print(f"部屋削除成功, ID={room_id}")
        return jsonify({"message": "OK"}), 200
    except Exception as e:
        print(f"エラー: {e}")
        return jsonify(
            {"message": "404-Not Found" if "NOT_FOUND" in str(e) else "500-Internal Server Error"}), 404 if "NOT_FOUND" in str(
            e) else 500

# 指定した対戦部屋に属するプレイヤーを取得する
@app.route('/rooms/<int:room_id>/players', methods=['GET'])
def get_players(room_id):
    validate_id(room_id)
    try:
        room = rooms_ref.document(str(room_id)).get()
        if room.exists:
            players = room.to_dict().get('players', [])
            print(f"GET: プレイヤー一覧")
            return jsonify({"players": players}), 200
        else:
            return jsonify({"message": "404-Not Found"}), 404
    except Exception as e:
        print(e)
        return jsonify({"message": "500-Internal Server Error"}), 500

# 指定した対戦部屋にプレイヤーを追加する
@app.route('/rooms/<int:room_id>/players', methods=['POST'])
def add_player(room_id):
    validate_id(room_id)
    try:
        player_id = generate_id()  # player_id をランダムに生成
        player_name = request.args.get('player_name')

        room = rooms_ref.document(str(room_id)).get()
        if room.exists:
            players = room.to_dict().get("players", [])
            # 新しいプレイヤーの情報
            new_player = {
                "player_id": player_id,
                "name": player_name,
                "lat": 0,
                "lag": 0,
                "spec": 0,
                "isDead": False,
                "killedTime": None,
                "killPlayerName": ""
            }
            players.append(new_player)
            rooms_ref.document(str(room_id)).update({"players": players})
            print(f"プレイヤー生成成功, ID={player_id}")
            return jsonify({"message": "OK", "player_id": player_id}), 200  # 生成された player_id を返す
        else:
            return jsonify({"message": "404-Not Found"}), 404
    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"message": "500-Internal Server Error"}), 500

# 指定したプレイヤーの情報を取得する
@app.route('/rooms/<int:room_id>/players/<int:player_id>', methods=['GET'])
def get_player(room_id, player_id):
    validate_id(room_id)
    validate_id(player_id)
    try:
        room = rooms_ref.document(str(room_id)).get()
        if room.exists:
            players = room.to_dict().get('players', [])
            for player in players:
                if player.get("player_id") == player_id:
                    return jsonify(player), 200
            return jsonify({"message": "404-Player Not Found"}), 404  # プレイヤーが見つからない場合の処理を追加
        else:
            return jsonify({"message": "404-Room Not Found"}), 404
    except Exception as e:
        print(e)
        return jsonify({"message": "Internal Server Error"}), 500

# 指定したプレイヤーの情報を更新する
@app.route('/rooms/<int:room_id>/players/<int:player_id>', methods=['PUT'])
def update_player(room_id, player_id):
    validate_id(room_id)
    validate_id(player_id)

    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        spec = request.args.get('spec')

        room = rooms_ref.document(str(room_id)).get()
        if room.exists:
            players = room.to_dict().get("players", [])
            for i, player in enumerate(players):
                if player.get("player_id") == player_id:
                    # name の更新は行わない
                    players[i].update({
                        "lat": lat,
                        "lag": lng,  # lag を lng に修正
                        "spec": spec
                    })
                    rooms_ref.document(str(room_id)).update({"players": players})
                    print(f"プレイヤー情報更新成功, ID={player_id}")
                    return jsonify({"message": "OK"}), 200
            return jsonify({"message": "Player Not Found"}), 404  # プレイヤーが見つからない場合の処理を追加

        else:
            return jsonify({"message": "Room Not Found"}), 404

    except (ValueError, TypeError) as e:  # lat, lng の型エラー処理
        print(f"エラー: {e}")
        return jsonify({"message": "Bad Request: Invalid lat or lng value"}), 400
    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

# 指定したプレイヤーを削除する
@app.route('/rooms/<int:room_id>/players/<int:player_id>', methods=['DELETE'])
def delete_player(room_id, player_id):
    validate_id(room_id)
    validate_id(player_id)
    try:
        room = rooms_ref.document(str(room_id)).get()
        if room.exists:
            players = room.to_dict().get("players", [])
            updated_players = [player for player in players if player.get("player_id") != player_id]
            if len(updated_players) < len(players):  # 削除されたプレイヤーがいる場合のみ更新
                rooms_ref.document(str(room_id)).update({"players": updated_players})
                print(f"プレイヤー削除成功, ID={player_id}")
                # もし部屋にプレイヤーがいなくなった場合、部屋も削除
                if len(updated_players) == 0:
                    rooms_ref.document(str(room_id)).delete()
                    print(f"部屋削除成功, ID={room_id}")
                return jsonify({"message": "OK"}), 200
            else:
                return jsonify({"message": "Player Not Found"}), 404  # プレイヤーが見つからない場合の処理を追加
        else:
            return jsonify({"message": "Room Not Found"}), 404
    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

# プレイヤーをキルする
@app.route('/rooms/<int:room_id>/players/<int:player_id>/kill', methods=['PUT'])
def kill_player(room_id, player_id):
    validate_id(room_id)
    validate_id(player_id)
    try:
        killed_id = int(request.args.get('killed_id'))
        validate_id(killed_id)

        room = rooms_ref.document(str(room_id)).get()
        if room.exists:
            players = room.to_dict().get("players", [])

            for i, player in enumerate(players):
                if player.get("player_id") == player_id:
                    players[i]["isDead"] = True
                    players[i]["killedTime"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime(
                        '%Y/%m/%d %H:%M:%S')
                    killed_player_name = next((p.get("name") for p in players if p.get("player_id") == killed_id), "")
                    players[i]["killPlayerName"] = killed_player_name
                    rooms_ref.document(str(room_id)).update({"players": players})

                    killer_name = next((p.get("name") for p in players if p.get("player_id") == killed_id), None)
                    killed_name = player.get("name")

                    # キルイベントを送信(socektio)、キルログ配信
                    socketio.emit('kill_event', {
                        'room_id': room_id,
                        'killer_id': killed_id,
                        'killer_name': killer_name,
                        'killed_id': player_id,
                        'killed_name': killed_name,
                    }, room=str(room_id), namespace='/') #ルームIDを名前空間に指定

                    # 死亡としてマーク
                    alive_players = [player for player in players if not player["isDead"]]
                    if len(alive_players) <= 1:
                        socketio.emit('game_over', {'room_id': room_id}, room=str(room_id), namespace='/') # ゲームオーバーイベントを送信
                        print(f"キル発生, 部屋ID={room_id}")
                        return jsonify({"message": "GAME_OVER"}), 200

                    print(f"キル, 倒されたプレイヤーID={player_id}, 倒したプレイヤーID={killed_id}")
                    return jsonify({"message": "KILLED"}), 200

            return jsonify({"message": "404-Player Not Found"}), 404  # プレイヤーが見つからない場合の処理を追加
        else:
            return jsonify({"message": "404-Room Not Found"}), 404

    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"message": "Internal Server Error" if "invalid literal for int()" not in str(
            e) else "Bad Request: killed_id must be integer and between 1 and 999999"}), 500 if "invalid literal for int()" not in str(
            e) else 400


if __name__ == '__main__':
  app.run(debug=True) # デバッグモードを有効にしてサーバーを起動