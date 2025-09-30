import os
from fastapi import  HTTPException, status
from temporalio.client import Client
from app.temporal.google_drive.workflows.GoogleDriveMetaDataWorkflow import GoogleDriveMetaDataWorkflow

async def startMetaDataFetching(user_id: str, google_drive_account_id: str):
    client = await Client.connect(os.getenv("TEMPORAL_CLIENT"))

    workflow_id = f"gdrive-workflow-{user_id}-{google_drive_account_id}"

    try:
        handle = await client.start_workflow(
            "GoogleDriveMetaDataWorkflow",             
            {"user_id": user_id, "google_drive_account_id": google_drive_account_id},  
            id=workflow_id,
            task_queue="folders-task-queue",
        )

        return {
            "message": "Workflow started successfully",
            "workflow_id": handle.id,
            "run_id": handle.run_id,
            "status": "RUNNING"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )