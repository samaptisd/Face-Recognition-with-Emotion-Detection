import uuid
from bson.objectid import ObjectId
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
import cv2
import face_recognition
import numpy as np
import datetime
import base64
from tensorflow.keras.models import load_model
import webbrowser


facetracker = load_model("facetracker.h5", compile=False)
emotion_model = load_model("emotiondetector.h5", compile=False)
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

app = Flask(__name__)
app.secret_key = "Aludecor"

client = MongoClient("mongodb://localhost:27017")
db = client["face_dict"]
users_collection = db["users"]
credentials_collection = db["auth"]
logs_collection = db["recognition_logs"]

known_faces = []
known_names = []

for user in users_collection.find():
    name = user.get("name")
    image_paths = user.get("image_paths", [])
    if name and image_paths:
        for image_path in image_paths:
            try:
                image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_faces.append(encodings[0])
                    known_names.append(name)
            except Exception as e:
                print(f"Error loading image {image_path}: {e}")

print("Loaded known faces for:", known_names)

def recognize_face(frame):
    rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    face_locations = face_recognition.face_locations(rgb_img)
    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

    recognized = []
    emotion_scores = [0.0] * len(emotion_labels)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        distances = face_recognition.face_distance(known_faces, face_encoding)
        best_match_index = np.argmin(distances)

        if distances[best_match_index] < 0.52:
            candidate_name = known_names[best_match_index]
            face_img_rgb = rgb_img[top:bottom, left:right]

            try:
                resized_rgb = cv2.resize(face_img_rgb, (120, 120))
                normalized_rgb = resized_rgb.astype("float32") / 255.0
                input_tensor = np.expand_dims(normalized_rgb, axis=0)

                pred_class, pred_coords = facetracker.predict(input_tensor)
                confidence = float(pred_class[0][0])

                if confidence > 0.5:
                    face_img_gray = gray_img[top:bottom, left:right]
                    resized_gray = cv2.resize(face_img_gray, (48, 48))
                    normalized_gray = resized_gray.astype("float32") / 255.0
                    emotion_input = np.expand_dims(normalized_gray, axis=(0, -1))

                    emotion_probs = emotion_model.predict(emotion_input)[0]
                    emotion_scores = emotion_probs.tolist()
                    emotion_label = emotion_labels[np.argmax(emotion_probs)]

                    recognized.append(f"{candidate_name} - {emotion_label}")

            except Exception as e:
                print(f"Model prediction error: {e}")

    return list(set(recognized)), emotion_scores

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, user_dict):
        self.id = str(user_dict["_id"])
        self.username = user_dict["username"]
        self.session_token = user_dict.get("session_token")

    @staticmethod
    def get(user_id):
        user = credentials_collection.find_one({"_id": ObjectId(user_id)})
        return User(user) if user else None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.before_request
def check_session_token():
    if current_user.is_authenticated:
        user = credentials_collection.find_one({"_id": ObjectId(current_user.id)})
        if user and user.get("session_token") != session.get("session_token"):
            logout_user()
            flash("Session expired. Logged in elsewhere.", "warning")
            return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = credentials_collection.find_one({"username": username, "password": password})
        if user:
            new_token = str(uuid.uuid4())
            credentials_collection.update_one({"_id": user["_id"]}, {"$set": {"session_token": new_token}})
            session["session_token"] = new_token
            login_user(User(user))
            flash("Logged in successfully!", "success")
            return redirect(url_for("face_recognition_ui"))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def face_recognition_ui():
    return render_template("face.html")

@app.route("/recognize", methods=["POST"])
@login_required
def recognize_endpoint():
    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"error": "No image data provided"}), 400

    header, encoded = data["image"].split(",", 1)
    image_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    recognized_names, emotion_scores = recognize_face(frame)

    if recognized_names:
        for name in recognized_names:
            logs_collection.insert_one({"name": name, "timestamp": datetime.datetime.utcnow()})

    return jsonify({"recognized": recognized_names, "emotions": emotion_scores})

@app.route("/logs")
@login_required
def logs():
    logs_cursor = logs_collection.find().sort("timestamp", -1).limit(10)
    logs_list = [{"name": log["name"], "timestamp": log["timestamp"].isoformat()} for log in logs_cursor]
    return jsonify({"logs": logs_list})

@app.route('/session_status')
@login_required
def session_status():
    user = credentials_collection.find_one({"_id": ObjectId(current_user.id)})
    if user and user.get("session_token") == session.get("session_token"):
        return jsonify({"status": "valid"})
    else:
        return jsonify({"status": "invalid"})

@app.route('/single_tab_error')
@login_required
def single_tab_error():
    return render_template("single_tab_error.html")

@app.route("/chat", methods=["POST"])
def chatbot_voice_assistant():
    data = request.get_json()
    query = data.get("query", "").lower()

    if "play music" in query:
        webbrowser.open("https://www.youtube.com/results?search_query=top+uplifting+songs")
        return jsonify({"reply": "Okay, playing music on YouTube."})

    elif "schedule meeting" in query or "calendar" in query:
        # Here you can integrate Google Calendar API
        return jsonify({"reply": "Okay, meeting scheduled in your calendar."})

    else:
        return jsonify({"reply": "Sorry, I didn't understand. Try saying play music or schedule meeting."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
