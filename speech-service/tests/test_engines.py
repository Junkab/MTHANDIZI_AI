import threading
import time

from app import engines


def test_asr_inference_is_serialized(monkeypatch):
    active_calls = 0
    max_active_calls = 0
    count_lock = threading.Lock()

    class FakeAsr:
        def transcribe_array(self, samples, audio_seconds):
            nonlocal active_calls, max_active_calls
            with count_lock:
                active_calls += 1
                max_active_calls = max(max_active_calls, active_calls)
            time.sleep(0.02)
            with count_lock:
                active_calls -= 1

    monkeypatch.setattr(engines, "get_asr", lambda: FakeAsr())
    workers = [
        threading.Thread(target=engines.transcribe_array, args=([], 1.0))
        for _ in range(4)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert max_active_calls == 1


def test_startup_warms_all_fixed_kiosk_prompts(monkeypatch):
    calls = []

    class FakeTts:
        def speak(self, text):
            calls.append(text)
            return type("Speech", (), {"source": "cache"})()

    monkeypatch.setattr(engines, "get_tts", lambda: FakeTts())
    monkeypatch.setattr(engines, "_tts_prompts_warmed", False)

    engines.warm_up_tts_prompts()

    assert calls == list(engines.KIOSK_PROMPTS)
    assert engines.tts_prompts_warmed() is True