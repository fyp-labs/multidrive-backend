from app.services.one_drive_services import FetchOneDriveMetaDataService

async def startMetaDataFetching(user_id: str, one_drive_account_id: str):
    return await FetchOneDriveMetaDataService.startMetaDataFetching(user_id,one_drive_account_id)
    