# workflows.py
from temporalio import workflow
from datetime import timedelta

# workflows.py
@workflow.defn
class GoogleDriveMetaDataWorkflow:
    @workflow.run
    async def run(self, params:dict):

        user_id = params["user_id"]
        googleDriveAccountId = params["google_drive_account_id"]

        folders = await workflow.execute_activity(
            "fetch_drive_folders_recursive",   # single activity
            {
                "user_id": user_id,
                "google_drive_account_id": googleDriveAccountId,
            },
            schedule_to_close_timeout=timedelta(seconds=30),
            task_queue="folders-task-queue"
        )
        
        for folder in folders:
            await workflow.execute_activity(
                "get_all_files_from_folders",
                {
                    "parent_id": folder.get("id"),
                    "folder_path": folder.get("folder_path"),
                    "user_id": user_id,
                    "google_drive_account_id": googleDriveAccountId,
                },
                schedule_to_close_timeout=timedelta(seconds=30),
                task_queue="files-task-queue"
            )

        return {"message":"Data Fetched Successfully"}
