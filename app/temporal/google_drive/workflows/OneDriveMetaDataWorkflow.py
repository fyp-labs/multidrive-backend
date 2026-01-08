# workflows.py
from temporalio import workflow
from datetime import timedelta
from temporalio.common import RetryPolicy

# workflows.py
@workflow.defn
class OneDriveMetaDataWorkflow:
    @workflow.run
    async def run(self, params:dict):

        user_id = params["user_id"]
        oneDriveAccountId = params["one_drive_account_id"]

        await workflow.execute_activity(
            "fetch_one_drive_metadata",   # single activity
            {
                "user_id": user_id,
                "one_drive_account_id": oneDriveAccountId,
            },
            start_to_close_timeout=timedelta(minutes=60),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=3, 
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0
            ),
            task_queue="one-drive-metadata-task-queue"
        )
        

        return {"message":"Data Fetched Successfully"}
