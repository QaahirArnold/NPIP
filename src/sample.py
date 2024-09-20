import pandas as pd

# Define the file paths
input_file = '/Users/qaahirarnold/Documents/2024/CSC3003S/NPIP/src/network_measurements.csv'
output_file = 'sampled_data.csv'

# Read the CSV file into a DataFrame
df = pd.read_csv(input_file)

# Sample 5% of the DataFrame
sample_df = df.sample(frac=0.05, random_state=1)  # You can change the random_state for different samples

# Save the sampled DataFrame to a new CSV file
sample_df.to_csv(output_file, index=False)

print(f'Sampled data has been saved to {output_file}')
