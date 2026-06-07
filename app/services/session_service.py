from app.services.dialog_service import complete_active_dialogs


def reset_session(db, user_id: int):
    """
    Завершает все активные диалоги пользователя.
    """
    complete_active_dialogs(db, user_id)