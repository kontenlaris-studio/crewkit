#!/usr/bin/env python3
"""Render CrewKit demo video: narrated slides from the verified runs.
Stdlib + PIL + ffmpeg + /opt/hatch/bin/tts (same pipeline as earlier projects)."""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "video")
os.makedirs(OUT, exist_ok=True)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

SECTIONS = [
    ("CrewKit", "A skeleton-crew automation template — Kiroween 2026, Skeleton Crew",
     ["One tiny core. A crew of apps.",
      "",
      "Every automation project re-builds the same bones:",
      "  scheduling, config, state, notifications.",
      "",
      "CrewKit is those bones — written once, properly —",
      "proven by two distinct apps built on top of it."],
     "Every automation project starts by rebuilding the same bones: a scheduler, configuration, state, and notifications. CrewKit is those bones, written once and written properly: a lean skeleton template, built with Kiro for the Skeleton Crew category of Kiroween 2026, and proven by two distinct applications that share nothing but the core."),
    ("The skeleton", "core/crewkit/ — 433 lines, Python standard library only",
     ["config.py  JSON config + CREWKIT_* env overrides",
      "clock.py   UTC time + a pure due-job scheduler",
      "store.py   atomic JSON state (temp file + rename)",
      "notify.py  console / file / webhook sinks",
      "runner.py  runs due jobs, records outcomes,",
      "           alerts on failure — a bad job never",
      "           kills the loop"],
     "The skeleton is five small modules. Config loads JSON with environment overrides. Clock provides U T C time and a pure scheduling function. Store persists state atomically, so a crash never corrupts it. Notify fans messages out to console, file, or webhook sinks. And the runner executes due jobs, records every outcome, and alerts on failure, because a raising job must never kill the loop. Four hundred thirty-three lines, standard library only, zero dependencies."),
    ("App 1 — Telegram Task Bot", "apps/telegram-task-bot/ — reminders on the skeleton",
     ["Live mode:  /add title | minutes · /list · /done id",
      "Offline demo, no token needed:",
      "",
      "$ python3 apps/telegram-task-bot/bot.py --demo",
      "[2024-01-01T12:00:00Z] Reminder: Review code",
      "  — Task due at 2024-01-01T11:00:00Z",
      "Demo completed."],
     "App one is a Telegram task bot. In live mode it long-polls Telegram and understands add, list, and done commands; a scheduler job on the skeleton watches due times and sends reminders. Its demo mode needs no token and no network: it loads sample tasks, runs the loop against a fake clock, and prints exactly the reminder that would be sent."),
    ("App 2 — Price Watch", "apps/price-watch/ — one core, a completely different job",
     ["Watches product pages; extracts prices from",
      "JSON-LD first, regex fallback second.",
      "",
      "$ python3 apps/price-watch/watch.py --demo",
      "[...] Price Alert: Widget",
      "  — Price $45.99 <= target $50.0",
      "Demo completed."],
     "App two could not be more different: a price-watch notifier. It fetches product pages, extracts the price from JSON-LD with a regex fallback, and the same runner and notifier from the skeleton fire an alert the moment a price drops to your target. Same bones, completely different creature. That is the whole point of a skeleton crew."),
    ("Built with Kiro", "Spec-first: steering, a spec, a custom agent, and a hook",
     [".kiro/steering/   product, tech, structure rules",
      ".kiro/specs/      requirements R1-R6 + design + tasks",
      ".kiro/agents/     crewkit-builder (kiro-cli agent create)",
      ".kiro/hooks/      self-test re-runs on every .py edit",
      "",
      "Two Kiro CLI sessions: core first, then both apps —",
      "each under a hard rule: finish only when tests pass."],
     "CrewKit was built spec-first with Kiro. Steering files fixed the product, tech, and structure rules. A written spec, requirements R one to R six, design, and tasks, came before any code. A custom Kiro agent, crewkit-builder, ran two build sessions, core first, then both apps, each under a hard rule: you are not finished until the self-test passes. And a hook re-runs that test every time a Python file changes."),
    ("Verified, not promised", "Deterministic proof from a clean checkout",
     ["$ python3 tests/selftest.py",
      "  Ran 34 tests — OK (offline, ~0.25 s)",
      "",
      "Core unit tests (R1-R5) + subprocess smoke tests",
      "that run both apps' demo modes end to end.",
      "Each app folder is self-contained: copy core/ +",
      "one app folder anywhere and it runs."],
     "And none of this is a promise: it is verified. Thirty-four deterministic tests pass offline in a quarter of a second, including smoke tests that execute both demo modes end to end. Each app folder is self-contained: copy the core plus one app folder into an empty directory, and it just runs."),
    ("Try the skeleton", "Take the bones. Build your own creature.",
     ["Repo:  github.com/kontenlaris-studio/crewkit",
      "Live:  kontenlaris-studio.github.io/crewkit",
      "",
      "MIT licensed. Python 3.11+. No pip installs.",
      "",
      "CrewKit — one tiny core, a crew of apps."],
     "CrewKit is M I T licensed and live now: the repository and the demo site are on screen. Take the bones, and build your own creature. CrewKit: one tiny core, a crew of apps."),
]

def slide(idx, title, subtitle, lines):
    img = Image.new("RGB", (1280, 720), (13, 10, 24))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1280, 10], fill=(139, 92, 246))
    d.text((60, 48), title, font=ImageFont.truetype(FB, 40), fill=(255, 255, 255))
    d.text((60, 104), subtitle, font=ImageFont.truetype(FR, 21), fill=(255, 170, 80))
    y = 168
    for ln in lines:
        d.text((60, y), ln, font=ImageFont.truetype(FM, 23), fill=(220, 230, 245))
        y += 40
    d.text((60, 668), f"CrewKit — Kiroween 2026 · Skeleton Crew · {idx+1}/{len(SECTIONS)}",
           font=ImageFont.truetype(FR, 18), fill=(140, 160, 190))
    p = os.path.join(OUT, f"slide{idx}.png")
    img.save(p)
    return p

def dur(path):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())

def main():
    concat_v, concat_a = [], []
    for i, (title, sub, lines, narr) in enumerate(SECTIONS):
        png = slide(i, title, sub, lines)
        mp3 = os.path.join(OUT, f"narr{i}.mp3")
        if not os.path.exists(mp3):
            r = subprocess.run(["/opt/hatch/bin/tts", "speak", "--output", mp3,
                                "--text-stdin", "--voice", "avocado_v2:MAI_03",
                                "--language", "en"],
                               input=narr, capture_output=True, text=True)
            if r.returncode != 0:
                print("TTS FAIL", i, r.stderr[-300:]); sys.exit(1)
        d = dur(mp3) + 0.4
        concat_v.append(f"file '{png}'\nduration {d:.2f}")
        concat_a.append(f"file '{mp3}'")
        print(f"section {i}: {d:.1f}s")
    last = os.path.join(OUT, f"slide{len(SECTIONS)-1}.png")
    concat_v.append(f"file '{last}'")
    open(os.path.join(OUT, "vlist.txt"), "w").write("\n".join(concat_v) + "\n")
    open(os.path.join(OUT, "alist.txt"), "w").write("\n".join(concat_a) + "\n")
    out = os.path.join(OUT, "crewkit-demo.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", os.path.join(OUT, "vlist.txt"),
                    "-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "alist.txt"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", out], check=True)
    print("VIDEO OK", out, f"{dur(out):.1f}s")

if __name__ == "__main__":
    main()
