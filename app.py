from flask import Flask, request, jsonify, render_template
import sqlite3
import requests
import json
from datetime import datetime

app = Flask(__name__)
DATABASE = 'weather.db'
API_KEY = '10685a1d3252bfd0952905f2a0874b53'

# --- Database Utilities ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS weather_requests (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            location TEXT NOT NULL,
                            start_date TEXT NOT NULL,
                            end_date TEXT NOT NULL,
                            weather_data TEXT
                        );''')
        conn.commit()

# --- Weather API Call ---
def get_weather_data(location):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={API_KEY}&units=metric"
    print("API URL:", url)  # Debug line

    response = requests.get(url)
    print("API Response Status:", response.status_code)
    print("API Response Text:", response.text)  # Debug line

    return response.json()

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def create_request():
    data = request.json
    location = data.get('location')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    try:
        # Validate date range
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end:
            return jsonify({'error': 'Start date must be before end date.'}), 400

        # Validate location using API
        weather = get_weather_data(location)
        if weather.get('cod') != 200:
            return jsonify({'error': 'Invalid location provided.'}), 400

        # Store in DB
        with get_db_connection() as conn:
            conn.execute("INSERT INTO weather_requests (location, start_date, end_date, weather_data) VALUES (?, ?, ?, ?)",
                         (location, start_date, end_date, json.dumps(weather)))
            conn.commit()

        return jsonify({'message': 'Weather request stored successfully.'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/read', methods=['GET'])
def read_requests():
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM weather_requests").fetchall()
    return jsonify([dict(row) for row in rows])

@app.route('/update/<int:request_id>', methods=['PUT'])
def update_request(request_id):
    data = request.json
    new_location = data.get('location')

    # Validate location
    weather = get_weather_data(new_location)
    if weather.get('cod') != 200:
        return jsonify({'error': 'Invalid location.'}), 400

    with get_db_connection() as conn:
        conn.execute("UPDATE weather_requests SET location = ?, weather_data = ? WHERE id = ?",
                     (new_location, json.dumps(weather), request_id))
        conn.commit()

    return jsonify({'message': 'Record updated successfully.'})

@app.route('/delete/<int:request_id>', methods=['DELETE'])
def delete_request(request_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM weather_requests WHERE id = ?", (request_id,))
        conn.commit()
    return jsonify({'message': 'Record deleted successfully.'})

@app.route('/export/json', methods=['GET'])
def export_json():
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM weather_requests").fetchall()
    data = [dict(row) for row in rows]

    with open('exported_data.json', 'w') as f:
        json.dump(data, f, indent=4)

    return jsonify({'message': 'Data exported to exported_data.json'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)