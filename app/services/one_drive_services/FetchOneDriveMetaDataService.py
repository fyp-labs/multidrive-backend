import os
from fastapi import  HTTPException, status
from temporalio.client import Client
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.one_drive_models.OneDriveFoldersModel import OneDriveFolder
from app.models.one_drive_models.OneDriveFoldersTreeModel import OneDriveFolderTree
from app.models.one_drive_models.OneDriveFilesModel import OneDriveFile


async def startMetaDataFetching(user_id: str, one_drive_account_id: str):
    client = await Client.connect(os.getenv("TEMPORAL_CLIENT"))

    workflow_id = f"onedrive-workflow-{user_id}-{one_drive_account_id}"

    try:
        handle = await client.start_workflow(
            "OneDriveMetaDataWorkflow",             
            {"user_id": user_id, "one_drive_account_id": one_drive_account_id},  
            id=workflow_id,
            task_queue="one-drive-metadata-task-queue",
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
    
def upsertOneDriveFolders(db: Session, folders: list[dict]):
    try:
        folderStmt = insert(OneDriveFolder).values(folders)
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
            
        raise e
    

def upsertOneDriveTree(db: Session, folder_tree: dict, userParams: dict):
    try:
        userId= userParams.get("user_id")
        oneDriveAccountId= userParams.get("one_drive_account_id")
        
        folderTreeStmt = insert(OneDriveFolderTree).values(
            user_id=userId,
            one_drive_account_id=oneDriveAccountId,
            folder_tree=folder_tree,
        )

            
        folderTreeUpsertStmt = folderTreeStmt.on_conflict_do_update(
            index_elements=["one_drive_account_id"],
            set_={
                "folder_tree": folderTreeStmt.excluded.folder_tree,
                "updated_at": datetime.now(timezone.utc),
            }
        )

        db.execute(folderTreeUpsertStmt)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
            
        raise e


def insertOneDriveFiles(db: Session, file_data: list[dict]):
    try:
        fileStmt = insert(OneDriveFile).values(file_data)
        fileUpsertStmt=fileStmt.on_conflict_do_update(
            index_elements=["file_id"],
            set_={
                "file_name": fileStmt.excluded.file_name,
                "file_parents": fileStmt.excluded.file_parents,
                "file_path": fileStmt.excluded.file_path,
                "updated_at": datetime.now(timezone.utc)
            }
        )

        db.execute(fileUpsertStmt)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
                       
        raise e