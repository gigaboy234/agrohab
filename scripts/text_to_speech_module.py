#!/usr/bin/env python3
"""Голосовой цикл: Vosk STT -> анализ Ollama -> TTS-воспроизведение.

Модуль сделан автономным, чтобы его можно было сначала запускать рядом с
ROS-стеком робота, а позже подключить к ROS-топикам или сервисам.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_COSYVOICE_ROOT = Path(os.getenv("COSYVOICE_ROOT", Path.home() / "CosyVoice"))
DEFAULT_COSYVOICE_MODEL = DEFAULT_COSYVOICE_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


@dataclass
class SpeechRecognizerConfig:
    vosk_model_path: str
    sample_rate: int = 16000
    device: int | None = None
    trigger: str = ""
    listen_seconds: float = 4.0


class VoskSpeechRecognizer:
    """Слой speech-to-text.

    Класс отвечает только за аудиовход и распознавание через Vosk:
    - принимает WAV-файл или поток с микрофона;
    - переводит распознанную речь в обычный текст;
    - удаляет опциональную фразу-триггер, например "робот".

    Класс не вызывает LLM и не генерирует звуковой ответ.
    """

    def __init__(self, config: SpeechRecognizerConfig) -> None:
        self.config = config

    def transcribe_wav(self, wav_path: str) -> str:
        """Распознать речь из mono 16-bit PCM WAV-файла."""
        self._ensure_vosk_model()
        import vosk

        with wave.open(wav_path, "rb") as wav_file:
            if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                raise ValueError("Vosk expects mono 16-bit PCM WAV input.")

            recognizer = vosk.KaldiRecognizer(
                vosk.Model(self.config.vosk_model_path),
                wav_file.getframerate(),
            )
            parts: list[str] = []
            while True:
                chunk = wav_file.readframes(4000)
                if not chunk:
                    break
                if recognizer.AcceptWaveform(chunk):
                    parts.append(self._extract_text(recognizer.Result()))
            parts.append(self._extract_text(recognizer.FinalResult()))
        return self._strip_trigger(" ".join(parts).strip())

    def listen_for_text(self) -> str:
        """Записать короткий отрезок с микрофона и распознать его через Vosk."""
        self._ensure_vosk_model()
        import sounddevice as sd
        import vosk

        audio_queue: queue.Queue[bytes] = queue.Queue()

        def callback(indata: bytes, frames: int, time_info: Any, status: Any) -> None:
            if status:
                print(status, file=sys.stderr)
            audio_queue.put(bytes(indata))

        recognizer = vosk.KaldiRecognizer(
            vosk.Model(self.config.vosk_model_path),
            self.config.sample_rate,
        )
        recognized: list[str] = []
        target_chunks = max(1, int(self.config.listen_seconds * self.config.sample_rate / 4000))

        try:
            with sd.RawInputStream(
                samplerate=self.config.sample_rate,
                blocksize=4000,
                dtype="int16",
                channels=1,
                callback=callback,
                device=self.config.device,
            ):
                for _ in range(target_chunks):
                    try:
                        chunk = audio_queue.get(timeout=self.config.listen_seconds + 2.0)
                    except queue.Empty:
                        print("Microphone timeout, stopping capture.", file=sys.stderr)
                        break
                    if recognizer.AcceptWaveform(chunk):
                        recognized.append(self._extract_text(recognizer.Result()))
        except Exception as exc:
            raise RuntimeError(f"Microphone access failed: {exc}") from exc

        recognized.append(self._extract_text(recognizer.FinalResult()))
        return self._strip_trigger(" ".join(recognized).strip())

    def normalize_text(self, text: str) -> str:
        """Применить ту же очистку триггера к прямому текстовому входу."""
        return self._strip_trigger(text.strip())

    def _ensure_vosk_model(self) -> None:
        if not self.config.vosk_model_path:
            raise RuntimeError("Set --vosk-model or VOSK_MODEL_PATH.")
        if not Path(self.config.vosk_model_path).exists():
            raise FileNotFoundError(f"Vosk model not found: {self.config.vosk_model_path}")

    @staticmethod
    def _extract_text(result_json: str) -> str:
        try:
            return str(json.loads(result_json).get("text", "")).strip()
        except json.JSONDecodeError:
            return ""

    def _strip_trigger(self, text: str) -> str:
        trigger = self.config.trigger.strip().lower()
        if not trigger:
            return text

        lowered = text.lower()
        if lowered.startswith(trigger):
            return text[len(trigger) :].strip(" ,.:;-")
        return text


@dataclass
class TextAnalyzerConfig:
    model: str = "llama3.1"
    url: str = DEFAULT_OLLAMA_URL
    timeout_sec: int = 120
    system_prompt: str = (
        "Ты голосовой модуль робота. Отвечай кратко, по-русски, без markdown. "
        "Если команда относится к роботу, формулируй понятный речевой ответ."
    )


class OllamaTextAnalyzer:
    """Слой анализа текста.

    Класс получает распознанный текст от VoskSpeechRecognizer и отправляет его
    в Ollama. На выходе возвращается короткий ответ на естественном языке,
    который можно передать в синтезатор речи.

    Побочные эффекты управления роботом не стоит добавлять сюда, пока нет
    явного контракта команд со слоем движения или ROS.
    """

    def __init__(self, config: TextAnalyzerConfig) -> None:
        self.config = config

    def analyze(self, text: str) -> str:
        """Отправить пользовательский текст в Ollama и вернуть текст ответа."""
        if not text:
            return "Я не расслышал команду."

        payload = {
            "model": self.config.model,
            "prompt": text,
            "system": self.config.system_prompt,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self.config.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self.config.timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned invalid JSON: {exc}") from exc

        answer = str(result.get("response", "")).strip()
        return answer or "Я получил пустой ответ от языковой модели."


@dataclass
class SpeechSynthesizerConfig:
    cosyvoice_root: Path = DEFAULT_COSYVOICE_ROOT
    cosyvoice_model: Path = DEFAULT_COSYVOICE_MODEL
    prompt_wav: str = ""
    prompt_text: str = "Привет, я голосовой модуль робота."
    output_path: str = ""
    speed: float = 1.0
    play_audio: bool = True


class SpeechSynthesizer:
    """Слой text-to-speech.

    Класс получает ответ от OllamaTextAnalyzer и превращает его в WAV-файл.
    Основной backend - CosyVoice; если он не может запуститься в текущем
    окружении, используется локальный системный TTS.

    Класс возвращает путь к созданному аудиофайлу, чтобы другой код робота мог
    переиспользовать его или позже опубликовать.
    """

    def __init__(self, config: SpeechSynthesizerConfig) -> None:
        self.config = config

    def speak(self, text: str) -> str:
        """Сгенерировать аудио ответа, опционально проиграть его и вернуть путь."""
        output_path = self.config.output_path or self._default_output_path()
        try:
            self._synthesize_with_cosyvoice(text, output_path)
        except Exception as exc:
            print(f"CosyVoice unavailable, falling back to system TTS: {exc}", file=sys.stderr)
            self._synthesize_with_system_tts(text, output_path)

        if self.config.play_audio:
            self._play(output_path)
        return output_path

    def _synthesize_with_cosyvoice(self, text: str, output_path: str) -> None:
        """Использовать локальную установку CosyVoice как основной TTS backend."""
        if not self.config.cosyvoice_root.exists():
            raise FileNotFoundError(f"CosyVoice root not found: {self.config.cosyvoice_root}")
        if not self.config.cosyvoice_model.exists():
            raise FileNotFoundError(f"CosyVoice model not found: {self.config.cosyvoice_model}")
        if not self.config.prompt_wav:
            raise RuntimeError("CosyVoice3 needs --prompt-wav for zero-shot synthesis.")
        if not Path(self.config.prompt_wav).exists():
            raise FileNotFoundError(f"Prompt WAV not found: {self.config.prompt_wav}")

        cosyvoice_root_str = str(self.config.cosyvoice_root)
        matcha_str = str(self.config.cosyvoice_root / "third_party" / "Matcha-TTS")
        if cosyvoice_root_str not in sys.path:
            sys.path.insert(0, cosyvoice_root_str)
        if matcha_str not in sys.path:
            sys.path.insert(0, matcha_str)

        import torchaudio
        from cosyvoice.cli.cosyvoice import AutoModel

        cosyvoice = AutoModel(model_dir=str(self.config.cosyvoice_model))
        generated = cosyvoice.inference_zero_shot(
            text,
            self.config.prompt_text,
            self.config.prompt_wav,
            stream=False,
            speed=self.config.speed,
        )
        for index, chunk in enumerate(generated):
            if index > 0:
                print("CosyVoice returned multiple chunks; saving the first one only.", file=sys.stderr)
                break
            torchaudio.save(output_path, chunk["tts_speech"], cosyvoice.sample_rate)
            return
        raise RuntimeError("CosyVoice returned no audio.")

    def _synthesize_with_system_tts(self, text: str, output_path: str) -> None:
        """Запасной backend для машин без готового окружения CosyVoice."""
        espeak = shutil.which("espeak") or shutil.which("espeak-ng")
        if espeak:
            result = subprocess.run([espeak, "-v", "ru", "-w", output_path, text], capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(f"espeak failed: {result.stderr.decode()}")
            return

        pyttsx3 = self._load_pyttsx3()
        if pyttsx3 is not None:
            engine = pyttsx3.init()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            return

        raise RuntimeError("No TTS backend found. Install CosyVoice deps, espeak, or pyttsx3.")

    @staticmethod
    def _load_pyttsx3() -> Any:
        try:
            import pyttsx3
        except ImportError:
            return None
        return pyttsx3

    @staticmethod
    def _play(path: str) -> None:
        for command in ("aplay", "paplay", "play"):
            player = shutil.which(command)
            if player:
                subprocess.run([player, path], check=False)
                return
        print(f"WARNING: No audio player found (tried aplay, paplay, play). Audio saved to {path}", file=sys.stderr)

    @staticmethod
    def _default_output_path() -> str:
        return str(Path(tempfile.gettempdir()) / "agrohab_voice_answer.wav")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agrohab text-to-speech voice loop.")
    parser.add_argument("--text", help="Use text as the trigger input instead of microphone audio.")
    parser.add_argument("--wav", help="Recognize speech from a mono 16-bit PCM WAV file.")
    parser.add_argument("--trigger", default=os.getenv("VOICE_TRIGGER", ""), help="Optional wake phrase to strip.")
    parser.add_argument("--vosk-model", default=os.getenv("VOSK_MODEL_PATH", ""), help="Path to Vosk model.")
    parser.add_argument("--sample-rate", type=int, default=16000, help="Microphone sample rate for Vosk.")
    parser.add_argument("--listen-seconds", type=float, default=4.0, help="Microphone listening window.")
    parser.add_argument("--device", type=int, default=None, help="sounddevice input device index.")
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", "llama3.1"))
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL))
    parser.add_argument("--cosyvoice-root", type=Path, default=DEFAULT_COSYVOICE_ROOT)
    parser.add_argument("--cosyvoice-model", type=Path, default=DEFAULT_COSYVOICE_MODEL)
    parser.add_argument("--prompt-wav", default=os.getenv("COSYVOICE_PROMPT_WAV", ""))
    parser.add_argument("--prompt-text", default=os.getenv("COSYVOICE_PROMPT_TEXT", "Привет, я голосовой модуль робота."))
    parser.add_argument("--output", default="", help="Where to save generated answer WAV.")
    parser.add_argument("--no-play", action="store_true", help="Save speech audio without playing it.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    def _shutdown(signum: int, frame: Any) -> None:
        print(f"\nReceived signal {signum}, shutting down.", file=sys.stderr)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    recognizer = VoskSpeechRecognizer(
        SpeechRecognizerConfig(
            vosk_model_path=args.vosk_model,
            sample_rate=args.sample_rate,
            device=args.device,
            trigger=args.trigger,
            listen_seconds=args.listen_seconds,
        )
    )
    analyzer = OllamaTextAnalyzer(TextAnalyzerConfig(model=args.ollama_model, url=args.ollama_url))
    synthesizer = SpeechSynthesizer(
        SpeechSynthesizerConfig(
            cosyvoice_root=args.cosyvoice_root,
            cosyvoice_model=args.cosyvoice_model,
            prompt_wav=args.prompt_wav,
            prompt_text=args.prompt_text,
            output_path=args.output,
            play_audio=not args.no_play,
        )
    )

    try:
        if args.text:
            user_text = recognizer.normalize_text(args.text)
        elif args.wav:
            user_text = recognizer.transcribe_wav(args.wav)
        else:
            user_text = recognizer.listen_for_text()
    except Exception as exc:
        print(f"Speech recognition failed: {exc}", file=sys.stderr)
        return 1

    print(f"Recognized: {user_text}")

    try:
        answer = analyzer.analyze(user_text)
    except Exception as exc:
        print(f"Text analysis failed: {exc}", file=sys.stderr)
        return 1

    print(f"Answer: {answer}")

    try:
        output_path = synthesizer.speak(answer)
    except Exception as exc:
        print(f"Speech synthesis failed: {exc}", file=sys.stderr)
        return 1

    print(f"Audio: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
