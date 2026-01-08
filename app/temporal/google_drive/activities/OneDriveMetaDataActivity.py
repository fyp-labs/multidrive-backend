from temporalio import activity
import asyncio
import uuid
from datetime import datetime
import requests
from functools import partial

from app.config.database import SessionLocal
from app.models.one_drive_models.OneDriveAccountsModel import OneDriveAccount
from app.services.one_drive_services.FetchOneDriveMetaDataService import (
    upsertOneDriveFolders,
    insertOneDriveFiles,
    upsertOneDriveTree,
)
from app.utils.fetch_one_drive_tokens import getOneDriveTokens



@activity.defn
async def fetch_one_drive_metadata(input: dict):
    user_id = input.get("user_id")
    one_drive_account_id = input.get("one_drive_account_id")

    loop = asyncio.get_running_loop()
    activity.heartbeat({"msg": "started"})

    tokens = await getOneDriveTokens({
        "user_id": user_id,
        "one_drive_account_id": one_drive_account_id
    })

    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    def get_root_sync():
        return requests.get("https://graph.microsoft.com/v1.0/me/drive/root", headers=headers).json()

    root = await loop.run_in_executor(None, get_root_sync)
    root_id = root["id"]

    folders = {
        root_id: {
            "id": root_id,
            "user_id": user_id,
            "one_drive_account_id": one_drive_account_id,
            "folder_name": "root",
            "folder_parents": "",
            "folder_path": "root",
            "children": []
        }
    }

    folder_tree = [{
        "id": root_id,
        "text": "My Files",
        "state": {"opened": True},
        "children": folders[root_id]["children"]
    }]

    all_items = []
    endpoint = "https://graph.microsoft.com/v1.0/me/drive/root/delta"

    while endpoint:
        def fetch_page():
            return requests.get(endpoint, headers=headers).json()

        data = await loop.run_in_executor(None, fetch_page)

        all_items.extend(data.get("value", []))
        endpoint = data.get("@odata.nextLink")

        activity.heartbeat({"items": len(all_items)})

    all_items.sort(key=lambda x: x.get("createdDateTime", ""))

    files = []
    pending_folders = {}

    for item in all_items:
        if item["name"] == "root":
            continue

        if "folder" in item:
            pending_folders[item["id"]] = item
        else:
            files.append(item)

    unresolved = dict(pending_folders)

    while unresolved:
        progress = False

        for fid, f in list(unresolved.items()):
            parent = f["parentReference"]["id"]

            if parent not in folders:
                continue

            path = f"{folders[parent]['folder_path']}/{f['name']}"

            folders[fid] = {
                "id": fid,
                "user_id": user_id,
                "one_drive_account_id": one_drive_account_id,
                "folder_name": f["name"],
                "folder_parents": parent,
                "folder_path": path,
                "children": []
            }

            folders[parent]["children"].append({
                "id": fid,
                "text": f["name"],
                "children": folders[fid]["children"]
            })

            del unresolved[fid]
            progress = True

        if not progress:
            break

    flat_folders = []
    folder_map = {}

    for f in folders.values():
        flat = dict(f)
        flat.pop("children", None)
        flat_folders.append(flat)
        folder_map[f["id"]] = f["folder_path"]

    def chunk(arr, size=1000):
        for i in range(0, len(arr), size):
            yield arr[i:i+size]

    for chunk_data in chunk(flat_folders):
        def save_folders():
            with SessionLocal() as db:
                upsertOneDriveFolders(db, chunk_data)

        await loop.run_in_executor(None, save_folders)

    def save_tree():
        with SessionLocal() as db:
            upsertOneDriveTree(db, folder_tree, userParams={
                    "user_id": user_id,
                    "one_drive_account_id": one_drive_account_id
                })

    await loop.run_in_executor(None, save_tree)

    file_rows = []

    for f in files:
        parent = f["parentReference"]["id"]
        folder_path = folder_map.get(parent)

        if not folder_path:
            continue

        created = datetime.fromisoformat(f["createdDateTime"].replace("Z", "+00:00"))

        file_rows.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "one_drive_account_id": one_drive_account_id,
            "file_id": f["id"],
            "file_name": f["name"],
            "file_parents": parent,
            "file_created_time": created,
            "md5Checksum": f.get("file", {}).get("hashes", {}).get("quickXorHash"),
            "mimeType": f.get("file", {}).get("mimeType"),
            "file_size": f.get("size"),
            "file_path": f"{folder_path}/{f['name']}",
            "webViewLink": f.get("webUrl")
        })

    for chunk_data in chunk(file_rows):
        def save_files():
            with SessionLocal() as db:
                insertOneDriveFiles(db, chunk_data)

        await loop.run_in_executor(None, save_files)

    activity.heartbeat({"msg": "completed"})
    return {"folders": len(flat_folders), "files": len(file_rows)}
