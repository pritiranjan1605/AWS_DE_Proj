# AWS Data Lake ETL Pipeline Architecture

## Overview
This document describes a robust, scalable, and secure AWS-based ETL (Extract, Transform, Load) pipeline for ingesting, validating, processing, and analyzing data from various external sources. The architecture leverages AWS managed services to ensure automation, reliability, and extensibility for enterprise data engineering needs.

---

## Architecture Components & Flow

### 1. External Data Sources
- **Types:** CSV, JSON, Parquet, FTP, API, Batch
- **Description:** Data is ingested from multiple external sources in various formats.

### 2. S3 Raw Bucket (`raw-data/`)
- **Purpose:** Landing zone for all incoming raw data files.
- **Process:** Data is uploaded directly or via streaming.

### 3. Lambda Ingestion Trigger
- **Trigger:** S3 ObjectCreated event
- **Purpose:** Initiates downstream processing as soon as new data arrives.

### 4. Glue Data Catalog
- **Purpose:** Registers and manages data schemas for all datasets.
- **Benefit:** Enables schema discovery and enforcement for downstream jobs.

### 5. Lambda - Data Validation
- **Tasks:**
  - Schema validation
  - Null checks
  - Size checks
- **Outcome:**
  - **Valid Data:** Proceeds to ETL orchestration
  - **Invalid Data:** Routed to quarantine

### 6. S3 Quarantine Bucket (`bad-data/`)
- **Purpose:** Stores invalid or corrupt data for further inspection and remediation.

### 7. Step Functions ETL Orchestration
- **Purpose:** Orchestrates the ETL workflow, including validation, transformation, and loading.

### 8. Glue Crawler & Metadata
- **Purpose:** Updates Glue Data Catalog with new/changed data structures.

### 9. Glue ETL Job (Spark Processing)
- **Tasks:**
  - Data cleaning (deduplication, type casting)
  - Business logic (joins, aggregations, enrichment)
- **Logging:** CloudWatch Logs for monitoring and troubleshooting
- **Notifications:** SNS/Alerts for errors or completion

### 10. S3 Curated Bucket (`curated-data/`)
- **Purpose:** Stores clean, validated, and transformed data ready for analytics.

### 11. S3 Analytics Bucket (`analytics-data/`)
- **Purpose:** Stores data optimized for analytics workloads.

### 12. Redshift/Serverless Data Warehouse
- **Purpose:** Centralized data warehouse for advanced analytics and BI.

### 13. Kinesis Data Streams & Lambda Streaming Processor
- **Purpose:** Supports real-time/streaming data ingestion and processing.

### 14. Amazon Athena & QuickSight
- **Athena:** Enables ad-hoc querying of curated/analytics data in S3.
- **QuickSight:** Provides dashboards and visualizations for business users.

### 15. IAM Policies
- **Purpose:** Secure access control for all AWS resources in the pipeline.

---

## Preprocessing Scripts

Below are example Python scripts for basic preprocessing and validation:

### 1. Schema Validation
```python
import pandas as pd

def validate_schema(df, expected_columns):
    missing = [col for col in expected_columns if col not in df.columns]
    extra = [col for col in df.columns if col not in expected_columns]
    if missing:
        print(f"Missing columns: {missing}")
    if extra:
        print(f"Unexpected columns: {extra}")
    return not missing and not extra
```

### 2. Null & Size Check
```python
def validate_nulls_and_size(df, min_rows=1):
    if df.isnull().any().any():
        print("Null values found!")
        return False
    if len(df) < min_rows:
        print(f"Not enough rows: {len(df)}")
        return False
    return True
```

### 3. ETL Processing Example: Date/Time Conversion & Value Transformation
```python
import pandas as pd

# Example ETL function: Convert timestamp to datetime, add new columns, and normalize values
def etl_process(df):
  # Convert 'timestamp' column to pandas datetime
  df['timestamp'] = pd.to_datetime(df['timestamp'])
  # Extract date and hour for partitioning or analytics
  df['date'] = df['timestamp'].dt.date
  df['hour'] = df['timestamp'].dt.hour
  # Normalize 'value' column (e.g., min-max scaling)
  min_val = df['value'].min()
  max_val = df['value'].max()
  df['value_normalized'] = (df['value'] - min_val) / (max_val - min_val)
  # Example: Add a flag for high value
  df['is_high_value'] = df['value'] > 15
  return df

# Usage example:
# df = pd.read_csv('sample.csv')
# df = etl_process(df)
# print(df.head())
```


---

## Sample Dataset

| id  | name     | value | timestamp           |
|-----|----------|-------|---------------------|
| 1   | Alice    | 10.5  | 2025-12-30T10:00:00 |
| 2   | Bob      | 20.0  | 2025-12-30T10:05:00 |
| 3   | Charlie  | 15.2  | 2025-12-30T10:10:00 |

---

## How the Pipeline Works (Step-by-Step)

1. **Data Ingestion:** External data is uploaded to the S3 raw bucket, either in batch or streaming mode.
2. **Ingestion Trigger:** S3 event triggers a Lambda function to start the validation process.
3. **Schema & Data Validation:** Lambda checks schema, nulls, and size. Invalid data is quarantined; valid data proceeds.
4. **Metadata Registration:** Glue Data Catalog and Crawler update schemas and metadata.
5. **ETL Orchestration:** Step Functions coordinate the ETL process, invoking Glue ETL jobs for cleaning, transformation, and enrichment.
6. **Data Storage:**
   - Cleaned data is stored in the S3 curated bucket.
   - Analytics-ready data is stored in the S3 analytics bucket.
   - Data is loaded into Redshift for warehousing.
7. **Streaming Support:** Kinesis and Lambda handle real-time data flows.
8. **Analytics & Visualization:** Athena enables ad-hoc queries; QuickSight provides dashboards.
9. **Security:** IAM policies enforce secure access at every stage.

---

## Image Reference

The following architecture diagram illustrates the complete pipeline:

![ETL Pipeline Architecture](./ETL_Pipeline.png)

---

## Summary

This AWS ETL pipeline architecture ensures scalable, automated, and secure data processing from ingestion to analytics, supporting both batch and streaming use cases for modern data engineering needs.
