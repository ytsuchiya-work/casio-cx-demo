#!/usr/bin/env python3
"""ナレーション付きデモ動画を組み立てる。
  plan.json : シーンの並び（静止画 or 録画クリップ）と、各シーンで読むナレーションの beat
  vo_script.json / vo/*.wav : demo-video スキルの voiceover.py gen で作った音声（1文1ファイル）
出力: out/casio-cx-demo.mp4（字幕焼き込み）と out/casio-cx-demo.srt
"""
import json, subprocess, wave, os, sys, shutil
from pathlib import Path

D = Path(__file__).resolve().parent
OUT = D / "out"; TMP = D / "tmp"
OUT.mkdir(exist_ok=True); TMP.mkdir(exist_ok=True)
W, H, FPS = 1920, 1080, 30
GAP = 0.45       # 文と文の間
LEAD = 0.5       # シーン開始からナレーションまで
TAIL = 0.8       # ナレーション後の余白
plan = json.load(open(D / "plan.json"))
vo = json.load(open(D / "vo_script.json"))["beats"]

def dur(p):
    with wave.open(str(p)) as w: return w.getnframes() / w.getframerate()

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: print(" ".join(map(str, cmd))[:600]); print(r.stderr[-2500:]); sys.exit(1)

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

scenes, subs, audio_parts = [], [], []
T = 0.0
for i, sc in enumerate(plan["scenes"]):
    lines = []
    for b in sc.get("beats", []):
        for k, ln in enumerate(vo[b]):
            f = D / "vo" / f"{b}_{k}.wav"
            lines.append((f, dur(f), ln["show"]))
    vo_len = sum(d for _, d, _ in lines) + GAP * max(0, len(lines) - 1)
    need = LEAD + vo_len + TAIL if lines else sc.get("min", 3.0)
    need = max(need, sc.get("min", 0))
    seg = TMP / f"s{i:02d}.mp4"
    vf_fit = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=white,format=yuv420p"
    if sc["type"] == "image":
        D_ = need
        zoom = sc.get("zoom")
        if zoom:  # ゆっくり寄る（x,y は寄せる中心の割合）
            zx, zy, zs = zoom
            n = int(D_ * FPS)
            vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=decrease,pad={W*2}:{H*2}:(ow-iw)/2:(oh-ih)/2:color=white,"
                  f"zoompan=z='1+({zs}-1)*on/{n}':x='(iw-iw/zoom)*{zx}':y='(ih-ih/zoom)*{zy}':d={n}:s={W}x{H}:fps={FPS},format=yuv420p")
        else:
            vf = vf_fit
        if zoom:
            run(["ffmpeg", "-y", "-i", str(D / sc["src"]), "-vf", vf, "-frames:v", str(int(D_ * FPS)), "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", str(seg)])
        else:
            run(["ffmpeg", "-y", "-loop", "1", "-t", f"{D_:.3f}", "-i", str(D / sc["src"]), "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", str(seg)])
    else:  # clip: 録画の [t0, t1] を need 秒に合わせる（長ければ早送り、短ければ最後で止める）
        t0, t1 = sc["t0"], sc["t1"]; S = t1 - t0
        D_ = max(need, S / sc.get("max_speed", 16)) if sc.get("fit", True) else max(need, S)
        speed = S / D_ if S > D_ else 1.0
        vf = f"setpts=PTS/{speed:.4f}," if speed > 1.0 else ""
        vf += vf_fit
        if speed > 1.3 and sc.get("badge", True):
            vf += (f",drawtext=fontfile=/System/Library/Fonts/ヒラギノ角ゴシック\\ W6.ttc:text='早送り ×{round(speed)}':x=w-tw-40:y=40:"
                   f"fontsize=34:fontcolor=white:box=1:boxcolor=0x1B3037@0.85:boxborderw=14")
        pad = max(0.0, D_ - S / speed)
        vf += f",tpad=stop_mode=clone:stop_duration={pad + 0.05:.3f},trim=duration={D_:.3f}"
        run(["ffmpeg", "-y", "-ss", f"{t0:.3f}", "-t", f"{S:.3f}", "-i", str(D / sc["src"]), "-vf", vf, "-an", "-r", str(FPS),
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", str(seg)])
        sc["_speed"] = round(speed, 2)
    # ナレーションの配置
    t = T + LEAD
    for f, d, show in lines:
        audio_parts.append((t, f))
        if show: subs.append((t, t + d, show))
        t += d + GAP
    scenes.append(seg); sc["_start"] = round(T, 2); sc["_dur"] = round(D_, 2)
    T += D_
    print(f"scene {i:02d} {sc['id']:<14s} {D_:6.1f}s  speed={sc.get('_speed', '-')}")

# 映像をつなぐ
lst = TMP / "list.txt"; lst.write_text("".join(f"file '{p}'\n" for p in scenes))
video = TMP / "video.mp4"
run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)])
# 音声を並べる（無音の上に adelay で重ねる）
inputs, filt = [], []
for k, (t, f) in enumerate(audio_parts):
    inputs += ["-i", str(f)]
    filt.append(f"[{k}:a]aresample=48000,adelay={int(t*1000)}|{int(t*1000)}[a{k}]")
mix = "".join(f"[a{k}]" for k in range(len(audio_parts)))
filt.append(f"{mix}amix=inputs={len(audio_parts)}:normalize=0:dropout_transition=0,apad,atrim=0:{T:.3f}[aout]")
audio = TMP / "audio.wav"
fscript = TMP / "afilter.txt"; fscript.write_text(";\n".join(filt))
run(["ffmpeg", "-y", *inputs, "-filter_complex_script", str(fscript), "-map", "[aout]", "-ac", "2", str(audio)])
# 字幕
srt = OUT / "casio-cx-demo.srt"
srt.write_text("".join(f"{i+1}\n{ts(a)} --> {ts(b)}\n{s}\n\n" for i, (a, b, s) in enumerate(subs)))
style = "FontName=Hiragino Sans,Fontsize=10.5,PrimaryColour=&H00FFFFFF,BackColour=&H33372E1B,BorderStyle=4,Outline=1,Shadow=0,MarginV=10,Bold=1"
final = OUT / "casio-cx-demo.mp4"
run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio), "-vf", f"subtitles={srt}:force_style='{style}'", "-c:v", "libx264", "-preset", "medium",
     "-crf", "20", "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(final)])
json.dump(plan, open(TMP / "plan.resolved.json", "w"), ensure_ascii=False, indent=1)
print(f"DONE {final} {T:.1f}s, {len(subs)} captions")
