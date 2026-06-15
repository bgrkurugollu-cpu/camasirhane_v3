"""Edge Gateway modülü Pydantic şemaları (bkz. docs/adr/0009-edge-gateway-network).

Edge cihazı bu sözleşmelerle outbound çağrı yapar; admin uçları ise ana
uygulamanın SPA'sı tarafından kullanılır.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Any


# ---------------------------------------------------------------------------
# Edge → Ana uygulama (outbound) sözleşmeleri
# ---------------------------------------------------------------------------

class HardwareItem(BaseModel):
    type: Optional[str] = None       # reader | printer
    model: Optional[str] = None
    transport: Optional[str] = None  # tcp | serial


class EnrollRequest(BaseModel):
    device_uid: str
    name: Optional[str] = None
    location: Optional[str] = None
    public_key: str = Field(..., description="PEM formatında RS256 public key")
    agent_version: Optional[str] = None
    hardware: Optional[List[HardwareItem]] = None


class Reading(BaseModel):
    client_reading_id: str
    rfid_tag: str
    islem_tipi: str = "kirli"
    read_at: Optional[datetime] = None
    reader_name: Optional[str] = None


class IngestRequest(BaseModel):
    readings: List[Reading]


# ---------------------------------------------------------------------------
# Admin (ana uygulama UI) sözleşmeleri
# ---------------------------------------------------------------------------

class EdgeDeviceOut(BaseModel):
    id: int
    device_uid: str
    name: Optional[str] = None
    location: Optional[str] = None
    status: str
    agent_version: Optional[str] = None
    hardware: Optional[Any] = None
    enrolled_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None

    class Config:
        from_attributes = True
