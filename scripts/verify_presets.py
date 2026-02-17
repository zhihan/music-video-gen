#!/usr/bin/env python3
"""Verify the three text presets (title, text, subtitle) by rendering sample images."""

import textwrap
from pathlib import Path
from moviepy import TextClip, CompositeVideoClip, ColorClip

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
TEXT_WIDTH = 680
FONT = "Arial"
TEXT_COLOR = "white"
TEXT_BG = "#000000AA"
OUTPUT_DIR = Path("samples/verify")

PRESETS = {
    "title":    {"font_size": 70, "chars_per_line": 17, "max_lines": 2},
    "text":     {"font_size": 50, "chars_per_line": 24, "max_lines": 5},
    "subtitle": {"font_size": 40, "chars_per_line": 30, "max_lines": 3},
}

# Test cases: each preset with text that fits and text that should truncate
TEST_CASES = {
    "title": {
        "fits": "CHRIST CAME.",
        "wraps": "WHY DID GOD CREATE MAN?",
        "truncates": "This is a very long title that should definitely be truncated because it exceeds two lines",
    },
    "text": {
        "fits": "If You lead me a way that I know, it would not benefit.",
        "wraps": "This leads to thousands of conversations: 'Who are You, Lord? What shall I do?' Each one forms a piece of our journey together.",
        "truncates": "As You lead me a way that I don't understand, I only can open to You. This leads to thousands of conversations: 'Who are You, Lord? What shall I do?' Each one forms a piece of our journey together, an eternal memorial between me and You. This extra text should be cut off.",
    },
    "subtitle": {
        "fits": "John 3:16",
        "wraps": "For God so loved the world that He gave His only begotten Son.",
        "truncates": "For God so loved the world that He gave His only begotten Son, that whoever believes in Him should not perish but have everlasting life. For God did not send His Son into the world to condemn the world.",
    },
}


def wrap_text(text, chars_per_line, max_lines):
    lines = textwrap.wrap(text, width=chars_per_line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        if len(last) > chars_per_line - 3:
            last = last[:chars_per_line - 3]
        lines[-1] = last.rstrip() + "..."
    return "\n".join(lines)


def calc_text_height(line_count, font_size):
    line_height = int(font_size * 1.4)
    return line_height * line_count + int(font_size * 0.3)


def render(preset_name, case_name, text):
    cfg = PRESETS[preset_name]
    font_size = cfg["font_size"]
    wrapped = wrap_text(text, cfg["chars_per_line"], cfg["max_lines"])
    line_count = wrapped.count("\n") + 1
    text_height = calc_text_height(line_count, font_size)

    text_clip = TextClip(
        text=wrapped,
        font=FONT,
        font_size=font_size,
        color=TEXT_COLOR,
        bg_color=TEXT_BG,
        size=(TEXT_WIDTH, text_height),
        method="caption",
        text_align="center",
        vertical_align="top",
    ).with_duration(1)

    info = f"preset={preset_name}  case={case_name}  font={font_size}  lines={line_count}/{cfg['max_lines']}"
    info_clip = TextClip(
        text=info,
        font=FONT,
        font_size=24,
        color="yellow",
        bg_color="#00000099",
        size=(VIDEO_WIDTH, 40),
        method="caption",
        text_align="left",
        vertical_align="center",
    ).with_duration(1).with_position(("center", 20))

    y_position = int(VIDEO_HEIGHT * 0.75) - text_height // 2
    text_clip = text_clip.with_position(("center", y_position))

    bg = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(30, 30, 30)).with_duration(1)
    comp = CompositeVideoClip([bg, text_clip, info_clip])

    output_path = OUTPUT_DIR / f"{preset_name}_{case_name}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comp.save_frame(str(output_path), t=0)

    comp.close()
    text_clip.close()
    info_clip.close()
    bg.close()

    return {
        "preset": preset_name,
        "case": case_name,
        "wrapped": wrapped,
        "lines": line_count,
        "max_lines": cfg["max_lines"],
        "height": text_height,
        "truncated": "..." in wrapped,
    }


def main():
    print("Verifying text presets...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for preset_name, cases in TEST_CASES.items():
        for case_name, text in cases.items():
            print(f"  Rendering {preset_name}_{case_name}...")
            r = render(preset_name, case_name, text)
            results.append(r)

    print()
    print("=" * 80)
    print(f"{'Preset':<12} {'Case':<12} {'Lines':>7} {'Trunc?':>8} {'Height':>8}")
    print("-" * 80)
    for r in results:
        print(f"{r['preset']:<12} {r['case']:<12} {r['lines']}/{r['max_lines']:>3} {'YES' if r['truncated'] else 'no':>8} {r['height']:>6}px")
    print("=" * 80)

    # Verify truncation logic
    print()
    print("Truncation verification:")
    for r in results:
        if r["case"] == "truncates":
            if r["truncated"]:
                print(f"  PASS: {r['preset']} truncates correctly with '...'")
            else:
                print(f"  FAIL: {r['preset']} should truncate but didn't!")
        elif r["case"] in ("fits", "wraps"):
            if not r["truncated"]:
                print(f"  PASS: {r['preset']}_{r['case']} not truncated (correct)")
            else:
                print(f"  FAIL: {r['preset']}_{r['case']} truncated unexpectedly!")


if __name__ == "__main__":
    main()
