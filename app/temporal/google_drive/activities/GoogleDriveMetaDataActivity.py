# activities.py
from temporalio import activity
from app.config.google_client import build_drive_service
import uuid
from datetime import datetime, timezone
from googleapiclient.errors import HttpError
from app.config.database import SessionLocal
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from app.models.google_drive_models.GoogleDriveAccountsModel import GoogleDriveAccount
from app.models.google_drive_models.GoogleDriveFolderModel import GoogleDriveFolder
from app.models.google_drive_models.GoogleDriveFolderTreeModel import GoogleDriveFolderTree
from app.models.google_drive_models.GoogleDriveFileModel import GoogleDriveFile
from app.utils.fetch_google_drive_tokens import getGoogleDriveTokens
from app.services.google_drive_services.FetchGoogleDriveMetaDataService import insertFolderAndTree,insertFiles

@activity.defn
async def fetch_drive_folders(input:dict):

    userId = input.get("user_id")
    googleDriveAccountId = input.get("google_drive_account_id")

    tokens=await getGoogleDriveTokens({"user_id":userId,"google_drive_account_id":googleDriveAccountId})

    parent_id="root"
    service = build_drive_service(
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token")
    )
    
    root = service.files().get(fileId='root', fields='id,name').execute()
    folders = {}
    folder_tree = []

    folders[root['id']] = {
        'id': root['id'],
        'user_id': userId,
        'google_drive_account_id': googleDriveAccountId,
        'folder_name': 'My Drive',
        'folder_parents': '',
        'folder_path': 'My Drive',
        'children': []
    }

    folder_tree.append({
        "id": root['id'],
        "text": "My Drive",
        "state": {"opened": True},
        "children": folders[root['id']]['children']
    })

    page_token = None
    while True:
        query = "'me' in owners and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, parents, mimeType, createdTime)",
            orderBy="createdTime",
            pageToken=page_token,
            pageSize=1000
        ).execute()

        for folder in response.get("files", []):
            parents = folder.get("parents", [])
            if not parents:
                continue

            parent_id = parents[0]
            if parent_id not in folders:
                continue  # Skip folders outside "My Drive"

            folder_id = folder["id"]
            folder_name = folder["name"]
            folder_path = f"{folders[parent_id]['folder_path']}/{folder_name.strip()}"

            folders[folder_id] = {
                'id': folder_id,
                'user_id': userId,
                'google_drive_account_id': googleDriveAccountId,
                'folder_name': folder_name,
                'folder_parents': parent_id,
                'folder_path': folder_path,
                'children': []
            }

            folders[parent_id]['children'].append({
                "id": folder_id,
                "text": folder_name,
                "state": {"opened": False},
                "children": folders[folder_id]['children']
            })
        
        activity.heartbeat({"page_token": page_token, "folders_so_far": len(folders)})

        page_token = response.get("nextPageToken", None)
        if not page_token:
            break

    flatFoldersList = []
    for f in folders.values():
        data = dict(f)
        data.pop("children", None)
        flatFoldersList.append(data)

    with SessionLocal() as db:
        insertFolderAndTree(db=db,folders=flatFoldersList,folder_tree=folder_tree,userParams= {"user_id" : userId,"google_drive_account_id" : googleDriveAccountId})

    return folders

@activity.defn
async def get_all_files_from_folders(input: dict):
    folders = input.get("folders", {})
    user_id = input.get("user_id")
    google_drive_account_id = input.get("google_drive_account_id")
    page_token = None
    file_data = []

    tokens = await getGoogleDriveTokens({
        "user_id": user_id,
        "google_drive_account_id": google_drive_account_id
    })

    service = build_drive_service(
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token")
    )

    try:

        while True:
            response = service.files().list(
                q = "'me' in owners and mimeType!='application/vnd.google-apps.folder' and trashed=false",
                fields="nextPageToken, files(id, name, parents, mimeType, createdTime, md5Checksum, size, viewedByMeTime, webViewLink, thumbnailLink)",
                orderBy="createdTime",
                pageToken=page_token,
                pageSize=1000
            ).execute()

            for file in response.get("files", []):
                parents = file.get("parents", [])
                if not parents:
                    continue
                parentId = parents[0]
                folder_info = folders.get(parentId)
                if not folder_info:
                    continue

                created_time = file.get("createdTime")
                viewed_time = file.get("viewedByMeTime")

                file_data.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "google_drive_account_id": google_drive_account_id,
                    "file_id": file["id"],
                    "file_name": file["name"],
                    "file_parents": parentId,
                    "file_created_time": datetime.strptime(created_time, "%Y-%m-%dT%H:%M:%S.%fZ"),
                    "md5Checksum": file.get("md5Checksum"),
                    "mime_type": file["mimeType"],
                    "file_size": file.get("size"),
                    "viewed_by_me_time": datetime.strptime(viewed_time, "%Y-%m-%dT%H:%M:%S.%fZ"),
                    "file_path": f"{folder_info['folder_path']}/{file['name']}",
                    "web_view_link": file.get("webViewLink"),
                    "thumbnail_link": file.get("thumbnailLink")
                })
            
            activity.heartbeat({"page_token": page_token, "files_so_far": len(file_data)})

            page_token = response.get("nextPageToken")
            if not page_token:
                break
        if file_data:
                with SessionLocal() as db:
                    insertFiles(db,file_data)

    except HttpError as e:
        print(f"An error occurred: {e}")

    