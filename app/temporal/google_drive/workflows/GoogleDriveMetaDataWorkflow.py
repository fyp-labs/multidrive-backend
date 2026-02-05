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
        
        # Execute RAG pipeline for image captioning and embedding
        rag_images_result = await workflow.execute_activity(
                "process_images_for_rag",
                {
                    "user_id": user_id,
                    "google_drive_account_id": googleDriveAccountId,
                },
                start_to_close_timeout=timedelta(hours=2),  # Longer timeout for image processing
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,  # Fewer retries for expensive operations
                    initial_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0
                ),
                task_queue="rag-task-queue"
            )
        
        # Execute RAG pipeline for document text extraction and embedding
        rag_documents_result = await workflow.execute_activity(
                "process_documents_for_rag",
                {
                    "user_id": user_id,
                    "google_drive_account_id": googleDriveAccountId,
                },
                start_to_close_timeout=timedelta(hours=3),  # Longer timeout for large document processing
                heartbeat_timeout=timedelta(minutes=2),  # Increased to 2 minutes for large PDFs
                retry_policy=RetryPolicy(
                    maximum_attempts=2,  # Fewer retries for expensive operations
                    initial_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0
                ),
                task_queue="rag-documents-task-queue"
            )

        return {
            "message": "Data Fetched Successfully",
            "rag_pipeline": {
                "images": rag_images_result,
                "documents": rag_documents_result
            }
        }
