import openai
import requests
import io
import base64
import time
from PIL import Image, PngImagePlugin
import re
from moviepy.editor import *
from moviepy.video.fx.all import *
from moviepy.editor import ImageClip, VideoClip, concatenate_videoclips, TextClip
from moviepy.video.fx.all import crop
import pysrt
from mutagen.mp3 import MP3
import os
import random
import subprocess
import shutil

IMAGE_FOLDER = "C:\\Users\\eggep\\PycharmProjects\\EthanAntonProject\\Images\\"
VIDEO_FILENAME = "C:\\Users\\eggep\\PycharmProjects\\EthanAntonProject\\raw_output.mp4"

openai.api_key = 'openai-key'
XI_API_KEY = "ElevenLabs-key"
voice_id = "aN3w9JU7WdifMkQFswn7"


def main():
    input_flagged = True
    while input_flagged:
        idea, input_flagged = generate_idea()
    content_r, price_c = create_content(idea)
    summary, content = split_summary_content(content_r)
    print("-----------------------------")
    print(f"SUMMARY RAW: {summary}")
    print("-----------------------------")
    print(f"ACTUAL CONTENT: {content}")
    prompts, price_p = prompt_maker(summary)
    print("-----------------------------")
    print(prompts)
    response_list = create_list(prompts)
    for i in range(12):
        stable_api(response_list[i])

    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    foName, justName = speak_text(content, tts_url)
    create_srt(foName, justName)

    audio_path = f"C:\\Users\\eggep\\PycharmProjects\\EthanAntonProject\\{foName}"

    remove_mp4_files(IMAGE_FOLDER)
    audio_dur = get_audio_duration(audio_path)
    create_video(audio_path)
    concat_videos()
    add_subtitles()
    add_audio_to_video(audio_path)
    speed_up_video('output.mp4.', 'output2.mp4', audio_dur)
    clear_directory()
    move_files_to_timestamped_folder("output.mp4", "output2.mp4")

    print(price_c + price_p)


def generate_idea():
    idea = input("Whats your idea? ")
    input_flagged = check_moderation(idea)
    if input_flagged == False:
        options = ['educational', 'entertaining', 'informative', 'factually accurate and true', 'fantasy',
                   'personal narrative',
                   'motivational', 'serious', 'silly', 'mature adult jokes, curse words']
        user_choices = []

        print(
            "Please choose from the following options (enter 'done' when finished, 'none' if you don't want to pick anything):")

        for i, option in enumerate(options, 1):
            print(f'{i}. {option}')

        print("Make sure to pick the NUMBER option you want")
        while True:

            user_input = input(" > ")

            if user_input.lower() == 'done':
                break
            elif user_input.lower() == 'none':
                user_choices = []
                break
            elif user_input.isdigit() and 1 <= int(user_input) <= len(options):
                choice = options[int(user_input) - 1]
                if choice not in user_choices:
                    user_choices.append(choice)
                    print(f"You've selected: {choice}")
                else:
                    print(f"You've already selected: {choice}")
            else:
                print("Invalid choice. Please try again.")

        idea += ', ' + ', '.join(user_choices)
        print(idea)
    return idea, input_flagged


def create_content(idea):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "Your task is to craft a piece of content. The piece of content needs to be less than 1000 characters long and two paragraphs. It needs to be 1000 characters or less. Your content should spell numbers out instead of writing them in digit form. Your hook should get right into the story. There needs to be less dense detail and more intriguing content, everything said should be interesting to the casual person. Instead of using complex language, use simpler, more understandable words. Make the vocabulary used simple. The script should end with a short summary of the text, it should be two full sentences. It should be formatted like the following: (Summary: <Insert summary here>). Do NOT use phrases like 'Wait, there's more!' or 'But that's not all', and you shouldn't use transitional phrases. Do not use exclamation marks. When prompted by the user should use real curse words like 'fuck' and 'shit', not 'shoot' or freak'. Your script may not address the audience whatsoever, and the script may not be peppy, or over-the-top. It needs to sound like something a human would write.  When prompted by the user you should use real curse words like 'fuck' and 'shit', not 'shoot' or freak'. Don't format it, don't add stage directions. Don't use Alliteration."},
            {"role": "user",
             "content": "write a two paragraph, 1000 character piece of content about a story about WW1, education, informative, fantasy, . Jump straight into the content, and create a compelling hook. Put the summary after the content"},
            {"role": "assistant",
             "content": "A violent pounding echoed through the darkness, shattering the silence of the night. A soldier, battered and bloodied, stood on the doorstep of a humble woman named Amelie Dupont. thirty-one days ago, War had invaded her peaceful life, leaving destruction in its wake. With an extraordinary bravery she didn't know she possessed, Amelie opened her home to weary soldiers, regardless of their nationality.\nBut it wasn't just her open door that made her remarkable; it was her hidden act of defiance. Each night, she crafted tales of peace and unity, slipping them into the soldiers' belongings without a trace. Amelie's stories, brimming with hope and humanity, found their way into the hands of soldiers from both sides of the conflict. These weren't tales of valiant heroes or grand battles, but rather stories of ordinary people yearning for peace. They spoke of home and shared dreams, igniting a flicker of compassion amidst the desolation of war.\nSummary: A French woman, in her estate, holds French and German soldiers in her house during WW1, slipping notes of peace and unity into their backpacks as a act of defiance."},
            {"role": "user",
             "content": f"Write a two paragraph, 1000 character long, piece of content about {idea}. Jump straight into the content, don't introduce anything, don't start with a starting phrase, and create a compelling hook, that leaves the reader wanting context, for example a hook for a history piece on world war one could be 'In the blood soaked trenches...' Put the summary after the content. In the summary, give only a simple description of the setting, the characters race and gender, and one sentence about the plot, not including the moral."}
        ],

        temperature=.88
    )
    total_tokens_usedC = response['usage']['total_tokens']
    price = (total_tokens_usedC / 1000) * .0015
    actualResponse = response['choices'][0]['message']['content']
    return actualResponse, price


def check_moderation(content):
    output = openai.Moderation.create(
        input=f"{content}",
    )
    flagged = False
    for result in output["results"]:
        if result["flagged"]:
            flagged_categories = [category for category, flagged in result["categories"].items() if flagged]
            print("Your content is most likely inappropriate, it's been flagged in the categories:",
                  ', '.join(flagged_categories),
                  "this means that the content won't generate correctly. Try toning down the",
                  ', '.join(flagged_categories),
                  "content by using different words or adding a moral to the story, or claiming it's for educational content.")
            flagged = True
    return flagged


def split_summary_content(text):
    # Split the text by the "Summary:" keyword
    parts = text.split("Summary:")

    # The first part is the content, the second part is the summary
    content = parts[0].strip()
    summary = parts[1].strip()

    return summary, content


def prompt_maker(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "Your job is to provide image prompts that can be used to generate visual representations of "
                        "the given content using Artificial Intelligence. Your prompts shouldn't include depictions "
                        "of words, like in headlines, or book titles, or signs. The prompts need to not mention anything in "
                        "motion. You need to listen to the user and learn from your mistakes. The prompts need to "
                        "only describe how the image looks, not describe what's going on"
                        "in the story, and therefore should not mention any names, things, or objects that require "
                        "the context of the story to understand. The prompts should not use adjectives or names. The "
                        "prompts should not mention names, instead describing them, For example the name 'Joe' would "
                        "become 'A man' when put in the prompt. Its important to specify the gender and race. Split "
                        "sentences with commas and full sentences are not necessary."},
            {"role": "user",
             "content": "That's incorrect, I need the prompts to talk more about describing the image instead of the "
                        "story. My content is about: In a cozy apartment, a mischievous orange cat named Oliver secretly plots to take over the world, while charming his handsome owner., make 6 prompts for that. Make sure to keep your prompts "
                        "purely about the composition of the scene. Keep it concise"},
            {"role": "assistant",
             "content": "1. an orange cat, on a windowsill, overlooking a city\n2. a pile of weapons, "
                        "swords and knives, in a corner\n3. The earth, an orange cat sitting on top\n4. a "
                        "orange cat, sitting in an apartment, looking out the window\n5. a musty basement, a machine "
                        "in the center, dark and dusty\n6. A handsome white man, an orange cat next to him, ruined city in "
                        "the background"},
            {"role": "user",
             "content": "Good job! Remember The image prompts should focus more on describing the image, rather then "
                        "describing the story itself. Also make sure"
                        "to describe and specify the gender and race in every prompt when possible. Don't add too many complicated parts to the "
                        "scene. And make it more concise. My content is about: In a nondescript setting, a male character named George, who is fit and attractive, overcomes his fear and bravely shares his incredible singing talent with the world during an open mic night at a local café., make 6 prompts for that."},
            {"role": "assistant",
             "content": "1. A fit attractive black man, holding a microphone, room full of instruments\n2. A dusty "
                        "room, cobwebs, microphone in the middle of the room\n3. One attractive black man, standing on "
                        "stage, people in foreground\n4. An attractive, black man, amongst musical instruments"
                        "\n5. A vibrant room, full of modern speakers, wires everywhere\n6. A portrait of a black man, handsome, smiling "},
            {"role": "user",
             "content": f"Great job! That's more of what I want to see. My new content is about: {prompt}. make 6 prompts for that? Keep them concise please"},
        ],
        temperature=0.77
    )
    total_tokens_usedP = response['usage']['total_tokens']
    price = (total_tokens_usedP / 1000) * .0015
    actualResponse = response['choices'][0]['message']['content']
    return actualResponse, price


def speak_text(text, tts_url):
    headers = {
        "Accept": "application/json",
        "xi-api-key": XI_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": .45,
            "similarity_boost": .75,
        }
    }
    response = requests.post(tts_url, json=data, headers=headers, stream=True)
    foName = f"output_{int(time.time())}"
    output_file = f"{foName}.mp3"

    file = open(output_file, 'wb')
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            file.write(chunk)
    file.close()
    return output_file, foName


def stable_api(prompt):
    url = "http://127.0.0.1:7860"
    negativePrompt = "Username, multiple images, watermark, extra limbs, mutated face, mutated eyes, ugly, mutated body, extra arms, extra legs, signature, lowres, text, error, bad anatomy, bad proportions "
    payload = {
        "prompt": prompt,
        "negative_prompt": negativePrompt,
        "cfg_scale": 10.5,
        "sd_model_checkpoint": "deliberate_v2.safetensors [9aba26abdf]",
        "steps": 45
    }

    response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)

    r = response.json()

    for i in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))

        png_payload = {
            "image": "data:image/png;base64," + i
        }
        response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", response2.json().get("info"))

        # Changed the save path here
        image.save(f'C:\\Users\\eggep\\PycharmProjects\\EthanAntonProject\\Images\\output_{int(time.time())}.png',
                   pnginfo=pnginfo)


def create_list(response):
    response_list = response.replace(".", "").split("\n")

    # Removing empty strings from the list and stripping the numbering
    response_list = [item.strip()[2:].strip() for item in response_list if item.strip() != ""]

    # Define the suffixes
    suffixes = [
        ", makoto shinkai, intricate,  greg rutkowski, highly detailed, oil painting, pastel, digital painting, "
        "artstation, concept art, sharp focus, illustration, by conrad roset, trending on artstation, concept art, "
        "soft lighting, moody",
        ", art by greg rutkowski, art by artgem, digital painting, artstation,  soft lighting, concept art, "
        "smooth soft lines, illustration, by Makoto Shinkai, peaceful, (best quality)",
    ]

    # Append each item in the response list with each suffix
    new_list = [item + suffix for item in response_list for suffix in suffixes]
    return new_list


def create_srt(file, foName):
    command = [
        "whisper",
        f'C:\\Users\\eggep\\PycharmProjects\\EthanAntonProject\\{file}',
        "--model",
        "small.en",
        "--language",
        "en",
        "--output_dir",
        "C:\\Users\\eggep\\PycharmProjects\\EthanAntonProject\\Whisper",
        "--word_timestamps",
        "True",
        "--output_format",
        "srt",
        "--highlight_words",
        "True",
        "--max_line_width",
        "25",
        "--max_line_count",
        "1"
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Check for errors
    if result.returncode != 0:
        print(f'Error occurred: {result.stderr.decode()}')
    else:
        print(f'Output: {result.stdout.decode()}')

    edit_srt_file(f"C:\\Users\\eggep\\PycharmProjects\\EthanAntonProject\\Whisper\\{foName}.srt")


def edit_srt_file(file_path):
    # Load the .srt file using pysrt
    subs = pysrt.open(file_path)

    # Identify the "sections" by checking the repeating sentences
    sections = []
    section = []
    prev_text = ''

    for sub in subs:
        if sub.text_without_tags == prev_text:
            section.append(sub)
        else:
            if section:
                sections.append(section)
            section = [sub]
        prev_text = sub.text_without_tags
    if section:
        sections.append(section)

    # List of color options
    color_options = ['AntiqueWhite', 'OrangeRed', 'Goldenrod', 'Gray', 'Tan']

    # Go through each section and modify the text
    for i, section in enumerate(sections):
        color = random.choice(color_options)  # Choose a random color at the start of the section
        for j, sub in enumerate(section):
            highlighted_words = re.findall(r'<u>(.*?)</u>', sub.text)
            if i % 3 != 2:  # We only change the first and second sections
                if highlighted_words:  # Only change if there's a highlighted word
                    # There's a 20% chance to wrap the text in color tags instead of removing the <u> tags
                    if random.random() < 0.2:
                        sub.text = ' '.join([f'<font color="{color}">{word}</font>' for word in highlighted_words])
                    else:
                        sub.text = ' '.join(highlighted_words)  # Keep only the underlined text, removing the <u> tags
                else:  # If there's no highlighted word, make the text empty
                    sub.text = ''
            else:  # In the third section, replace the <u> tags with the chosen tags
                tag = (f'<font color="{color}">', '</font>')  # Use the randomly chosen color
                if highlighted_words:  # Replace if there's a highlighted word
                    sub.text = re.sub(r'<u>(.*?)</u>', tag[0] + r'\1' + tag[1], sub.text)
                else:  # If there's no highlighted word, keep the original text (without any tags)
                    sub.text = sub.text_without_tags
    # Save the modified subtitles to a new .srt file
    subs.save('new_file.srt', encoding='utf-8')


def remove_mp4_files(image_folder):
    for file in os.listdir(image_folder):
        if file.endswith('.mp4'):
            os.remove(f"{image_folder}{file}")


def get_audio_duration(audio_path):
    audio = MP3(audio_path)
    return audio.info.length


def transition(sorted_images):
    if random.randint(1, 10) % 2 == 0:
        init_image = IMAGE_FOLDER + sorted_images
        vid = f'{init_image[0:-4]}new.mp4'
        cmd = ['ffmpeg', "-y", '-i', vid, "-vf", "reverse", f'{init_image[0:-4]}r.mp4']
        subprocess.run(cmd, check=True)
        os.remove(vid)


def create_video(audio_path):
    images = [img for img in os.listdir(IMAGE_FOLDER) if
              img.endswith(".png")]  # Checks if image is png and appends to list

    for i in range(len(images)):
        pan(IMAGE_FOLDER + images[i], audio_path)
        transition(images[i])


def pan(image_path, audio_path):
    # Load your image as a clip
    init_image = image_path
    image = ImageClip(image_path)

    # Determine the dimensions of the image
    width, height = image.size

    # Determine the width and height of the crop to match a 9:16 aspect ratio
    crop_width = min(width, height * 9 // 16)
    crop_height = crop_width * 16 // 9

    # Define a function for the sliding effect
    def make_frame(t):
        # Calculate the time for one full pan across an image based on audio duration and image number
        pan_time = audio_dur / image_num

        progress = t / pan_time  # progress of the pan
        crop_x = int(progress * (width - crop_width))  # x position of the crop's left edge

        # Create a cropped version of the image, representing the current "frame" of the video
        frame = crop(image, x1=crop_x, y1=0, width=crop_width, height=crop_height)

        return frame.img

    # Create a video clip using the sliding effect
    audio_dur = get_audio_duration(audio_path)
    images = [img for img in os.listdir(IMAGE_FOLDER) if
              img.endswith(".png")]  # Checks if image is png and appends to list
    image_num = len(images)
    duration = audio_dur / image_num
    panning_clip = VideoClip(make_frame, duration=duration)

    # Resize the video clip to match the size of a phone screen (1080x1920 pixels for Full HD)
    panning_clip = panning_clip.resize(height=1920)

    # Write the result to a file
    panning_clip.write_videofile(f'{init_image[0:-4]}new.mp4', fps=60)


def concat_videos():
    video_files = [f"{IMAGE_FOLDER}{file}" for file in os.listdir(IMAGE_FOLDER) if file.endswith('.mp4')]

    # Concatenate the video clips into one final clip
    with open('concat.txt', 'w') as f:
        for path in video_files:
            f.write(f"file '{path}'\n")

    command = ['ffmpeg', "-y", '-f', 'concat', '-safe', '0', '-i', 'concat.txt', '-c', 'copy', 'output.mp4']
    subprocess.run(command, check=True)


def add_subtitles():
    command = [
        "ffmpeg",
        "-y",
        "-i",
        "output.mp4",
        "-vf",
        "subtitles=new_file.srt:force_style='Fontname=Impact,PrimaryColour=&H00FFFFFF,Alignment=10,OutlineColour=&H00000000,BackColour=&H00000000,BorderStyle=1,Outline=2,Fontsize=16,Spacing=0.2,Shadow=.85'",
        "raw_output2.mp4"
    ]
    subprocess.run(command, check=True)


def add_audio_to_video(audio_path):
    command = ["ffmpeg","-i", f"{audio_path}", "-i", "raw_output2.mp4", "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", "output.mp4"]
    subprocess.run(command, check=True)

def speed_up_video(file, output_file, duration):
    if duration > 60:
        speed = duration / 60.0
        speed = round(speed, 2)
        # speed up video
        command = ['ffmpeg', '-i', file, '-vf', f'setpts={1/speed}*PTS', '-af', f'atempo={speed}', output_file]
        subprocess.run(command)
    else:
        pass

def clear_directory():
    dir_path = r'C:\Users\eggep\PycharmProjects\EthanAntonProject\Images'
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

def move_files_to_timestamped_folder(file1, file2):
    # create a timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')

    # define the directory path
    base_path = r"C:\Users\eggep\PycharmProjects\EthanAntonProject"
    new_folder_name = f'output_at_{timestamp}'
    new_folder_path = os.path.join(base_path, new_folder_name)

    # create the new directory
    os.makedirs(new_folder_path, exist_ok=True)

    # move the files
    try:
        shutil.move(file1, new_folder_path)
        shutil.move(file2, new_folder_path)
    except Exception as e:
        print(f"An error occurred while moving the files: {e}")
    else:
        print(f"Successfully moved files to {new_folder_path}.")

main()