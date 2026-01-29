"""SAM API Voice Routes - Voice pipeline control, emotion, audio processing."""

from datetime import datetime
from shared_state import get_voice_pipeline


def api_voice_start() -> dict:
    """Start the voice pipeline."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        pipeline.start()
        return {
            "success": True,
            "running": True,
            "config": {
                "emotion_backend": pipeline.config.emotion_backend,
                "response_strategy": pipeline.config.response_strategy,
                "rvc_enabled": pipeline.config.rvc_enabled,
                "enable_backchannels": pipeline.config.enable_backchannels,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_stop() -> dict:
    """Stop the voice pipeline."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        pipeline.stop()
        return {
            "success": True,
            "running": False,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_status() -> dict:
    """Get voice pipeline status and statistics."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        emotion = pipeline.get_current_emotion()
        conversation_state = pipeline.get_conversation_state()
        stats = pipeline.get_stats()

        return {
            "success": True,
            "running": pipeline._running,
            "current_emotion": {
                "primary": emotion.primary_emotion.value if emotion else None,
                "confidence": emotion.confidence if emotion else 0.0,
                "valence": emotion.primary.valence if emotion else 0.0,
                "arousal": emotion.primary.arousal if emotion else 0.5,
            } if emotion else None,
            "conversation": {
                "phase": conversation_state.phase.value,
                "current_speaker": conversation_state.current_speaker.value,
                "turn_count": len(conversation_state.turns),
                "user_emotion": conversation_state.user_emotion,
            },
            "stats": stats,
            "config": {
                "emotion_backend": pipeline.config.emotion_backend,
                "response_strategy": pipeline.config.response_strategy,
                "rvc_enabled": pipeline.config.rvc_enabled,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_emotion() -> dict:
    """Get current detected user emotion."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        emotion = pipeline.get_current_emotion()
        trajectory = pipeline.get_emotional_trajectory()

        if emotion:
            return {
                "success": True,
                "emotion": {
                    "primary": emotion.primary_emotion.value,
                    "secondary": emotion.secondary_emotion.value if emotion.secondary_emotion else None,
                    "confidence": emotion.confidence,
                    "dimensions": {
                        "valence": emotion.primary.valence,
                        "arousal": emotion.primary.arousal,
                        "dominance": emotion.primary.dominance,
                    },
                    "intensity": emotion.intensity.value,
                    "context_string": emotion.to_context_string(),
                },
                "trajectory": trajectory,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": True,
                "emotion": None,
                "trajectory": trajectory,
                "message": "No emotion detected yet",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_config(config_updates: dict = None) -> dict:
    """Get or update voice pipeline configuration."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        if config_updates:
            if "response_strategy" in config_updates:
                pipeline.set_response_strategy(config_updates["response_strategy"])
            if "backchannel_probability" in config_updates:
                pipeline.set_backchannel_probability(config_updates["backchannel_probability"])
            if "rvc_enabled" in config_updates:
                pipeline.enable_rvc(config_updates["rvc_enabled"])
            if "rvc_model" in config_updates:
                pipeline.enable_rvc(True, config_updates["rvc_model"])

        return {
            "success": True,
            "config": {
                "sample_rate": pipeline.config.sample_rate,
                "chunk_size_ms": pipeline.config.chunk_size_ms,
                "emotion_backend": pipeline.config.emotion_backend,
                "emotion_update_interval_ms": pipeline.config.emotion_update_interval_ms,
                "conversation_mode": pipeline.config.conversation_mode,
                "enable_backchannels": pipeline.config.enable_backchannels,
                "backchannel_probability": pipeline.config.backchannel_probability,
                "response_strategy": pipeline.config.response_strategy,
                "prosody_intensity": pipeline.config.prosody_intensity,
                "rvc_enabled": pipeline.config.rvc_enabled,
                "rvc_model": pipeline.config.rvc_model,
                "enable_speculative_generation": pipeline.config.enable_speculative_generation,
                "max_response_tokens": pipeline.config.max_response_tokens,
            },
            "updated": bool(config_updates),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_process_audio(audio_base64: str) -> dict:
    """Process audio chunk through voice pipeline."""
    import base64
    import numpy as np

    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    if not pipeline._running:
        return {"success": False, "error": "Voice pipeline not running. Call /api/voice/start first."}

    try:
        audio_bytes = base64.b64decode(audio_base64)
        audio_chunk = np.frombuffer(audio_bytes, dtype=np.float32)

        events = []
        for event in pipeline.process_audio(audio_chunk):
            event_data = {
                "type": event.type.value,
                "timestamp": event.timestamp,
            }

            if hasattr(event, 'text') and event.text:
                event_data["text"] = event.text
            if hasattr(event, 'audio') and event.audio is not None:
                event_data["audio_base64"] = base64.b64encode(
                    event.audio.astype(np.float32).tobytes()
                ).decode()
            if hasattr(event, 'partial_text'):
                event_data["partial_text"] = event.partial_text
            if hasattr(event, 'turn_end_probability'):
                event_data["turn_end_probability"] = event.turn_end_probability
            if hasattr(event, 'current_emotion'):
                event_data["current_emotion"] = event.current_emotion
            if hasattr(event, 'emotion'):
                event_data["emotion"] = event.emotion
            if hasattr(event, 'new_speaker'):
                event_data["new_speaker"] = event.new_speaker
            if hasattr(event, 'reason'):
                event_data["reason"] = event.reason
            if hasattr(event, 'trigger'):
                event_data["trigger"] = event.trigger

            events.append(event_data)

        return {
            "success": True,
            "events": events,
            "event_count": len(events),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_voice_process_stream(audio_base64: str):
    """Process audio chunk and stream events via SSE."""
    import base64
    import numpy as np
    import json as json_module

    pipeline = get_voice_pipeline()
    if not pipeline:
        yield f'data: {json_module.dumps({"error": "Voice pipeline not available"})}\n\n'
        return

    if not pipeline._running:
        yield f'data: {json_module.dumps({"error": "Voice pipeline not running"})}\n\n'
        return

    try:
        audio_bytes = base64.b64decode(audio_base64)
        audio_chunk = np.frombuffer(audio_bytes, dtype=np.float32)

        for event in pipeline.process_audio(audio_chunk):
            event_data = {
                "type": event.type.value,
                "timestamp": event.timestamp,
            }

            if hasattr(event, 'text') and event.text:
                event_data["text"] = event.text
            if hasattr(event, 'audio') and event.audio is not None:
                event_data["audio_base64"] = base64.b64encode(
                    event.audio.astype(np.float32).tobytes()
                ).decode()
            if hasattr(event, 'partial_text'):
                event_data["partial_text"] = event.partial_text
            if hasattr(event, 'turn_end_probability'):
                event_data["turn_end_probability"] = event.turn_end_probability
            if hasattr(event, 'current_emotion'):
                event_data["current_emotion"] = event.current_emotion

            yield f'data: {json_module.dumps(event_data)}\n\n'

        yield f'data: {json_module.dumps({"done": True})}\n\n'

    except Exception as e:
        yield f'data: {json_module.dumps({"error": str(e)})}\n\n'


def api_voice_conversation_state() -> dict:
    """Get full conversation state."""
    pipeline = get_voice_pipeline()
    if not pipeline:
        return {"success": False, "error": "Voice pipeline not available"}

    try:
        state = pipeline.get_conversation_state()
        timing = state.get_timing_stats()

        return {
            "success": True,
            "state": {
                "phase": state.phase.value,
                "current_speaker": state.current_speaker.value,
                "user_partial_text": state.user_partial_text,
                "user_final_text": state.user_final_text,
                "user_emotion": state.user_emotion,
                "user_arousal": state.user_arousal,
                "user_valence": state.user_valence,
                "sam_response_text": state.sam_response_text,
                "sam_response_emotion": state.sam_response_emotion,
                "recent_backchannels": state.recent_backchannels,
                "backchannel_count": state.backchannel_count,
                "interrupt_count": state.interrupt_count,
            },
            "timing": timing,
            "turns": [
                {
                    "speaker": turn.speaker.value,
                    "text": turn.text[:100] if len(turn.text) > 100 else turn.text,
                    "emotion": turn.emotion,
                    "was_interrupted": turn.was_interrupted,
                    "start_time": turn.start_time,
                    "end_time": turn.end_time,
                }
                for turn in state.turns[-10:]
            ],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Route tables
GET_ROUTES = {
    "/api/voice/start": lambda params: api_voice_start(),
    "/api/voice/stop": lambda params: api_voice_stop(),
    "/api/voice/status": lambda params: api_voice_status(),
    "/api/voice/emotion": lambda params: api_voice_emotion(),
    "/api/voice/config": lambda params: api_voice_config(),
    "/api/voice/conversation": lambda params: api_voice_conversation_state(),
}

POST_ROUTES = {
    "/api/voice/config": lambda data: api_voice_config(data),
    "/api/voice/process": lambda data: api_voice_process_audio(data.get("audio_base64", "")) if data.get("audio_base64") else {"success": False, "error": "Missing audio_base64"},
}

STREAM_POST_ROUTES = {
    "/api/voice/stream": lambda data: api_voice_process_stream(data.get("audio_base64", "")) if data.get("audio_base64") else None,
}
