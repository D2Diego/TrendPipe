import itertools
import io
import os
import random
import gc
import subprocess
import sys
import tempfile
import unicodedata
from contextlib import ExitStack, redirect_stdout
from functools import lru_cache
from typing import List
from loguru import logger
import numpy as np
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    afx,
)
from moviepy.video.tools.subtitles import SubtitlesClip
from PIL import Image, ImageDraw, ImageFont

from app.config import config
from app.models import const
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services import bgm as bgm_service
from app.services.utils import video_effects
from app.utils import file_security, utils

class SubClippedVideoClip:
    def __init__(
        self,
        file_path,
        start_time=None,
        end_time=None,
        width=None,
        height=None,
        duration=None,
        source_file_path=None,
    ):
        self.file_path = file_path
        self.start_time = start_time
        self.end_time = end_time
        self.width = width
        self.height = height
        self.source_file_path = source_file_path or file_path
        if duration is None:
            self.duration = end_time - start_time
        else:
            self.duration = duration

    def __str__(self):
        return f"SubClippedVideoClip(file_path={self.file_path}, start_time={self.start_time}, end_time={self.end_time}, duration={self.duration}, width={self.width}, height={self.height})"


audio_codec = "aac"
# Docker Lee. ffmpeg/AAC The group is more susceptible to audio quality fluctuations under default configurations.
# Here you can raise the audio frequency to avoid introducing a significant distortion at the fractional stage because the default value is too low.
audio_bitrate = "192k"
fps = 30
# FFmpeg Collapse by Frame Rate/At the end, the time may be longer. MoviePy The theory read in dozens of milliseconds.
# Here's an extra small amount of security for the video material to avoid a black screen at the end of the audio because of the frame.
# There is no picture of the situation in Cardon or the last subsection.
_VIDEO_DURATION_SAFETY_MARGIN = 0.1
_MIN_MATERIAL_DIMENSION = 480
# Message applications and partial encoders take the image down, for example. WhatsApp Yes. 9:16 Yes.
# Material pressured. 478x850，That's right. 480 Two pixels less. Press directly 480 The hard card will get all this stuff.
# Drop it and finally... "no valid materials found" Total failure. Here's a very small difference.
# The release of material that is slightly below the threshold merely because it is fine-tuned still holds back the real low-level material.
_MIN_DIMENSION_TOLERANCE = 10
_DEFAULT_VIDEO_CODEC = "libx264"
_SUPPORTED_VIDEO_CODECS = (
    "libx264",
    "h264_nvenc",
    "h264_amf",
    "h264_qsv",
    "h264_mf",
    "h264_videotoolbox",
)
_runtime_disabled_video_codecs = set()


def _get_required_video_duration(audio_duration: float) -> float:
    """
    Returns the target time for which the video material is fusion.

    Use of scenery: The material is required to overwhelm the background. Just "just equals"
    It's a long time.FFmpeg Maybe because the frame rate is rounded to the final video is a little short, so one more is added.
    Light balance. The function is independent and allows testing and subsequent adjustment of the residual size to actual feedback.
    """
    return max(0.0, float(audio_duration) + _VIDEO_DURATION_SAFETY_MARGIN)


def is_material_resolution_acceptable(width: int, height: int) -> bool:
    """
    Determines whether the material resolution is sufficient for synthesis.

    Named Minimum 480x480，But it's allowed lower. `_MIN_DIMENSION_TOLERANCE` A pixel,
    To Compatible Encoder/The message should be taken down (e.g. WhatsApp Yes. 478x850）。
    """
    min_dimension = _MIN_MATERIAL_DIMENSION - _MIN_DIMENSION_TOLERANCE
    return width >= min_dimension and height >= min_dimension


def _prioritize_unique_source_clips(
    subclipped_items: List[SubClippedVideoClip],
    concat_mode: VideoConcatMode,
) -> List[SubClippedVideoClip]:
    """
    Priority should be given to each source material only once, reducing the probability of recurrence of the same material in the film.

    Online material is often subject to “one long video is cut into several short clips”. The old logic is
    random Directly disrupt all short clips in mode leading to multiple slices of the same source video
    The distribution is at the beginning and in the middle, and users feel that the material is duplicated. This function only adjusts the order of the clips:
    One of the longest pieces in each source file, the rest of which is used as the background; when the material is not long enough, it's a little bit longer.
    Follow-up clips are still allowed to complete the audio length and avoid disrupting the video generation success rate. Maximum Priority
    The clips were designed to avoid random selection of small fragments at the end of the video, leading to premature re-use of the material when there was sufficient material.
    """
    if not subclipped_items:
        return []

    concat_mode_value = getattr(concat_mode, "value", concat_mode)
    if concat_mode_value != VideoConcatMode.random.value:
        return subclipped_items

    grouped_items: dict[str, list[SubClippedVideoClip]] = {}
    for item in subclipped_items:
        grouped_items.setdefault(item.source_file_path, []).append(item)

    primary_items = []
    overflow_items = []
    for items in grouped_items.values():
        primary_item = max(items, key=lambda item: item.duration)
        primary_items.append(primary_item)
        overflow_items.extend(item for item in items if item is not primary_item)

    random.shuffle(primary_items)
    random.shuffle(overflow_items)
    logger.info(
        "prioritized unique video materials, "
        f"sources: {len(grouped_items)}, "
        f"primary clips: {len(primary_items)}, "
        f"fallback clips: {len(overflow_items)}"
    )
    return primary_items + overflow_items


def get_ffmpeg_binary():
    """
    From history. video Service Reading FFmpeg path.

    The real resolution logic has been drawn. `app.utils.utils.get_ffmpeg_binary()`，Video, voice
    The same set of priorities should be used for both subsequent new links; this should be kept in thin packaging to avoid external scripts or
    Old Test Direct Import `app.services.video.get_ffmpeg_binary` It happens. AttributeError。
    """
    return utils.get_ffmpeg_binary()


def _get_configured_video_codec() -> str:
    """
    Reads the user-configured video encoder.

    This configuration is for advanced users and is used to try to enable NVENC/AMF/QSV/VideoToolbox Waiting for hardware
    code. This is a place where only fixed white lists are allowed. FFmpeg Error after argument
    Parameters lead to uncontrollable output formats and even allow the generation task to fail at a subsequent stage.
    """
    configured_codec = str(
        config.app.get("video_codec", _DEFAULT_VIDEO_CODEC) or _DEFAULT_VIDEO_CODEC
    ).strip()
    if configured_codec not in _SUPPORTED_VIDEO_CODECS:
        logger.warning(
            f"unsupported video codec configured: {configured_codec}, "
            f"fallback to {_DEFAULT_VIDEO_CODEC}"
        )
        return _DEFAULT_VIDEO_CODEC
    return configured_codec


@lru_cache(maxsize=16)
def _ffmpeg_encoder_exists(ffmpeg_binary: str, codec: str) -> bool:
    """
    Check Current FFmpeg Whether or not to declare support for the specified encoder.

    That's proof. FFmpeg Include the encoder，Can't prove current machine hardware and drive
    It's got to work. So if the actual code fails, it's still back. libx264。
    """
    try:
        result = subprocess.run(
            [ffmpeg_binary, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning(
            "failed to inspect ffmpeg encoders, "
            f"fallback to {_DEFAULT_VIDEO_CODEC}: {str(exc)}"
        )
        return False

    if result.returncode != 0:
        logger.warning(
            "failed to inspect ffmpeg encoders, "
            f"fallback to {_DEFAULT_VIDEO_CODEC}: {(result.stderr or result.stdout or '').strip()}"
        )
        return False
    return codec in result.stdout


def _get_effective_video_codec(preferred_codec: str | None = None) -> str:
    """
    Returns the video encoder that is actually used.

    User selects the hardware encoder, first FFmpeg encoder list detection;if this process already exists
    The actual code failed and returned directly, avoiding the repetition of each segment of a task.
    """
    selected_codec = preferred_codec or _get_configured_video_codec()
    if selected_codec == _DEFAULT_VIDEO_CODEC:
        return _DEFAULT_VIDEO_CODEC

    if selected_codec in _runtime_disabled_video_codecs:
        logger.warning(
            f"video codec {selected_codec} was disabled after a runtime failure, "
            f"fallback to {_DEFAULT_VIDEO_CODEC}"
        )
        return _DEFAULT_VIDEO_CODEC

    ffmpeg_binary = utils.get_ffmpeg_binary()
    if not _ffmpeg_encoder_exists(ffmpeg_binary, selected_codec):
        logger.warning(
            f"ffmpeg encoder {selected_codec} is not available, "
            f"fallback to {_DEFAULT_VIDEO_CODEC}"
        )
        return _DEFAULT_VIDEO_CODEC

    return selected_codec


def _disable_runtime_video_codec(codec: str, reason: str):
    if codec == _DEFAULT_VIDEO_CODEC:
        return
    _runtime_disabled_video_codecs.add(codec)
    logger.warning(
        f"video codec {codec} failed, fallback to {_DEFAULT_VIDEO_CODEC}. "
        f"reason: {reason}"
    )


def _get_temp_audio_dir(output_dir: str) -> str:
    """
    Return the directory to use for MoviePy's temporary audio file.

    On Windows, Windows Defender can lock files written to the task output
    directory while scanning them, causing MoviePy to fail with a
    PermissionError (WinError 32) on the TEMP_MPY_wvf_snd temp file and
    leaving the final MP4 at 0 bytes.  Using the system temp directory
    sidesteps the scan without changing behaviour on other platforms.

    On Linux/macOS/Docker the output directory is returned unchanged so
    existing behaviour is preserved.
    """
    if sys.platform == "win32":
        return tempfile.gettempdir()
    return output_dir


def _fallback_write_videofile(clip, output_file: str, failed_codec: str, reason: str, **kwargs):
    """
    Hardware encoding failed libx264 Retry, only a successful retest will disable the hardware encoder.

    Windows Let's go. FFmpeg Reasons for failure are complex: maybe graphic cards./Driving not supported, or output
    Document occupancy, directory access, soft-kill interception, etc. IO Problem. Only libx264 I’m not sure if I can write it.
    It is possible to judge the original failure rate from the hardware encoder itself and avoid error in subsequent assignments.
    """
    clip.write_videofile(output_file, codec=_DEFAULT_VIDEO_CODEC, **kwargs)
    _disable_runtime_video_codec(failed_codec, reason)
    return _DEFAULT_VIDEO_CODEC


def _write_videofile_with_codec_fallback(clip, output_file: str, codec: str, **kwargs):
    """
    Write video using the specified encoder, automatically when failed libx264 Try again.

    The availability of the hardware encoder depends not only on FFmpeg，It also depends on the graphic card, the driver and the current operating environment.
    The generation of tasks cannot fail as a whole because the advanced encoder is not available, so here you can return to focus.
    """
    effective_codec = _get_effective_video_codec(codec)
    try:
        clip.write_videofile(output_file, codec=effective_codec, **kwargs)
        return effective_codec
    except Exception as exc:
        if effective_codec == _DEFAULT_VIDEO_CODEC:
            raise
        return _fallback_write_videofile(
            clip,
            output_file,
            failed_codec=effective_codec,
            reason=str(exc),
            **kwargs,
        )


def _escape_ffmpeg_concat_path(file_path: str) -> str:
    # concat demuxer The path of the package using a single quotation sign requires a first-hand transposition of the single quotation sign in the path.
    return file_path.replace("'", "'\\''")


def _format_ffmpeg_concat_path(file_path: str) -> str:
    """
    Generate concat demuxer path in the file list.

    FFmpeg Official documentation requirements concat list Special characters and spaces in them need to be converted;Windows
    A backslash in an absolute path is also easy to interpret to a transliteration character. Here's a uniform slash.
    Jean. `C:\\Users\\...` ♪ Turn into ♪ `C:/Users/...`，Reprocess single quotes, compatible. macOS/Linux。
    """
    absolute_path = os.path.abspath(file_path)
    return _escape_ffmpeg_concat_path(absolute_path.replace("\\", "/"))


def concat_video_clips_with_ffmpeg(
    clip_files: List[str],
    output_file: str,
    threads: int,
    output_dir: str,
    max_duration: float | None = None,
):
    concat_list_file = os.path.join(output_dir, "ffmpeg-concat-list.txt")
    with open(concat_list_file, "w", encoding="utf-8") as fp:
        for clip_file in clip_files:
            fp.write(f"file '{_format_ffmpeg_concat_path(clip_file)}'\n")

    def build_command(codec: str) -> list[str]:
        command = [
            utils.get_ffmpeg_binary(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_file,
            "-c:v",
            codec,
            "-threads",
            str(threads or 2),
            "-pix_fmt",
            "yuv420p",
        ]
        if max_duration is not None and max_duration > 0:
            command.extend(["-t", f"{max_duration:.3f}"])
        command.append(output_file)
        return command

    def run_concat(codec: str):
        command = build_command(codec)
        # Use ffmpeg Do a serial and code only once, avoid MoviePy It's been recoded over and over again when we merge paragraphs.
        # This reduces the risk of poor quality and colour deviation.
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            error_message = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(error_message or "ffmpeg concat failed")
        return codec

    try:
        effective_codec = _get_effective_video_codec()
        try:
            return run_concat(effective_codec)
        except Exception as exc:
            if effective_codec == _DEFAULT_VIDEO_CODEC:
                raise
            result_codec = run_concat(_DEFAULT_VIDEO_CODEC)
            _disable_runtime_video_codec(effective_codec, str(exc))
            return result_codec
    finally:
        delete_files(concat_list_file)


def _sanitize_image_file(image_path: str) -> str:
    # Some local pictures can be used. Pillow Open it, but it'll be damaged. EXIF/eXIf Metadata Cause
    # ImageClip Directly remove anomalies at the resolution stage. Here's to re-export a clean picture, strip out the bad metadata.
    image_root, _ = os.path.splitext(image_path)
    sanitized_path = f"{image_root}.sanitized.png"

    with Image.open(image_path) as image:
        image.load()
        # Harmonize Export As PNG，Avoid JPEG/PNG Different metadata paths continue to bring the bad pieces over.
        cleaned_image = Image.new(image.mode, image.size)
        cleaned_image.putdata(list(image.getdata()))
        cleaned_image.save(sanitized_path)

    return sanitized_path


def _open_image_clip_with_fallback(image_path: str):
    # Priority is given to opening the original picture directly; if damage to metadata fails, try to generate a copy of the non-metadata.
    try:
        return ImageClip(image_path), image_path
    except Exception as exc:
        logger.warning(
            f"failed to open image directly, trying sanitized copy: {image_path}, error: {str(exc)}"
        )
        sanitized_path = _sanitize_image_file(image_path)
        return ImageClip(sanitized_path), sanitized_path


def _open_video_clip_quietly(video_path: str, audio: bool = False) -> VideoFileClip:
    """
    Open video files quietly, avoid. MoviePy 2.1.x Put ffmpeg Detection information printed directly to stdout。

    Background:
    Current version-dependent `FFMPEG_VideoReader` Internal presence `print(self.infos)` and
    `print(ffmpeg command)`，Output when reading an intermediate video without track
    `audio_found: False`。It's just input material. metadata，It doesn't mean there's no audio in the end.
    But it's misleading. WebUI/The end user thinks the generation failed.

    Achieved:
    1. Only open VideoFileClip Redirect within short windows stdout；
    2. Default `audio=False`，The project's video content phase does not need to keep the originals.
       And eventually, the audio will be... `generate_video()` Unified stage mount;
    3. If relying on the library does output content, downgrade it to debug Logs, allowing for check-ups, if necessary.
    """
    captured_stdout = io.StringIO()
    with redirect_stdout(captured_stdout):
        clip = VideoFileClip(video_path, audio=audio)

    moviepy_stdout = captured_stdout.getvalue().strip()
    if moviepy_stdout:
        logger.debug(
            "suppressed MoviePy video reader stdout for "
            f"{video_path}, chars: {len(moviepy_stdout)}"
        )

    return clip


def close_clip(clip):
    if clip is None:
        return
        
    try:
        # close main resources
        if hasattr(clip, 'reader') and clip.reader is not None:
            clip.reader.close()
            
        # close audio resources
        if hasattr(clip, 'audio') and clip.audio is not None:
            if hasattr(clip.audio, 'reader') and clip.audio.reader is not None:
                clip.audio.reader.close()
            del clip.audio
            
        # close mask resources
        if hasattr(clip, 'mask') and clip.mask is not None:
            if hasattr(clip.mask, 'reader') and clip.mask.reader is not None:
                clip.mask.reader.close()
            del clip.mask
            
        # handle child clips in composite clips
        if hasattr(clip, 'clips') and clip.clips:
            for child_clip in clip.clips:
                if child_clip is not clip:  # avoid possible circular references
                    close_clip(child_clip)
            
        # clear clip list
        if hasattr(clip, 'clips'):
            clip.clips = []
            
    except Exception as e:
        logger.error(f"failed to close clip: {str(e)}")
    
    del clip
    gc.collect()

def delete_files(files: List[str] | str):
    if isinstance(files, str):
        files = [files]

    # When recycles the video, the same temporary segment path will be FFmpeg The spell list appears repeatedly.
    # Collapse must keep duplicate entries, but clean-up can only be deleted once; here the weight should be done in the same order, so that all
    # Callers get behaviors like thorium and avoid first-time deletion and successive output FileNotFoundError。
    unique_files = dict.fromkeys(file for file in files if file)
    for file in unique_files:
        try:
            os.remove(file)
        except FileNotFoundError:
            # Cleanup action allows files to no longer exist, for example FFmpeg Failed path or simultaneous cleanup already
            # Recycle files; this is not an issue for users and should not contaminate the generation log.
            continue
        except OSError as e:
            # Permissions, read-only filesystems or disk anomalies leave real temporary files and retain them warning
            # To facilitate the targeting of environmental problems based on specific pathways and system errors.
            logger.warning(f"failed to delete temporary file {file}: {str(e)}")


def get_bgm_file(bgm_type: str = "random", bgm_file: str = ""):
    if not bgm_type:
        return ""

    if bgm_file:
        try:
            resolved_bgm_file = bgm_service.resolve_bgm_file(bgm_file)
        except ValueError as exc:
            # API In the request. bgm_file From user input, only allow parsing to user BGM Or embedded
            # Sing directory, stop MoviePy Reads any server file such as configuration, key, etc.
            logger.warning(
                f"reject unsafe bgm file: {bgm_file}, error: {str(exc)}"
            )
            return ""
        return resolved_bgm_file

    if bgm_type == "random":
        files = bgm_service.list_bgm_files()
        # When background music directories are empty, go back to 'no' BGM”，Avoid random.choice([]) Drop the anomaly.
        if not files:
            logger.warning("no background music files found")
            return ""
        return random.choice(files)

    return ""


def combine_videos(
    combined_video_path: str,
    video_paths: List[str],
    audio_file: str,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_concat_mode: VideoConcatMode = VideoConcatMode.random,
    video_transition_mode: VideoTransitionMode = None,
    max_clip_duration: int = 5,
    threads: int = 2,
    clip_speed: float = 1.0,
) -> str:
    audio_clip = AudioFileClip(audio_file)
    try:
        # All we have to do here is read the adhesive audio to determine the length of the material's video fusion; it won't be used again.
        # audio_clip。Closes immediately after reading has been completed to avoid early retreat or an abnormal path leaking the file handle.
        audio_duration = audio_clip.duration
    finally:
        close_clip(audio_clip)
    logger.info(f"audio duration: {audio_duration} seconds")
    logger.info(f"maximum clip duration: {max_clip_duration} seconds")
    required_video_duration = _get_required_video_duration(audio_duration)
    logger.info(
        f"required video duration: {required_video_duration:.2f} seconds "
        f"(audio duration + {_VIDEO_DURATION_SAFETY_MARGIN:.2f}s safety margin)"
    )

    # Compatibility API Non-transmission mode when directly called, avoiding follow-up visits .value When it crashes.
    transition_value = getattr(video_transition_mode, "value", video_transition_mode)
    normalized_clip_speed = utils.normalize_clip_speed(clip_speed)
    if normalized_clip_speed != 1.0:
        # Only one final effective value is recorded, which facilitates positioning API The issue of the integration of transboundary parameters,
        # Do not repeat the same log in the swath-by-shot path.
        logger.info(f"clip playback speed: {normalized_clip_speed:.2f}x")
    # max_clip_duration It's the final play time in the film, not the reading time in the source video.
    # MoviePy Here. 0.5 Play speed 1.5 The second source will get it. 3 Second Snippets 2 Play speed
    # 6 The second-source images will get the same. 3 Snippets. Therefore, the length of time must be reversed at speed before the slice is cut; if
    # Still Fixed Read 3 Slow down and cut the second from the source. 3 The second starts, it skips the middle.
    # 1.5 Second image. This calculation also ensures continuity and non-duplication of the source time line at different speeds.
    source_clip_duration = max_clip_duration * normalized_clip_speed
    output_dir = os.path.dirname(combined_video_path)

    aspect = VideoAspect(video_aspect)
    video_width, video_height = aspect.to_resolution()

    processed_clips = []
    subclipped_items = []
    video_duration = 0
    for video_path in video_paths:
        clip = _open_video_clip_quietly(video_path)
        clip_duration = clip.duration
        clip_w, clip_h = clip.size
        close_clip(clip)
        
        start_time = 0

        while start_time < clip_duration:
            end_time = min(start_time + source_clip_duration, clip_duration)

            # Retain all valid subparagraphs.
            # So it doesn't lose the whole video itself. max_clip_duration”The material,
            # And I'm not going to swallow the last little part of the long video.
            if end_time > start_time:
                subclipped_items.append(
                    SubClippedVideoClip(
                        file_path=video_path,
                        start_time=start_time,
                        end_time=end_time,
                        width=clip_w,
                        height=clip_h,
                        source_file_path=video_path,
                    )
                )

            start_time = end_time
            if video_concat_mode.value == VideoConcatMode.sequential.value:
                break

    subclipped_items = _prioritize_unique_source_clips(
        subclipped_items=subclipped_items,
        concat_mode=video_concat_mode,
    )
        
    logger.debug(f"total subclipped items: {len(subclipped_items)}")
    
    # Add downloaded clips over and over until the duration of the audio (max_duration) has been reached
    for i, subclipped_item in enumerate(subclipped_items):
        if video_duration >= required_video_duration:
            break
        
        logger.debug(
            f"processing clip {i+1}: {subclipped_item.width}x{subclipped_item.height}, "
            f"source: {os.path.basename(subclipped_item.source_file_path)}, "
            f"current duration: {video_duration:.2f}s, "
            f"remaining: {required_video_duration - video_duration:.2f}s"
        )
        
        try:
            clip = _open_video_clip_quietly(subclipped_item.file_path).subclipped(
                subclipped_item.start_time, subclipped_item.end_time
            )
            # Play speed is an attribute of the material itself and should be applied before the switch. Here. Fade/Slide Wait a second.
            # It doesn't follow the speed of the material. 0.5 seconds or 2 seconds;the next maximum length crop continues as
            # (c) A security wall with a long period of error or abnormal material at the float point to ensure that the final segment does not exceed the configuration ceiling.
            if normalized_clip_speed != 1.0:
                clip = clip.with_speed_scaled(normalized_clip_speed)
            clip_duration = clip.duration
            # Not all videos are same size, so we need to resize them
            clip_w, clip_h = clip.size
            if clip_w != video_width or clip_h != video_height:
                clip_ratio = clip.w / clip.h
                video_ratio = video_width / video_height
                logger.debug(f"resizing clip, source: {clip_w}x{clip_h}, ratio: {clip_ratio:.2f}, target: {video_width}x{video_height}, ratio: {video_ratio:.2f}")
                
                if clip_ratio == video_ratio:
                    clip = clip.resized(new_size=(video_width, video_height))
                else:
                    if clip_ratio > video_ratio:
                        scale_factor = video_width / clip_w
                    else:
                        scale_factor = video_height / clip_h

                    new_width = int(clip_w * scale_factor)
                    new_height = int(clip_h * scale_factor)

                    background = ColorClip(size=(video_width, video_height), color=(0, 0, 0)).with_duration(clip_duration)
                    clip_resized = clip.resized(new_size=(new_width, new_height)).with_position("center")
                    clip = CompositeVideoClip([background, clip_resized])
                    
            shuffle_side = random.choice(["left", "right", "top", "bottom"])
            if transition_value in (None, VideoTransitionMode.none.value):
                clip = clip
            elif transition_value == VideoTransitionMode.fade_in.value:
                clip = video_effects.fadein_transition(clip, 1)
            elif transition_value == VideoTransitionMode.fade_out.value:
                clip = video_effects.fadeout_transition(clip, 1)
            elif transition_value == VideoTransitionMode.slide_in.value:
                clip = video_effects.slidein_transition(clip, 1, shuffle_side)
            elif transition_value == VideoTransitionMode.slide_out.value:
                clip = video_effects.slideout_transition(clip, 1, shuffle_side)
            elif transition_value == VideoTransitionMode.zoom_in.value:
                clip = video_effects.zoomin_transition(clip, 1)
            elif transition_value == VideoTransitionMode.zoom_out.value:
                clip = video_effects.zoomout_transition(clip, 1)
            elif transition_value == VideoTransitionMode.shuffle.value:
                transition_funcs = [
                    lambda c: video_effects.fadein_transition(c, 1),
                    lambda c: video_effects.fadeout_transition(c, 1),
                    lambda c: video_effects.slidein_transition(c, 1, shuffle_side),
                    lambda c: video_effects.slideout_transition(c, 1, shuffle_side),
                    lambda c: video_effects.zoomin_transition(c, 1),
                    lambda c: video_effects.zoomout_transition(c, 1),
                ]
                shuffle_transition = random.choice(transition_funcs)
                clip = shuffle_transition(clip)

            if clip.duration > max_clip_duration:
                clip = clip.subclipped(0, max_clip_duration)
                
            # wirte clip to temp file
            clip_file = f"{output_dir}/temp-clip-{i+1}.mp4"
            _write_videofile_with_codec_fallback(
                clip,
                clip_file,
                codec=_get_configured_video_codec(),
                logger=None,
                fps=fps,
            )

            # Store clip duration before closing
            clip_duration_saved = clip.duration
            close_clip(clip)

            processed_clips.append(
                SubClippedVideoClip(
                    file_path=clip_file,
                    duration=clip_duration_saved,
                    width=clip_w,
                    height=clip_h,
                    source_file_path=subclipped_item.source_file_path,
                )
            )
            video_duration += clip_duration_saved
            
        except Exception as e:
            logger.error(f"failed to process clip: {str(e)}")
    
    # loop processed clips until the video duration covers the audio duration and the small safety margin.
    if video_duration < required_video_duration:
        logger.warning(
            f"video duration ({video_duration:.2f}s) is shorter than required duration "
            f"({required_video_duration:.2f}s), looping clips to match audio length."
        )
        base_clips = processed_clips.copy()
        for clip in itertools.cycle(base_clips):
            if video_duration >= required_video_duration:
                break
            processed_clips.append(clip)
            video_duration += clip.duration
        logger.info(
            f"video duration: {video_duration:.2f}s, audio duration: {audio_duration:.2f}s, "
            f"required duration: {required_video_duration:.2f}s, "
            f"looped {len(processed_clips)-len(base_clips)} clips"
        )
     
    # merge video clips progressively, avoid loading all videos at once to avoid memory overflow
    logger.info("starting clip merging process")
    if not processed_clips:
        logger.warning("no clips available for merging")
        return combined_video_path
    
    clip_files = [clip.file_path for clip in processed_clips]
    logger.info(f"concatenating {len(clip_files)} clips with ffmpeg")
    concat_video_clips_with_ffmpeg(
        clip_files=clip_files,
        output_file=combined_video_path,
        threads=threads,
        output_dir=output_dir,
        max_duration=audio_duration,
    )
    
    # clean temp files
    delete_files(clip_files)
            
    logger.info("video combining completed")
    return combined_video_path


def wrap_text(text, max_width, font="Arial", fontsize=60):
    # Subtitles must really be created TextClip Done before, otherwise MoviePy Press original text only
    # Calculates the rendering area. Here. PIL Measurement of width by current font and font to ensure that every line is as wide as possible
    # Controls the width of the video to avoid a direct spill of large characters or Chinese long sentences.
    font = ImageFont.truetype(font, fontsize)
    max_width = int(max_width)

    def get_text_size(inner_text):
        inner_text = inner_text.strip()
        if not inner_text:
            return 0, fontsize
        left, top, right, bottom = font.getbbox(inner_text)
        return right - left, bottom - top

    width, height = get_text_size(text)
    if width <= max_width:
        return text, height

    def split_long_token(token):
        # ♪ When one ♪ token It is a very broad time in itself (often in Chinese without spaces, or in English with a long word).
        # Declines to character level splits. The key point is: detected candidate When it's too wide, submit the last one.
        # It's still legal. current，If you insert the current character in the next line, you cannot insert the hyperwide character back into the previous line.
        lines = []
        current = ""
        for char in token:
            candidate = f"{current}{char}"
            candidate_width, _ = get_text_size(candidate)
            if candidate_width <= max_width or not current:
                current = candidate
                continue
            lines.append(current)
            current = char
        if current:
            lines.append(current)
        return lines

    lines = []
    current = ""
    words = text.split(" ")
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        candidate_width, _ = get_text_size(candidate)
        if candidate_width <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)

        word_width, _ = get_text_size(word)
        if word_width <= max_width:
            current = word
        else:
            lines.extend(split_long_token(word))
            current = ""

    if current:
        lines.append(current)

    line_start_punctuation = "，。！？；：、,.!?;:)]}）】》」』”’"
    for index in range(1, len(lines)):
        # When the Chinese long sentence is divided by character, the last closed point, such as period, commas, may be separated
        # Put it in the next line, which leads to an abnormally high subtitling background.
        # Down there. This is the last word in the previous line without redesigning the line-to-line algorithm.
        # Moves to front of the pointer line so that the pointer follows the text and is compatible with the usual closed point in English.
        if not lines[index] or lines[index][0] not in line_start_punctuation:
            continue
        if len(lines[index - 1]) <= 1:
            continue

        candidate = f"{lines[index - 1][-1]}{lines[index]}"
        candidate_width, _ = get_text_size(candidate)
        if candidate_width <= max_width:
            lines[index] = candidate
            lines[index - 1] = lines[index - 1][:-1]

    result = "\n".join(line.strip() for line in lines if line.strip()).strip()
    height = len(lines) * height
    return result, height


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    # Subtitle background color from API/WebUI argument, may be empty or format irregular. It's only accepted here.
    # #RRGGBB Form, illicit value back to black, avoid PIL The rendering phase throws an abnormally interrupted task.
    if isinstance(color, str) and color.startswith("#") and len(color) == 7:
        try:
            return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))
        except ValueError:
            pass
    return (0, 0, 0)


def _rounded_subtitle_background_clip(
    width: int,
    height: int,
    color: str,
    alpha: int = 140,
    radius: int = 16,
) -> ImageClip:
    # The new subtitle background is only used when user visible: by RGBA Images draw round corners of translucent floors.
    # Give it back. MoviePy As Transparency ImageClip Participation in synthesis. The default path is completely unchanged.
    # At the same time, you can experiment with softer subtitle visual effects at low cost.
    rgb = _hex_to_rgb(color)
    safe_alpha = max(0, min(255, int(alpha)))
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [0, 0, max(0, width - 1), max(0, height - 1)],
        radius=max(0, int(radius)),
        fill=(rgb[0], rgb[1], rgb[2], safe_alpha),
    )
    return ImageClip(np.array(img), transparent=True)


def _get_visible_center_position(
    text_clip: TextClip,
    container_width: int,
    container_height: int,
) -> tuple[int, int]:
    """
    Press the text for real visible pixels TextClip Put it in the center of the background container.

    MoviePy Yes. TextClip It's fine by font line. baseline Creates a transparent canvas. A lot of fonts.
    Visible fonts are not at the geometry center of this canvas. `with_position("center")`
    It puts the whole picture of transparency in the middle, causing the subtitles to look up or down. Read here TextClip
    Transparency mask，Based on actual pixels. bbox Calculating text offsets for viewing by users
    Visualization in the subtitle background.
    """
    x = int(round((container_width - text_clip.w) / 2))
    y = int(round((container_height - text_clip.h) / 2))

    try:
        if text_clip.mask is None:
            return x, y

        mask_frame = text_clip.mask.get_frame(0)
        ys, _ = np.where(mask_frame > 0.01)
        if len(ys) == 0:
            return x, y

        visible_top = int(ys.min())
        visible_bottom = int(ys.max())
        visible_height = visible_bottom - visible_top + 1
        y = int(round((container_height - visible_height) / 2 - visible_top))
    except Exception as exc:
        logger.debug(f"failed to center subtitle text by visible mask: {str(exc)}")

    return x, y


def subtitle_colors_are_indistinguishable(params: VideoParams) -> bool:
    """To determine whether subtitle text and background are the same, the user is reminded that subtitles may not be visible."""
    if not params.subtitle_enabled or not params.text_background_color:
        return False

    def normalize_color(value):
        if isinstance(value, bool):
            return "#000000" if value else ""
        return str(value or "").strip().lower()

    text_color = normalize_color(params.text_fore_color)
    background_color = normalize_color(params.text_background_color)
    return bool(text_color and text_color == background_color)


@lru_cache(maxsize=64)
def _subtitle_font_supports_sample(font_path: str, sample: str) -> bool:
    """Checks if the font contains the fonts required for the sample text and caches the duplicate check results."""
    try:
        font = ImageFont.truetype(font_path, 30)
        missing_mask = font.getmask("\U0010ffff")
        missing_signature = (
            missing_mask.size,
            missing_mask.getbbox(),
            bytes(missing_mask),
        )
        for char in sample:
            char_mask = font.getmask(char)
            char_signature = (
                char_mask.size,
                char_mask.getbbox(),
                bytes(char_mask),
            )
            if char_mask.getbbox() is None or char_signature == missing_signature:
                return False
        return True
    except Exception as e:
        # Font detection failure should not prevent the user from generating; logs should be kept for environmental compatibility screening.
        logger.warning(f"failed to inspect subtitle font glyphs: {font_path}, {e}")
        return True


def subtitle_font_supports_text(font_path: str, text: str) -> bool:
    """Checks if fonts can draw letters and numbers in text, ignoring blanks and labels."""
    sample = "".join(
        dict.fromkeys(
            char
            for char in str(text or "")
            if unicodedata.category(char)[0] in {"L", "N"}
        )
    )[:64]
    if not sample:
        return True
    return _subtitle_font_supports_sample(font_path, sample)


def generate_video(
    video_path: str,
    audio_path: str,
    subtitle_path: str,
    output_file: str,
    params: VideoParams,
    bgm_file_override: str | None = None,
) -> bool:
    """
    Synthesizes the final video and returns the success of this background music processing.

    Return value only BGM Processing status: No request BGM returns when mixed successfully True；Please.
    BGM But return when loading, effects or mixing failed False。Even BGM If you fail, you continue to export only
    Narrative video that allows the task group to decide whether or not to display a downgrade warning to the user.
    """
    aspect = VideoAspect(params.video_aspect)
    video_width, video_height = aspect.to_resolution()

    logger.info(f"generating video: {video_width} x {video_height}")
    logger.info(f"  ① video: {video_path}")
    logger.info(f"  ② audio: {audio_path}")
    logger.info(f"  ③ subtitle: {subtitle_path}")
    logger.info(f"  ④ output: {output_file}")

    # https://github.com/harry0703/MoneyPrinterTurbo/issues/217
    # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'final-1.mp4.tempTEMP_MPY_wvf_snd.mp3'
    # write into the same directory as the output file
    output_dir = os.path.dirname(output_file)

    font_path = ""
    if params.subtitle_enabled:
        if not params.font_name:
            params.font_name = "STHeitiMedium.ttc"
        font_path = os.path.join(utils.font_dir(), params.font_name)
        if os.name == "nt":
            font_path = font_path.replace("\\", "/")

        logger.info(f"  ⑤ font: {font_path}")

    def resolve_subtitle_background_color():
        # Compatible historical parameters:API Lee. `text_background_color` It's probably a boolean.
        # Could also be the actual colour string. It's a uniform here. True/False
        # Directly to TextClip Then there was an unpredictable rendering.
        if isinstance(params.text_background_color, bool):
            return "#000000" if params.text_background_color else None
        return params.text_background_color

    def create_text_clip(subtitle_item):
        params.font_size = int(params.font_size)
        params.stroke_width = int(params.stroke_width)
        phrase = subtitle_item[1]
        max_width = video_width * 0.9
        bg_color = resolve_subtitle_background_color()
        rounded_bg_enabled = bool(
            getattr(params, "rounded_subtitle_background", False) and bg_color
        )
        has_subtitle_background = bool(bg_color)
        # Rounded background generated by the true width of the text, with greater restraint in left and right white; old rectangle background retained
        # Large security margins to avoid long subtitles or cuttings in the historical configuration.
        padding_ratio = 0.4 if rounded_bg_enabled else 0.6
        pad_x = int(params.font_size * padding_ratio) if has_subtitle_background else 0
        # Subtitle background requires clear inner margins for text. First deduct from available width
        # padding Change your line, so you don't have to keep English or big characters full. 90% The video is wide.
        # text to the edge of the background box, which appears to be cut. Normal rectangle background and rounded background
        # This logic is followed; backgroundless subtitles remain the maximum width.
        text_max_width = max(1, int(max_width) - 2 * pad_x)
        wrapped_txt, txt_height = wrap_text(
            phrase,
            max_width=text_max_width,
            font=font_path,
            fontsize=params.font_size,
        )
        interline = int(params.font_size * 0.25)
        line_count = wrapped_txt.count("\n") + 1
        vertical_padding = int(params.font_size * 0.35)
        text_clip_margin_y = max(
            int(params.font_size * 0.3), int(params.stroke_width * 2)
        )
        # MoviePy Yes. `method=label` The next one will automatically shrink the height of the text box.
        # The lower part of the last line is easily cut off when you have a side or background colour. It's here.
        # A more conservative height, counting line spacing and extra white.
        # Background boxes and text themselves can be rendered completely.
        clip_h = int(txt_height + vertical_padding + (interline * line_count))

        if rounded_bg_enabled:
            # Rounded background needs to fit text width instead of following 90% Video width. Here you go.
            # PIL The maximum of one line of text is measured, with horizontal margins, to avoid short subtitles having a wide base.
            try:
                font = ImageFont.truetype(font_path, params.font_size)
                text_w = max(
                    int(font.getbbox(line)[2] - font.getbbox(line)[0])
                    for line in wrapped_txt.split("\n")
                )
            except Exception as exc:
                logger.warning(
                    f"failed to measure subtitle text width, fallback to max width: {str(exc)}"
                )
                text_w = int(max_width)

            box_w = max(1, min(int(max_width), text_w + 2 * pad_x))
            radius = max(8, int(params.font_size * 0.4))
            text_clip = TextClip(
                text=wrapped_txt,
                font=font_path,
                font_size=params.font_size,
                color=params.text_fore_color,
                bg_color=None,
                stroke_color=params.stroke_color,
                stroke_width=params.stroke_width,
                interline=interline,
                size=(box_w, None),
                text_align="center",
                margin=(0, text_clip_margin_y),
            )
            clip_h = max(clip_h, text_clip.h)
            bg_clip = _rounded_subtitle_background_clip(
                width=box_w,
                height=clip_h,
                color=bg_color,
                alpha=140,
                radius=radius,
            )
            text_position = _get_visible_center_position(text_clip, box_w, clip_h)
            _clip = CompositeVideoClip(
                [bg_clip, text_clip.with_position(text_position)],
                size=(box_w, clip_h),
            )
        elif bg_color:
            size = (
                int(max_width),
                clip_h,
            )
            text_clip = TextClip(
                text=wrapped_txt,
                font=font_path,
                font_size=params.font_size,
                color=params.text_fore_color,
                bg_color=None,
                stroke_color=params.stroke_color,
                stroke_width=params.stroke_width,
                interline=interline,
                size=(int(max_width), None),
                text_align="center",
                margin=(0, text_clip_margin_y),
            )
            size = (size[0], max(size[1], text_clip.h))
            bg_clip = _rounded_subtitle_background_clip(
                width=size[0],
                height=size[1],
                color=bg_color,
                alpha=255,
                radius=0,
            )
            text_position = _get_visible_center_position(text_clip, size[0], size[1])
            _clip = CompositeVideoClip(
                [bg_clip, text_clip.with_position(text_position)],
                size=size,
            )
        else:
            size = (
                int(max_width),
                clip_h,
            )
            _clip = TextClip(
                text=wrapped_txt,
                font=font_path,
                font_size=params.font_size,
                color=params.text_fore_color,
                bg_color=None,
                stroke_color=params.stroke_color,
                stroke_width=params.stroke_width,
                interline=interline,
                size=size,
                text_align="center",
            )
        duration = subtitle_item[0][1] - subtitle_item[0][0]
        _clip = _clip.with_start(subtitle_item[0][0])
        _clip = _clip.with_end(subtitle_item[0][1])
        _clip = _clip.with_duration(duration)
        if params.subtitle_position == "bottom":
            _clip = _clip.with_position(("center", video_height * 0.95 - _clip.h))
        elif params.subtitle_position == "top":
            _clip = _clip.with_position(("center", video_height * 0.05))
        elif params.subtitle_position == "custom":
            # Ensure the subtitle is fully within the screen bounds
            margin = 10  # Additional margin, in pixels
            max_y = video_height - _clip.h - margin
            min_y = margin
            custom_y = (video_height - _clip.h) * (params.custom_position / 100)
            custom_y = max(
                min_y, min(custom_y, max_y)
            )  # Constrain the y value within the valid range
            _clip = _clip.with_position(("center", custom_y))
        else:  # center
            _clip = _clip.with_position(("center", "center"))
        return _clip

    # MoviePy Yes. CompositeAudioClip.close() It won't shut down. AudioFileClip。Here.
    # ExitStack Obvious holding of all original files reader，Make sure it works. Subtitles are abnormal.
    # You can release any path such as video writing failure. FFmpeg Subprocess, especially avoid Windows The file is occupied.
    with ExitStack() as clip_stack:
        source_video_clip = clip_stack.enter_context(
            _open_video_clip_quietly(video_path)
        )
        voice_source_clip = clip_stack.enter_context(AudioFileClip(audio_path))
        video_clip = source_video_clip
        audio_clip = voice_source_clip.with_effects(
            [afx.MultiplyVolume(params.voice_volume)]
        )

        def make_textclip(text):
            return TextClip(
                text=text,
                font=font_path,
                font_size=params.font_size,
            )

        if subtitle_path and os.path.exists(subtitle_path):
            sub = clip_stack.enter_context(
                SubtitlesClip(
                    subtitles=subtitle_path,
                    encoding="utf-8",
                    make_textclip=make_textclip,
                )
            )
            text_clips = []
            for item in sub.subtitles:
                clip = create_text_clip(subtitle_item=item)
                text_clips.append(clip)
            video_clip = CompositeVideoClip([video_clip, *text_clips])
            clip_stack.callback(video_clip.close)

        bgm_enabled = bgm_service.should_use_bgm(
            params.bgm_type, params.bgm_volume
        )
        if not bgm_enabled and params.bgm_type:
            # All BGM Source shared this short-circuit rule. Volume is not greater 0 cannot parse random or
            # Customised files cannot load documents returned by the provider to avoid meaningless IO And mix.
            logger.info(
                f"skipping background music because volume is not positive: "
                f"type={params.bgm_type}, volume={params.bgm_volume}"
            )

        # The provider ' s play can be fed directly into the corresponding document at the task hierarchy.None Means following random/Custom
        # BGM Parsing, empty string explicitly disables this article BGM；But any source must first adopt the generic volume rule.
        bgm_file = ""
        if bgm_enabled:
            bgm_file = (
                bgm_file_override
                if bgm_file_override is not None
                else get_bgm_file(
                    bgm_type=params.bgm_type,
                    bgm_file=params.bgm_file,
                )
            )
        bgm_mix_succeeded = True
        if bgm_file:
            try:
                bgm_effects = [
                    afx.MultiplyVolume(params.bgm_volume),
                    afx.AudioFadeOut(3),
                ]
                # Random Service Parsing/Custom music may be shorter than a piece and need to be filled in cycle; task level
                # Pass. override The imported document indicates that the provider has completed its long-term suitability. It's based on...
                # The source decides whether to recycle and avoid changing the white list for each additional provider in the future.
                if bgm_file_override is None:
                    bgm_effects.append(afx.AudioLoop(duration=video_clip.duration))
                bgm_source_clip = clip_stack.enter_context(AudioFileClip(bgm_file))
                bgm_clip = bgm_source_clip.with_effects(bgm_effects)
                audio_clip = CompositeAudioClip([audio_clip, bgm_clip])
            except Exception:
                bgm_mix_succeeded = False
                # Record complete stacking and stable context to distinguish between file decoded,MoviePy Effects and effects
                # CompositeAudioClip failed;document content and API Key Not going into the log.
                logger.exception(
                    f"failed to mix background music: type={params.bgm_type}, "
                    f"file={bgm_file}"
                )

        final_video_clip = video_clip.with_audio(audio_clip)
        clip_stack.callback(final_video_clip.close)
        # Visibility follows the input audio sampling rate; if not available, back MoviePy Default 44100Hz。
        # This will reduce the number of different environments. Docker .
        output_audio_fps = int(getattr(audio_clip, "fps", 0) or 44100)
        _write_videofile_with_codec_fallback(
            final_video_clip,
            output_file=output_file,
            codec=_get_configured_video_codec(),
            audio_codec=audio_codec,
            audio_fps=output_audio_fps,
            audio_bitrate=audio_bitrate,
            temp_audiofile_path=_get_temp_audio_dir(output_dir),
            threads=params.n_threads or 2,
            logger=None,
            fps=fps,
        )
        return bgm_mix_succeeded


def preprocess_video(materials: List[MaterialInfo], clip_duration=4):
    # WebUI In some secondary generation scenarios, empty material lists may be uploaded, which returns the empty result and avoids dropping NoneType Unusual.
    if not materials:
        return []

    # Only pre-process verified material is returned to avoid low-resolution images continuing into subsequent video synthesis processes.
    valid_materials = []
    local_videos_dir = utils.storage_dir("local_videos", create=True)

    for material in materials:
        if not material.url:
            continue

        try:
            material_source_path = file_security.resolve_path_within_directory(
                local_videos_dir, material.url
            )
        except ValueError as exc:
            # local video_source The material path is from API Parameters, which must be limited to a dedicated catalogue of material.
            # Allows users to pass file names, which are also compatible with the absolute path of historical return, but does not allow escape to the system
            # Other directories to avoid any access to or adoption of files MoviePy Detection of locally sensitive documents.
            logger.warning(
                f"skip unsafe local material: {material.url}, "
                f"local_videos_dir: {local_videos_dir}, error: {str(exc)}"
            )
            continue

        ext = utils.parse_extension(material_source_path)
        try:
            # Picture material is read directly in graphic form, avoiding going first VideoFileClip The error triggers an unstable retreat branch.
            if ext in const.FILE_TYPE_IMAGES:
                clip, material_source_path = _open_image_clip_with_fallback(
                    material_source_path
                )
            else:
                clip = _open_video_clip_quietly(material_source_path)
        except Exception:
            # Non-standard extension or detection failed to revert to photo mode to accommodate historical direct transmission of local picture paths.
            try:
                clip, material_source_path = _open_image_clip_with_fallback(
                    material_source_path
                )
            except Exception as exc:
                logger.warning(
                    f"skip unreadable local material: {material.url}, error: {str(exc)}"
                )
                continue
        try:
            width = clip.size[0]
            height = clip.size[1]
            if not is_material_resolution_acceptable(width, height):
                logger.warning(
                    f"low resolution material: {width}x{height}, minimum "
                    f"{_MIN_MATERIAL_DIMENSION}x{_MIN_MATERIAL_DIMENSION} required "
                    f"(tolerance {_MIN_DIMENSION_TOLERANCE}px)"
                )
                # Close the resource as soon as the low-resolution material is detected and do not return the material to the follow-up process.
                close_clip(clip)
                continue

            if ext in const.FILE_TYPE_IMAGES:
                logger.info(f"processing image: {material_source_path}")
                # We've already opened the material once when we're detecting the dimensions. clip。
                close_clip(clip)
                # Create an image clip and set its duration to 3 seconds
                clip = (
                    ImageClip(material_source_path)
                    .with_duration(clip_duration)
                    .with_position("center")
                )
                # Apply a zoom effect using the resize method.
                # A lambda function is used to make the zoom effect dynamic over time.
                # The zoom effect starts from the original size and gradually scales up to 120%.
                # t represents the current time, and clip.duration is the total duration of the clip (3 seconds).
                # Note: 1 represents 100% size, so 1.2 represents 120% size.
                zoom_clip = clip.resized(
                    lambda t: 1 + (clip_duration * 0.03) * (t / clip.duration)
                )

                # Optionally, create a composite video clip containing the zoomed clip.
                # This is useful when you want to add other elements to the video.
                final_clip = CompositeVideoClip([zoom_clip])

                # Output the video to a file.
                video_file = f"{material_source_path}.mp4"
                final_clip.write_videofile(video_file, fps=30, logger=None)
                close_clip(clip)
                close_clip(final_clip)
                material.url = video_file
                logger.success(f"image processed: {video_file}")
            else:
                # The normal video material only needs to read the dimensions for validation and release the handle immediately after the verification has been completed.
                close_clip(clip)
                # Update url to the resolved absolute path so that downstream
                # stages (combine_videos) can open the file without re-resolving.
                material.url = material_source_path
        except Exception:
            close_clip(clip)
            raise

        valid_materials.append(material)

    return valid_materials
