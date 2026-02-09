"""
Cleanup Service - автоматическое удаление старых файлов

Удаляет документы и файлы, которые старше FILE_RETENTION_DAYS дней.
"""
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.document import Document

logger = logging.getLogger(__name__)


def cleanup_old_files():
    """
    Удаляет документы и связанные файлы старше FILE_RETENTION_DAYS дней.
    """
    db: Session = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=settings.FILE_RETENTION_DAYS)
        
        # Получаем все документы старше cutoff_date
        old_documents = db.query(Document).filter(
            Document.uploaded_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for doc in old_documents:
            try:
                # Удаляем физический файл
                if doc.file_path and os.path.exists(doc.file_path):
                    os.remove(doc.file_path)
                    logger.info(f"Deleted file: {doc.file_path}")
                
                # Удаляем запись из БД
                db.delete(doc)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Error deleting document {doc.id}: {e}")
                continue
        
        db.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleanup completed: {deleted_count} old documents deleted")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Cleanup service error: {e}")
        db.rollback()
        return 0
    finally:
        db.close()
