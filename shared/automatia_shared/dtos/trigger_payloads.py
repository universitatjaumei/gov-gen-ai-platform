from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class TriggerPayloadMeta(BaseModel):
    trigger_id: int
    trigger_type: str  # 'file_watcher' | 'mail_watcher' | 'web_watcher' | 'scheduler'
    timestamp: datetime
    execution_id: str

class FileWatcherPayload(BaseModel):
    meta: TriggerPayloadMeta
    data: Dict[str, Any]  # file_path, file_name, extension, size_bytes, relative_path

class MailWatcherPayload(BaseModel):
    meta: TriggerPayloadMeta
    data: Dict[str, Any]  # sender, subject, body_text, received_at, attachments, primary_attachment

class WebWatcherPayload(BaseModel):
    meta: TriggerPayloadMeta
    data: Dict[str, Any]  # url, change_detected, diff_text, full_text_content, html_snapshot, screenshot_path

class SchedulerPayload(BaseModel):
    meta: TriggerPayloadMeta
    data: Dict[str, Any]  # timestamp, trigger_name, day_of_week, is_scheduled
