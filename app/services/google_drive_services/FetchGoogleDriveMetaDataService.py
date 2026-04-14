import os
from fastapi import  HTTPException, status
from temporalio.client import Client
from app.temporal.google_drive.workflows.GoogleDriveMetaDataWorkflow import GoogleDriveMetaDataWorkflow
from app.models.google_drive_models.GoogleDriveFolderModel import GoogleDriveFolder
from app.models.google_drive_models.GoogleDriveFolderTreeModel import GoogleDriveFolderTree
from app.models.google_drive_models.GoogleDriveFileModel import GoogleDriveFile
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from temporalio.common import WorkflowIDConflictPolicy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import traceback


async def startMetaDataFetching(user_id: str, google_drive_account_id: str):
    client = await Client.connect(os.getenv("TEMPORAL_CLIENT"))

    workflow_id = f"gdrive-workflow-{user_id}-{google_drive_account_id}"

    try:
        handle = await client.start_workflow(
            "GoogleDriveMetaDataWorkflow",             
            {"user_id": user_id, "google_drive_account_id": google_drive_account_id},  
            id=workflow_id,
            task_queue="folders-task-queue",
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )

        return {
            "message": "Workflow started successfully",
            "workflow_id": handle.id,
            "run_id": handle.run_id,
            "status": "RUNNING"
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )
    
def upsertGoogleDriveFolders(db: Session, folders: list[dict], userParams: dict):
    try:
        userId= userParams.get("user_id")
        googleDriveAccountId= userParams.get("google_drive_account_id")
        folderStmt = insert(GoogleDriveFolder).values(folders)
        upsertFolderStmt = folderStmt.on_conflict_do_update(
            index_elements=["id"],  
            set_={
                "folder_name": folderStmt.excluded.folder_name,
                "folder_parents": folderStmt.excluded.folder_parents,
                "folder_path": folderStmt.excluded.folder_path,
                "updated_at": datetime.now(timezone.utc),
            },
        )

        db.execute(upsertFolderStmt)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        traceback.print_exc()
        raise e

def upsertGoogleDriveTree(db: Session, folder_tree: dict, userParams: dict):
    try:
        userId= userParams.get("user_id")
        googleDriveAccountId= userParams.get("google_drive_account_id")
        
        folderTreeStmt = insert(GoogleDriveFolderTree).values(
            user_id=userId,
            google_drive_account_id=googleDriveAccountId,
            folder_tree=folder_tree,
        )

            
        folderTreeUpsertStmt = folderTreeStmt.on_conflict_do_update(
            index_elements=["google_drive_account_id"],
            set_={
                "folder_tree": folderTreeStmt.excluded.folder_tree,
                "updated_at": datetime.now(timezone.utc),
            }
        )

        db.execute(folderTreeUpsertStmt)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        traceback.print_exc()
        raise e


def insertFiles(db: Session, file_data: list[dict]):
    try:
        fileStmt = insert(GoogleDriveFile).values(file_data)
        fileUpsertStmt=fileStmt.on_conflict_do_update(
            index_elements=["file_id"],
            set_={
                "file_name": fileStmt.excluded.file_name,
                "file_parents": fileStmt.excluded.file_parents,
                "viewed_by_me_time": fileStmt.excluded.viewed_by_me_time,
                "file_path": fileStmt.excluded.file_path,
                "updated_at": datetime.now(timezone.utc)
            }
        )

        db.execute(fileUpsertStmt)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        traceback.print_exc()
        raise e