import gradio as gr
import subprocess, os, uuid, re
from faster_whisper import WhisperModel

os.makedirs("outputs", exist_ok=True)

CONSONANT_MAP = {
    'क': 'k',  'ख': 'kh', 'ग': 'g',  'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh','ज': 'j',  'झ': 'jh', 'ञ': 'n',
    'ट': 't',  'ठ': 'th', 'ड': 'd',  'ढ': 'dh', 'ण': 'n',
    'ड़': 'r', 'ढ़': 'rh',
    'त': 't',  'थ': 'th', 'द': 'd',  'ध': 'dh', 'न': 'n',
    'प': 'p',  'फ': 'f',  'ब': 'b',  'भ': 'bh', 'म': 'm',
    'य': 'y',  'र': 'r',  'ल': 'l',  'व': 'v',  'ळ': 'l',
    'श': 'sh', 'ष': 'sh', 'स': 's',  'ह': 'h',
    'क़': 'q',  'ख़': 'kh', 'ग़': 'g',  'ज़': 'z',
    'फ़': 'f',  'य़': 'y',
}
MATRA_MAP = {
    'ा': 'aa', 'ि': 'i',  'ी': 'i',  'ु': 'u',  'ू': 'oo',
    'े': 'e',  'ै': 'ai', 'ो': 'o',  'ौ': 'au',
    'ृ': 'ri', 'ं': 'n',  'ँ': 'n',  'ः': '',
}
VOWEL_MAP = {
    'अ': 'a',  'आ': 'aa', 'इ': 'i',  'ई': 'i',  'उ': 'u',  'ऊ': 'oo',
    'ए': 'e',  'ऐ': 'ai', 'ओ': 'o',  'औ': 'au', 'ऋ': 'ri',
    'ऑ': 'o',  'ऍ': 'e',
}
SPECIAL_CASES = {
    'क्षमा': 'kshama', 'क्ष': 'ksh', 'त्र': 'tr',
    'ज्ञ': 'gya', 'श्र': 'shr', 'द्ध': 'ddh',
    'द्व': 'dv', 'न्ह': 'nh', 'म्ह': 'mh',
    'ल्ह': 'lh', 'त्त': 'tt', 'क्क': 'kk',
    'च्च': 'chch', 'ज्ज': 'jj', 'ल्ल': 'll',
    'न्न': 'nn', 'म्म': 'mm', 'स्स': 'ss', 'र्': 'r',
}
WORD_MAP = {
    'vah': 'woh', 'vo': 'woh', 'yah': 'yeh', 'yaha': 'yahan',
    'vaha': 'wahan', 'vahan': 'wahan', 'apa': 'aap', 'aap': 'aap',
    'ham': 'hum', 'hama': 'hum', 'mujhe': 'mujhe', 'tumhe': 'tumhe',
    'karana': 'karna', 'karna': 'karna', 'jana': 'jaana',
    'kara': 'kar', 'karo': 'karo', 'kiya': 'kiya',
    'hain': 'hain', 'hai': 'hai', 'tha': 'tha', 'thi': 'thi', 'the': 'the',
    'raha': 'raha', 'rahi': 'rahi', 'rahe': 'rahe',
    'chahiye': 'chahiye', 'hoga': 'hoga', 'hogi': 'hogi', 'honge': 'honge',
    'men': 'mein', 'mem': 'mein', 'mein': 'mein',
    'se': 'se', 'ko': 'ko', 'ne': 'ne', 'par': 'par',
    'ka': 'ka', 'ki': 'ki', 'ke': 'ke',
    'nahin': 'nahi', 'nahi': 'nahi', 'theek': 'theek', 'sahi': 'sahi',
    'accha': 'accha', 'pakka': 'pakka', 'bahut': 'bahut', 'bahot': 'bahut',
    'sirf': 'sirf', 'abhi': 'abhi', 'pehle': 'pehle', 'baad': 'baad',
    'phir': 'phir', 'lekin': 'lekin', 'kyunki': 'kyunki', 'toh': 'toh',
    'kyun': 'kyun', 'kya': 'kya', 'kahan': 'kahan',
    'zyada': 'zyada', 'jyada': 'zyada', 'thoda': 'thoda',
    'jaldi': 'jaldi', 'zaroori': 'zaroori',
    'sab': 'sab', 'kuch': 'kuch', 'liye': 'liye',
    'yaar': 'yaar', 'bhai': 'bhai', 'bhi': 'bhi', 'hi': 'hi', 'mat': 'mat',
}

HALANT = '\u094d'
ANUSVARA = '\u0902'
CHANDRABINDU = '\u0901'
NUKTA = '\u093c'
LONG_A_MATRA = '\u093e'


def parse_devanagari_word(word):
    if word in SPECIAL_CASES:
        return SPECIAL_CASES[word]
    for deva, rom in SPECIAL_CASES.items():
        if len(deva) > 1:
            word = word.replace(deva, '\x00' + rom + '\x00')
    chars = list(word)
    n = len(chars)
    syls = []
    i = 0
    while i < n:
        ch = chars[i]
        if ch == '\x00':
            j = i + 1; buf = ''
            while j < n and chars[j] != '\x00':
                buf += chars[j]; j += 1
            syls.append(('C_pure', buf)); i = j + 1; continue
        if ch in VOWEL_MAP:
            v = VOWEL_MAP[ch]
            if i + 1 < n and chars[i+1] in (ANUSVARA, CHANDRABINDU):
                v += 'n'; i += 1
            syls.append(('V', v)); i += 1; continue
        if ch in CONSONANT_MAP or (i+1 < n and chars[i+1] == NUKTA and ch+NUKTA in CONSONANT_MAP):
            if i+1 < n and chars[i+1] == NUKTA and ch+NUKTA in CONSONANT_MAP:
                rc = CONSONANT_MAP[ch+NUKTA]; i += 2
            else:
                rc = CONSONANT_MAP.get(ch, ch); i += 1
            if i < n and chars[i] == HALANT:
                syls.append(('C_pure', rc)); i += 1; continue
            if i < n and chars[i] in MATRA_MAP:
                mc = chars[i]; mv = MATRA_MAP[mc]; i += 1
                is_long_a = (mc == LONG_A_MATRA)
                if i < n and chars[i] in (ANUSVARA, CHANDRABINDU):
                    mv += 'n'; i += 1
                syls.append(('CV', rc, mv, is_long_a))
            else:
                if i < n and chars[i] in (ANUSVARA, CHANDRABINDU):
                    syls.append(('CV', rc, 'an', False)); i += 1
                else:
                    syls.append(('Ca', rc))
            continue
        if ch in (ANUSVARA, CHANDRABINDU):
            syls.append(('V', 'n')); i += 1; continue
        if ch == '\u0903': i += 1; continue
        syls.append(('X', ch)); i += 1

    total = len(syls)
    out = []
    for idx, syl in enumerate(syls):
        is_last = (idx == total - 1)
        stype = syl[0]
        if stype == 'Ca':
            rc = syl[1]
            if is_last: out.append(rc)
            elif idx+1 < total and syls[idx+1][0] in ('CV', 'C_pure'): out.append(rc)
            else: out.append(rc + 'a')
        elif stype == 'CV':
            rc, mv = syl[1], syl[2]
            is_long_a = syl[3] if len(syl) > 3 else False
            if is_last and is_long_a: mv = 'a'
            out.append(rc + mv)
        elif stype == 'C_pure': out.append(syl[1])
        else: out.append(syl[1])
    return ''.join(out)


def is_devanagari(text):
    return bool(re.search(r'[\u0900-\u097F]', text))


def devanagari_to_hinglish(text):
    tokens = re.split(r'([\u0900-\u097F]+)', text)
    out = []
    for tok in tokens:
        if not tok: continue
        if not is_devanagari(tok): out.append(tok); continue
        words = tok.split()
        roman_words = []
        for dw in words:
            roman = parse_devanagari_word(dw)
            rl = roman.lower()
            if rl in WORD_MAP: roman = WORD_MAP[rl]
            roman_words.append(roman)
        out.append(' '.join(roman_words))
    return re.sub(r' {2,}', ' ', ''.join(out)).strip()


def fmt(s):
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return f"{h:02}:{m:02}:{sec:06.3f}".replace(".", ",")


_model = None
_model_size = None


def get_model(size="medium"):
    global _model, _model_size
    if _model is None or _model_size != size:
        _model = WhisperModel(size, device="cpu", compute_type="int8",
                              num_workers=2, cpu_threads=4)
        _model_size = size
    return _model


def transcribe_audio(audio_path, words_per_line, model_size, progress=gr.Progress()):
    if audio_path is None:
        return None, "❌ Pehle audio/video file upload karo!"
    try:
        job_id = str(uuid.uuid4())
        wav_path = f"outputs/{job_id}.wav"
        out_path = f"outputs/{job_id}.srt"
        words_per_line = int(words_per_line)

        progress(0.05, desc="Audio convert ho raha hai...")
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1",
             "-af", "loudnorm=I=-16:LRA=11:TP=-1.5", wav_path],
            capture_output=True)
        if r.returncode != 0:
            return None, f"❌ FFmpeg error: {r.stderr.decode()}"

        progress(0.15, desc=f"Whisper {model_size} load ho raha hai...")
        model = get_model(model_size)

        progress(0.3, desc="Transcribe ho rahi hai...")
        segments_gen, _ = model.transcribe(
            wav_path, task="transcribe", language="hi",
            beam_size=5, best_of=5, temperature=[0.0, 0.2, 0.4],
            condition_on_previous_text=False,
            no_speech_threshold=0.6, log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4, vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=400),
            word_timestamps=False, chunk_length=30,
            initial_prompt="यह एक हिंदी बातचीत है।",
        )

        progress(0.5, desc="Segments collect ho rahe hain...")
        raw_segments = []
        for seg in segments_gen:
            raw = seg.text.strip()
            if raw:
                raw_segments.append({"start": seg.start, "end": seg.end, "raw_text": raw})

        if not raw_segments:
            return None, "❌ Koi speech detect nahi hui."

        progress(0.6, desc="Hinglish conversion ho rahi hai...")
        total = len(raw_segments)
        for i, seg in enumerate(raw_segments):
            seg["hinglish_text"] = (
                devanagari_to_hinglish(seg["raw_text"])
                if is_devanagari(seg["raw_text"]) else seg["raw_text"]
            )
            if i % 10 == 0:
                progress(0.6 + 0.3 * (i / max(total, 1)))

        progress(0.92, desc="SRT ban rahi hai...")
        parts = []; n = 1
        for seg in raw_segments:
            t1, t2 = seg["start"], seg["end"]
            words = seg["hinglish_text"].strip().split()
            if not words: continue
            groups = [words[i:i+words_per_line] for i in range(0, len(words), words_per_line)]
            tpg = (t2 - t1) / max(len(groups), 1)
            for j, g in enumerate(groups):
                gs = t1 + j * tpg; ge = gs + tpg
                parts.append(f"{n}\n{fmt(gs)} --> {fmt(ge)}\n{' '.join(g)}\n\n")
                n += 1

        if n == 1:
            return None, "❌ Koi valid text nahi mila."

        srt = ''.join(parts)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(srt)
        try: os.remove(wav_path)
        except: pass

        progress(1.0, desc="Ho gaya!")
        return out_path, f"✅ Ho gaya! {n-1} lines • {len(raw_segments)} segments • Whisper {model_size}"

    except Exception as e:
        import traceback
        return None, f"❌ Error:\n{str(e)}\n\n{traceback.format_exc()}"


css = """
footer { display: none !important; }
.gradio-container { max-width: 760px !important; margin: 0 auto !important; }
"""

with gr.Blocks(title="HinglishSRT") as demo:
    gr.HTML("""
    <div style="text-align:center;padding:28px 0 16px">
      <div style="font-size:1.9rem;font-weight:900;background:linear-gradient(90deg,#ff6b35,#ffb347);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px">
        🎙️ HinglishSRT
      </div>
      <div style="color:#5a6280;font-size:.9rem">
        Hindi Audio → WhatsApp Hinglish Subtitles • 100% Free • No API Key
      </div>
    </div>
    """)

    file_input = gr.File(
        label="🎵 Audio / Video Upload Karo",
        file_types=[".mp3",".mp4",".wav",".ogg",".m4a",".webm",".flac",".mkv",".aac",".mov",".avi"],
        type="filepath"
    )
    with gr.Row():
        model_dropdown = gr.Dropdown(choices=["medium","small"], value="medium",
                                     label="🤖 Whisper Model")
        words_slider = gr.Slider(minimum=1, maximum=12, value=6, step=1,
                                 label="📝 Words per subtitle line")

    submit_btn = gr.Button("🎯 Hinglish Subtitles Banao", variant="primary", size="lg")
    status_box = gr.Textbox(label="Status", interactive=False,
                            placeholder="File upload karo aur button dabao...")
    output_file = gr.File(label="⬇️ SRT File Download Karo")

    submit_btn.click(fn=transcribe_audio,
                     inputs=[file_input, words_slider, model_dropdown],
                     outputs=[output_file, status_box])

demo.queue()
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    css=css,
)
