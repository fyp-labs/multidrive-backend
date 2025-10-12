# worker.py
import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker
from app.temporal.google_drive.workflows.GoogleDriveMetaDataWorkflow import GoogleDriveMetaDataWorkflow
from app.temporal.google_drive.activities.GoogleDriveMetaDataActivity import fetch_drive_folders,get_all_files_from_folders
from dotenv import load_dotenv
load_dotenv()


async def main():
    client = await Client.connect(os.getenv("TEMPORAL_CLIENT"))
    worker_folders = Worker(
        client,
        task_queue="folders-task-queue",
        workflows=[GoogleDriveMetaDataWorkflow],   
        activities=[fetch_drive_folders],
    )

    worker_files = Worker(
        client,
        task_queue="files-task-queue",
        workflows=[GoogleDriveMetaDataWorkflow],   
        activities=[get_all_files_from_folders],
    )

    
    await asyncio.gather(
        worker_folders.run(),
        worker_files.run(),
    )

if __name__ == "__main__":
    asyncio.run(main())
