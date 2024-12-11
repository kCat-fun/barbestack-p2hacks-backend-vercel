import random
from flask import Flask, jsonify, request
from firebase_admin import credentials, firestore, initialize_app

# Firebaseの初期化
cred = credentials.Certificate("./key.json") # サービスアカウントキーへのパスを指定
initialize_app(cred)

db = firestore.client()
rooms_ref = db.collection('rooms') # Firestoreのroomsコレクションへの参照

app = Flask(__name__)

@app.route('/rooms', methods=['GET'])
def get_rooms():
    try:
        all_rooms = []
        for doc in rooms_ref.stream():
            room_data = doc.to_dict()
            if 'id' in room_data and isinstance(room_data['id'], int): #idフィールドが存在し、int型であることを確認
                all_rooms.append(room_data['id'])
            else:
                print(f"Skipping document without valid id: {doc.id}")

        return jsonify({'rooms': all_rooms}), 200
    except Exception as e:
        print(f"部屋取得に失敗: {e}")
        return jsonify({'message': '500:Internal Server Error.'}), 500

@app.route('/rooms', methods=['POST'])
def create_room():
    """
    新しいroomを作成
    """
    try:
        # 新しいidを生成 (例: 乱数を使用)
        new_id = random.randint(100000, 999999) # 必要に応じて範囲を変更

        # Firestoreに新しいドキュメントを追加。idフィールドを含む
        new_room_ref = rooms_ref.add({'id': new_id})

        return jsonify({'id': new_id}), 200

    except Exception as e:
        print(f"部屋作成失敗: {e}")
        return jsonify({'message': '500:内部エラー'}), 500

@app.route('/rooms/<int:id>', methods=['DELETE'])
def delete_room(id):
    """
    指定されたroomを削除
    """
    try:
        # idが存在するドキュメントを検索
        docs = rooms_ref.where('id', '==', id).stream()
        for doc in docs:  # 見つかったドキュメントを削除 (idはuniqueと仮定)
            doc.reference.delete()
            return jsonify({'message': f'部屋 {id} の削除に成功しました。'}), 200

        # idが見つからない場合
        return jsonify({'message': f'部屋 {id} が見つかりませんでした。'}), 404

    except Exception as e:
        print(f"Error deleting room: {e}")
        return jsonify({'message': '500:内部エラー'}), 500


if __name__ == '__main__':
    app.run(debug=True)
    # delete_room(363262)
    # app.run()
