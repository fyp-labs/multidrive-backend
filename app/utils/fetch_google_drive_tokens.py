from sqlalchemy.future import select
from app.models.google_drive_models.GoogleDriveAccountsModel import GoogleDriveAccount
from app.config.database import SessionLocal
from app.config.encryption import decrypt

async def getGoogleDriveTokens(input: dict):
    """Fetch Google Drive tokens for an activity context."""
    with SessionLocal() as db_session:
        user_id = input.get("user_id")
        google_drive_account_id = input.get("google_drive_account_id")

        query = (
            select(GoogleDriveAccount.access_token, GoogleDriveAccount.refresh_token)
            .where(
                GoogleDriveAccount.user_id == user_id,
                GoogleDriveAccount.id == google_drive_account_id
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
