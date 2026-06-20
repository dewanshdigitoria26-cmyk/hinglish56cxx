import streamlit as st
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
    'क्षमा': 'kshama', 'क्ष': 'ksh',   'त्र': 'tr',
    'ज्ञ': 'gya',      'श्र': 'shr',   'द्ध': 'ddh',
    'द्व': 'dv',       'न्ह': 'nh',    'म्ह': 'mh',
    'ल्ह': 'lh',       'त्त': 'tt',    'क्क': 'kk',
    'च्च': 'chch',     'ज्ज': 'jj',    'ल्ल': 'll',
    'न्न': 'nn',       'म्म': 'mm',    'स्स': 'ss',
    'र्': 'r',
}

WORD_MAP = {
    'vah': 'woh',      'vo': 'woh',       'yah': 'yeh',
    'yaha': 'yahan',   'vaha': 'wahan',   'vahan': 'wahan',
    'apa': 'aap',      'aap': 'aap',      'ham': 'hum',
    'hama': 'hum',     'mujhe': 'mujhe',  'tumhe': 'tumhe',
    'unhe': 'unhe',    'inhe': 'inhe',
    'karana': 'karna', 'karna': 'karna',  'jana': 'jaana',
    'aana': 'aana',    'dena': 'dena',    'lena': 'lena',
    'bolna': 'bolna',  'hona': 'hona',    'rehna': 'rehna',
    'sunna': 'sunna',  'dekhna': 'dekhna','samajhna': 'samajhna',
    'batana': 'batana','milna': 'milna',  'padhna': 'padhna',
    'khelna': 'khelna','likhna': 'likhna',
    'kara': 'kar',     'karo': 'karo',    'kiya': 'kiya',
    'kii': 'ki',       'hain': 'hain',    'hai': 'hai',
    'tha': 'tha',      'thi': 'thi',      'the': 'the',
    'raha': 'raha',    'rahi': 'rahi',    'rahe': 'rahe',
    'chahie': 'chahiye','chahiye': 'chahiye',
    'milegi': 'milegi','milega': 'milega','milenge': 'milenge',
    'hoga': 'hoga',    'hogi': 'hogi',    'honge': 'honge',
    'men': 'mein',     'mem': 'mein',     'mein': 'mein',
    'se': 'se',        'ko': 'ko',        'ne': 'ne',
    'par': 'par',      'ka': 'ka',        'ki': 'ki',   'ke': 'ke',
    'usaki': 'uski',   'usaka': 'uska',   'unaki': 'unki',
    'unaka': 'unka',   'apaki': 'apki',   'apaka': 'apka',
    'tumhari': 'tumhari','tumhara': 'tumhara','tumhare': 'tumhare',
    'hamari': 'hamari','hamara': 'hamara','hamare': 'hamare',
    'meri': 'meri',    'mera': 'mera',    'mere': 'mere',
    'teri': 'teri',    'tera': 'tera',    'tere': 'tere',
    'nahin': 'nahi',   'naheen': 'nahi',  'nahi': 'nahi',
    'thika': 'theek',  'theek': 'theek',  'sahi': 'sahi',
    'accha': 'accha',  'acha': 'accha',   'pakka': 'pakka',
    'bahut': 'bahut',  'bahuta': 'bahut', 'bahot': 'bahut',
    'sirf': 'sirf',    'abhi': 'abhi',
    'pahle': 'pehle',  'pehle': 'pehle',  'pahale': 'pehle',
    'baad': 'baad',    'phir': 'phir',
    'lekin': 'lekin',  'isliye': 'isliye','kyunki': 'kyunki',
    'toh': 'toh',      'tah': 'toh',
    'kyom': 'kyun',    'kyun': 'kyun',
    'kya': 'kya',      'kahan': 'kahan',  'kaha': 'kahan',
    'kitna': 'kitna',  'kitni': 'kitni',  'kitne': 'kitne',
    'zyada': 'zyada',  'jyada': 'zyada',
    'thoda': 'thoda',  'thodi': 'thodi',
    'kam': 'kam',      'jaldi': 'jaldi',  'dhire': 'dheere',
    'zaruri': 'zaroori','zaroori': 'zaroori',
    'sabhi': 'sabhi',  'sab': 'sab',      'kuch': 'kuch',
    'liye': 'liye',    'yaar': 'yaar',    'bhai': 'bhai',
    'kal': 'kal',      'pata': 'pata',    'baat': 'baat',
    'bhi': 'bhi',      'hi': 'hi',        'mat': 'mat',
    'peyment': 'payment', 'akaunt': 'account',
    'bijaness': 'business', 'onalain': 'online',
    'teem': 'team',    'mobail': 'mobile',
}

HALANT       = '\u094d'
ANUSVARA     = '\u0902'
CHANDRABINDU = '\u0901'
NUKTA        = '\u093c'
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
            syls.append(('C_pure', buf))
            i = j + 1; continue
        if ch in VOWEL_MAP:
            v = VOWEL_MAP[ch]
            if i + 1 < n and chars[i + 1] in (ANUSVARA, CHANDRABINDU):
                v += 'n'; i += 1
            syls.append(('V', v)); i += 1; continue
        if ch in CONSONANT_MAP or (
            i + 1 < n and chars[i + 1] == NUKTA and ch + NUKTA in CONSONANT_MAP
        ):
            if i + 1 < n and chars[i + 1] == NUKTA and ch + NUKTA in CONSONANT_MAP:
                rc = CONSONANT_MAP[ch + NUKTA]; i += 2
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
            if is_last:
                out.append(rc)
            elif idx > 0 and idx + 1 < total and syls[idx + 1][0] in ('CV', 'C_pure'):
                out.append(rc)
            else:
                out.append(rc + 'a')
        elif stype == 'CV':
            rc, mv = syl[1], syl[2]
            is_long_a = syl[3] if len(syl) > 3 else False
            if is_last and is_long_a:
                mv = 'a'
            out.append(rc + mv)
        elif stype == 'C_pure':
            out.append(syl[1])
        else:
            out.append(syl[1])
    return ''.join(out)


def is_devanagari(text):
    return bool(re.search(r'[\u0900-\u097F]', text))


def devanagari_to_hinglish(text):
    tokens = re.split(r'([\u0900-\u097F]+)', text)
    out = []
    for tok in tokens:
        if not tok:
            continue
        if not is_devanagari(tok):
            out.append(tok)
            continue
        deva_words = tok.split()
        roman_words = []
        for dw in deva_words:
            roman = parse_devanagari_word(dw)
            rl = roman.lower()
            if rl in WORD_MAP:
                roman = WORD_MAP[rl]
            roman_words.append(roman)
        out.append(' '.join(roman_words))
    return re.sub(r' {2,}', ' ', ''.join(out)).strip()


def fmt(s):
    h   = int(s // 3600)
    m   = int((s % 3600) // 60)
    sec = s % 60
    return f"{h:02}:{m:02}:{sec:06.3f}".replace(".", ",")


@st.cache_resource
def get_model(size="medium"):
    return WhisperModel(size, device="cpu", compute_type="int8", num_workers=2, cpu_threads=4)


# ── UI ────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="HinglishSRT", page_icon="🎙️", layout="centered")

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { max-width: 760px; padding-top: 2rem; }
.stButton > button {
    background: linear-gradient(90deg,#ff6b35,#ffb347) !important;
    color: white !important; font-weight: 700 !important;
    border: none !important; border-radius: 10px !important;
    font-size: 1rem !important; width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;padding:1.5rem 0 1rem">
  <div style="font-size:2rem;font-weight:900;background:linear-gradient(90deg,#ff6b35,#ffb347);
       -webkit-background-clip:text;-webkit-text-fill-color:transparent">
    🎙️ HinglishSRT
  </div>
  <div style="color:#888;font-size:.9rem;margin-top:4px">
    Hindi Audio → WhatsApp Hinglish Subtitles &nbsp;•&nbsp; 100% Free &nbsp;•&nbsp; No API Key
  </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.info("📁 **Koi bhi File**\nMP3 MP4 WAV OGG M4A WEBM FLAC MKV")
c2.info("🆓 **100% Free**\nNo API key • No cost")
c3.info("💬 **WhatsApp Style**\nNatural Roman Hinglish")

st.divider()

uploaded_file = st.file_uploader(
    "🎵 Audio / Video Upload Karo",
    type=["mp3","mp4","wav","ogg","m4a","webm","flac","mkv","aac","wma","mov","avi"]
)

ca, cb = st.columns(2)
with ca:
    model_size = st.selectbox("🤖 Whisper Model", ["medium","small"], index=0,
                              help="medium = best accuracy")
with cb:
    words_per_line = st.slider("📝 Words per subtitle line", 1, 12, 6)

run_btn = st.button("🎯 Hinglish Subtitles Banao")

if run_btn:
    if uploaded_file is None:
        st.error("❌ Pehle audio/video file upload karo!")
    else:
        job_id   = str(uuid.uuid4())
        ext      = os.path.splitext(uploaded_file.name)[1]
        inp_path = f"outputs/{job_id}_input{ext}"
        wav_path = f"outputs/{job_id}.wav"
        out_path = f"outputs/{job_id}.srt"

        with open(inp_path, "wb") as f:
            f.write(uploaded_file.read())

        status   = st.empty()
        progress = st.progress(0)

        try:
            status.info("⏳ Audio convert ho raha hai...")
            progress.progress(5)
            r = subprocess.run(
                ["ffmpeg","-y","-i",inp_path,"-ar","16000","-ac","1",
                 "-af","loudnorm=I=-16:LRA=11:TP=-1.5", wav_path],
                capture_output=True
            )
            if r.returncode != 0:
                st.error(f"❌ FFmpeg error: {r.stderr.decode()}"); st.stop()

            status.info(f"⏳ Whisper {model_size} load ho raha hai...")
            progress.progress(15)
            model = get_model(model_size)

            status.info("⏳ Transcribe ho rahi hai... thoda time lagega")
            progress.progress(30)
            segments_gen, _ = model.transcribe(
                wav_path, task="transcribe", language="hi",
                beam_size=5, best_of=5, temperature=[0.0,0.2,0.4],
                condition_on_previous_text=False,
                no_speech_threshold=0.6, log_prob_threshold=-1.0,
                compression_ratio_threshold=2.4, vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=400),
                word_timestamps=False, chunk_length=30,
                initial_prompt=(
                    "\u092f\u0939 \u090f\u0915 \u0939\u093f\u0902\u0926\u0940 "
                    "\u092c\u093e\u0924\u091a\u0940\u0924 \u0939\u0948\u0964"
                ),
            )

            status.info("⏳ Segments collect ho rahe hain...")
            progress.progress(50)
            raw_segments = []
            for seg in segments_gen:
                raw = seg.text.strip()
                if raw:
                    raw_segments.append({"start":seg.start,"end":seg.end,"raw_text":raw})

            if not raw_segments:
                st.error("❌ Koi speech detect nahi hui."); st.stop()

            status.info("⏳ Hinglish conversion ho rahi hai...")
            total = len(raw_segments)
            for i, seg in enumerate(raw_segments):
                seg["hinglish_text"] = (
                    devanagari_to_hinglish(seg["raw_text"])
                    if is_devanagari(seg["raw_text"]) else seg["raw_text"]
                )
                if i % 10 == 0:
                    progress.progress(int(60 + 30 * (i / max(total, 1))))

            progress.progress(92)
            parts = []; n = 1
            for seg in raw_segments:
                t1, t2 = seg["start"], seg["end"]
                words  = seg["hinglish_text"].strip().split()
                if not words: continue
                groups = [words[i:i+words_per_line] for i in range(0,len(words),words_per_line)]
                tpg    = (t2-t1) / max(len(groups),1)
                for j, g in enumerate(groups):
                    gs = t1+j*tpg; ge = gs+tpg
                    parts.append(f"{n}\n{fmt(gs)} --> {fmt(ge)}\n{' '.join(g)}\n\n")
                    n += 1

            if n == 1:
                st.error("❌ Koi valid text nahi mila."); st.stop()

            srt_content = ''.join(parts)
            progress.progress(100)
            status.success(
                f"✅ Ho gaya! {n-1} subtitle lines ready!  \n"
                f"📊 {len(raw_segments)} segments • 🎯 Whisper {model_size}"
            )
            st.download_button(
                "⬇️ SRT File Download Karo",
                data=srt_content,
                file_name=f"{os.path.splitext(uploaded_file.name)[0]}_hinglish.srt",
                mime="text/plain",
            )

        except Exception as e:
            import traceback
            st.error(f"❌ Error:\n{str(e)}\n\n{traceback.format_exc()}")
        finally:
            for p in [inp_path, wav_path]:
                try: os.remove(p)
                except: pass

st.divider()
st.markdown("""
<div style="background:#0d1117;border:1px solid rgba(255,107,53,0.2);
     border-radius:12px;padding:14px;font-size:.78rem;color:#7a849a;line-height:2">
💡 <b style="color:#ff6b35">Tips:</b><br>
✅ <b style="color:#ddd">Clear audio</b> use karo — background noise se accuracy kam hoti hai<br>
✅ <b style="color:#ddd">medium model</b> recommend hai — ~30% better accuracy<br>
⚠️ Medium model pehli baar ~1.4GB download karega<br>
⚠️ Rare words mein manually adjust kar lena
</div>
<div style="text-align:center;padding:.8rem 0;color:#3a4260;font-size:.7rem">
Powered by Whisper + Custom Hinglish Parser • 100% Free
</div>
""", unsafe_allow_html=True)
