from django.shortcuts import render
from .forms import PodcastForm
import google.generativeai as genai
import requests
import os
import re
import subprocess
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICES = {
    "HOST": os.getenv("ELEVENLABS_HOST_VOICE_ID"),
    "GUEST": os.getenv("ELEVENLABS_GUEST_VOICE_ID")
}

INTRO_MUSIC_PATH = os.getenv("INTRO_MUSIC_PATH", "podcast/static/intro.mp3")
OUTRO_MUSIC_PATH = os.getenv("OUTRO_MUSIC_PATH", "podcast/static/outro.mp3")

genai.configure(api_key=GEMINI_API_KEY)

def clean_script(text):
    text = re.sub(r"[#*_`~]", "", text)
    text = re.sub(r"\([^)]*\)|\*[^*]*\*", "", text)
    lines = text.splitlines()
    filtered = [line.strip() for line in lines if re.match(r"^\[\w+\]:", line.strip())]
    return "\n".join(filtered), lines

def synthesize_speech(text, voice_id, temp_dir, index):
    print(f"[DEBUG] Requesting TTS for line {index}: {text}")
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        path = os.path.join(temp_dir, f"part_{index}.mp3")
        with open(path, "wb") as f:
            f.write(response.content)
        print(f"[DEBUG] TTS success: {path}")
        return path
    else:
        print(f"[ERROR] TTS failed for line {index} with status {response.status_code}: {response.text}")
        return None

def merge_audio_ffmpeg(file_list, output_path):
    print(f"[DEBUG] Merging {len(file_list)} audio files...")
    list_file = os.path.join(os.path.dirname(output_path), "concat_list.txt")
    with open(list_file, "w") as f:
        for filepath in file_list:
            print(f"[DEBUG] Adding to merge list: {filepath}")
            f.write(f"file '{filepath}'\n")
    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
         "-acodec", "libmp3lame", "-b:a", "192k", output_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print("[DEBUG] FFmpeg stdout:", result.stdout)
    print("[DEBUG] FFmpeg stderr:", result.stderr)

def parse_segments(script):
    return re.findall(r"\[(\w+)\]:\s*((?:.|\n)*?)(?=\n\[\w+\]:|\Z)", script.strip())

def index(request):
    script = None
    audio_url = None
    error_message = None

    if request.method == 'POST':
        form = PodcastForm(request.POST)
        if form.is_valid():
            topic = form.cleaned_data['topic']

            try:
                model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
                response = model.generate_content(f"Write a podcast script about: {topic}. Use [HOST]: and [GUEST]:. Avoid markdown or asterisk formatting.")
                raw_script = response.text
                cleaned_script, raw_lines = clean_script(raw_script)
                script = cleaned_script if cleaned_script.strip() else raw_script
                if not cleaned_script.strip():
                    error_message = "⚠️ Gemini response did not include valid [HOST]: or [GUEST]: lines. Showing raw content instead."
            except Exception as e:
                script = f"(Fallback Script) Gemini failed: {topic}"
                error_message = str(e)

            try:
                segments = parse_segments(script)
                print(f"[DEBUG] Segments to synthesize (before limit): {len(segments)}")

                # 💡 Character quota limiting
                MAX_TTS_CREDITS = 9000
                used_credits = 0
                filtered_segments = []
                for speaker, line in segments:
                    cost = len(line.strip())
                    if used_credits + cost > MAX_TTS_CREDITS:
                        break
                    filtered_segments.append((speaker, line))
                    used_credits += cost

                segments = filtered_segments
                print(f"[DEBUG] Segments to synthesize (after limit): {len(segments)}")

                with tempfile.TemporaryDirectory() as temp_dir:
                    parts = []

                    if os.path.exists(INTRO_MUSIC_PATH):
                        print("[DEBUG] Adding intro music to playlist")
                        parts.append(INTRO_MUSIC_PATH)

                    for i, (speaker, line) in enumerate(segments):
                        line = line.strip().replace("\n", " ")
                        voice_id = ELEVENLABS_VOICES.get(speaker.upper(), ELEVENLABS_VOICES["HOST"])
                        print(f"[DEBUG] Synthesizing voice for: {speaker.upper()} with voice ID {voice_id}")
                        audio_path = synthesize_speech(line, voice_id, temp_dir, i)
                        if audio_path:
                            parts.append(audio_path)
                        else:
                            print(f"[WARN] Skipping line {i} due to failed synthesis.")

                    if os.path.exists(OUTRO_MUSIC_PATH):
                        print("[DEBUG] Adding outro music to playlist")
                        parts.append(OUTRO_MUSIC_PATH)

                    if len(parts) < 2:
                        error_message = "❌ Podcast audio could not be generated. Only music was available."
                        print("[ERROR] No speech audio generated.")
                    else:
                        final_path = "podcast/static/podcast.mp3"
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)
                        merge_audio_ffmpeg(parts, final_path)
                        audio_url = "/static/podcast.mp3"

            except Exception as e:
                error_message = f"Audio generation or merging failed: {str(e)}"
                print(f"[ERROR] {error_message}")

    else:
        form = PodcastForm()

    return render(request, 'index.html', {
        'form': form,
        'script': script,
        'audio_url': audio_url,
        'error_message': error_message
    })
