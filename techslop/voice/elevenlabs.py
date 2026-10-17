from pathlib import Path

from techslop.voice.base import TTSProvider


class ElevenLabsTTS(TTSProvider):
    def __init__(self, config):
        self.config = config

    async def synthesize_chunk(self, text: str, output_path: Path) -> Path:
        raise PermissionError("ElevenLabs is restricted to the explicitly authorized manual Actions test; automatic generation is disabled")
