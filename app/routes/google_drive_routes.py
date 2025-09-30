from fastapi import APIRouter, Depends
from app.controllers.google_drive_controllers import FetchGoogleDriveMetaDataController

router = APIRouter()

@router.get("/metadata/{user_id}/{google_drive_account_id}")
async def startMetaDataFetching(user_id: str, google_drive_account_id: str):
    return await FetchGoogleDriveMetaDataController.startMetaDataFetching(user_id,google_drive_account_id)

