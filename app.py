from flask import Flask, request, render_template, jsonify, redirect, url_for, Response
import math
import sqlite3
from werkzeug.utils import secure_filename
import hashlib
import uuid
import requests
import os
import time
from datetime import datetime


app = Flask(__name__)

########################################################################################################

# Function to generate a unique API key
def generate_api_key():
    return str(uuid.uuid4())

# Function to get state and country from latitude and longitude using reverse geocoding API
def get_location_data(latitude, longitude):
    # Example API (replace with your preferred API)
    url = f'https://api.geoapify.com/v1/geocode/reverse?lat={latitude}&lon={longitude}&format=json&apiKey=146c75d7aeb743f89cf5c5267d349f0f'
    response = requests.get(url)
    data = response.json()

    state = data['results'][0]['state']
    county = data['results'][0]['county']
    return state, county

# Function to get ip address
def get_my_ip():
    return request.remote_addr

# Function to get weather data based on latitude and longitude
def get_weather_data(latitude, longitude):
    # Example API (replace with your preferred weather API)
    url = f'https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,rain,wind_speed_10m'
    response = requests.get(url)
    data = response.json()
    return data 

# Function to categorize description
def categorize_description(description):
    # Example logic for categorization
    if 'dangerous' in description.lower():
        return 'dangerous'
    elif 'offensive' in description.lower():
        return 'offensive'
    else:
        return 'normal'

# Register endpoint
@app.route('/', methods=['GET', 'POST'])
def root():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            return render_template("myform1.html", title="My Form1", error="Username and password cannot be empty.")
        
        password = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect('mydb.db')
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=?", (username,))
            user = c.fetchone()
            if user:
                if user[2] == password:
                    return redirect(url_for('home', username=username))
                else:
                    return render_template("myform1.html", title="My Form1", error="Incorrect password. Please try again")
            else:
                return render_template("myform1.html", title="My Form1", error="User donot exist. Please register.")
        

        finally:
            api_key = generate_api_key()
            c.execute("INSERT INTO users (username, password, api_key) VALUES (?, ?, ?)",
                    (username, password, api_key))
            conn.commit()
            conn.close()  
    return render_template("myform1.html", title="My Form1")

# Home endpoint
@app.route('/home/<username>', methods=['GET'])
def home(username):
    conn = sqlite3.connect('mydb.db')
    c = conn.cursor()
    c.execute("SELECT api_key FROM users WHERE username=?", (username,))
    api_key = c.fetchone()[0]
    conn.close()
    return render_template("myform2.html", username=username, api_key=api_key)

# Report endpoint
@app.route("/report", methods=["POST"])
def report():
    entry_date = datetime.now()
    api_key = request.form['api_key']
    latitude = request.form["latitude"]
    longitude = request.form["longitude"]
    description = request.form["description"]
    filename = request.files.get("file1", None)
    os.makedirs("uploads", exist_ok=True)

    if filename:
        path = f"uploads/{time.time()}{secure_filename(filename.filename)}"
        filename.save(path)
    else:
        print("nofile")   
        return {"success":False} 
     # IP address
    ipaddress = get_my_ip()
    # Get state and country from latitude and longitude
    state, county = get_location_data(latitude, longitude)

    # Get current weather data
    data = get_weather_data(latitude, longitude)
    temperature = data['current']['temperature_2m']
    humidity = data['current']['relative_humidity_2m']
    rainfall = data['current']['rain']
    wind_speed = data['current']['wind_speed_10m']

    # Get username from API key
    conn = sqlite3.connect('mydb.db')
    c = conn.cursor()
    c.execute("SELECT username, user_id FROM users WHERE api_key=?", (api_key,))
    user_data = c.fetchone()
    conn.close()

    if user_data:
        username, user_id = user_data
    else:
        return jsonify({'error': 'Invalid API key'}), 401

    # Categorize description
    category = categorize_description(description)

    # Insert report into the database
    conn = sqlite3.connect('mydb.db')
    c = conn.cursor()
    c.execute("INSERT INTO reports (user_id, username, entry_date, latitude, longitude, ipaddress, description, path, state, county, temperature, humidity, wind_speed, rainfall, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, username, entry_date, latitude, longitude, ipaddress, description, path, state, county, temperature, humidity, wind_speed, rainfall, category))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Report submitted successfully'}), 201

# Data endpoint
@app.route('/data', methods=['GET'])
def get_data():
    output_format = request.args.get('output', 'html')
    start_date = request.args.get('start_date', '2024-05-02 17:30:50.910834')
    end_date = request.args.get('end_date', '2024-05-04 17:31:50.910834')
    lat = request.args.get('lat', 30)
    lng = request.args.get('lng', 90)
    dist = request.args.get('dist', 10000000)
    max_reports = int(request.args.get('max', -1))
    sort_order = request.args.get('sort', 'newest')

    # Fetch data from the database based on query parameters
     # Construct SQL query based on the provided parameters
    query = "SELECT * FROM reports WHERE 1=1"
    params = []

    if start_date:
        query += " AND entry_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND entry_date <= ?"
        params.append(end_date)

    if lat and lng and dist:
        query += " AND (6371 * acos(cos(radians(?)) * cos(radians(latitude)) * cos(radians(longitude) - radians(?)) + sin(radians(?)) * sin(radians(latitude)))) <= ?"
        params.extend([lat, lng, lat, dist])

    if sort_order == 'newest':
        query += " ORDER BY entry_date DESC"
    else:
        query += " ORDER BY entry_date ASC"

    if max_reports > 0:
        query += f" LIMIT {max_reports}"


    # Execute the query and fetch data from the database
    conn = sqlite3.connect('mydb.db')
    conn.create_function("acos", 1, acos_func)
    conn.create_function("cos", 1, cos_func)
    conn.create_function("radians", 1, radian_func)
    conn.create_function("sin", 1, sin_func)
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchall()
    conn.close()


    # Format the data based on the specified output format
    if output_format == 'csv':
        # Generate CSV file
        csv_data = generate_csv(data)
        return Response(csv_data, mimetype='text/csv',headers={'Content-Disposition': 'attachment; filename=reports.csv'})
    elif output_format == 'json':
        header = ['Report ID', 'User ID', 'Entry Date', 'Latitude', 'Longitude', 'Description', 'Path', 'County',
              'State', 'Username', 'Temperature', 'Humidity', 'Wind Speed', 'Rainfall', 'Category', 'Ip Address']
        data.insert(0, header)
        return jsonify(data)
    else:
        # Return HTML response
        # return render_template("data.html", data=data)
        htmltable = convert_to_html_table(data)
        return htmltable

def generate_csv(data):
    # Generate CSV data from the list of dictionaries or tuples
    csv_data = ""
    header = ['Report ID', 'User ID', 'Entry Date', 'Latitude', 'Longitude', 'Description', 'Path', 'County',
              'State', 'Username', 'Temperature', 'Humidity', 'Wind Speed', 'Rainfall', 'Category', 'Ip Address']
    data.insert(0, header)
    for row in data:
        csv_data += ','.join(map(str, row)) + '\n'
    return csv_data

def convert_to_html_table(data):
    try:
        # html_table = ""
        html_table = "<table border='1'><tr><th>Report ID</th><th>User ID</th><th>Entry Date</th><th>Latitude</th><th>Longitude</th><th>Description</th><th>Path</th><th>County</th><th>State</th><th>Username</th><th>Temperature</th><th>Humidity</th><th>Wind Speed</th><th>Rainfall</th><th>Category</th><th>IP Address</th></tr>"
        for row in data:
            html_table += "<tr>"
            for item in row:
                html_table += "<td>{}</td>".format(item)
            html_table += "</tr>"
        html_table += "</table>"
        return html_table
    except Exception as e:
        return f"An error occurred: {str(e)}"
    
def acos_func(data):
    return math.acos(data)

def cos_func(data):
    return math.cos(data)

def radian_func(data):
    return math.radians(data)

def sin_func(data):
    return math.sin(data)

if __name__ == '__main__':
    app.run(debug=True, port=5050)

