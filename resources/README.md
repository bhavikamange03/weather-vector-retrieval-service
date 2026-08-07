# Scheduled Weather Data Ingestion Job

This directory contains the configuration for a Databricks Job that automatically syncs weather data every 6 hours.

## Files

### `ingest_weather_embeddings_job.py`
Python script that performs the actual data ingestion:
- Fetches latest weather alerts, forecasts, and discussions
- Generates embeddings for all text content
- Stores results in Lakebase PostgreSQL database
- Provides detailed logging and metrics

### `ingest_weather_embeddings.job.yml`
DABs (Declarative Automation Bundles) job configuration:
- Defines the job schedule (every 6 hours)
- Configures compute resources (single-node cluster)
- Sets up retry logic and notifications
- Specifies required Python libraries

## Schedule

**Frequency**: Every 6 hours  
**Cron Expression**: `0 0 */6 * * ?`  
**Timezone**: America/Los_Angeles  

The job runs at:
- 00:00 (midnight)
- 06:00 (6 AM)
- 12:00 (noon)
- 18:00 (6 PM)

## Deployment

### Option 1: Deploy via DABs CLI (Recommended)

```bash
# From the project root
databricks bundle deploy --target <target_name>
```

This will:
1. Validate the job configuration
2. Deploy the job to your Databricks workspace
3. Start the schedule automatically

### Option 2: Manual Deployment via UI

1. Go to **Workflows** → **Jobs** in Databricks
2. Click **Create Job**
3. Configure:
   - **Name**: Weather Data Ingestion - Every 6 Hours
   - **Task Type**: Python script
   - **Source**: `/Workspace/Users/<your_email>/weather-vector-retrieval-service/resources/ingest_weather_embeddings_job.py`
   - **Cluster**: Single-node cluster with required libraries
   - **Schedule**: Cron expression `0 0 */6 * * ?`

### Option 3: Deploy via Databricks CLI

```bash
databricks jobs create --json-file resources/ingest_weather_embeddings.job.yml
```

## Monitoring

### View Job Runs

```bash
# List recent runs
databricks jobs runs list --job-name "Weather Data Ingestion - Every 6 Hours" --limit 10

# Get details of a specific run
databricks jobs runs get --run-id <run_id>
```

### Check Logs

Logs are available in the Databricks UI:
1. Go to **Workflows** → **Jobs**
2. Click on the job name
3. Select a run to view logs

The logs include:
- Start/end timestamps
- Documents fetched by type (alerts, forecasts, discussions)
- Database metrics (documents added, embeddings generated)
- Error messages if the job fails

### Email Notifications

By default, email notifications are sent on failure to the job owner.

To add more recipients, edit `ingest_weather_embeddings.job.yml`:

```yaml
email_notifications:
  on_failure:
    - your.email@company.com
    - team.email@company.com
  on_success:  # Optional
    - success.email@company.com
```

## Configuration

### Adjust Schedule

Edit the cron expression in `ingest_weather_embeddings.job.yml`:

```yaml
schedule:
  quartz_cron_expression: "0 0 */6 * * ?"  # Every 6 hours
  timezone_id: "America/Los_Angeles"
```

**Common schedules:**
- Every 3 hours: `0 0 */3 * * ?`
- Every 12 hours: `0 0 */12 * * ?`
- Daily at 8 AM: `0 0 8 * * ?`
- Every 30 minutes: `0 */30 * * * ?`

### Adjust Compute Resources

For larger datasets or faster processing, modify the cluster config:

```yaml
new_cluster:
  spark_version: "14.3.x-scala2.12"
  node_type_id: "i3.xlarge"  # Change to larger instance
  num_workers: 2  # Add workers for parallel processing
```

### Adjust Timeout

If ingestion takes longer than 1 hour:

```yaml
timeout_seconds: 7200  # 2 hours
```

## Troubleshooting

### Job Fails with "Module not found"

Ensure all required libraries are listed in the job configuration:

```yaml
libraries:
  - pypi:
      package: "sentence-transformers"
  - pypi:
      package: "psycopg2-binary"
  - pypi:
      package: "sqlalchemy"
  - pypi:
      package: "requests"
```

### Job Times Out

1. Check the logs to see which step is slow
2. Increase `timeout_seconds` in the job config
3. Consider optimizing the ingestion logic
4. Add more workers to the cluster

### Database Connection Errors

1. Verify Lakebase credentials are configured
2. Check network connectivity from cluster
3. Ensure database tables exist (run setup SQL scripts)

### No New Data Ingested

This can happen if:
- No new weather alerts/forecasts since last run
- Weather service API is down
- Data deduplication prevented re-ingesting existing records

Check the logs for "Documents added: 0" to confirm.

## Pausing/Resuming the Job

### Via UI
1. Go to **Workflows** → **Jobs**
2. Click on the job name
3. Toggle the **Pause** switch

### Via CLI
```bash
# Pause
databricks jobs update --job-id <job_id> --pause-status PAUSED

# Resume
databricks jobs update --job-id <job_id> --pause-status UNPAUSED
```

### Via Code
```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
job = w.jobs.get(job_id=<job_id>)
w.jobs.update(job_id=job.job_id, new_settings={'pause_status': 'PAUSED'})
```

## Manual Trigger

To run the job immediately (outside the schedule):

### Via UI
1. Go to **Workflows** → **Jobs**
2. Click on the job name
3. Click **Run now**

### Via CLI
```bash
databricks jobs run-now --job-name "Weather Data Ingestion - Every 6 Hours"
```

### Via Python
```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
run = w.jobs.run_now(job_id=<job_id>)
print(f"Started run: {run.run_id}")
```

## Metrics

Each job run reports:
- **Duration**: Time taken to complete
- **Documents added**: New weather documents inserted
- **Embeddings added**: New vector embeddings generated
- **Document types**: Breakdown by source (alerts, forecasts, discussions)

Example output:
```
================================================================================
Ingestion Job Complete
End Time: 2026-08-07 12:06:45
Duration: 23.45 seconds
Documents added: 47
Embeddings added: 89
Final state: 1234 documents, 2456 embeddings
================================================================================
```

## Cost Optimization

### Use Smaller Clusters
For light workloads, use `m5.large` or `m5.xlarge` instances.

### Use Spot Instances
Add to cluster config:
```yaml
aws_attributes:
  availability: "SPOT"
  spot_bid_price_percent: 100
```

### Adjust Schedule
If weather doesn't change frequently in your region, consider:
- Every 12 hours instead of 6
- Only during business hours

### Use Serverless
Consider using Databricks Serverless compute (if available) to eliminate cluster startup time.

## Next Steps

1. ✅ Deploy the job using `databricks bundle deploy`
2. ✅ Verify the first run completes successfully
3. ✅ Set up monitoring alerts (if needed)
4. ✅ Adjust schedule based on your requirements
5. ✅ Monitor costs and optimize as needed

---

**Questions?** Check the main project README or Databricks documentation.