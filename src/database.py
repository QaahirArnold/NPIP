import sqlite3
import pandas as pd
import os


# Load the original CSV file
original_file = '/Users/qaahirarnold/Documents/2024/CSC3003S/NPIP/src/sampled_data.csv'
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
def insert_download_data():
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
def insert_upload_data():
    for index, row in upload_df.iterrows():
        # Insert into Upload_Data
        c.execute("""INSERT OR IGNORE INTO Upload_Data (date, isp, city, mbps) 
                     VALUES (?, ?, ?, ?)""",
                  (row['Date'], row['ASName'], row['City'], row['MeanThroughputMbps']))

# Function to print rows of a table specified by the user
def print_table_data(table_name):
    try:
        c.execute(f"SELECT * FROM {table_name}")
        rows = c.fetchall()
        if rows:
            for row in rows:
                print(row)
        else:
            print(f"No data found in table {table_name}.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")

# Function to export a table to CSV
def export_table_to_csv(table_name):
    try:
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql_query(query, conn)
        df.to_csv(f"../downloads/{table_name}.csv", index=False)
        print(f"Table {table_name} exported successfully to {table_name}.csv.")
    except Exception as e:
        print(f"Error exporting table {table_name}: {e}")

# Function to clear all data from the tables
def clear_all_tables():
    try:
        c.execute("DELETE FROM Download_Data")
        c.execute("DELETE FROM Upload_Data")
        c.execute("DELETE FROM Latency_Data")
        conn.commit()  # Make sure changes are committed
        print("All tables cleared successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error clearing tables: {e}")

# Simple text interface
def menu():
    while True:
        print("\nNetwork Performance Database Menu:")
        print("1. Insert download data from CSV")
        print("2. Insert upload data from CSV")
        print("3. Print rows from a table")
        print("4. Export table to CSV")
        print("5. Clear all tables")
        print("6. Exit")
        choice = input("Enter your choice (1/2/3/4/5/6): ")

        if choice == '1':
            insert_download_data()
            conn.commit()
            print("Download data inserted successfully.")
        elif choice == '2':
            insert_upload_data()
            conn.commit()
            print("Upload data inserted successfully.")
        elif choice == '3':
            table_name = input("Enter the table name to print (Download_Data, Upload_Data, Latency_Data): ")
            print_table_data(table_name)
        elif choice == '4':
            table_name = input("Enter the table name to export to CSV (Download_Data, Upload_Data, Latency_Data): ")
            export_table_to_csv(table_name)
        elif choice == '5':
            confirm = input("Are you sure you want to clear all data from the tables? (yes/no): ")
            if confirm.lower() == 'yes':
                clear_all_tables()
            else:
                print("Operation cancelled.")
        elif choice == '6':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please select 1, 2, 3, 4, 5, or 6.")

# Run the menu
menu()

# Commit changes and close the connection
conn.commit()
conn.close()
