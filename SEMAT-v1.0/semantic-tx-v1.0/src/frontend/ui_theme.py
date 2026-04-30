from __future__ import annotations

import streamlit as st
from ai_sound.audio_processing import AudioMetadata

def apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

        :root {
            --bg-soft: #f7f9fc;
            --ink: #10243e;
            --primary: #0f5ab6;
            --primary-soft: #deebff;
            --accent: #ff7f32;
            --good: #098551;
            --warn: #9f5b00;
            --bad: #ad1f2b;
        }

        html, body, [class*="css"] {
            font-family: "Manrope", sans-serif;
        }

        .main .block-container {
            padding-top: 1.3rem;
            padding-bottom: 2rem;
            max-width: 1160px;
        }

        .hero-wrap {
            border-radius: 20px;
            padding: 1.2rem 1.35rem 1.05rem 1.35rem;
            background:
                radial-gradient(circle at 20% 10%, #ffffff 0%, #eef4ff 45%, #dce9ff 100%);
            border: 1px solid #c8daf8;
            margin-bottom: 1rem;
        }

        .hero-title {
            font-size: 1.68rem;
            font-weight: 800;
            color: var(--ink);
            line-height: 1.25;
            margin-bottom: 0.6rem;
        }

        .hero-meta {
            display: flex;
            align-items: center;
            gap: .5rem;
            flex-wrap: wrap;
        }

        .hero-pill {
            display: inline-block;
            background: #0f5ab6;
            color: #ffffff;
            font-size: .72rem;
            text-transform: uppercase;
            letter-spacing: .07em;
            font-weight: 800;
            border-radius: 999px;
            padding: .22rem .58rem;
        }

        .hero-session {
            font-size: .81rem;
            color: #35557d;
            font-weight: 700;
        }

        .pipeline-card {
            border-radius: 14px;
            border: 1px solid #d9e5f7;
            padding: .66rem .72rem .68rem .72rem;
            background: #ffffff;
            min-height: 113px;
        }

        .pipeline-card.done {
            background: linear-gradient(180deg, #f7fff9 0%, #eefbf3 100%);
            border-color: #c8ecd7;
        }

        .pipeline-title {
            font-size: .85rem;
            color: #1d3557;
            font-weight: 700;
            margin-bottom: .18rem;
        }

        .pipeline-desc {
            color: #4c6383;
            font-size: .77rem;
            line-height: 1.35;
            min-height: 2.4em;
        }

        .chip {
            display: inline-block;
            margin-top: .3rem;
            font-size: .7rem;
            border-radius: 999px;
            padding: .16rem .45rem;
            font-weight: 800;
            letter-spacing: .03em;
            text-transform: uppercase;
        }

        .chip.wait {
            color: #5f6b7b;
            background: #edf1f8;
        }

        .chip.ok {
            color: #0d6f45;
            background: #d7f5e5;
        }

        .log-item {
            border-left: 4px solid #bdd0ef;
            padding: .45rem .65rem;
            border-radius: 7px;
            margin-bottom: .45rem;
            background: #f6f9ff;
            color: #2c4467;
            font-size: .84rem;
        }

        .log-item.success { border-left-color: #87d3af; background: #f3fff8; }
        .log-item.error { border-left-color: #df8b8b; background: #fff5f5; }
        .log-item.info { border-left-color: #bdd0ef; background: #f6f9ff; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pipeline_card(title: str, description: str, done: bool) -> str:
    status_text = "ready" if done else "waiting"
    chip_class = "ok" if done else "wait"
    done_class = "done" if done else ""
    return f"""
    <div class="pipeline-card {done_class}">
      <div class="pipeline-title">{title}</div>
      <div class="pipeline-desc">{description}</div>
      <span class="chip {chip_class}">{status_text}</span>
    </div>
    """


def log_item(timestamp: str, stage: str, message: str, status: str) -> str:
    safe_stage = stage.replace("<", "").replace(">", "")
    safe_message = message.replace("<", "").replace(">", "")
    return (
        f'<div class="log-item {status}"><strong>{timestamp}</strong> '
        f'[{safe_stage}] {safe_message}</div>'
    )

def render_hero(config: dict) -> None:
    st.markdown(
        f"""
        <div class="hero-wrap">
            <div class="hero-title">Semantic Audio Communication using Generative AI</div>
            <div class="hero-meta">
                <span class="hero-pill">Transmitter</span>
                <span class="hero-session">Session {config["session_id"]}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def show_audio_metrics(audio_meta: AudioMetadata | None) -> None:
    if not audio_meta:
        return
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Duration", f"{audio_meta.processed_duration_sec:.2f}s")
    col_b.metric("Sample Rate", f"{audio_meta.sample_rate_hz} Hz")
    col_c.metric("Peak Level", f"{audio_meta.peak_dbfs:.1f} dBFS")
    col_d.metric("RMS Level", f"{audio_meta.rms_dbfs:.1f} dBFS")
