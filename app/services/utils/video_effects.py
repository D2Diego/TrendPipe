import numpy as np
from moviepy import Clip, ColorClip, CompositeVideoClip, vfx
from PIL import Image


# FadeIn
def fadein_transition(clip: Clip, t: float) -> Clip:
    return clip.with_effects([vfx.FadeIn(t)])


# FadeOut
def fadeout_transition(clip: Clip, t: float) -> Clip:
    return clip.with_effects([vfx.FadeOut(t)])


# SlideIn
def slidein_transition(clip: Clip, t: float, side: str) -> Clip:
    width, height = clip.size

    # MoviePy Internal SlideIn In the current processing chain, full screen material is unstable.
    # There would be a situation where “the logical application of the transition is almost invisible in the picture”.
    # Here's the black bottom. + A bit of moving painting to ensure that the effect of the diversion is visible and can be controlled.
    def position(current_time: float):
        progress = min(max(current_time / max(t, 0.001), 0), 1)

        if side == "left":
            return (-width + width * progress, 0)
        if side == "right":
            return (width - width * progress, 0)
        if side == "top":
            return (0, -height + height * progress)
        if side == "bottom":
            return (0, height - height * progress)
        return (0, 0)

    background = ColorClip(size=(width, height), color=(0, 0, 0)).with_duration(
        clip.duration
    )
    moving_clip = clip.with_position(position)
    return CompositeVideoClip([background, moving_clip], size=(width, height)).with_duration(
        clip.duration
    )


# SlideOut
def slideout_transition(clip: Clip, t: float, side: str) -> Clip:
    width, height = clip.size
    transition_start = max(clip.duration - t, 0)

    # SlideOut The same change to a visible shift ensures a steady slide at the end of the clip.
    def position(current_time: float):
        if current_time <= transition_start:
            return (0, 0)

        progress = min(
            max((current_time - transition_start) / max(t, 0.001), 0), 1
        )

        if side == "left":
            return (-width * progress, 0)
        if side == "right":
            return (width * progress, 0)
        if side == "top":
            return (0, -height * progress)
        if side == "bottom":
            return (0, height * progress)
        return (0, 0)

    background = ColorClip(size=(width, height), color=(0, 0, 0)).with_duration(
        clip.duration
    )
    moving_clip = clip.with_position(position)
    return CompositeVideoClip([background, moving_clip], size=(width, height)).with_duration(
        clip.duration
    )


# Keep original design 20% It's a three-second short film. Ken Burns Sensitivity.
# The stability of the scaling is ensured by sampling at the lower pixel centre and does not mask the source video coding by weakening the effect margin.
_ZOOM_MAX_SCALE = 1.2


def _zoom_frame(frame: np.ndarray, scale_factor: float) -> np.ndarray:
    """Use a pixel centre to cut to achieve a non-blackside and stable scaling effect.

    You can't first convert the crop width height to an integer: when the zoom scale changes, the integer boundary moves by a long, unsynchronous beat.
    and changes the semi-pixel sampling phase during the odd-size switching, which eventually takes the form of video shaking.Pillow Yes. EXTENT
    Convert to receive the floating point boundary directly and complete subpixel sampling on a fixed output canvas; left, upper and lower boundary
    It is always symmetrical around the centre of the same floating point, and therefore applies to the scene where the entire video is continuously slowly scaled.
    """
    if scale_factor <= 0:
        raise ValueError("scale_factor must be greater than zero")

    # 1 Double-scaling returns directly to the frame, avoiding the slight blurring of the initial frame due to pointless heavy sampling.
    if abs(scale_factor - 1.0) < 1e-9:
        return frame

    height, width = frame.shape[:2]
    crop_width = width / scale_factor
    crop_height = height / scale_factor
    left = (width - crop_width) / 2
    top = (height - crop_height) / 2
    right = left + crop_width
    bottom = top + crop_height

    image = Image.fromarray(frame)
    transformed = image.transform(
        (width, height),
        Image.Transform.EXTENT,
        (left, top, right, bottom),
        # The video continues to be scaled up to focus more on the coherence of the adjacent frames.BICUBIC/LANCZOS It's a bit sharper.
        # However, high frequency textures are prone to ringing and flashing when crossing the sampling grid;BILINEAR More soft,
        # A more stable sense of dynamicism can be exchanged for a small amount of sharpness.
        resample=Image.Resampling.BILINEAR,
    )
    return np.asarray(transformed)


def zoomin_transition(clip: Clip, t: float) -> Clip:
    """Smuggle from the original image to the entire footage 1.2 Double."""
    # t For the time being, keep the same call for signatures as any other transposition function; zoom in to cover the entire segment,
    # Otherwise, at the end of the short-term scaling, the picture will suddenly remain static and not suitable for static or low-motion material.
    _ = t
    duration = max(clip.duration, 0.001)

    def scale_effect(get_frame, current_time: float):
        progress = min(max(current_time / duration, 0), 1)
        scale_factor = 1 + (_ZOOM_MAX_SCALE - 1) * progress
        return _zoom_frame(get_frame(current_time), scale_factor)

    return clip.transform(scale_effect)


def zoomout_transition(clip: Clip, t: float) -> Clip:
    """From whole session 1.2 It's smoother to the original image."""
    # and zoomin_transition Unanimously,t Only for compatible and uniform transpositions.
    _ = t
    duration = max(clip.duration, 0.001)

    def scale_effect(get_frame, current_time: float):
        progress = min(max(current_time / duration, 0), 1)
        scale_factor = _ZOOM_MAX_SCALE - (_ZOOM_MAX_SCALE - 1) * progress
        return _zoom_frame(get_frame(current_time), scale_factor)

    return clip.transform(scale_effect)
