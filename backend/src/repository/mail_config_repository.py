"""Mail (SMTP) config repository — a singleton settings row. There is always
at most one row; unlike app_config, no migration seeds a default row here
(there's no sensible default mail server), so `get_config` can return None
until the first save."""

from typing import Optional

from models.base import SessionLocal
from models.mail_config import MailConfigModel


class MailConfigRepository:
    """Repository class for the singleton mail/SMTP config row."""

    def get_config(self) -> Optional[MailConfigModel]:
        with SessionLocal() as session:
            return session.query(MailConfigModel).first()

    def upsert_config(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        sender_name: str,
        sender_email: str,
        use_tls: bool,
        actor_id: Optional[int] = None,
    ) -> MailConfigModel:
        """Update the single row if one exists, otherwise create it."""
        with SessionLocal() as session:
            config = session.query(MailConfigModel).first()
            if config is None:
                config = MailConfigModel(
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    smtp_username=smtp_username,
                    smtp_password=smtp_password,
                    sender_name=sender_name,
                    sender_email=sender_email,
                    use_tls=use_tls,
                    created_by=actor_id,
                )
                session.add(config)
            else:
                config.smtp_host = smtp_host
                config.smtp_port = smtp_port
                config.smtp_username = smtp_username
                config.smtp_password = smtp_password
                config.sender_name = sender_name
                config.sender_email = sender_email
                config.use_tls = use_tls
                config.updated_by = actor_id
            session.commit()
            session.refresh(config)
            return config
