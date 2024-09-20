from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_session import Session
import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from google.cloud import bigquery
from google.oauth2 import service_account
import csv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, 
            template_folder='../templates',  # Relative path to the templates directory
            static_folder='../static')       # Relative path to the static directory

# Configure session
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem for session storage

# Configure Flask-Session with filesystem
sess = Session(app)

# Connect to the SQLite database
def get_db_connection():
    conn = sqlite3.connect('network_performance.db')
    conn.row_factory = sqlite3.Row  # So we can return dict-like rows
    return conn

def fetch_data():
    # Load credentials from the service account key file
    credentials = service_account.Credentials.from_service_account_file(
        '/Users/qaahirarnold/keyfile.json'  # Replace with the actual path to your keyfile
    )

    # Initialize the BigQuery client with the correct project ID
    client = bigquery.Client(
        credentials=credentials,
        project="focus-antler-432214-b4"  # Replace with your Google Cloud project ID
    )

    # Optimized query with TABLESAMPLE SYSTEM for sampling and combining both downloads and uploads
    query = """
    WITH latest_data AS (
    SELECT MAX(date) AS max_date
    FROM `measurement-lab.ndt.unified_downloads`
    WHERE date >= '2020-01-01' AND client.Geo.ContinentCode = 'AF'
    ),
    sampled_data AS (
    SELECT
        date AS Date,
        'download' AS Direction,
        a.MeanThroughputMbps,
        client.Network.ASName,
        client.Geo.City,
        a.MinRTT AS Latency
    FROM
        `measurement-lab.ndt.unified_downloads`
    WHERE
        date >= '2020-01-01'
        AND date <= (SELECT max_date FROM latest_data)
        AND client.Geo.ContinentCode = 'AF'
        AND RAND() < 0.05  -- This samples approximately 5% of the rows

    UNION ALL

    SELECT
        date AS Date,
        'upload' AS Direction,
        a.MeanThroughputMbps,
        client.Network.ASName,
        client.Geo.City,
        a.MinRTT AS Latency
    FROM
        `measurement-lab.ndt.unified_uploads`
    WHERE
        date >= '2020-01-01'
        AND date <= (SELECT max_date FROM latest_data)
        AND client.Geo.ContinentCode = 'AF'
        AND RAND() < 0.05  -- This samples approximately 5% of the rows
    ),
    daily_aggregates AS (
    SELECT
        Date,
        Direction,
        AVG(MeanThroughputMbps) AS MeanThroughputMbps,
        ASName,
        City,
        AVG(Latency) AS Latency,
        COUNT(*) AS SampleSize
    FROM
        sampled_data
    GROUP BY
        Date, Direction, ASName, City
    )
    SELECT *
    FROM daily_aggregates
    ORDER BY Date DESC, Direction, ASName, City

    """

    # Run the query
    query_job = client.query(query, location="US")

    # Fetch the results
    results = query_job.result()

    # Write the results to a CSV file
    with open('/Users/qaahirarnold/Documents/2024/CSC3003S/NPIP/data/network_measurements.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # Write the headers
        writer.writerow(['Date', 'MeanThroughputMbps', 'ASName', 'City', 'Latency'])
        
        # Write the rows
        for row in results:
            writer.writerow([row.Date, row.UUID, row.MeanThroughputMbps, row.ASName, row.City, row.TestTime, row.Latency, row.MeasurementType])

    print("Data successfully written to network_measurements.csv")

def process_data():
    # Load the original CSV file
    original_file = '/Users/qaahirarnold/Documents/2024/CSC3003S/NPIP/data/network_measurements.csv'
    df = pd.read_csv(original_file)


    # Clean up the 'Direction' column by removing extra spaces and making it lowercase
    df['Direction'] = df['Direction'].str.strip().str.lower()

    # Split data into download and upload, considering cleaned 'Direction' values
    download_data = df[df['Direction'] == 'download']
    upload_data = df[df['Direction'] == 'upload']

    # Rename columns specifically for download and save to download_measurements.csv
    download_data = download_data.rename(columns={'AvgThroughputMbps': 'MeanThroughputMbps', 'AvgLatency': 'Latency'})
    download_data.to_csv('download_measurements.csv', index=False)

    # Rename columns specifically for upload and save to upload_measurements.csv
    upload_data = upload_data.rename(columns={'AvgThroughputMbps': 'MeanThroughputMbps', 'AvgLatency': 'Latency'})
    upload_data.to_csv('upload_measurements.csv', index=False)

    print("Data has been split, columns renamed, and saved to download_measurements.csv and upload_measurements.csv")

    # Load the CSV files into pandas DataFrames
    download_df = pd.read_csv('/Users/qaahirarnold/Documents/2024/CSC3003S/NPIP/data/download_measurements.csv')
    upload_df = pd.read_csv('/Users/qaahirarnold/Documents/2024/CSC3003S/NPIP/data/upload_measurements.csv')



    # Connect to the SQLite database using an absolute path
    conn = sqlite3.connect('network_performance.db')
    c = conn.cursor()

    download_table_query = '''
    CREATE TABLE IF NOT EXISTS Download_Data (
        date DATE NOT NULL,
        isp TEXT,
        city TEXT,
        mbps INTEGER
    );
    '''


    upload_table_query = '''CREATE TABLE IF NOT EXISTS Upload_Data (
        date DATE NOT NULL,
        isp TEXT,
        city TEXT,
        mbps INTEGER
    );
    '''


    latency_table_query = '''CREATE TABLE IF NOT EXISTS Latency_Data (
        date DATE NOT NULL,
        isp TEXT,
        city TEXT,
        latency INTEGER
    );
    '''

    # Execute the query
    c.execute(download_table_query)
    c.execute(upload_table_query)
    c.execute(latency_table_query)

    # Insert data from download CSV into Download_Data and Latency_Data tables
    
    for index, row in download_df.iterrows():
        # Insert into Download_Data
        c.execute("""INSERT OR IGNORE INTO Download_Data (date, isp, city, mbps) 
                    VALUES (?, ?, ?, ?)""",
                (row['Date'], row['ASName'], row['City'], row['MeanThroughputMbps']))

        # Insert into Latency_Data
        c.execute("""INSERT OR IGNORE INTO Latency_Data (date, isp, city, latency) 
                    VALUES (?, ?, ?, ?)""",
                (row['Date'], row['ASName'], row['City'], row['Latency']))

    # Insert data from upload CSV into Upload_Data table

    for index, row in upload_df.iterrows():
        # Insert into Upload_Data
        c.execute("""INSERT OR IGNORE INTO Upload_Data (date, isp, city, mbps) 
                    VALUES (?, ?, ?, ?)""",
                (row['Date'], row['ASName'], row['City'], row['MeanThroughputMbps']))

    # Commit changes and close the connection
    conn.commit()
    conn.close()


# Route to display homepage and allow selection
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    c = conn.cursor()

    # Query available cities
    cities = pd.read_sql_query("SELECT DISTINCT city FROM (SELECT city FROM Download_Data UNION SELECT city FROM Upload_Data)", conn)
    available_cities = cities['city'].tolist()

    # Query available networks
    networks = pd.read_sql_query("SELECT DISTINCT isp FROM (SELECT isp FROM Download_Data UNION SELECT isp FROM Upload_Data)", conn)
    available_networks = networks['isp'].tolist()

    # Process form submission
    if request.method == 'POST':
        comparison_type = request.form.get('comparison_type')
        selected_city1 = request.form.get('city1')
        selected_city2 = request.form.get('city2')
        selected_network = request.form.get('network')

        # Provide default city if none is selected
        #if not selected_city1:
        #    selected_city1 = 'Cape Town'
        #if not selected_city2:
        #    selected_city2 = 'Cape Town'

        if comparison_type == '1':
            return redirect(url_for('compare_city', city=selected_city1))
        elif comparison_type == '2':
            return redirect(url_for('compare_networks', city1=selected_city1, city2=selected_city2, network=selected_network))
        elif comparison_type == '3':
            return redirect(url_for('compare_multiple_networks', city1=selected_city1, city2=selected_city2))

    return render_template('index.html', available_cities=available_cities, available_networks=available_networks)


@app.route('/compare_city', methods=['GET', 'POST'])
def compare_city():
    conn = get_db_connection()

    # Query available cities
    cities = pd.read_sql_query("SELECT DISTINCT city FROM (SELECT city FROM Download_Data UNION SELECT city FROM Upload_Data)", conn)
    available_cities = cities['city'].tolist()

    selected_city = request.args.get('city')  # Default to 'Cape Town' if no city is selected
    if request.method == 'POST':
        selected_city = request.form.get('city')

    # Query available networks for the selected city
    networks_query = """
        SELECT DISTINCT isp 
        FROM (
            SELECT isp FROM Download_Data WHERE city = ?
            UNION 
            SELECT isp FROM Upload_Data WHERE city = ?
        )
    """
    networks = pd.read_sql_query(networks_query, conn, params=[selected_city, selected_city])
    available_networks = networks['isp'].tolist()

    selected_networks = request.form.getlist('networks')

    if request.method == 'POST' and selected_networks:
        # Query to get comparison data for selected networks
        query = f'''
            SELECT download.isp, 
                   AVG(download.mbps) AS avg_download_mbps,
                   AVG(upload.mbps) AS avg_upload_mbps,
                   AVG(latency.latency) AS avg_latency
            FROM Download_Data AS download
            LEFT JOIN Upload_Data AS upload 
                ON download.city = upload.city AND download.isp = upload.isp
            LEFT JOIN Latency_Data AS latency 
                ON download.city = latency.city AND download.isp = latency.isp
            WHERE download.city = ?
            AND download.isp IN ({','.join(['?'] * len(selected_networks))})
            GROUP BY download.isp
            ORDER BY avg_download_mbps DESC
        '''
        params = [selected_city] + selected_networks
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.DataFrame()  # Empty DataFrame if no networks selected or GET request

    return render_template('compare_city.html', 
                           selected_city=selected_city, 
                           networks=df, 
                           available_cities=available_cities, 
                           available_networks=available_networks)

# Route for comparing a network between two cities
@app.route('/compare_networks', methods=['GET', 'POST'])
def compare_networks():
    conn = get_db_connection()
    c = conn.cursor()

    # Query available cities
    cities = pd.read_sql_query("SELECT DISTINCT city FROM (SELECT city FROM Download_Data UNION SELECT city FROM Upload_Data)", conn)
    available_cities = cities['city'].tolist()

    # Process form submission
    if request.method == 'POST':
        city1 = request.form.get('city1')
        city2 = request.form.get('city2')
        selected_networks = request.form.getlist('networks')

        # Query to get comparison data for selected networks
        query = f'''
            SELECT download.city, download.isp, 
                   AVG(download.mbps) AS avg_download_mbps,
                   AVG(upload.mbps) AS avg_upload_mbps,
                   AVG(latency.latency) AS avg_latency
            FROM Download_Data AS download
            LEFT JOIN Upload_Data AS upload 
                ON download.city = upload.city AND download.isp = upload.isp
            LEFT JOIN Latency_Data AS latency 
                ON download.city = latency.city AND download.isp = latency.isp
            WHERE download.city IN (?, ?)
            AND download.isp IN ({','.join(['?'] * len(selected_networks))})
            GROUP BY download.city, download.isp
            ORDER BY download.city, avg_download_mbps DESC
        '''
        params = [city1, city2] + selected_networks
        df = pd.read_sql_query(query, conn, params=params)
        
        return render_template('compare_networks.html', city1=city1, city2=city2, networks=df, available_cities=available_cities)

    return render_template('compare_networks.html', available_cities=available_cities)

@app.route('/get_common_networks', methods=['GET'])
def get_common_networks():
    city1 = request.args.get('city1')
    city2 = request.args.get('city2')

    conn = get_db_connection()
    query = f'''
        SELECT DISTINCT download.isp
        FROM Download_Data AS download
        WHERE download.city = ?
        AND download.isp IN (
            SELECT DISTINCT isp
            FROM Download_Data
            WHERE city = ?
        )
    '''
    networks = pd.read_sql_query(query, conn, params=[city1, city2])
    return networks['isp'].tolist()

# Route for comparing multiple networks between two cities
@app.route('/compare_multiple_networks', methods=['GET', 'POST'])
def compare_multiple_networks():
    conn = get_db_connection()

    # Query available cities
    cities = pd.read_sql_query("SELECT DISTINCT city FROM (SELECT city FROM Download_Data UNION SELECT city FROM Upload_Data)", conn)
    available_cities = cities['city'].tolist()

    # Initialize variables
    city1 = None
    city2 = None
    results = pd.DataFrame()  # Empty DataFrame

    if request.method == 'POST':
        city1 = request.form.get('city1')
        city2 = request.form.get('city2')
        networks1 = request.form.getlist('networks1[]')
        networks2 = request.form.getlist('networks2[]')

        # Combine networks from both cities
        all_networks = networks1 + networks2

        if all_networks:  # Only query if networks are selected
            query = f'''
                SELECT download.city, download.isp, 
                       AVG(download.mbps) AS avg_download_mbps,
                       AVG(upload.mbps) AS avg_upload_mbps,
                       AVG(latency.latency) AS avg_latency
                FROM Download_Data AS download
                LEFT JOIN Upload_Data AS upload ON download.city = upload.city AND download.isp = upload.isp
                LEFT JOIN Latency_Data AS latency ON download.city = latency.city AND download.isp = latency.isp
                WHERE download.city IN (?, ?)
                AND download.isp IN ({','.join(['?'] * len(all_networks))})
                GROUP BY download.city, download.isp
                ORDER BY download.city, avg_download_mbps DESC
            '''
            params = [city1, city2] + all_networks
            results = pd.read_sql_query(query, conn, params=params)
            
            # Replace NaN values with None
            results = results.where(pd.notnull(results), None)

    # Always return a rendered template, even if it's just with the form
    return render_template('compare_multiple_networks.html', 
                           available_cities=available_cities,
                           selected_city1=city1,
                           selected_city2=city2,
                           results=results) 

@app.route('/get_networks', methods=['GET'])
def get_networks():
    city1 = request.args.get('city1')
    city2 = request.args.get('city2')

    conn = get_db_connection()
    
    if city2:
        # If two cities are provided, get common networks
        query = """
            SELECT DISTINCT d1.isp
            FROM Download_Data d1
            JOIN Download_Data d2 ON d1.isp = d2.isp
            WHERE d1.city = ? AND d2.city = ?
            ORDER BY d1.isp
        """
        networks = pd.read_sql_query(query, conn, params=[city1, city2])
    else:
        # If only one city is provided, get networks for that city
        query = "SELECT DISTINCT isp FROM Download_Data WHERE city = ? ORDER BY isp"
        networks = pd.read_sql_query(query, conn, params=[city1])
    return networks['isp'].tolist()

@app.route('/compare_networks', methods=['POST'])
def compare_networks_ajax():
    data = request.get_json()
    city = data.get('city')
    networks = data.get('networks')

    conn = get_db_connection()
    query = f'''
        SELECT download.isp AS network, 
               AVG(download.mbps) AS avg_download_mbps,
               AVG(upload.mbps) AS avg_upload_mbps,
               AVG(latency.latency) AS avg_latency
        FROM Download_Data AS download
        LEFT JOIN Upload_Data AS upload ON download.city = upload.city AND download.isp = upload.isp
        LEFT JOIN Latency_Data AS latency ON download.city = latency.city AND download.isp = latency.isp
        WHERE download.city = '{city}' AND download.isp IN ({",".join(f"'{network}'" for network in networks)})
        GROUP BY download.isp
    '''
    df = pd.read_sql_query(query, conn)
    return df.to_json(orient='records')

@app.route('/time_analysis', methods=['GET', 'POST'])
def time_analysis():
    conn = get_db_connection()

    # Query available cities
    cities = pd.read_sql_query("SELECT DISTINCT city FROM Download_Data ORDER BY city", conn)
    available_cities = cities['city'].tolist()

    # Set default date range (last 30 days)
    end_date = datetime.now().date()
    start_date = end_date - relativedelta(days=730)

    results = pd.DataFrame()
    selected_city = None
    selected_network = None

    if request.method == 'POST':
        selected_city = request.form.get('city')
        selected_network = request.form.get('network')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()

        query = '''
            SELECT download.date, 
                   AVG(download.mbps) AS avg_download_mbps,
                   AVG(upload.mbps) AS avg_upload_mbps,
                   AVG(latency.latency) AS avg_latency
            FROM Download_Data AS download
            LEFT JOIN Upload_Data AS upload 
                ON download.city = upload.city AND download.isp = upload.isp AND download.date = upload.date
            LEFT JOIN Latency_Data AS latency 
                ON download.city = latency.city AND download.isp = latency.isp AND download.date = latency.date
            WHERE download.city = ? AND download.isp = ? AND download.date BETWEEN ? AND ?
            GROUP BY download.date
            ORDER BY download.date
        '''
        results = pd.read_sql_query(query, conn, params=[selected_city, selected_network, start_date, end_date])
        results['date'] = pd.to_datetime(results['date'])

    return render_template('time_analysis.html',
                           available_cities=available_cities,
                           selected_city=selected_city,
                           selected_network=selected_network,
                           start_date=start_date,
                           end_date=end_date,
                           results=results)

@app.route('/get_top_networks', methods=['GET'])
def get_top_networks():
    city = request.args.get('city1')

    conn = get_db_connection()

    # Query to get the top 5 networks for the selected city, sorted by average download speed
    query = '''
        SELECT isp, AVG(mbps) AS avg_download_mbps
        FROM Download_Data
        WHERE city = ?
        GROUP BY isp
        ORDER BY avg_download_mbps DESC
        LIMIT 5
    '''
    top_networks = pd.read_sql_query(query, conn, params=[city])

    # Convert the DataFrame to a list of dicts for easy JSON response
    top_networks_list = top_networks[['isp', 'avg_download_mbps']].to_dict(orient='records')

    # Prepare the response
    response = []
    for network in top_networks_list:
        response.append({
            'name': network['isp'],
            'download_speed': network['avg_download_mbps']
        })

    return jsonify(response)

@app.route('/get_common_cities', methods=['GET'])
def get_common_cities():
    city1 = request.args.get('city1')

    # Query to get cities with common networks
    common_cities_query = """
    SELECT DISTINCT d2.city
    FROM Download_Data AS d1
    JOIN Upload_Data AS u1
        ON d1.city = u1.city
        AND d1.isp = u1.isp
    JOIN Download_Data AS d2
        ON d1.isp = d2.isp
    JOIN Upload_Data AS u2
        ON d2.city = u2.city
        AND d2.isp = u2.isp
    WHERE d1.city = ?
    AND d2.city != d1.city
    GROUP BY d2.city
    HAVING COUNT(DISTINCT d1.isp) > 0
    """

    try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(common_cities_query, (city1,))
            common_cities = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500

    return jsonify(common_cities)

@app.route('/get_top_networks_in_city', methods=['GET'])
def get_top_networks_in_city():
    city = request.args.get('city')
    if not city:
        return jsonify({'error': 'City parameter is required'}), 400

    query = """
    SELECT 
        download.isp AS name, 
        download.avg_download_mbps, 
        upload.avg_upload_mbps, 
        latency.avg_latency
    FROM (
        SELECT isp, AVG(mbps) AS avg_download_mbps
        FROM Download_Data
        WHERE city = ?
        GROUP BY isp
    ) AS download
    JOIN (
        SELECT isp, AVG(mbps) AS avg_upload_mbps
        FROM Upload_Data
        WHERE city = ?
        GROUP BY isp
    ) AS upload ON download.isp = upload.isp
    JOIN (
        SELECT isp, AVG(latency) AS avg_latency
        FROM Latency_Data
        WHERE city = ?
        GROUP BY isp
    ) AS latency ON download.isp = latency.isp
    ORDER BY download.avg_download_mbps DESC
    LIMIT 5;
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (city, city, city))  # Pass city parameter three times
        networks = cursor.fetchall()
        conn.close()

        return jsonify([{
            'name': row[0],  # Adjust indexing if needed
            'avg_download_mbps': row[1],
            'avg_upload_mbps': row[2],
            'avg_latency': row[3]
        } for row in networks])
    except sqlite3.Error as e:
        print(f"Database error in get_top_networks_in_city: {e}")  # For debugging
        return jsonify({'error': str(e)}), 500


@app.route('/get_top_cities_in_africa', methods=['GET'])
def get_top_cities_in_africa():
    query = """
    SELECT 
    download.city AS name, 
    download.avg_download_mbps, 
    upload.avg_upload_mbps, 
    latency.avg_latency
    FROM (
        SELECT city, AVG(mbps) AS avg_download_mbps
        FROM Download_Data
        GROUP BY city
    ) AS download
    JOIN (
        SELECT city, AVG(mbps) AS avg_upload_mbps
        FROM Upload_Data
        GROUP BY city
    ) AS upload ON download.city = upload.city
    JOIN (
        SELECT city, AVG(latency) AS avg_latency
        FROM Latency_Data
        GROUP BY city
    ) AS latency ON download.city = latency.city
    ORDER BY download.avg_download_mbps DESC
    LIMIT 5;
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        cities = cursor.fetchall()
        conn.close()

        return jsonify([{
            'name': row['name'],
            'avg_download_mbps': row['avg_download_mbps'],
            'avg_upload_mbps': row['avg_upload_mbps'],
            'avg_latency': row['avg_latency']
        } for row in cities])
    except sqlite3.Error as e:
        print(f"Database error in get_top_cities_in_africa: {e}")  # For debugging
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
