# G1 Cup Approach Solution — восстановительный пакет

Архитектура:

```text
RealSense + YOLO → /perception/cup_pose_map
→ cup_center_then_adaptive_node.py
→ /cmd_vel_raw
→ ros_cmd_vel_udp_exporter.py
→ UDP 127.0.0.1:15000
→ g1_sdk_udp_receiver_fsm801.py
→ Unitree SDK2 / FSM801
→ Unitree G1
```

## Развертывание на роботе

```bash
cd ~
unzip g1_cup_solution_package.zip -d ~/
cd ~/g1_cup_solution_package
./deploy_to_home.sh
~/check_g1_solution_deps.sh
```

Если есть `MISSING` по Python/ROS зависимостям:

```bash
~/install_g1_solution_deps.sh
~/check_g1_solution_deps.sh
```

Модель YOLO должна быть здесь:

```bash
~/g1_robot_delivery_solution_foxy/models/yolo26n.pt
```

## Холодный старт текущего этапа center + adaptive

```bash
~/cold_cleanup_g1_cup.sh
```

Открыть терминалы:

1. `~/start_realsense_g1.sh`
2. `~/start_tf_g1.sh`
3. `~/start_yolo_cup_standalone.sh`
4. `~/g1_raw_udp_exporter_stable.sh`
5. `~/g1_receiver_fsm801_stable.sh`
6. `~/cup_center_then_adaptive_stable.sh`
7. Проверка: `~/preflight_g1_cup.sh`
8. Старт: `~/cup_approach_start.sh`
9. Стоп: `~/cup_approach_stop.sh`

## Критерий успеха

- `/perception/cup_pose_map` публикуется.
- `/cmd_vel_raw`: publisher `cup_center_then_adaptive_node`, subscriber `ros_cmd_vel_udp_exporter`.
- `ss -lunp | grep 15000` показывает python receiver.
- В receiver есть `GetFsmId after: (0, 801)`.
- В движении видны `UDP recv vx=0.300` или `UDP recv wz=...` и `SDK Move sent ...`.

## Голосовой модуль

Отдельный модуль голосового цикла находится в:

```bash
scripts/text_to_speech_module.py
```

Архитектура модуля:

```text
VoskSpeechRecognizer -> OllamaTextAnalyzer -> SpeechSynthesizer
```

Проверка текстового входа без микрофона:

```bash
python3 scripts/text_to_speech_module.py \
  --text "объясни статус робота" \
  --ollama-model llama3.1 \
  --no-play
```

Проверка распознавания из WAV-файла:

```bash
VOSK_MODEL_PATH=/path/to/vosk-model-small-ru \
python3 scripts/text_to_speech_module.py \
  --wav /path/to/input.wav \
  --ollama-model llama3.1
```

Запуск с микрофоном:

```bash
VOSK_MODEL_PATH=/path/to/vosk-model-small-ru \
COSYVOICE_PROMPT_WAV=/path/to/prompt.wav \
python3 scripts/text_to_speech_module.py \
  --trigger "робот" \
  --ollama-model llama3.1
```

По умолчанию TTS пробует использовать локальный `/home/darknight/CosyVoice`
и модель `Fun-CosyVoice3-0.5B`. Для CosyVoice3 нужен `prompt.wav`; если он не
передан, модуль попробует системный TTS через `espeak`/`pyttsx3`.
