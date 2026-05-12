import json
from glob import glob
from pathlib import Path
from typing import Any, Dict
from huggingface_hub import snapshot_download

class RecordedMoves:
    """Load a library of recorded moves from a HuggingFace dataset."""

    def __init__(self, hf_dataset_name: str):
        """Initialize RecordedMoves."""
        self.hf_dataset_name = hf_dataset_name
        self.local_path = snapshot_download(self.hf_dataset_name, repo_type="dataset")
        self.moves: Dict[str, Any] = {}
        self.sounds: Dict[str, Any] = {}

        self.process()

    def process(self) -> None:
        """Populate recorded moves and sounds."""
        move_paths_tmp = glob(f"{self.local_path}/*.json")
        move_paths = [Path(move_path) for move_path in move_paths_tmp]
        for move_path in move_paths:
            move_name = move_path.stem

            move = json.load(open(move_path, "r"))
            self.moves[move_name] = move
        
        sound_paths_tmp = glob(f"{self.local_path}/*.wav")
        sound_paths = [Path(sound_path) for sound_path in sound_paths_tmp]
        for sound_path in sound_paths:
            sound_name = sound_path.stem
            self.sounds[sound_name] = str(sound_path)