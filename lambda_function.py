import os
import shutil
import stat
import srt
import re
import boto3

# Move the ffmpeg executable to a writable location (/tmp)
ffmpeg_bin = "/tmp/ffmpeg-linux64-v4.2.2"
shutil.copyfile('/opt/python/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2', ffmpeg_bin)
os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg_bin
os.chmod(ffmpeg_bin, os.stat(ffmpeg_bin).st_mode | stat.S_IEXEC)

from moviepy.editor import vfx, AudioFileClip, CompositeAudioClip, VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
from youtube_transcript_api.formatters import SRTFormatter
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube


def lambda_handler(event, context):
    link = event["link"]
    video_id = event["video_id"]
    bucket_name = event["bucket_name"]
    
    # DEFINE AUDIOCLIP
    audioclip = AudioFileClip("/opt/python/cybershort3.mp3")
    new_audioclip = CompositeAudioClip([audioclip])
    
    # GENERATE SUBTITLES
    formatter = SRTFormatter()
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    subtitles = formatter.format_transcript(transcript)
    subtitle_generator = srt.parse(subtitles)
    subtitles = list(subtitle_generator)

    # DOWNLOAD THE VIDEO
    yt = YouTube(link)
    mp4_files = yt.streams.filter(file_extension="mp4")
    mp4_360p_files = mp4_files.get_by_resolution("360p")
    downloaded_video = "your_video.mp4"
    mp4_360p_files.download(output_path="/tmp", filename=downloaded_video)
    downloaded_video = os.path.join("/tmp", "your_video.mp4")
    
    # CONSTANTS
    pattern = re.compile(r'.*c[ou]me[a-z]?')
    marg = 200
    delay = 6

    # array for storing videos
    video_clips = []

    # for each line in the subtitles
    for sub in subtitles:

        # if found match to 'cum'
        if re.findall(pattern, sub.content):
            try:
                # finds approximate # of seconds per word
                sec_per_word = (sub.end - sub.start)/len(sub.content.split())

                # create the subtitle for the matched scenes
                speech = re.findall(pattern, sub.content)[0]
                new_speech = re.sub(r'c[ou]me.*', ' cum', speech)
                if len(new_speech.split()) > 4:
                    new_temp = new_speech.split()
                    cumind = new_temp.index('cum')
                    new_speech = " ".join(new_temp[cumind-3:])

                # shorten the sentence based on the number of words and seconds for word
                n_words_before_come = len(speech[0].split())
                new_end = sub.start + sec_per_word*(n_words_before_come+delay)

                # open the video
                video = VideoFileClip(downloaded_video).subclip(f'{sub.start}', f'{new_end}')
                duration = 3
                # make clip from image
                clip2 = video.to_ImageClip(t=f'{duration}', duration=duration)
                # add margins
                clip2 = clip2.margin(10, color=(255, 255, 255))
                clip2 = clip2.margin(marg)
                # define audio clip
                clip2.audio = new_audioclip
                # fix the size
                clip2 = clip2.fx(vfx.resize, newsize=video.size)

                # define the text
                txt_clip = TextClip(txt=new_speech, fontsize = 40, color = 'white', stroke_width=2)  

                # set position and duration of text
                txt_clip = txt_clip.set_position("bottom").set_duration(duration)  

                # Overlay the text clip on the first video clip  
                video2 = CompositeVideoClip([clip2, txt_clip])

                # add the combined video and 'cum' scene to the array
                video_clips.append(concatenate_videoclips([video,video2], method='compose'))
            except:
                continue
                
    finale = concatenate_videoclips(video_clips)
    
    # extract and save the audio file
    audio = finale.audio
    audio.fps = 44100
    audio_path = os.path.join("/tmp", "my_new_audio.mp3")
    audio.write_audiofile(audio_path)
    
    # write the video to a file and attach the audiofile
    final_path = os.path.join("/tmp", "my_new_video.mp4")
    new_path = f"{'_'.join(yt.title.lower().split())}.mp4"
    finale.write_videofile(final_path, audio=audio_path)
    finale.close()

    # Upload the file to the S3 bucket
    s3 = boto3.client("s3")
    s3.upload_file(final_path, bucket_name, new_path)
    
    # create a download URL for the video
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': bucket_name,
            'Key': new_path
        },
        ExpiresIn=24 * 3600
    )
    
    return url
