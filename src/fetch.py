from google.cloud import bigquery
from google.oauth2 import service_account
import csv

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
