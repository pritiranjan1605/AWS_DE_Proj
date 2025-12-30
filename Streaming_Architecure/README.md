
# AWS Streaming Data Architecture

This architecture is designed to efficiently handle both real-time (streaming) and periodic (batch) data, ensuring that data is reliably ingested, processed, stored, and made available for analytics and business intelligence. Below, each component and process is explained in greater detail, including practical examples and technical context.

This document explains the updated AWS streaming and batch data architecture as shown in the latest diagram. The architecture is designed for efficient, scalable, and secure data ingestion, processing, storage, and analytics using AWS managed services.

---

## 1. Data Sources

### Live Data Source
- **What it is:** Systems or devices that generate data continuously and require near-instant processing. Examples include IoT sensors (temperature, GPS), application logs, clickstreams, or financial transactions.
- **How it works:** As soon as an event occurs (e.g., a sensor reading or a user click), the data is sent to the ingestion layer for immediate processing.
- **Business value:** Enables use cases like real-time monitoring, fraud detection, and instant user feedback.

### Batch Data Source
- **What it is:** Systems that produce data in bulk at regular intervals. This could be daily sales reports, hourly log exports, or periodic database dumps.
- **How it works:** Data is collected over a period, then uploaded as files (CSV, JSON, Parquet, etc.) to the ingestion layer.
- **Business value:** Supports historical analysis, compliance reporting, and large-scale data integration from legacy systems.

---

## 2. Ingestion

### Kinesis Data Streams (Streaming Ingestion)
- **What it is:** A fully managed AWS service for collecting, processing, and analyzing real-time, streaming data at scale.
- **How it works:** Producers (apps, devices) send events to Kinesis, which buffers and distributes them to consumers (like Lambda functions) in real time. Data is retained for a configurable window (e.g., 24 hours), allowing for replay or multiple consumers.
- **Technical note:** Kinesis provides ordering, durability, and parallelism via shards, and can scale to handle thousands of events per second.
- **Business value:** Ensures no data is lost, even during spikes, and enables real-time analytics and alerting.

### S3 Raw Bucket (Batch Ingestion)
- **What it is:** An Amazon S3 bucket dedicated to storing all incoming batch files in their original, unprocessed form.
- **How it works:** Batch files are uploaded (manually, via scripts, or automated jobs) and stored as-is. This provides a reliable audit trail and allows for reprocessing if downstream logic changes.
- **Technical note:** S3 versioning and lifecycle policies can be used to manage data retention and cost.
- **Business value:** Guarantees data lineage and compliance, and supports data recovery and replay.

---

## 3. Streaming ETL

#### Sample Lambda Function for Streaming ETL
Below is a sample AWS Lambda function (Python) that processes records from Kinesis, validates, enriches, and writes cleaned events to S3:

```python
import json
import boto3
import base64
import datetime

s3 = boto3.client('s3')
S3_BUCKET = 'your-cleansed-bucket'

def lambda_handler(event, context):
	for record in event['Records']:
		# Decode and parse the Kinesis data
		payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
		data = json.loads(payload)

		# Example validation: check for required fields
		if 'timestamp' not in data or 'value' not in data:
			continue  # Skip invalid records

		# Example enrichment: add processing time
		data['processed_at'] = datetime.datetime.utcnow().isoformat()

		# Write cleaned record to S3 (partitioned by date)
		date_str = data['timestamp'].split('T')[0]
		s3.put_object(
			Bucket=S3_BUCKET,
			Key=f'cleaned/date={date_str}/{record["eventID"]}.json',
			Body=json.dumps(data)
		)
	return {'statusCode': 200, 'body': 'Processed records'}
```

> Replace `your-cleansed-bucket` with your actual S3 bucket name. This function can be deployed as a Lambda triggered by a Kinesis Data Stream.

---

#### Using AWS Kinesis Agent on EC2 for Data Ingestion
The AWS Kinesis Agent is a stand-alone Java application that collects and sends data (such as log files) from EC2 instances to Kinesis Data Streams or Firehose.

**Install Kinesis Agent on Amazon Linux/EC2:**
```bash
sudo yum install -y aws-kinesis-agent
```

**Configure the Agent:**
Edit the configuration file (usually `/etc/aws-kinesis/agent.json`):
```json
{
	"cloudwatch.emitMetrics": true,
	"kinesis.endpoint": "",
	"firehose.endpoint": "",
	"flows": [
		{
			"filePattern": "/var/log/myapp/*.log",
			"kinesisStream": "YourKinesisStreamName"
		}
	]
}
```

**Start the Agent:**
```bash
sudo service aws-kinesis-agent start
```

**Monitor the Agent:**
```bash
tail -f /var/log/aws-kinesis-agent/aws-kinesis-agent.log
```

> Adjust the `filePattern` and `kinesisStream` to match your use case. The agent will automatically monitor the specified files and send new data to Kinesis.

### Lambda (Streaming ETL)
- **What it is:** AWS Lambda is a serverless compute service that runs code in response to events (such as new records in Kinesis).
- **How it works:** Each event from Kinesis triggers a Lambda function, which can validate (e.g., schema checks), filter (e.g., drop irrelevant events), and enrich (e.g., add metadata or look up reference data) the incoming data. Lambda can also write a copy of the raw event to S3 for audit purposes.
- **Technical note:** Lambda functions are stateless, scale automatically, and can process thousands of events per second with low latency.
- **Business value:** Enables real-time data quality enforcement, enrichment, and routing without managing servers.

---

## 4. Data Lake

### S3 Raw
- **Purpose:** Central repository for all original, unprocessed data—both from batch uploads and streaming events. This ensures that the "source of truth" is always available for compliance, debugging, or reprocessing.

### S3 Cleansed
- **Purpose:** Stores data that has been validated, cleaned, and structured. For example, Lambda writes cleaned streaming events here, and batch ETL jobs output cleaned batch data. This zone is used for downstream analytics and machine learning.

### S3 Curated
- **Purpose:** Contains data that has been further transformed, aggregated, or enriched for specific business use cases. Data here is typically partitioned and optimized for query performance (e.g., Parquet format, partitioned by date).

---

## 5. Batch ETL

#### Sample AWS Glue Job Script (PySpark)
Below is a sample AWS Glue job (PySpark) for batch transformation. It reads data from S3, converts date/time fields, removes nulls, and writes the cleaned data back to S3:

```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, to_timestamp

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'SOURCE_S3_PATH', 'TARGET_S3_PATH'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read data from S3
df = spark.read.option('header', True).csv(args['SOURCE_S3_PATH'])

# Convert 'timestamp' column to timestamp type
df = df.withColumn('timestamp', to_timestamp(col('timestamp')))

# Remove rows with null values
df_clean = df.dropna()

# Write cleaned data back to S3 in Parquet format
df_clean.write.mode('overwrite').parquet(args['TARGET_S3_PATH'])

job.commit()
```

> Pass the `SOURCE_S3_PATH` and `TARGET_S3_PATH` as job parameters. This script can be extended for more complex transformations.

---

#### Script to Read from S3 and Load into Redshift (Python with boto3 & psycopg2)
Below is a sample script to load cleaned data from S3 into Amazon Redshift using the COPY command:

```python
import psycopg2

# Redshift connection details
redshift_host = 'your-redshift-cluster.xxxxxxxx.region.redshift.amazonaws.com'
redshift_port = 5439
redshift_db = 'your_db'
redshift_user = 'your_user'
redshift_password = 'your_password'
redshift_table = 'your_table'
s3_path = 's3://your-cleansed-bucket/cleaned/'
iam_role = 'arn:aws:iam::123456789012:role/YourRedshiftRole'

conn = psycopg2.connect(
	host=redshift_host,
	port=redshift_port,
	dbname=redshift_db,
	user=redshift_user,
	password=redshift_password
)
cur = conn.cursor()

copy_sql = f'''
	COPY {redshift_table}
	FROM '{s3_path}'
	IAM_ROLE '{iam_role}'
	FORMAT AS PARQUET;
'''

cur.execute(copy_sql)
conn.commit()
cur.close()
conn.close()
```

> Update the connection details, S3 path, and IAM role as per your environment. This script assumes the data is stored in Parquet format.

### AWS Glue Jobs
- **What it is:** A serverless ETL service that automates the discovery, transformation, and loading of batch data.
- **How it works:** Glue jobs read raw files from S3, apply transformations (cleaning, deduplication, schema mapping), and write the results to S3 Cleansed or Curated. Glue can also update the AWS Glue Data Catalog for schema management.
- **Business value:** Reduces operational overhead and accelerates data onboarding.

### Amazon EMR Spark
- **What it is:** A managed cluster platform for running big data frameworks like Apache Spark.
- **How it works:** EMR clusters process large volumes of data in parallel, supporting complex transformations, joins, and aggregations. EMR is ideal for heavy batch workloads or machine learning pipelines.
- **Business value:** Enables scalable, cost-effective processing of massive datasets.

---

## 6. Analytics

### Athena
- **What it is:** A serverless, interactive query service that lets you analyze data in S3 using standard SQL.
- **How it works:** Users or applications run SQL queries directly on S3 Cleansed or Curated data, with results returned in seconds. Athena integrates with Glue Catalog for schema discovery.
- **Business value:** Enables fast, flexible, and cost-effective analytics without infrastructure management.

### Redshift
- **What it is:** A fully managed, petabyte-scale data warehouse for complex analytics and reporting.
- **How it works:** Data from S3 Curated is loaded into Redshift for high-performance SQL analytics, BI, and dashboarding. Redshift can also federate queries to S3 (Spectrum).
- **Business value:** Supports enterprise-scale analytics, reporting, and data science.

### QuickSight
- **What it is:** AWS's cloud-native BI and visualization tool.
- **How it works:** Connects to Athena and Redshift to create interactive dashboards, reports, and visualizations for business users.
- **Business value:** Empowers self-service analytics and data-driven decision making across the organization.

---

## 7. Data Flow Summary

1. **Live events** (e.g., IoT sensor readings, user clicks) are sent to Kinesis Data Streams, which buffers and delivers them to Lambda for real-time validation, enrichment, and cleaning. Cleaned events are written to S3 Cleansed, while raw events can be optionally archived in S3 Raw for audit or replay.
2. **Batch files** (e.g., daily sales reports, log exports) are uploaded to the S3 Raw Bucket and stored in their original format, ensuring data lineage and compliance.
3. **Batch ETL** jobs (using Glue or EMR) read raw data from S3, perform cleaning, transformation, and enrichment, and write the results to S3 Cleansed (for validated data) and S3 Curated (for analytics-ready datasets).
4. **Analytics** is performed using Athena (for ad-hoc SQL queries on S3) and Redshift (for high-performance data warehousing and BI). QuickSight connects to both for business dashboards and visualizations.

---

## Architecture Diagram

Below is the updated architecture diagram referenced in this explanation:

![Streaming Architecture](./AWS_DataLake_Streaming.png)

---

## Summary

This simplified AWS streaming and batch data architecture provides a robust, scalable, and secure solution for ingesting, processing, storing, and analyzing both real-time and periodic data. It leverages AWS managed services for automation, governance, and analytics, supporting modern data engineering and business intelligence needs.
