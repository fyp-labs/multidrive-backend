from sqlalchemy.future import select
from app.models.one_drive_models.OneDriveAccountsModel import OneDriveAccount
from app.config.database import SessionLocal
from app.config.encryption import decrypt

async def getOneDriveTokens(input: dict):
    """Fetch OneDrive tokens for an activity context."""
    with SessionLocal() as db_session:
        user_id = input.get("user_id")
        one_drive_account_id = input.get("one_drive_account_id")

        query = (
            select(OneDriveAccount.access_token, OneDriveAccount.refresh_token)
            .where(
                OneDriveAccount.user_id == user_id,
                OneDriveAccount.id == one_drive_account_id
            )
        )

        result = db_session.execute(query)
        tokens = result.fetchone()

        if tokens:
            access_token, refresh_token = tokens
            return {
                "access_token": decrypt(access_token),
                "refresh_token": decrypt(refresh_token),
            }

        return None
