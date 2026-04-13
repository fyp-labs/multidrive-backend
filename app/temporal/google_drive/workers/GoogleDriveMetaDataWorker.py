# worker.py
import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker
from app.temporal.google_drive.workflows.GoogleDriveMetaDataWorkflow import GoogleDriveMetaDataWorkflow
from app.temporal.google_drive.workflows.OneDriveMetaDataWorkflow import OneDriveMetaDataWorkflow
from app.temporal.google_drive.activities.GoogleDriveMetaDataActivity import fetch_drive_folders,get_all_files_from_folders
from app.temporal.google_drive.activities.GoogleDriveImageRAGActivity import process_images_for_rag
from app.temporal.google_drive.activities.GoogleDriveDocumentRAGActivity import process_documents_for_rag
from app.temporal.google_drive.activities.OneDriveMetaDataActivity import fetch_one_drive_metadata
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

    worker_one_drive = Worker(
        client,
        task_queue="one-drive-metadata-task-queue",
        workflows=[OneDriveMetaDataWorkflow],   
        activities=[fetch_one_drive_metadata],
    )

    worker_rag = Worker(
        client,
        task_queue="rag-task-queue",
        workflows=[GoogleDriveMetaDataWorkflow],   
        activities=[process_images_for_rag],
    )

    worker_rag_documents = Worker(
        client,
        task_queue="rag-documents-task-queue",
        workflows=[GoogleDriveMetaDataWorkflow],   
        activities=[process_documents_for_rag],
    )

    
    await asyncio.gather(
        worker_folders.run(),
        worker_files.run(),
        worker_one_drive.run(),
        worker_rag.run(),
        worker_rag_documents.run()
    )

if __name__ == "__main__":
    asyncio.run(main())
