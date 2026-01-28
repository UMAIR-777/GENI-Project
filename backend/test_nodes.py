# Correct way now
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="sk_68036d446bd94d583783e44189d93bc4054381286c851209")


# Example: list voices
voices = client.voices.get_all()
for v in voices:
    print(v.name, v.voice_id)



