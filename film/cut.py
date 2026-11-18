#!/usr/bin/env python3
"""Cut the intro film: thirteen generated shots, the on-screen text, and the sound.

    python3 film/cut.py            # builds film/renders/intro.mp4
    python3 film/cut.py --install  # and copies it to deck/assets/video/intro.mp4
    python3 film/cut.py --silent   # no sound, even if film/sound.json exists

What goes in:
  film/generated/clips/v2/shotNN.mp4   the silent shots from the video tool (24 fps)
  film/sound.json                      which sound sits where (see "Sound" below)
  film/generated/sound/*               the sound files that list names

What it makes on the way, in film/generated/cut/: one text picture per shot (ovNN.png), one
part per shot (partNN.mp4) and the sound mix (mix.wav).

The text is drawn here, never by the video tool. Narrator lines are small and cream, the four
questions and the last line are large and gold. Needs ffmpeg and Pillow.

Sound: film/sound.json is a list of cues. Each cue is
  {"file": "rain.wav", "at": 0.0, "len": 6.0, "level": -30, "in": 0.3, "out": 0.5, "from": 0.0}
"at" is the second in the film where it starts, "len" how long it plays, "level" the mean
level in dB it is brought to (so a loud and a quiet source end up where we want them), "in"
and "out" are fades, "from" skips into the source. For a single event in an otherwise quiet
clip (keys, a door) give "peak" instead of "level": the loudest moment is brought to that.
"loop": 2 plays the source three times in a row, for a bed that is longer than its clip.
"note" is for people. There is no music and no voice: the presenter speaks over the film.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

FILM = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FILM)
SHOTS = os.path.join(FILM, "generated", "clips", "v2")
CUT = os.path.join(FILM, "generated", "cut")
SOUND = os.path.join(FILM, "generated", "sound")
CUES = os.path.join(FILM, "sound.json")
OUT = os.path.join(FILM, "renders", "intro.mp4")
DECK = os.path.join(ROOT, "deck", "assets", "video", "intro.mp4")

W, H, FPS = 1280, 720, 24
FONT = "/System/Library/Fonts/Supplemental/BigCaslon.ttf"
GOLD = (236, 210, 138, 255)
CREAM = (246, 236, 210, 255)

# One entry per shot: (kind, text). "line" is a narrator line, "ask" is a big gold question.
TEXT = {
    1: ("line", "For decades, the wandmaker remembered every wand he ever sold."),
    3: ("line", "But the notebooks are piling up, the queue is growing,"),
    4: ("line", "and he would quite like an afternoon off."),
    5: ("line", "Then, one evening, he read about agents."),
    7: ("line", "He did not sleep that night."),
    8: ("line", "By morning, the shop had a digital apprentice."),
    9: ("ask", "Can I limit what it can do?"),
    10: ("ask", "Can I see what it did?"),
    11: ("ask", "Can I trust it to ship?"),
    12: ("ask", "Can it handle the back-to-school rush?"),
    13: ("ask", "How could he do it?"),
}

# The last shot: its text fades in half a second after the cut (1:05.0 in the film), and the
# film stops after 127 frames of it (1:09.79), just before the smile is complete. The player
# holds the last frame. There is no end card.
LAST = 13
LAST_TEXT_IN = 0.5
LAST_TEXT_FADE = 0.5
LAST_FRAMES = 127

# Sound: one gain for the whole mix, and how long the sound takes to fade at the very end.
MASTER_DB = 0
END_FADE = 0.8


def run(*cmd):
    subprocess.run(cmd, check=True)


def frames(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", path], text=True)
    return int(out.strip().strip(","))


def band(img, y0, y1, max_alpha):
    """Darken the lower part of the frame so the text reads on any shot."""
    g = Image.new("L", (1, H), 0)
    for y in range(H):
        if y0 <= y <= y1:
            g.putpixel((0, y), int(max_alpha * (y - y0) / (y1 - y0)))
        elif y > y1:
            g.putpixel((0, y), max_alpha)
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    black.putalpha(g.resize((W, H)))
    img.alpha_composite(black)


def centred(img, text, size, y, fill, wrap):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, size)
    for i, line in enumerate(textwrap.wrap(text, wrap)):
        x = (W - d.textlength(line, font=f)) / 2
        yy = y + i * int(size * 1.15)
        d.text((x + 2, yy + 3), line, font=f, fill=(0, 0, 0, 220))
        d.text((x, yy), line, font=f, fill=fill)


def overlay(n):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    kind, text = TEXT.get(n, (None, ""))
    if kind == "line":
        band(img, 470, 640, 190)
        centred(img, text, 40, 600 if len(text) < 48 else 578, CREAM, 52)
    elif kind == "ask":
        band(img, 380, 620, 215)
        centred(img, text, 74, 560, GOLD, 40)
    path = os.path.join(CUT, f"ov{n:02d}.png")
    img.save(path)
    return path


def part(n):
    shot = os.path.join(SHOTS, f"shot{n:02d}.mp4")
    out = os.path.join(CUT, f"part{n:02d}.mp4")
    enc = ["-r", str(FPS), "-an", "-c:v", "libx264", "-crf", "18", out]
    if n == LAST:
        graph = (f"[0:v]scale={W}:{H},setsar=1[v];"
                 f"[1:v]format=rgba,fade=t=in:st={LAST_TEXT_IN}:d={LAST_TEXT_FADE}:alpha=1[t];"
                 f"[v][t]overlay=0:0,format=yuv420p")
        run("ffmpeg", "-v", "error", "-y", "-i", shot, "-loop", "1", "-framerate", str(FPS),
            "-i", overlay(n), "-filter_complex", graph, "-frames:v", str(LAST_FRAMES), *enc)
    else:
        graph = f"[0:v]scale={W}:{H},setsar=1[v];[v][1:v]overlay=0:0,format=yuv420p"
        run("ffmpeg", "-v", "error", "-y", "-i", shot, "-i", overlay(n),
            "-filter_complex", graph, *enc)
    return out


def levels(path, start, length):
    """Mean and peak level in dB of the stretch of a source that a cue uses."""
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", str(start), "-t", str(length), "-i", path,
         "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", out)
    peak = re.search(r"max_volume: (-?[\d.]+) dB", out)
    return (float(mean.group(1)) if mean else -30.0, float(peak.group(1)) if peak else -6.0)


def mix(total):
    """Lay every cue on the film's clock and write one stereo file of exactly the film's length."""
    cues = json.load(open(CUES))
    args, graph, names = [], [], []
    for i, c in enumerate(cues):
        src = os.path.join(SOUND, c["file"])
        start = c.get("from", 0.0)
        length = min(c["len"], total - c["at"])
        mean, peak = levels(src, start, length)
        gain = c["peak"] - peak if "peak" in c else c["level"] - mean
        fin, fout = c.get("in", 0.2), c.get("out", 0.4)
        if c.get("loop"):
            args += ["-stream_loop", str(c["loop"])]
        args += ["-i", src]
        graph.append(
            f"[{i}:a]atrim={start}:{start + length},asetpts=PTS-STARTPTS,"
            f"aformat=sample_rates=48000:channel_layouts=stereo,"
            f"afade=t=in:d={fin},afade=t=out:st={max(0, length - fout)}:d={fout},"
            f"volume={gain:.2f}dB,adelay={int(c['at'] * 1000)}:all=1[a{i}]")
        names.append(f"[a{i}]")
    graph.append(
        f"{''.join(names)}amix=inputs={len(cues)}:normalize=0:duration=longest,"
        f"volume={MASTER_DB}dB,alimiter=limit=0.7,apad,atrim=0:{total},"
        f"afade=t=out:st={total - END_FADE}:d={END_FADE}[out]")
    out = os.path.join(CUT, "mix.wav")
    run("ffmpeg", "-v", "error", "-y", *args, "-filter_complex", ";".join(graph),
        "-map", "[out]", "-ar", "48000", "-ac", "2", out)
    return out


def main():
    os.makedirs(CUT, exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    parts = [part(n) for n in range(1, LAST + 1)]
    listing = os.path.join(CUT, "list.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    total_frames = sum(frames(p) for p in parts)
    total = total_frames / FPS

    silent = os.path.join(CUT, "silent.mp4")
    run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing,
        "-c", "copy", silent)
    if "--silent" not in sys.argv and os.path.exists(CUES):
        run("ffmpeg", "-v", "error", "-y", "-i", silent, "-i", mix(total), "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT)
        sound = "with sound"
    else:
        run("ffmpeg", "-v", "error", "-y", "-i", silent, "-c", "copy",
            "-movflags", "+faststart", OUT)
        sound = "silent"
    print(f"{os.path.relpath(OUT, ROOT)}: {total_frames} frames, {total:.2f} s, {sound}")
    if "--install" in sys.argv:
        shutil.copyfile(OUT, DECK)
        print(f"copied to {os.path.relpath(DECK, ROOT)}")


if __name__ == "__main__":
    main()
