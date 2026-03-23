# Class Diagram — esist-semantic-transmitter

The diagram below maps every class, dataclass, exception, and functional module in the
`front-end/` source tree, together with their attributes, methods, and inter-module
relationships.

```mermaid
classDiagram
    direction TB

    %% ─────────────────────────────────────────────
    %% audio_processing module
    %% ─────────────────────────────────────────────
    namespace audio_processing {
        class AudioMetadata {
            <<dataclass>>
            +float original_duration_sec
            +float processed_duration_sec
            +int sample_rate_hz
            +int channels
            +float peak_dbfs
            +float rms_dbfs
            +as_dict() dict
        }

        class AudioPreprocessError {
            <<exception>>
        }

        class audio_processing {
            <<module>>
            +preprocess_audio(raw_audio, target_sample_rate_hz) tuple[bytes, AudioMetadata]
        }
    }

    %% ─────────────────────────────────────────────
    %% stt module
    %% ─────────────────────────────────────────────
    namespace stt {
        class STTError {
            <<exception>>
        }

        class TranscriptionResult {
            <<dataclass>>
            +str text
            +str provider
            +int latency_ms
            +str model
        }

        class stt {
            <<module>>
            +transcribe_with_openai(audio_wav, api_key, model, language_hint, timeout_sec) TranscriptionResult
        }
    }

    %% ─────────────────────────────────────────────
    %% transport module
    %% ─────────────────────────────────────────────
    namespace transport {
        class DeliveryResult {
            <<dataclass>>
            +bool ok
            +str transport
            +int status_code
            +int latency_ms
            +str message
            +dict|str|None response_payload
        }

        class transport {
            <<module>>
            +build_semantic_packet(transcript, semantics, session_id, speaker_label, audio_meta, language_hint) dict
            +send_packet(packet, transport_mode, endpoint, timeout_sec, bearer_token) DeliveryResult
        }
    }

    %% ─────────────────────────────────────────────
    %% semantic module
    %% ─────────────────────────────────────────────
    namespace semantic {
        class semantic {
            <<module>>
            +normalize_transcript(text) str
            +encode_semantics(transcript) dict
        }
    }

    %% ─────────────────────────────────────────────
    %% ui_theme module
    %% ─────────────────────────────────────────────
    namespace ui_theme {
        class ui_theme {
            <<module>>
            +apply_theme() None
            +pipeline_card(title, description, done) str
            +log_item(timestamp, stage, message, status) str
        }
    }

    %% ─────────────────────────────────────────────
    %% app module (Streamlit entry-point)
    %% ─────────────────────────────────────────────
    namespace app {
        class app {
            <<module>>
            +initialize_state() None
            +clear_pipeline_outputs() None
            +add_event(stage, message, status) None
            +register_audio(audio_bytes, source, audio_format) None
            +render_sidebar() dict
            +render_hero(config) None
            +process_and_transcribe(config) None
            +build_packet(config, transcript_text) None
            +show_audio_metrics(audio_meta) None
            +main() None
        }
    }

    %% ─────────────────────────────────────────────
    %% Inheritance
    %% ─────────────────────────────────────────────
    AudioPreprocessError --|> RuntimeError : extends
    STTError --|> RuntimeError : extends

    %% ─────────────────────────────────────────────
    %% Intra-module production relationships
    %% ─────────────────────────────────────────────
    audio_processing ..> AudioMetadata : creates
    audio_processing ..> AudioPreprocessError : raises

    stt ..> TranscriptionResult : creates
    stt ..> STTError : raises

    transport ..> DeliveryResult : creates
    transport ..> AudioMetadata : uses (build_semantic_packet)

    %% ─────────────────────────────────────────────
    %% app → module imports
    %% ─────────────────────────────────────────────
    app --> audio_processing : imports
    app --> stt : imports
    app --> transport : imports
    app --> semantic : imports
    app --> ui_theme : imports

    %% ─────────────────────────────────────────────
    %% app → concrete class usage
    %% ─────────────────────────────────────────────
    app ..> AudioMetadata : show_audio_metrics / process_and_transcribe
    app ..> AudioPreprocessError : catches
    app ..> TranscriptionResult : reads latency_ms / provider
    app ..> STTError : catches
    app ..> DeliveryResult : reads ok / message / latency_ms
```

## Module and class summary

| Location | Symbol | Kind | Responsibility |
|---|---|---|---|
| `transmitter/audio_processing.py` | `AudioMetadata` | dataclass | Stores original + processed duration, sample rate, channels, peak/RMS levels; serialises via `as_dict()` |
| `transmitter/audio_processing.py` | `AudioPreprocessError` | exception | Signals failures during audio normalisation or silence trimming |
| `transmitter/audio_processing.py` | `preprocess_audio()` | function | Converts raw audio bytes → mono 16 kHz WAV, normalises, trims silence; returns `(bytes, AudioMetadata)` |
| `transmitter/stt.py` | `STTError` | exception | Signals transcription failures (missing key, empty response, HTTP error) |
| `transmitter/stt.py` | `TranscriptionResult` | dataclass | Holds transcript text, provider name, latency, and model identifier |
| `transmitter/stt.py` | `transcribe_with_openai()` | function | Sends a WAV buffer to the OpenAI Whisper API; returns `TranscriptionResult` |
| `transmitter/transport.py` | `DeliveryResult` | dataclass | Captures delivery outcome: success flag, transport type, HTTP status, latency, message, and optional receiver response |
| `transmitter/transport.py` | `build_semantic_packet()` | function | Assembles a versioned JSON packet from transcript, semantic encoding, session metadata, and audio profile; appends SHA-256 checksum |
| `transmitter/transport.py` | `send_packet()` | function | Dispatches a semantic packet via Mock demo, HTTP POST, or WebSocket; returns `DeliveryResult` |
| `transmitter/semantic.py` | `normalize_transcript()` | function | Collapses whitespace in transcript text |
| `transmitter/semantic.py` | `encode_semantics()` | function | Extracts language guess, intent, tone, keywords, named entities (numbers/emails/URLs), summary, word count, and character count |
| `transmitter/ui_theme.py` | `apply_theme()` | function | Injects global CSS (Manrope/JetBrains Mono fonts, palette, pipeline cards, log items) into the Streamlit page |
| `transmitter/ui_theme.py` | `pipeline_card()` | function | Renders an HTML pipeline-step card with a ready/waiting status chip |
| `transmitter/ui_theme.py` | `log_item()` | function | Renders an HTML timeline entry with colour-coded status border |
| `app.py` | `initialize_state()` | function | Seeds Streamlit session state with all default values on first run |
| `app.py` | `clear_pipeline_outputs()` | function | Resets processed audio, transcript, semantic payload, packet, and delivery result |
| `app.py` | `add_event()` | function | Appends a timestamped event to the in-session pipeline timeline (capped at 30) |
| `app.py` | `register_audio()` | function | Deduplicates incoming audio via SHA-256 fingerprint and resets downstream state |
| `app.py` | `render_sidebar()` | function | Draws all Streamlit sidebar controls; returns a `config` dict consumed by pipeline steps |
| `app.py` | `render_hero()` | function | Renders the top hero banner with session ID |
| `app.py` | `process_and_transcribe()` | function | Orchestrates `preprocess_audio()` → STT (OpenAI or manual fallback) → stores transcript |
| `app.py` | `build_packet()` | function | Calls `encode_semantics()` then `build_semantic_packet()`; stores results in session state |
| `app.py` | `show_audio_metrics()` | function | Renders four Streamlit metric tiles from an `AudioMetadata` instance |
| `app.py` | `main()` | function | Top-level Streamlit entry point: initialises state, applies theme, renders all UI sections and the pipeline timeline |
