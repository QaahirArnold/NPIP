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

# Replace with your job_id
job_id = 'aa3d2e46-9829-4659-a890-ef9a1f7a40e9'

# Fetch the job using the job_id
query_job = client.get_job(job_id)

# Check if the job is done
if query_job.state == 'DONE':
    # Fetch the results
    results = query_job.result()  # This will return an iterable result
    with open('network_measurements.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # Write the headers
        writer.writerow(['Date', 'Direction','AvgThroughputMbps', 'ASName', 'City', 'AvgLatency'])
        
        # Write the rows
        for row in results:
            writer.writerow([row.Date, row.Direction, row.AvgThroughputMbps, row.ASName, row.City, row.AvgLatency,])

    print("Data successfully written to network_measurements.csv")

else:
    print(f"Job {job_id} is still running. Please try again later.")



