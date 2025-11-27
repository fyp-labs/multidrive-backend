# activities.py
from temporalio import activity
from app.config.google_client import build_drive_service
import uuid
import asyncio
from datetime import datetime, timezone
from googleapiclient.errors import HttpError
from app.config.database import SessionLocal
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from functools import partial
from app.models.google_drive_models.GoogleDriveAccountsModel import GoogleDriveAccount
from app.models.google_drive_models.GoogleDriveFolderModel import GoogleDriveFolder
from app.models.google_drive_models.GoogleDriveFolderTreeModel import GoogleDriveFolderTree
from app.models.google_drive_models.GoogleDriveFileModel import GoogleDriveFile
from app.utils.fetch_google_drive_tokens import getGoogleDriveTokens
from app.services.google_drive_services.FetchGoogleDriveMetaDataService import upsertGoogleDriveFolders,upsertGoogleDriveTree,insertFiles


@activity.defn
async def fetch_drive_folders(input: dict):
    userId = input.get("user_id")
    googleDriveAccountId = input.get("google_drive_account_id")
    
    loop = asyncio.get_running_loop()

    activity.heartbeat({"msg": "activity started"})

    tokens = await getGoogleDriveTokens({
        "user_id": userId,
        "google_drive_account_id": googleDriveAccountId
    })

    service = build_drive_service(
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token")
    )

    def get_root_sync():
        return service.files().get(
            fileId="root",
            fields="id,name"
        ).execute()

    root = await loop.run_in_executor(None, get_root_sync)

    folders = {}
    folder_tree = []

    folders[root["id"]] = {
        "id": root["id"],
        "user_id": userId,
        "google_drive_account_id": googleDriveAccountId,
        "folder_name": "My Drive",
        "folder_parents": "",
        "folder_path": "My Drive",
        "children": []
    }

    folder_tree.append({
        "id": root["id"],
        "text": "My Drive",
        "state": {"opened": True},
        "children": folders[root["id"]]["children"]
    })

    rawFolders = {}
    page_token = None

    activity.heartbeat({"msg": "starting folder listing"})

    while True:
        params = {
            "q": "'me' in owners and mimeType='application/vnd.google-apps.folder' and trashed=false",
            "fields": "nextPageToken, files(id,name,parents)",
            "orderBy": "createdTime",
            "pageSize": 1000,
            "pageToken": page_token
        }

        list_req = service.files().list(**params)
        response = await loop.run_in_executor(None, list_req.execute)

        for f in response.get("files", []):
            rawFolders[f["id"]] = {
                "id": f["id"],
                "name": f["name"],
                "parents": f.get("parents", [])
            }

        page_token = response.get("nextPageToken")

        activity.heartbeat({
            "msg": "listing pages",
            "received": len(rawFolders),
            "page_token": page_token
        })

        if not page_token:
            break

    activity.heartbeat({
        "msg": "completed listing",
        "total_raw": len(rawFolders)
    })

    
    pending = dict(rawFolders)

    activity.heartbeat({
        "msg": "starting tree resolution",
        "pending": len(pending)
    })

    loop_counter = 0

    while pending:
        progress = False
        
        await asyncio.sleep(0) 

        for folder_id, folder in list(pending.items()):
            parents = folder["parents"]

            if not parents:
                del pending[folder_id]
                continue

            parent_id = parents[0]

            if parent_id not in folders:
                continue

            folder_name = folder["name"]
            folder_path = f"{folders[parent_id]['folder_path']}/{folder_name}"

            folders[folder_id] = {
                "id": folder_id,
                "user_id": userId,
                "google_drive_account_id": googleDriveAccountId,
                "folder_name": folder_name,
                "folder_parents": parent_id,
                "folder_path": folder_path,
                "children": []
            }

            folders[parent_id]["children"].append({
                "id": folder_id,
                "text": folder_name,
                "children": folders[folder_id]["children"]
            })

            del pending[folder_id]
            progress = True

        loop_counter += 1

        activity.heartbeat({
            "msg": "resolving tree",
            "loop": loop_counter,
            "pending": len(pending)
        })

        if not progress:
            break

    activity.heartbeat({
        "msg": "tree resolution completed",
        "total_folders": len(folders)
    })

    files_to_fetch_from_folders={}
    flat_folders = []

    for item in folders.values():
        f = dict(item)
        f.pop("children", None)
        files_to_fetch_from_folders[f.get("id")]=f
        flat_folders.append(f)

    def chunk(arr, n):
        for i in range(0, len(arr), n):
            yield arr[i:i+n]

    chunks = list(chunk(flat_folders, 1000))

    def upsert_folders_sync(chunk_data):
        with SessionLocal() as db:
            upsertGoogleDriveFolders(
                db=db,
                folders=chunk_data,
                userParams={
                    "user_id": userId,
                    "google_drive_account_id": googleDriveAccountId
                }
            )

    for i, c in enumerate(chunks):
        activity.heartbeat({
            "msg": "db upsert",
            "chunk": i + 1,
            "chunk_size": len(c),
            "remaining_chunks": len(chunks) - (i + 1)
        })
        
        await loop.run_in_executor(None, partial(upsert_folders_sync, c))


    def upsert_tree_sync(tree_data):
        with SessionLocal() as db:
            upsertGoogleDriveTree(
                db=db,
                folder_tree=tree_data,
                userParams={
                    "user_id": userId,
                    "google_drive_account_id": googleDriveAccountId
                }
            )

    activity.heartbeat({"msg": "db: writing folder_tree"})
    
    await loop.run_in_executor(None, partial(upsert_tree_sync, folder_tree))

    activity.heartbeat({"msg": "db completed"})

    
    return len(files_to_fetch_from_folders)

@activity.defn
async def get_all_files_from_folders(input: dict):
    activity.heartbeat({"step": "init"})
    
    user_id = input.get("user_id")
    google_drive_account_id = input.get("google_drive_account_id")
    page_token = None
    file_data = []

    loop = asyncio.get_running_loop()

    def get_folders_sync():
        with SessionLocal() as db:
            return db.query(
                GoogleDriveFolder.id,
                GoogleDriveFolder.folder_path
            ).filter(
                GoogleDriveFolder.user_id == user_id,
                GoogleDriveFolder.google_drive_account_id == google_drive_account_id
            ).all()

    folders = await loop.run_in_executor(None, get_folders_sync)
    folder_map = {f.id: f.folder_path for f in folders}

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
            list_request = service.files().list(
                q="'me' in owners and mimeType!='application/vnd.google-apps.folder' and trashed=false",
                fields="nextPageToken, files(id, name, parents, mimeType, createdTime, md5Checksum, size, viewedByMeTime, webViewLink, thumbnailLink)",
                orderBy="createdTime",
                pageToken=page_token,
                pageSize=1000
            )
            
            response = await loop.run_in_executor(None, list_request.execute)

            for file in response.get("files", []):
                parents = file.get("parents", [])
                if not parents: continue

                parentId = parents[0]
                folder_path = folder_map.get(parentId)
                if not folder_path: continue

                created_time = file.get("createdTime")
                viewed_time = file.get("viewedByMeTime")

                c_time_obj = datetime.strptime(created_time, "%Y-%m-%dT%H:%M:%S.%fZ") if created_time else None
                v_time_obj = datetime.strptime(viewed_time, "%Y-%m-%dT%H:%M:%S.%fZ") if viewed_time else None

                file_data.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "google_drive_account_id": google_drive_account_id,
                    "file_id": file["id"],
                    "file_name": file["name"],
                    "file_parents": parentId,
                    "file_created_time": c_time_obj,
                    "md5Checksum": file.get("md5Checksum"),
                    "mime_type": file["mimeType"],
                    "file_size": file.get("size"),
                    "viewed_by_me_time": v_time_obj,
                    "file_path": f"{folder_path}/{file['name']}",
                    "web_view_link": file.get("webViewLink"),
                    "thumbnail_link": file.get("thumbnailLink")
                })
            
            activity.heartbeat({"page_token": page_token, "count": len(file_data)})
            
            page_token = response.get("nextPageToken")
            
            if file_data:
                def save_db_sync(data):
                    with SessionLocal() as db:
                        insertFiles(db, data)
                
                await loop.run_in_executor(None, partial(save_db_sync, file_data))
                
                file_data = []

            if not page_token:
                break

    except HttpError as e:
        print(f"An error occurred: {e}")
        raise e 

    return {"message": "All Done"}