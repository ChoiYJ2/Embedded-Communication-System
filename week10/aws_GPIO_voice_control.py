"""Getting Started Example for Python 2.7+/3.3++"""
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
import os
import sys
import subprocess
from tempfile import gettempdir
from time import sleep
import time
import boto3
import asyncio
import sounddevice
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from gpiozero import LED, Button

led = LED(18)
led1 = LED(23)
led2 = LED(24)
button = Button(25)

#Create a client using the credentials and region defined in the [adminuser]
#section of the AWS credentials file (~/.aws/credentials).
session = Session(profile_name="default")
polly = session.client("polly")

def awstts(string_input):
    response = polly.synthesize_speech(Text=string_input, OutputFormat="mp3", VoiceId="Seoyeon")
    
    #Access the audio stream from the response
    if "AudioStream" in response:
        with closing(response["AudioStream"]) as stream:
            output = os.path.join(gettempdir(), "speech.mp3")

            try:
                #Open a file for writing the output as a binary stream
                with open(output, "wb") as file:
                    file.write(stream.read())
            except IOError as error:
                #Could not write to file, exit gracefully
                print(error)
                sys.exit(-1)
    else:
        # The response didn't contain audio data, exit gracefully
        print("Could not stream audio")
        sys.exit(-1)
    # Play the audio using the platform's default player
    if sys.platform == "win32":
        os.startfile(output)
    else:
        subprocess.call(["mpg321", "-g", "5", output])

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
def transcribe_file(job_name, file_uri, transcribe_client):
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': file_uri},
        MediaFormat='wav',
        LanguageCode='en-US'
    )

    max_tries = 60
    while max_tries > 0:
        max_tries -= 1
        job = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = job['TranscriptionJob']['TranscriptionJobStatus']
        if job_status in ['COMPLETED', 'FAILED']:
            print(f"Job {job_name} is {job_status}.")
            if job_status == 'COMPLETED':
                print(
                    f"Download the transcript from\n"
                    f"\t{job['TranscriptionJob']['Transcript']['TranscriptFileUri']}.")
            break
        else:
            print(f"Waiting for {job_name}. Current status is {job_status}.")
        time.sleep(10)


def main():
    transcribe_client = boto3.client('transcribe')
    file_uri = 's3://test-transcribe/answer2.wav'
    transcribe_file('Example-job', file_uri, transcribe_client)

class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # This handler can be implemented to handle transcriptions as needed.
        # Here's an example to get started.
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:
                print(alt.transcript) #문자열
                #light on / off로 말하자
                if "on" in alt.transcript or "up" in alt.transcript:
                    if "Red" in alt.transcript or "red" in alt.transcript:
                        led.on()
                    elif "Yellow" in alt.transcript or "yellow" in alt.transcript:
                        led1.on()
                    elif "Green" in alt.transcript or "green" in alt.transcript:
                        led2.on()
                elif "off" in alt.transcript or "kill" in alt.transcript or "down" in alt.transcript:
                    if "Red" in alt.transcript or "red" in alt.transcript:
                        led.off()
                    elif "Yellow" in alt.transcript or "yellow" in alt.transcript:
                        led1.off()
                    elif "Green" in alt.transcript or "green" in alt.transcript:
                        led2.off()
 

async def mic_stream():
    # This function wraps the raw input stream from the microphone forwarding
    # the blocks to an asyncio.Queue.
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()

    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))

    # Be sure to use the correct parameters for the audio stream that matches
    # the audio formats described for the source language you'll be using:
    # https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html
    stream = sounddevice.RawInputStream(
        channels=1,
        samplerate=44100,
        callback=callback,
        blocksize=1024 * 2,
        dtype="int16",
    )
    # Initiate the audio stream and asynchronously yield the audio chunks
    # as they become available.
    with stream:
        while True:
            indata, status = await input_queue.get()
            yield indata, status


async def write_chunks(stream):
    # This connects the raw audio chunks generator coming from the microphone
    # and passes them along to the transcription stream.
    async for chunk, status in mic_stream():
        await stream.input_stream.send_audio_event(audio_chunk=chunk)
    await stream.input_stream.end_stream()


async def basic_transcribe():
    # Setup up our client with our chosen AWS region
    client = TranscribeStreamingClient(region="us-west-2")

    # Start transcription to generate our async stream
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=44100,
        media_encoding="pcm",
    )

    # Instantiate our handler and start processing events
    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(write_chunks(stream), handler.handle_events())

#awstts("음성제어 서비스를 시작합니다. LED를 켤 경우 원하는 LED색상과 켜줘라는 명령어를 말씀해주세요. LED를 끌 경우 원하는 LED색상과 꺼줘라는 명령어를 말씀해주세요. 숫자를 이진수로 표현하고 싶다면 이진수 모드라고 말씀해주세요.")
while True:
    if button.is_pressed:
        while True:
            print("start")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(basic_transcribe())
            loop.close()    