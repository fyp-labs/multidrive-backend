from fastapi import APIRouter, Depends
from app.controllers.one_drive_controllers import FetchOneDriveMetaDataController

router = APIRouter()

@router.get("/metadata/{user_id}/{one_drive_account_id}")
async def startMetaDataFetching(user_id: str, one_drive_account_id: str):
    return await FetchOneDriveMetaDataController.startMetaDataFetching(user_id,one_drive_account_id)
