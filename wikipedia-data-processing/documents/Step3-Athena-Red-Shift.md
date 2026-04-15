``` 
CREATE DATABASE wiki_db;
CREATE EXTERNAL TABLE IF NOT EXISTS wiki_db.bronze_edits (
  page_title string,
  editor_username string,
  edit_size_bytes int,
  timestamp string,
  edit_impact string
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://wiki-knowledge-lake-bronze-tekraj/bronze/'
TBLPROPERTIES ('skip.header.line.count'='1');

SELECT * FROM wiki_db.bronze_edits 
LIMIT 10;
```

## AWS SageMaker
2. Launch SageMaker Studio
Go to the SageMaker Console.

Click on Studio in the left sidebar.

Set up a "Domain" (use Quick Setup if it's your first time).

Launch the Studio Dashboard.

3. Build the Model (Two Simple Ways)
Option A: The "Mathematician" Way (Notebooks)
If you want to use your Python skills (Pandas, Scikit-Learn):

Open a JupyterLab notebook within Studio.

Use the SageMaker Python SDK to pull data from your S3 bucket.

Simple Code Example:
```
import pandas as pd
import boto3

# Load data from your Bronze bucket
s3 = boto3.client('s3')
obj = s3.get_object(Bucket='wiki-knowledge-lake-bronze-tekraj', Key='bronze/your_file.csv')
df = pd.read_csv(obj['Body'])

# Now you can use standard Scikit-Learn or XGBoost logic
```


This error occurs because SageMaker Unified Studio needs permission to "act as" your IAM role. In AWS, a Trust Policy is a security gate that defines which services (like SageMaker, Glue, or Athena) are allowed to assume the identity of a specific role.

Since you are likely using an AWS Academy or Learner Lab environment, you may have restricted permissions to edit IAM roles directly, but here is how you fix this if you have access:

How to Update the Trust Policy
Open IAM Console: Go to the IAM (Identity and Access Management) dashboard.

Find the Role: Click on Roles in the left sidebar and search for LabRole.

Edit Trust Relationship:

Click on the LabRole name.

Click on the Trust relationships tab (next to Permissions).

Click the Edit trust policy button.

Merge the JSON: * You need to add the services listed in your error message to the existing policy.

Note: Do not delete the existing trust entries (like ec2.amazonaws.com), or your existing Glue jobs might stop working!

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "logs.amazonaws.com",
                    "glue.amazonaws.com",
                    "ec2.amazonaws.com",
                    "ssm.amazonaws.com",
                    "athena.amazonaws.com",
                    "lambda.amazonaws.com",
                    "cloudformation.amazonaws.com",
                    "states.amazonaws.com",
                    "iot.amazonaws.com",
                    "sagemaker.amazonaws.com",
                    "elasticmapreduce.amazonaws.com",
                    "resource-groups.amazonaws.com",
                    "sqs.amazonaws.com",
                    "s3.amazonaws.com",
                    "sns.amazonaws.com",
                    "lakeformation.amazonaws.com",
                    "bedrock.amazonaws.com",
                    "scheduler.amazonaws.com",
                    "airflow-serverless.amazonaws.com",
                    "redshift.amazonaws.com",
                    "emr-serverless.amazonaws.com",
                    "datazone.amazonaws.com"
                ]
            },
            "Action": [
                "sts:AssumeRole",
                "sts:TagSession",
                "sts:SetContext",
                "sts:SetSourceIdentity"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "036628614391"
                }
            }
        }
    ]
}
```