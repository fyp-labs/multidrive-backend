from app.services.google_drive_services import FetchGoogleDriveMetaDataService

async def startMetaDataFetching(user_id: str, google_drive_account_id: str):
    return await FetchGoogleDriveMetaDataService.startMetaDataFetching(user_id,google_drive_account_id)
    