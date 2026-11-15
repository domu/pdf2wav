# PDF in audiolibro

App Streamlit che estrae il testo da uno o più PDF, lo legge con una voce
selezionabile in italiano, francese, inglese o spagnolo e genera un MP3
scaricabile, riproducibile con i comuni player Android. Se carichi più PDF,
il testo viene unito nell'ordine di caricamento e salvato in un unico MP3.

## Avvio su Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

La sintesi usa Microsoft Edge TTS e richiede Internet. Il testo dei PDF viene
inviato al servizio per generare l'audio. I PDF scansionati composti solo da
immagini richiedono OCR, non incluso nell'app.
