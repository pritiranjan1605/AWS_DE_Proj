import csv
import datetime

# Simulated extract from Netezza (replace with actual DB connection in production)
def extract_data(table, columns):
    print(f"Extracting data from {table} for columns: {columns}")
    # Simulated data
    return [
        {col: f"sample_{col}_value" for col in columns}
        for _ in range(3)
    ]

# Simulated transform (add your logic here)
def transform_data(data):
    print("Transforming data...")
    # Example: Add a processed timestamp
    for row in data:
        row['processed_at'] = datetime.datetime.now().isoformat()
    return data

# Simulated load to AWS Redshift (replace with actual Redshift connection in production)
def load_data(table, data):
    print(f"Loading data into {table}...")
    for row in data:
        print(row)

# Read metadata from CSV
def read_metadata(metadata_file):
    metadata = {}
    with open(metadata_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            key = (row['source_table'], row['target_table'])
            if key not in metadata:
                metadata[key] = []
            metadata[key].append(row)
    return metadata

def main():
    metadata_file = 'sample_metadata.csv'
    metadata = read_metadata(metadata_file)
    for (source_table, target_table), columns_info in metadata.items():
        columns = [col['column_name'] for col in columns_info]
        data = extract_data(source_table, columns)
        data = transform_data(data)
        load_data(target_table, data)

if __name__ == "__main__":
    main()
