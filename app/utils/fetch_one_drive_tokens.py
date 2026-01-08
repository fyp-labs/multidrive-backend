from sqlalchemy.future import select
from app.models.one_drive_models.OneDriveAccountsModel import OneDriveAccount
from app.config.database import SessionLocal  

async def getOneDriveTokens(input: dict):
    """Fetch Google Drive tokens for an activity context."""
    with SessionLocal() as db_session:
        user_id = input.get("user_id")
        google_drive_account_id = input.get("one_drive_account_id")

        query = (
            select(OneDriveAccount.access_token, OneDriveAccount.refresh_token)
            .where(
                OneDriveAccount.user_id == user_id,
                OneDriveAccount.id == google_drive_account_id
            )
        )

        result = db_session.execute(query)
        tokens = result.fetchone()

        if tokens:
            access_token, refresh_token = tokens
            return {"access_token": access_token, "refresh_token": refresh_token}

        return None
