import subprocess

from brainsuck.frames import extract_scene_frames, find_ffmpeg


def test_find_ffmpeg_exists():
    assert find_ffmpeg().exists()


def _flashing_video(path):
    """10 s video alternating black/white every second: 9 hard scene cuts."""
    subprocess.run(
        [str(find_ffmpeg()), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         "color=c=black:s=160x120:r=10:d=10,geq=lum='if(mod(floor(T),2),255,0)':cb=128:cr=128",
         "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )


def test_scene_frames_capped(tmp_path):
    video = tmp_path / "flash video.mp4"
    _flashing_video(video)
    frames = extract_scene_frames(video, tmp_path / "เฟรม", max_frames=3)
    assert len(frames) == 3
    times = [t for t, _ in frames]
    assert times == sorted(times)
    assert all(p.exists() for _, p in frames)


def test_scene_frames_uncapped_finds_cuts(tmp_path):
    video = tmp_path / "v.mp4"
    _flashing_video(video)
    frames = extract_scene_frames(video, tmp_path / "f")
    assert 8 <= len(frames) <= 10
    assert not [p for p in (tmp_path / "f").iterdir() if p not in {f for _, f in frames}]
