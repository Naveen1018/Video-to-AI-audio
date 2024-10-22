import streamlit as st
import openai
import requests
import json
import moviepy.editor as mp
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
import os

# Set up Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "<path_to_google_credentials.json>"

def transcribe_audio(audio_file):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_file.read())
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )
    response = client.recognize(config=config, audio=audio)
    transcription = " ".join([result.alternatives[0].transcript for result in response.results])
    return transcription

def correct_transcription(transcription):
    azure_openai_key = "22ec84421ec24230a3638d1b51e3a7dc"  # Replace with your actual key
    azure_openai_endpoint = "https://internshala.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"  # Replace with your actual endpoint URL

    headers = {
        "Content-Type": "application/json",
        "api-key": azure_openai_key
    }
    
    # Modify the prompt to ask for grammatical correction and removal of filler words
    data = {
        "messages": [{"role": "user", "content": f"Please correct the following transcription, removing any grammatical mistakes and filler words (like um, uh, etc.): {transcription}"}],
        "max_tokens": 100
    }
    
    response = requests.post(azure_openai_endpoint, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    else:
        st.error(f"Error in correction: {response.status_code} - {response.text}")
        return transcription

def generate_audio(text):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-D"  # Choose a voice model
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content

def replace_audio_in_video(video_file, new_audio):
    video = mp.VideoFileClip(video_file.name)
    audio = mp.AudioFileClip(new_audio)

    # Sync the audio with the video
    original_audio_duration = video.audio.duration
    new_audio_duration = audio.duration

    # If the new audio is shorter, we can loop it to match the duration
    if new_audio_duration < original_audio_duration:
        audio = mp.concatenate_audioclips([audio] * int(original_audio_duration // new_audio_duration + 1))
        audio = audio.subclip(0, original_audio_duration)  # Trim to original duration

    final_video = video.set_audio(audio)
    final_video_file = "final_video.mp4"
    final_video.write_videofile(final_video_file, codec='libx264')
    return final_video_file

def main():
    st.title("Video Audio Replacement with AI Voice")
    
    video_file = st.file_uploader("Upload Video File", type=["mp4", "mov", "avi"])
    
    if video_file is not None:
        # Step 1: Extract audio and transcribe
        audio_content = mp.AudioFileClip(video_file.name).to_soundarray(fps=16000)
        transcription = transcribe_audio(audio_content)
        st.write("Transcription:", transcription)
        
        # Step 2: Correct transcription
        corrected_transcription = correct_transcription(transcription)
        st.write("Corrected Transcription:", corrected_transcription)
        
        # Step 3: Generate new audio
        new_audio_content = generate_audio(corrected_transcription)
        new_audio_file = "new_audio.wav"
        with open(new_audio_file, "wb") as f:
            f.write(new_audio_content)
        
        # Step 4: Replace audio in video
        final_video_file = replace_audio_in_video(video_file, new_audio_file)
        st.success("Audio replaced successfully!")
        st.video(final_video_file)

if __name__ == "__main__":
    main()