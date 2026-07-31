#!/usr/bin/env python3
"""The site does not frame a show in terms of the time of day.

    python3 tools/check_vocabulary.py [site_dir]
    python3 tools/check_vocabulary.py --probe [site_dir]   # prove it can fail

Exits non-zero and quotes every offending sentence.

Ian, 2026-07-27, on a heading that read "One or two nights": *"I'm not sure
where you picked up the 'nights' lexicon. While it's true that most shows are
at night, this seems over-specific."* The unit is a **show**, counted as one
everywhere from BUSTOUT_GAP to shows_since, and a matinee or a festival
afternoon is no less one.

That ruling already had a guard -- `tools/check_few_plays.py` asserts the word
cannot come back into any string derived from FEW_NAMES. It was scoped to one
function, so it passed while `years.html`, written three days later, put the
word back as a *unit*: a column head, a hero card, a glossary label and 39
blocks of "4 nights, of 4 ever". A check that covers one function reports a
clean pass over a site that has the bug somewhere else. This one reads the
built pages.

What is not an offence:

  * **Song titles.** Waiting All Night, O Holy Night, After Midnight and The
    Night the Lights Went Out in Georgia are the band's words, not this
    site's. Every name in the archive is subtracted from the text first.
  * **Venue and tour names**, on the same grounds.
  * **Proper nouns** -- The Tonight Show, Late Night with Jimmy Fallon,
    Saturday Night Live. A television booking is a title.
  * **phish.net's own prose**, which the site quotes rather than writes:
    `.note`, `.jam` and `.ax-note` are the three places it appears.
  * **Genuine times of day.** The watch window opens at 23:00 UTC because
    shows start in the evening; that is a fact about clocks, not a unit.
    Nothing in reader-facing text has needed it yet, so there is no exemption
    for it here -- add one with a comment if a real case turns up.
"""
import glob
import html
import os
import re
import sys

#: Words that frame a show by when it happened. Checked case-insensitively and
#: on a word boundary, so "midnight" and "fortnight" are not hits.
BANNED = ("night", "nights", "tonight", "evening", "evenings")

#: Where phish.net's prose lands rather than this site's own. A show page
#: uses `.notes`, a song page `.note`, the not-a-show page `.ax-note`, and
#: both carry `.jam`. All four, because the first cut listed only `note` and a
#: `\bnote\b` matches none of `notes` -- which is the same class of mistake
#: this file exists to catch. An exemption that silently matches nothing makes
#: the check *louder*, which is the safe direction for it to fail in.
QUOTED = ("notes", "note", "jam", "ax-note")

#: Titles of things, which happen to contain a banned word.
PROPER = ("The Tonight Show Starring Jimmy Fallon", "The Tonight Show",
          "Late Night with Jimmy Fallon", "Late Night", "Saturday Night Live",
          "Tonight Show")


def archive_names(site_dir):
    """Every song, venue and tour name the built site could be printing.

    Read out of the built pages rather than out of `site/data`, which holds a
    calendar and a card index and no song names at all -- a first cut walked
    it, collected 153 venues, exempted nothing else, and reported 245 pages of
    Waiting All Night.
    """
    names = set()
    # The song pages are the fullest list of song names there is. Read whole:
    # every page carries its stylesheet inline, so the <h1> is well past the
    # first 4 KB and a head-only read found none of the 589.
    for path in glob.glob(os.path.join(site_dir, "song", "*.html")):
        with open(path, encoding="utf-8") as fh:
            found = re.search(r"<h1[^>]*>(.*?)</h1>", fh.read(), re.S)
        if found:
            names.add(html.unescape(re.sub(r"<[^>]+>", "", found.group(1))))
    # Songs with no page of their own still get printed -- the years and
    # not-a-show pages name them -- and the songs index lists every one.
    songs = os.path.join(site_dir, "songs.html")
    if os.path.isfile(songs):
        with open(songs, encoding="utf-8") as fh:
            names.update(html.unescape(n) for n in
                         re.findall(r'data-song="([^"]+)"', fh.read()))
    # Rooms. The venues page lists only the 153 the *archive* holds a report
    # from, and the archive starts in 2009 -- so a song page's 1991 row names
    # Starry Night and its 1994 row The Edge Night Club, neither of which that
    # page has ever heard of. Every `.r-venue` on every page is the full set.
    for path in glob.glob(os.path.join(site_dir, "*.html")) \
            + glob.glob(os.path.join(site_dir, "*", "*.html")):
        with open(path, encoding="utf-8") as fh:
            page = fh.read()
        names.update(html.unescape(v) for v in re.findall(
            r"class='(?:r-venue|vn-venue)'>(.*?)<", page))
        # And the songs either side of a performance, plus the years page's
        # chips -- the only places a cover with no page of its own gets named:
        # You Shook Me All Night Long, You Gotta See Mama Every Night, Night
        # Moves, Night and Day, The Lion Sleeps Tonight.
        for frag in re.findall(r"class='nb-(?:in|out)[^']*'>(.*?)</span>",
                               page) \
                + re.findall(r"<div class='chips'>(.*?)</div>", page):
            for cell in re.findall(r"<(?:a|span)[^>]*>(.*?)</(?:a|span)>",
                                   frag) or [frag]:
                names.add(html.unescape(
                    re.sub(r"<[^>]+>", "", re.sub(r"<b>.*?</b>", "",
                                                  cell))).strip())
    return {n for n in names if n.strip()}


def reader_text(markup):
    """What a reader actually reads: no script, no style, no quoted prose."""
    markup = re.sub(r"<script\b.*?</script>", " ", markup, flags=re.S | re.I)
    markup = re.sub(r"<style\b.*?</style>", " ", markup, flags=re.S | re.I)
    for cls in QUOTED:
        markup = re.sub(r"<(\w+)[^>]*\bclass=['\"][^'\"]*\b%s\b[^'\"]*['\"]"
                        r".*?</\1>" % re.escape(cls), " ", markup,
                        flags=re.S | re.I)
    # Attribute values a reader is shown or read aloud, kept before tags go.
    # `data-search` is deliberately not among them: it is a lowercased haystack
    # for the filter box, holding every venue name and every word of
    # phish.net's jam notes, and nobody reads it.
    spoken = " ".join(re.findall(
        r"(?:aria-label|title|alt|content)=[\"']([^\"']*)[\"']", markup))
    markup = re.sub(r"<[^>]+>", " ", markup)
    text = html.unescape(markup + " " + spoken)
    # og:url and the card URL are `content` values and are read to nobody; a
    # slug is not prose, and o-holy-night.html is not this site calling a show
    # a night.
    return re.sub(r"https?://\S+", " ", text)


def name_mask(names):
    """One alternation over the names that could possibly matter, longest first.

    Two things this is not. It is **not a loop of str.replace**: run in
    sequence, a short name eats the middle of a longer one and leaves the tail
    behind. "Sleep" is a song, so "The Lion Sleeps Tonight" came out as
    "The Lion s Tonight" and the tonight survived as an offence on three
    pages. One pass cannot do that -- the alternation takes the longest name
    at each position and consumes it whole.

    And it is **not every name**. Only a name that itself contains a banned
    word can hide one, so 4,000 titles filter to about thirty. The first cut
    compiled the lot and ran past two minutes over 1,313 pages; this runs in
    about one second and checks exactly the same thing.
    """
    banned = re.compile(r"\b(?:%s)\b" % "|".join(BANNED), re.I)
    parts = sorted({n.strip() for n in list(names) + list(PROPER)
                    if n.strip() and banned.search(n)}, key=len, reverse=True)
    return re.compile("|".join(re.escape(p) for p in parts), re.I) \
        if parts else None


def offences(text, mask):
    """Banned words left once every name in the archive is subtracted."""
    if mask is not None:
        text = mask.sub(" ", text)
    hits = []
    for word in BANNED:
        for found in re.finditer(r"\b%s\b" % word, text, re.I):
            start = max(0, found.start() - 60)
            hits.append(re.sub(r"\s+", " ",
                               text[start:found.end() + 40]).strip())
    return hits


#: The proof, which lives here rather than beside it so the two cannot drift.
#: Four injections that must fail and two that must not: a check nobody has
#: watched fail is a check that passes for the wrong reason, and the two
#: exemptions are the half of this file most likely to swallow a real hit.
#: (page, find, replace, must_fail)
PROBE = (
    ("years.html", "<div class='lbl'>Shows read</div>",
     "<div class='lbl'>Nights read</div>", True),
    ("years.html", "<dt>A show</dt>", "<dt>A night</dt>", True),
    ("method.html", "against the show, so", "against the night, so", True),
    ("years.html", "aria-label='1998, 67 shows'",
     "aria-label='1998, 67 nights'", True),
    ("show/2012-06-22.html", "<div class='notes'>",
     "<div class='notes'>Played late that night. ", False),
    ("songs.html", '<li data-song="Bathtub Gin"',
     '<li data-song="Waiting All Night"', False),
)


def probe(site_dir="site"):
    """Inject each PROBE case into a copy of the site and assert the verdict."""
    import shutil
    import subprocess
    import tempfile
    bad = []
    for page, find, repl, must_fail in PROBE:
        tmp = tempfile.mkdtemp()
        try:
            copy = os.path.join(tmp, "site")
            shutil.copytree(site_dir, copy)
            path = os.path.join(copy, page)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if find not in text:
                bad.append("anchor gone from %s: %r" % (page, find[:48]))
                continue
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace(find, repl, 1))
            failed = subprocess.run(
                [sys.executable, os.path.abspath(__file__), copy],
                capture_output=True, text=True).returncode != 0
            print("  %s  %-34s -> check %s"
                  % ("ok " if failed == must_fail else "BAD", repl[:34],
                     "failed" if failed else "passed"))
            if failed != must_fail:
                bad.append("%s: wanted the check to %s, it %s"
                           % (page, "fail" if must_fail else "pass",
                              "failed" if failed else "passed"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if bad:
        print("\nPROBE FAILED:")
        for line in bad:
            print("   ", line)
        return 1
    print("\nall %d injections behaved: the check fires on this site's words "
          "and stays quiet on the band's" % len(PROBE))
    return 0


def main(site_dir="site"):
    names = archive_names(site_dir)
    mask = name_mask(names)
    pages = sorted(glob.glob(os.path.join(site_dir, "*.html"))
                   + glob.glob(os.path.join(site_dir, "*", "*.html")))
    bad, checked = {}, 0
    for path in pages:
        with open(path, encoding="utf-8") as fh:
            hits = offences(reader_text(fh.read()), mask)
        checked += 1
        if hits:
            bad[path] = hits
    total = sum(len(v) for v in bad.values())
    if bad:
        print("%d page(s) frame a show by the time of day:\n" % len(bad))
        for path in sorted(bad):
            print("  %s" % path)
            for hit in bad[path][:6]:
                print("      ...%s..." % hit)
            if len(bad[path]) > 6:
                print("      (+%d more)" % (len(bad[path]) - 6))
        print("\n%d occurrence(s) over %d pages. The unit is a show."
              % (total, checked))
        return 1
    print("%d pages checked, %d name(s) exempted, 0 problem(s)"
          % (checked, len(names)))
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--probe":
        sys.exit(probe(*args[1:]))
    sys.exit(main(*args))
