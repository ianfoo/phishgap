#!/usr/bin/env python3
"""Assert the paper renders: right colour, and actually textured.

    python3 tools/check_paper.py [site_dir]

Written to fail rather than to print, like check_few_plays.py. It shoots the
built pages in a headless browser and samples the painted pixels, because the
two things it guards are both invisible to everything else we have.

**The grain can stop painting and nothing notices.** It did, for its whole
life: generated on every build, published, linked from the sheet, and switched
off by one word -- BODY_BOX_CSS used the `background` shorthand, which resets
`background-image`. The page is the right colour either way, just flat, so no
screenshot and no reading of the CSS ever showed it. Ian eventually asked what
grain.png was for.

**And the grain can wreck the contrast and nothing notices either.**
tools/contrast_audit.html reads getComputedStyle().backgroundColor, which
returns the token, not the composite -- so it cannot see a texture at all. The
first tuning (multiply on cream, screen on near-black, against a mid-grey tile)
took the light paper down 20.8% of its luminance and the dark paper up 216%,
which moves every ratio on the site, and the audit would still have printed
"Pass".

So this measures what is on the screen:

  mean   the paper's own colour must survive the texture. soft-light is the
         identity at mid-grey and the tiles are centred there, so the mean
         should come back within a whisker of the token.
  sd     the texture must be present, and be the same *perceptual* strength in
         both palettes -- sd of CIE L*, against GRAIN_TARGET_DL. A tile that
         stopped painting reads 0.00 here and fails.
"""
import collections
import os
import statistics
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import possumlogic as P                                    # noqa: E402

#: How far the rendered mean may sit from the palette's own paper, per channel.
#: One level is rounding; three would be a visible cast.
MEAN_TOLERANCE = 2
#: How far the measured texture may sit from what write_grain solved for.
#: Generous, because it is a sampled patch rather than the whole tile.
SD_TOLERANCE = 0.25
#: Pages worth checking: one per base stylesheet, since each sets its own body.
PAGES = ("index.html", "show/2026-05-01.html", "song/tweezer.html",
         "method.html")

#: Sampled from the top padding: `body` has clamp(1.4rem,4vw,3.5rem) of it, so
#: at 900px wide the first 30 rows of every page type are paper and nothing
#: else. Sampling the bottom-right instead put the patch inside a table row on
#: half the pages and read the ink.
PATCH_TOP, PATCH_BOTTOM = 4, 28
PATCH_LEFT, PATCH_RIGHT = 120, 780


def lstar(v):
    v = max(0.0, min(255.0, v)) / 255
    y = v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    return 116 * (y ** (1 / 3)) - 16 if y > 0.008856 else 903.3 * y


def sample(site_dir, page, theme, exe):
    """-> (mean rgb, sd of L*) over an empty patch of that page's paper.

    The theme is stamped onto <html> in a copy written *beside the original*,
    so every relative URL in the page -- the sheet, the tiles, the face --
    still resolves without a <base>. An iframe was the first shape of this and
    it was three bugs at once: the src was resolved against the wrong depth,
    the theme never reached the inner document, and the patch landed on the
    harness rather than the page.
    """
    from PIL import Image
    src = os.path.join(site_dir, page)
    with open(src, encoding="utf-8") as fh:
        markup = fh.read()
    # THEME_JS runs inline at parse time and calls apply(localStorage), which
    # with nothing stored *removes* data-theme -- so stamping the attribute on
    # <html> is not enough, the page wipes it before it paints. A script at the
    # end of <body> runs after it and wins.
    stamped = markup.replace(
        "</body>",
        "<script>document.documentElement.setAttribute("
        "'data-theme','%s')</script></body>" % theme, 1)
    assert stamped != markup, "no </body> to re-stamp the theme in: " + page
    # Beside the original, and removed again: a harness left in site/ ships,
    # and one of them reached sitemap.xml.
    probe = os.path.join(os.path.dirname(src), "_paper_probe.html")
    with open(probe, "w", encoding="utf-8") as fh:
        fh.write(stamped)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            shot = os.path.join(tmp, "p.png")
            subprocess.run(
                [exe, "--headless", "--disable-gpu", "--hide-scrollbars",
                 "--force-device-scale-factor=1", "--window-size=900,600",
                 "--screenshot=" + shot, "--virtual-time-budget=15000",
                 "file://" + os.path.abspath(probe)],
                check=True, timeout=120,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            im = Image.open(shot).convert("RGB")
            px = [im.getpixel((x, y))
                  for x in range(PATCH_LEFT, PATCH_RIGHT)
                  for y in range(PATCH_TOP, PATCH_BOTTOM)]
    finally:
        os.remove(probe)
    mean = tuple(sum(p[i] for p in px) / len(px) for i in range(3))
    return mean, statistics.pstdev([lstar(p[0]) for p in px])


def main():
    site_dir = sys.argv[1] if len(sys.argv) > 1 else "site"
    exe = P.chrome_exe()
    if not exe:
        print("no Chrome-family browser found; skipping")
        return 0
    try:
        import PIL                                          # noqa: F401
    except ImportError:
        print("Pillow not installed; skipping")
        return 0

    bad = []
    for theme, palette in (("light", P.LIGHT), ("dark", P.DARK)):
        want = tuple(int(palette["paper"].lstrip("#")[i:i + 2], 16)
                     for i in (0, 2, 4))
        target = P._grain_spread.__defaults__[0]
        for page in PAGES:
            if not os.path.isfile(os.path.join(site_dir, page)):
                continue
            mean, sd = sample(site_dir, page, theme, exe)
            drift = max(abs(mean[i] - want[i]) for i in range(3))
            print("%-24s %-5s mean %s want %s  drift %.1f  sd(L*) %.2f"
                  % (page, theme, tuple(round(m, 1) for m in mean), want,
                     drift, sd))
            if drift > MEAN_TOLERANCE:
                bad.append("%s %s: paper drifted %.1f levels from %s -- the "
                           "texture is shifting the page colour"
                           % (page, theme, drift, want))
            if abs(sd - target) > SD_TOLERANCE:
                bad.append("%s %s: texture measures sd(L*) %.2f, wanted %.2f "
                           "%s" % (page, theme, sd, target,
                                   "-- the grain is not painting" if sd < 0.1
                                   else "-- the grain is mistuned"))
    for line in bad:
        print("FAIL:", line)
    if bad:
        return 1
    print("ok: paper holds its colour and carries its texture, both palettes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
