# File: graph_states.py

from typing_extensions import TypedDict
from typing import Optional

class VoiceCallState(TypedDict, total=False):
    phone: str
    lead_id: str
    call_sid: str           # ✅ add this
    lead_name: Optional[str]
    current_node: Optional[str]
    is_paused: bool
    waiting_for: Optional[str]
    last_spoken: Optional[str]
    audio_file: Optional[str]
    score: Optional[int]
    qualified: Optional[bool]


