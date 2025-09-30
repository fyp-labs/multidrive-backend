# activities.py
from temporalio import activity
from app.config.google_client import build_drive_service
import uuid
from datetime import datetime, timezone
from googleapiclient.errors import HttpError
from app.config.database import SessionLocal
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from app.models.google_drive_models.GoogleDriveFolderModel import GoogleDriveFolder
from app.models.google_drive_models.GoogleDriveFolderTreeModel import GoogleDriveFolderTree
from app.models.google_drive_models.GoogleDriveFileModel import GoogleDriveFile

@activity.defn
async def fetch_drive_folders_recursive(input:dict):

    userId = input.get("user_id")
    googleDriveAccountId = input.get("google_drive_account_id")

    parent_id="root"
    service = build_drive_service(
        access_token="ya29.a0AQQ.......................",
        refresh_token="1//0..................."
    )
    
    folders = []
    folder_tree = {
        "id": parent_id,
        "text": "My Drive",
        "state": {"opened": True},
        "children": []
    }

    def _walk(pid, path, node):
        page_token = None
        rootFolderId = None

        while True:
            results = service.files().list(
                q=f"'{pid}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="nextPageToken, files(id, name, parents)",
                pageToken=page_token,
            ).execute()

            for f in results.get("files", []):
           
                if "parents" in f:
                    rootFolderId = f["parents"][0]

                folderPath = f"{path}/{f['name'].strip()}"
                folders.append({
                    "id": f["id"],
                    "user_id": userId,
                    "google_drive_account_id": googleDriveAccountId,
                    "folder_name": f["name"],
                    "folder_parents": f.get("parents", [""])[0],
                    "folder_path": folderPath,
                })

                child_node = {
                    "id": f["id"],
                    "text": f["name"],
                    "state": {"opened": False},
                    "children": []
                }
                node["children"].append(child_node)

               
                _walk(f["id"], folderPath, child_node)

        
            page_token = results.get("nextPageToken", None)
            if not page_token:
                break

        return rootFolderId

   
    rootFolderId = _walk(parent_id, "My Drive", folder_tree)

    folder_tree["id"]=rootFolderId
    folders.append({
        "id": rootFolderId,
        "user_id" : userId,
        "google_drive_account_id" : googleDriveAccountId,
        "folder_name": "My Drive",
        "folder_parents": "",
        "folder_path": "My Drive",
    })

    with SessionLocal() as db:
        try:
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

            db.execute(upsertFolderStmt)
            db.execute(folderTreeUpsertStmt)
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            
            raise e
        

    return folders

@activity.defn
async def get_all_files_from_folders( input:dict):
    parent_id = input.get("parent_id", "root")
    folder_path = input.get("folder_path", "")
    user_id = input.get("user_id")
    google_drive_account_id = input.get("google_drive_account_id")
    page_token = None
    file_data = []
    service = build_drive_service(
        access_token="ya29.a0AQQ.......................",
        refresh_token="1//0..................."
    )

    try:
        while True:
            params = {
                "q": f"'{parent_id}' in parents and trashed = false",
                "fields": "nextPageToken, files(id, name, parents, createdTime, md5Checksum, mimeType, size, viewedByMeTime, webViewLink,thumbnailLink)",
                "pageToken": page_token,
                "pageSize": 1000  
            }

            response = service.files().list(**params).execute()

            for file in response.get("files", []):
                if file.get("mimeType") == "application/vnd.google-apps.folder":
                    continue 

                file_data.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "google_drive_account_id": google_drive_account_id,
                    "file_id": file["id"],
                    "file_name": file["name"],
                    "file_parents": file["parents"][0] if "parents" in file else None,
                    "file_created_time": datetime.strptime(file["createdTime"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "md5Checksum": file.get("md5Checksum"),
                    "mime_type": file["mimeType"],
                    "file_size": file.get("size"),
                    "viewed_by_me_time": datetime.strptime(file["viewedByMeTime"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S") if "viewedByMeTime" in file else None,
                    "file_path": f"{folder_path}/{file['name']}",
                    "web_view_link": file.get("webViewLink"),
                    "thumbnail_link": file.get("thumbnailLink")
                })

            if file_data:
                with SessionLocal() as db:
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
                       
                        raise e

            page_token = response.get("nextPageToken", None)
            if page_token is None:
                break

    except HttpError as e:
        print(f"An error occurred: {e}")

    return file_data