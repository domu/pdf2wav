import asyncio
import re
import tempfile
from io import BytesIO
from pathlib import Path

import aiohttp
import edge_tts
import streamlit as st
from pypdf import PdfReader
from pypdf.errors import PdfReadError


LANGUAGES = {
    "Italiano": [
        ("Voce femminile", "it-IT-ElsaNeural"),
        ("Voce maschile", "it-IT-DiegoNeural"),
    ],
    "Francese": [
        ("Voce femminile", "fr-FR-DeniseNeural"),
        ("Voce maschile", "fr-FR-HenriNeural"),
    ],
    "Inglese": [
        ("Voce femminile", "en-US-AriaNeural"),
        ("Voce maschile", "en-US-GuyNeural"),
    ],
    "Spagnolo": [
        ("Voce femminile", "es-ES-ElviraNeural"),
        ("Voce maschile", "es-ES-AlvaroNeural"),
    ],
}


def extract_pdf_text(uploaded_file):
    reader = PdfReader(BytesIO(uploaded_file.getvalue()), strict=False)
    if reader.is_encrypted:
        raise PdfReadError("il PDF è protetto da password.")

    page_texts = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(page_text.strip() for page_text in page_texts if page_text.strip())
    empty_pages = sum(not page_text.strip() for page_text in page_texts)
    return text, empty_pages


def create_mp3(text: str, voice: str) -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "audiolibro.mp3"
        asyncio.run(edge_tts.Communicate(text, voice).save(str(output_path)))
        return output_path.read_bytes()


def reset_voice_selection():
    st.session_state.pop("voice_selection", None)


st.set_page_config(page_title="PDF in audiolibro", page_icon=":material/headphones:")
st.title("PDF in audiolibro")
st.write(
    "Carica uno o più PDF, scegli la lingua e la voce, quindi crea un file MP3 "
    "ascoltabile e scaricabile."
)
st.info(
    "La sintesi vocale richiede una connessione Internet: il testo estratto dai PDF "
    "viene inviato al servizio Microsoft Edge TTS. I PDF scansionati senza testo "
    "selezionabile non possono essere convertiti (OCR non incluso).",
    title="Nota su privacy e PDF scansionati",
)

language = st.selectbox(
    "Lingua della lettura",
    list(LANGUAGES),
    key="language",
    on_change=reset_voice_selection,
)
voice_label, voice_id = st.selectbox(
    "Tipo di voce",
    LANGUAGES[language],
    format_func=lambda option: option[0],
    key="voice_selection",
)
uploaded_files = st.file_uploader(
    "Seleziona uno o più file PDF",
    type=["pdf"],
    accept_multiple_files=True,
)

if st.button(
    "Crea audiolibro MP3",
    type="primary",
    disabled=not uploaded_files,
):
    st.session_state.pop("audio_result", None)
    document_texts = []
    extraction_errors = []
    unreadable_pages = []

    with st.spinner("Leggo i PDF..."):
        for uploaded_file in uploaded_files:
            try:
                text, empty_pages = extract_pdf_text(uploaded_file)
            except (PdfReadError, ValueError, OSError) as error:
                extraction_errors.append(f"{uploaded_file.name}: {error}")
                continue

            if not text:
                extraction_errors.append(
                    f"{uploaded_file.name}: non contiene testo estraibile."
                )
                continue

            document_texts.append(text)
            if empty_pages:
                unreadable_pages.append(
                    f"{uploaded_file.name}: {empty_pages} pagina/e senza testo estraibile"
                )

    if extraction_errors:
        st.error(
            "Non ho creato l'audiolibro perché non è stato possibile leggere "
            "correttamente ogni PDF:\n\n" + "\n\n".join(extraction_errors),
            title="Controlla i file caricati",
        )
    elif document_texts:
        if unreadable_pages:
            st.warning(
                "Alcune pagine potrebbero essere immagini e non verranno lette: "
                + "; ".join(unreadable_pages)
            )

        audio_bytes = None
        try:
            with st.spinner("Genero l'audiolibro..."):
                audio_bytes = create_mp3("\n\n".join(document_texts), voice_id)
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            OSError,
            edge_tts.exceptions.EdgeTTSException,
        ) as error:
            st.error(f"Generazione audio non riuscita: {error}")

        if audio_bytes is not None:
            if not audio_bytes:
                st.error("Il servizio di sintesi non ha restituito audio.")
            else:
                first_name = Path(uploaded_files[0].name).stem
                safe_name = re.sub(
                    r"[^\w-]+", "_", first_name, flags=re.UNICODE
                ).strip("_")
                output_name = (
                    f"{safe_name or 'audiolibro'}_audiolibro.mp3"
                    if len(uploaded_files) == 1
                    else "documenti_audiolibro.mp3"
                )
                st.session_state["audio_result"] = {
                    "bytes": audio_bytes,
                    "name": output_name,
                    "language": language,
                    "voice": voice_label,
                }

result = st.session_state.get("audio_result")
if result:
    st.success(
        f"Audiolibro pronto — {result['language']}, {result['voice']}. "
        "Il file MP3 può essere copiato sul tuo dispositivo Android."
    )
    st.audio(result["bytes"], format="audio/mpeg", alt="Anteprima dell'audiolibro")
    st.download_button(
        "Scarica MP3",
        data=result["bytes"],
        file_name=result["name"],
        mime="audio/mpeg",
        width="stretch",
    )
