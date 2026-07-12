import assemblyai as aai
from app.core.config import settings

# AssemblyAI setup
aai.settings.api_key = settings.ASSEMBLYAI_API_KEY


class RealtimeTranscriber:
    """
    AssemblyAI Real-time Transcriber wrapper
    Doctor bole → chunks frontend se aayenge → text return karega
    """

    def __init__(self, on_text_callback, on_final_callback, on_error_callback):
        """
        on_text_callback   → partial text milne pe call hoga (live preview)
        on_final_callback  → final confirmed text (save ke liye)
        on_error_callback  → error pe call hoga
        """
        self.on_text    = on_text_callback
        self.on_final   = on_final_callback
        self.on_error   = on_error_callback
        self.transcriber = None
        self.full_text   = []  # sab final texts yahan store honge


    def start(self):
        """AssemblyAI se connection start karo"""

        def on_open(session_opened: aai.RealtimeSessionOpened):
            print(f"AssemblyAI session opened: {session_opened.session_id}")

        def on_data(transcript: aai.RealtimeTranscript):
            if not transcript.text:
                return

            if isinstance(transcript, aai.RealtimeFinalTranscript):
                # Final text — confident hai AssemblyAI
                self.full_text.append(transcript.text)
                self.on_final(transcript.text)

            elif isinstance(transcript, aai.RealtimePartialTranscript):
                # Partial text — live preview ke liye
                self.on_text(transcript.text)

        def on_error(error: aai.RealtimeError):
            self.on_error(str(error))

        def on_close():
            print("AssemblyAI session closed")

        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=16_000,          # 16kHz — browser default
            on_data=on_data,
            on_error=on_error,
            on_open=on_open,
            on_close=on_close,
            encoding=aai.AudioEncoding.pcm_s16le,  # raw PCM audio
        )

        self.transcriber.connect()


    def send_audio(self, audio_chunk: bytes):
        """Browser se aaya audio chunk AssemblyAI ko bhejo"""
        if self.transcriber:
            self.transcriber.stream(audio_chunk)


    def stop(self) -> str:
        """
        Recording stop karo
        Poora text return karo (sab final transcripts join karke)
        """
        if self.transcriber:
            self.transcriber.close()

        return " ".join(self.full_text)


    def get_full_transcript(self) -> str:
        """Abhi tak ka poora text"""
        return " ".join(self.full_text)