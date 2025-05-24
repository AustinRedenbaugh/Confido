from pydub import AudioSegment
import math
import os

# Load the original MP3
audio = AudioSegment.from_mp3("static/keyboard-typing.mp3")

# Chunk size in milliseconds (1.5 seconds)
chunk_duration_ms = 1500

# Total number of full chunks
num_chunks = len(audio) // chunk_duration_ms

# Create output directory
os.makedirs("chunks", exist_ok=True)

# Split and export chunks
for i in range(num_chunks):
    start = i * chunk_duration_ms
    end = start + chunk_duration_ms
    chunk = audio[start:end]
    out_path = f"static/keyboard-typing-{i+1}.mp3"
    chunk.export(out_path, format="mp3")
    print(f"Exported {out_path}")

print(f"✅ Done. Exported {num_chunks} full chunks of 1.5 seconds each.")
