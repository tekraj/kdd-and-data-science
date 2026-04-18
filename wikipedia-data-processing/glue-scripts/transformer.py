import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrameCollection, DynamicFrame
from pyspark.sql import functions as F 

# --- TRANSFORM FUNCTION ---
def MyTransform(glueContext, dfc) -> DynamicFrame:
    # 1. Extract the DynamicFrame
    dyf = next(iter(dfc.values()))
    df = dyf.toDF()

    # 2. Logic to handle columns safely
    actual_bot_col = next((c for c in df.columns if c.lower().strip() == 'is_bot'), 'is_bot')
    
    # 3. Perform Transformations
    # Cast to int and handle nulls
    df = df.withColumn("edit_size_bytes", F.coalesce(F.col("edit_size_bytes").cast("int"), F.lit(0)))
    
    processed_df = df.filter(F.col(actual_bot_col).cast("string") == "false") \
        .withColumn("page_title", F.lower(F.col("page_title"))) \
        .withColumn("edit_impact", 
            F.when(F.abs(F.col("edit_size_bytes")) > 1000, "High")
            .when(F.abs(F.col("edit_size_bytes")) > 100, "Medium")
            .otherwise("Low")
        )

    # 4. Drop the bot column
    final_df = processed_df.drop(actual_bot_col)

    # 5. Return as a SINGLE DynamicFrame
    return DynamicFrame.fromDF(final_df, glueContext, "transformed_data")

# --- JOB INITIALIZATION ---
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# --- SOURCE NODE ---
AmazonS3_node_source = glueContext.create_dynamic_frame.from_options(
    format_options={"quoteChar": "\"", "withHeader": True, "separator": ","}, 
    connection_type="s3", 
    format="csv", 
    connection_options={"paths": ["s3://wiki-knowledge-lake-bronze-tekraj/raw-edits/"], "recurse": True}, 
    transformation_ctx="AmazonS3_node_source"
)

# --- TRANSFORM NODE ---
Transformed_Data_Node = MyTransform(
    glueContext, 
    DynamicFrameCollection({"source": AmazonS3_node_source}, glueContext)
)

# --- SINK NODE (S3) ---
# Coalesce(1) ensures we get one single CSV file instead of multiple small ones
if (Transformed_Data_Node.count() >= 1):
    Transformed_Data_Node = Transformed_Data_Node.coalesce(1)

# UPDATED: Removed 'snappy' compression to ensure the output is a standard readable CSV
AmazonS3_node_sink = glueContext.write_dynamic_frame.from_options(
    frame=Transformed_Data_Node, 
    connection_type="s3", 
    format="csv", 
    connection_options={
        "path": "s3://wiki-knowledge-lake-bronze-tekraj/bronze/", 
        "partitionKeys": []
    }, 
    transformation_ctx="AmazonS3_node_sink"
)

job.commit()