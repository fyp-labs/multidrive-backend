# workflows.py
from temporalio import workflow
from datetime import timedelta
from temporalio.common import RetryPolicy

# workflows.py
@workflow.defn
class GoogleDriveMetaDataWorkflow:
    @workflow.run
    async def run(self, params:dict):

        user_id = params["user_id"]
        googleDriveAccountId = params["google_drive_account_id"]

        folders = await workflow.execute_activity(
            "fetch_drive_folders",   # single activity
            {
                "user_id": user_id,
                "google_drive_account_id": googleDriveAccountId,
            },
            start_to_close_timeout=timedelta(minutes=60),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=3, 
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0
            ),
            task_queue="folders-task-queue"
        )
        
        await workflow.execute_activity(
                "get_all_files_from_folders",
                {
                    "folders": folders,
                    "user_id": user_id,
                    "google_drive_account_id": googleDriveAccountId,
                },
                start_to_close_timeout=timedelta(minutes=60),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(
                    maximum_attempts=3, 
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0
                ),
                task_queue="files-task-queue"
            )

        return {"message":"Data Fetched Successfully"}
