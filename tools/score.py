"""Motion Crackers launch — score renderer.

Every sound is a recorded instrument sample (Karoryfer Swirly Drums, Virtuosity Drums,
Growlybass, Emily Guitar, VCSL percussion/mallets). This script only sequences, tunes,
mixes and masters them. 120 BPM, A dorian. Timeline is locked to video/index.html.

usage: python3 tools/score.py <samples_dir> <out.wav>
"""
import sys, glob, os
from fractions import Fraction
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
DUR = 20.0
BPM = 120
BEAT = 60 / BPM
S16 = BEAT / 4
ROOT = sys.argv[1]
OUT = sys.argv[2]
rng = np.random.default_rng(7)

# ------------------------------------------------------------------ samples
_cache = {}


def load(path):
    if path in _cache:
        return _cache[path]
    x, sr = sf.read(path, always_2d=True)
    x = x.astype(np.float64)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = x[:, :2]
    if sr != SR:
        f = Fraction(SR, sr).limit_denominator(1000)
        x = signal.resample_poly(x, f.numerator, f.denominator, axis=0)
    x = x / (np.max(np.abs(x)) + 1e-12)  # every hit peak-normalised; levels are set in the score
    _cache[path] = x
    return x


def P(*parts):
    return os.path.join(ROOT, *parts)


def pick(pattern, i=None):
    files = sorted(glob.glob(pattern))
    assert files, pattern
    return files[(i if i is not None else rng.integers(len(files))) % len(files)]


def pitch(x, st):
    if abs(st) < 1e-3:
        return x
    r = Fraction(2 ** (-st / 12)).limit_denominator(400)
    return signal.resample_poly(x, r.numerator, r.denominator, axis=0)


NOTE = {"C": 0, "Db": 1, "C#": 1, "D": 2, "Eb": 3, "D#": 3, "E": 4, "F": 5, "Gb": 6, "F#": 6, "G": 7, "Ab": 8, "G#": 8, "A": 9, "Bb": 10, "A#": 10, "B": 11}


def midi(n):
    name, octv = n[:-1], int(n[-1])
    return 12 * (octv + 1) + NOTE[name]


def label_midi(lbl):
    lbl = lbl.lower()
    name = lbl[:-1]
    name = name[0].upper() + name[1:]
    return 12 * (int(lbl[-1]) + 1) + NOTE[name]


# ------------------------------------------------------------------ buses
buses = {}


def bus(name):
    if name not in buses:
        buses[name] = np.zeros((int(SR * (DUR + 3)), 2))
    return buses[name]


def place(name, x, t, db=0.0, pan=0.0, length=None, fade=0.03, fadein=0.0):
    x = x.copy()
    if length is not None:
        n = int(length * SR)
        x = x[: n + int(fade * SR)]
        nf = min(int(fade * SR), len(x))
        if len(x) > n and nf > 0:
            x[-nf:] *= np.cos(np.linspace(0, np.pi / 2, nf))[:, None] ** 2
    if fadein > 0:
        nf = int(fadein * SR)
        x[:nf] *= np.linspace(0, 1, nf)[:, None]
    g = 10 ** (db / 20)
    l = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2)
    r = np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
    x = x * g * np.array([min(1, l), min(1, r)])
    b = bus(name)
    i = int(round(t * SR))
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), len(b) - i)
    b[i : i + n] += x[:n]


# ------------------------------------------------------------------ instruments
SW = P("karoryfer.swirly-drums", "Samples")
VD = P("virtuosity_drums", "Samples")
VC = P("VCSL", "Idiophones")


def kick(t, vel=3, db=0.0):
    a = load(pick(P(VD, "kickmic", "kick", f"kickmic_kick_snoff_vl{vel}_rr*.flac")))
    b = load(pick(P(VD, "room", "kick", f"room_kick_snoff_vl{vel}_rr*.flac")))
    n = max(len(a), len(b))
    x = np.zeros((n, 2)); x[: len(a)] += a; x[: len(b)] += 0.45 * b
    place("kick", x, t, db - 2)


def snare(t, vel=8, db=0.0, kind="main"):
    top = load(pick(P(SW, f"snare_{kind}", f"snare_*_vl{vel}_rr*_top.wav")))
    btm = load(pick(P(SW, f"snare_{kind}", f"snare_*_vl{vel}_rr*_btm.wav")))
    n = max(len(top), len(btm))
    x = np.zeros((n, 2)); x[: len(top)] += top; x[: len(btm)] += 0.35 * btm
    place("snare", x, t, db - 2)


def xstick(t, vel=3, db=0.0, pan=0.0):
    # crossstick layers: vl1..16 (vel 1..4 -> vl 4..16)
    place("snare", load(P(VD, "mid", "snare", f"mid_snare_crossstick_vl{min(16, vel * 4)}.flac")), t, db - 9, pan)


def vsnare(t, art="center", vel=3, db=0.0):
    top = {"center": 36, "rimshot": 12}[art]
    place("snare", load(P(VD, "mid", "snare", f"mid_snare_{art}_vl{max(1, min(top, round(vel * top / 4)))}.flac")), t, db - 6)


def hat(t, vel=6, db=0.0, kind="tight", length=None):
    place("hats", load(pick(P(SW, f"hat_{kind}", f"*_vl{vel}_rr*.wav"))), t, db - 14, 0.25, length=length, fade=0.06)


def tom(t, which="mhi", vel=7, db=0.0, pan=0.0):
    place("toms", load(pick(P(SW, f"tom_{which}", f"*_vl{vel}_rr*.wav"))), t, db - 7, pan)


def splash(t, vel=5, db=0.0, length=None):
    place("cym", load(pick(P(SW, "splash", f"*_vl{vel}_rr*.wav"))), t, db - 10, -0.2, length=length, fade=0.6)


def logdrum(t, hi=False, v=2, db=0.0, st=0.0):
    p = pick(P(VC, "Struck Idiophones", "Slit Drum", f"LogDrum{'Hi' if hi else 'Lo'}_MedM_v{v}_rr1_Sum.wav"))
    place("perc", pitch(load(p), st + (1 if hi else 0)), t, db - 5, 0.15 if hi else -0.1)


def shaker(t, db=0.0, i=None):
    p = pick(P(VC, "Struck Idiophones", "Shaker, Small", "Mid_ShakerDouble_*"), i)
    place("perc", load(p), t, db - 6, 0.35)


def clap(t, db=0.0):
    place("perc", load(pick(P(VC, "Struck Idiophones", "Claps", "Clap_rr*.wav"))), t, db - 10, -0.05)


# tonal instruments: (glob, label->actual offset)
BASS_ST = P("karoryfer.growlybass", "staccato")
BASS_SU = P("karoryfer.growlybass", "sustain")
GTR = P("karoryfer.emilyguitar", "notes")


def nearest(folder, pat, target, offset):
    best = None
    for f in glob.glob(os.path.join(folder, pat)):
        lbl = os.path.basename(f).split("_")[0]
        try:
            m = label_midi(lbl) + offset
        except Exception:
            continue
        d = target - m
        if best is None or abs(d) < abs(best[1]) or (abs(d) == abs(best[1]) and d > 0):
            best = (lbl, d)
    return best


def bass(t, note, length=0.2, db=0.0, sustain=False, dyn="f"):
    m = midi(note)
    folder = BASS_SU if sustain else BASS_ST
    lbl, d = nearest(folder, "*_rr1.wav", m, -12)
    pat = f"{lbl}_{dyn}_rr*.wav" if sustain else f"{lbl}_staccato_rr*.wav"
    x = pitch(load(pick(os.path.join(folder, pat))), d)
    place("bass", x, t, db - 7, 0.0, length=length, fade=0.05 if sustain else 0.025)


def gtr_note(t, note, dyn="mf", length=None, db=0.0, pan=0.0, fade=0.08):
    m = midi(note)
    lbl, d = nearest(GTR, "*_mf_rr1.wav", m, 0)
    x = pitch(load(pick(os.path.join(GTR, f"{lbl}_{dyn}_rr*.wav"))), d)
    place("gtr", x, t, db - 13, pan, length=length, fade=fade)


def chord(t, notes, dyn="mf", length=None, db=0.0, strum=0.011, up=False, pan=-0.2):
    seq = list(reversed(notes)) if up else notes
    for k, n in enumerate(seq):
        gtr_note(t + k * strum, n, dyn, None if length is None else length - k * strum, db - 2.5, pan + 0.06 * k, fade=0.05)


def mute(t, i=None, db=0.0, pan=0.3):
    p = pick(P("karoryfer.emilyguitar", "noises", f"muted{1 + (i if i is not None else int(rng.integers(5)))}_rr*.wav"))
    place("gtr", load(p), t, db - 11, pan, length=0.14, fade=0.03)


def vibes(t, note, db=0.0, pan=0.0, length=None):
    m = midi(note)
    folder = P(VC, "Struck Idiophones", "Vibraphone", "Soft Mallets")
    lbl, d = None, None
    best = None
    for f in glob.glob(os.path.join(folder, "Vibes_soft_*_v2_rr1_Main.wav")):
        l = os.path.basename(f).split("_")[2]
        mm = label_midi(l) + 12
        if best is None or abs(m - mm) < abs(best[1]):
            best = (l, m - mm)
    lbl, d = best
    x = pitch(load(pick(os.path.join(folder, f"Vibes_soft_{lbl}_v2_rr*_Main.wav"))), d)
    place("keys", x, t, db - 12, pan, length=length, fade=0.8)


def marimba(t, note, db=0.0, pan=0.0, dyn="med"):
    m = midi(note)
    folder = P(VC, "Struck Idiophones", "Marimba")
    best = None
    for f in glob.glob(os.path.join(folder, f"Marimba_hit_Outrigger_*_{dyn}_01.wav")):
        l = os.path.basename(f).split("_")[3]
        mm = label_midi(l) + 12
        if best is None or abs(m - mm) < abs(best[1]):
            best = (l, m - mm)
    x = pitch(load(os.path.join(folder, f"Marimba_hit_Outrigger_{best[0]}_{dyn}_01.wav")), best[1])
    place("keys", x, t, db - 12, pan)


# ------------------------------------------------------------------ the arrangement
def at(bar, step=0.0):
    return bar * 16 * S16 + step * S16


AM9 = ["A2", "G3", "C4", "E4", "B4"]       # stab voicing (root on the low A string)
AM9_UP = ["G3", "C4", "E4", "B4"]
D9 = ["F#3", "C4", "E4", "A4"]
FMAJ7 = ["F3", "A3", "C4", "E4"]
EM7 = ["E3", "G3", "B3", "D4"]

# --- bar 0: the dot. log drums answer each shape morph
logdrum(0.0, False, 3, 0)
kick(0.0, 2, -4)
logdrum(0.5, True, 2, -1)
logdrum(1.0, False, 2, -1)
kick(1.0, 1, -8)
logdrum(1.25, True, 2, -3, st=-2)
logdrum(1.5, True, 3, -2, st=3)
shaker(1.5, -10)
# the dot shrinks and flies to the "i": pickup
mute(1.75, 1, -4)
mute(1.875, 3, -2)
xstick(1.875, 2, -6)
bass(1.75, "G1", 0.22, -3)


def groove_bar(bar, chordname, fill=False, ghosts=True, last_beat=True):
    """Dry, tight 16th-note pocket. chordname: 'Am' or 'D'."""
    t0 = at(bar)
    # kick
    for s in [0, 7, 10] if not fill else [0, 7]:
        kick(t0 + s * S16, 4 if s == 0 else 3, 0 if s == 0 else -2)
    # backbeat
    snare(t0 + 4 * S16, 9, -1)
    if last_beat and not fill:
        snare(t0 + 12 * S16, 9, -1)
    if ghosts:
        snare(t0 + 6 * S16, 3, -9)
        if not fill:
            snare(t0 + 15 * S16, 2, -11)
    # hats: 8ths, accents on the off-beat, a little swing on the 16th ghosts
    end = 12 if fill else 16
    for s in range(0, end, 2):
        hat(t0 + s * S16, 7 if s % 4 == 2 else 5, -3 if s % 4 == 2 else -6)
    for s in [3, 11]:
        if s < end:
            hat(t0 + s * S16 + 0.012, 3, -11)
    if not fill and last_beat:
        hat(t0 + 14 * S16, 6, -8, "open", length=0.22)
    for s in range(0, end):
        shaker(t0 + s * S16 + (0.01 if s % 2 else 0), -21 if s % 2 else -17, i=s % 4)
    # bass
    if chordname == "Am":
        line = [(0, "A1", 0.32), (3, "A2", 0.1), (6, "A1", 0.12), (8, "E2", 0.2), (10, "G2", 0.1), (11, "A2", 0.1), (14, "G1", 0.12)]
    else:
        line = [(0, "D2", 0.32), (3, "D3", 0.1), (6, "D2", 0.12), (8, "A1", 0.2), (10, "C2", 0.1), (11, "D2", 0.1), (14, "E2", 0.12)]
    for s, n, L in line:
        if fill and s >= 12:
            continue
        bass(t0 + s * S16, n, L, -1 if s == 0 else -4)
    # guitar: short clean stab on the "e" of 1 and the "and" of 3, muted chks between
    v = AM9_UP if chordname == "Am" else D9
    chord(t0 + 2 * S16, v, "mf", 0.13, -3)
    chord(t0 + 10 * S16, v, "mp", 0.11, -5, up=True)
    mute(t0 + 6 * S16, 0, -9)
    if not fill:
        mute(t0 + 14 * S16, 2, -8)


# --- bars 1-4: groove A (2.0 – 10.0)
kick(2.0, 4, 1)
splash(2.0, 5, -12, length=1.6)
chord(2.0, AM9, "f", 0.42, -1)
groove_bar(1, "Am")
groove_bar(2, "D", fill=True)
# "AI" glitch 4.5–4.875: cross-stick + mutes flicker on 16ths, period pops at 5.0
for k, tt in enumerate([4.5, 4.625, 4.75]):
    xstick(tt, 3, -3, pan=[-0.3, 0.3, 0][k])
    mute(tt + 0.004, k + 1, -7, pan=[0.3, -0.3, 0][k])
logdrum(5.0, True, 2, -6, st=5)
# tom fill into the tile morph
tom(5.5, "mhi", 8, -3, 0.2)
tom(5.625, "mhi", 6, -6, 0.2)
tom(5.75, "floor", 8, -2, -0.2)
tom(5.875, "floor", 6, -5, -0.2)
kick(5.75, 2, -6)
# 6.0: the dot becomes a tile and the camera pulls back
splash(6.0, 7, -9, length=2.0)
chord(6.0, ["D3", "F#3", "C4", "E4", "A4"], "f", 0.5, -1)
groove_bar(3, "Am")
groove_bar(4, "D", last_beat=False)
# rows close (9.5) – pickup into the zoom
mute(9.5, 2, -7)
mute(9.625, 4, -8)
tom(9.75, "mhi", 6, -7, 0.2)
tom(9.875, "floor", 6, -6, -0.2)

# --- bars 5-6: dive into one piece, then a full-screen showcase — one design per beat (10.0 – 14.0)
kick(10.0, 4, 0)
bass(10.0, "F1", 1.95, -2, sustain=True, dyn="p")
for k, n in enumerate(FMAJ7):
    vibes(10.0 + k * 0.012, n, -6, pan=-0.35 + 0.23 * k, length=1.95)
for s in range(32):
    tt = 10.0 + s * S16
    if s % 2 == 0:
        hat(tt, 5 if s % 4 else 6, -7 if s % 4 else -5)
    else:
        hat(tt + 0.01, 3, -12)
    shaker(tt, -21 if s % 2 else -17, i=s % 4)
bass(12.0, "E1", 1.45, -2, sustain=True, dyn="p")
for k, n in enumerate(EM7):
    vibes(12.0 + k * 0.012, n, -7, pan=-0.35 + 0.23 * k, length=1.45)
# every cut (a dot that grows into the next design) gets a marimba note + a kick or a cross-stick
melody = ["A3", "C4", "E4", "D4", "G4", "E4", "A3"]
for k, n in enumerate(melody):
    tt = 10.5 + k * BEAT
    marimba(tt, n, -2, pan=[-0.3, 0.3][k % 2] * 0.6)
    if k % 2 == 0:
        xstick(tt, 3, -2, pan=0.1)
    else:
        kick(tt, 3, -2)
    mute(tt + 0.25, k % 5, -10)
kick(12.0, 3, -3)
kick(13.0, 3, -2)
bass(13.0, "A1", 0.3, -2)
bass(13.375, "A2", 0.1, -5)
bass(13.75, "G1", 0.1, -4)
# snare build into 14.0 (the last design collapses into the full stop)
for k in range(4):
    vsnare(13.5 + k * S16, "center", 1 + k, -10 + 2.5 * k)

# --- bar 7: "Each with its prompt." (14.0 – 15.5), then a full stop
kick(14.0, 4, 1)
splash(14.0, 6, -11, length=1.4)
chord(14.0, AM9, "f", 0.36, -1)
groove_bar(7, "Am", last_beat=False)
logdrum(14.5, False, 3, -3)  # the period lands
# 15.5: silence. the dot hops off the line …
logdrum(15.5, True, 2, -6, st=5)
mute(15.75, 1, -6)
mute(15.875, 3, -4)

# --- bars 8-9: the crack and the name (16.0 – 20.0)
kick(16.0, 4, 1)
vsnare(16.0, "rimshot", 4, -3)
splash(16.0, 7, -10, length=1.2)
bass(16.0, "A1", 0.2, -1)
stab = None
chord(16.0, AM9_UP, "f", 0.1, -3)
# glitch steps on every 16th: alternating chopped sounds that follow the letters
cycle = ["x", "m", "h", "s", "x", "m", "flash", "h", "x", "m", "s", "x"]
for k, kind in enumerate(cycle):
    tt = 16.0 + (k + 1) * S16
    if tt >= 17.5:
        break
    lvl = -9 + 5 * (k / 11)
    if kind == "x":
        xstick(tt, 3, lvl, pan=0.3 if k % 2 else -0.3)
    elif kind == "m":
        mute(tt, k % 5, lvl - 1, pan=-0.3 if k % 2 else 0.3)
    elif kind == "h":
        hat(tt, 7, lvl - 2)
    elif kind == "s":
        chord(tt, AM9_UP, "mp", 0.06, lvl - 2, strum=0.004)
    elif kind == "flash":
        kick(tt, 3, -3)
        chord(tt, AM9_UP, "mf", 0.08, lvl, strum=0.004)
    if k % 2 == 1:
        bass(tt, "A2" if k % 4 == 1 else "E2", 0.06, -10)
# 17.5: resolve — the clean wordmark
kick(17.5, 4, 1)
vsnare(17.5, "rimshot", 3, -6)
splash(17.5, 8, -10)
bass(17.5, "A1", 2.4, -1, sustain=True, dyn="f")
chord(17.5, ["A2", "E3", "G3", "C4", "E4", "B4"], "f", 2.45, 0, strum=0.016)
for k, n in enumerate(["A3", "C4", "E4", "G4"]):
    vibes(17.5 + 0.03 + k * 0.01, n, -9, pan=-0.3 + 0.2 * k, length=2.4)
logdrum(17.5, False, 3, -6)


# ------------------------------------------------------------------ mixing
def biquad(kind, f, q=0.707, gain_db=0.0):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f / SR; c = np.cos(w); s = np.sin(w); al = s / (2 * q)
    if kind == "lp":
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]; a = [1 + al, -2 * c, 1 - al]
    elif kind == "hp":
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]; a = [1 + al, -2 * c, 1 - al]
    elif kind == "peak":
        b = [1 + al * A, -2 * c, 1 - al * A]; a = [1 + al / A, -2 * c, 1 - al / A]
    elif kind == "lowshelf":
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
        a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    elif kind == "highshelf":
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
        a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    return np.array(b) / a[0], np.array(a) / a[0]


def eq(x, *bands):
    for band in bands:
        b, a = biquad(*band)
        x = signal.lfilter(b, a, x, axis=0)
    return x


def comp(x, thr_db=-18, ratio=3, att=0.005, rel=0.12, makeup=0.0):
    env_in = np.max(np.abs(x), axis=1)
    a_a = np.exp(-1 / (att * SR)); a_r = np.exp(-1 / (rel * SR))
    # envelope follower (vectorised via lfilter on a peak-hold approximation)
    env = signal.lfilter([1 - a_r], [1, -a_r], env_in)
    env = np.maximum(env, signal.lfilter([1 - a_a], [1, -a_a], env_in))
    lvl = 20 * np.log10(env + 1e-9)
    over = np.maximum(0, lvl - thr_db)
    gr = -over * (1 - 1 / ratio)
    g = 10 ** ((gr + makeup) / 20)
    return x * g[:, None]


def make_ir(rt60=1.3, pre=0.012, damp=5500, length=2.4, seed=3):
    r = np.random.default_rng(seed)
    n = int(length * SR)
    tt = np.arange(n) / SR
    env = np.exp(-6.91 * tt / rt60)
    ir = r.standard_normal((n, 2)) * env[:, None]
    # frequency-dependent decay: progressively darker tail
    dark = eq(ir, ("lp", damp * 0.45))
    mix = np.clip(tt / (rt60 * 0.6), 0, 1)[:, None]
    ir = ir * (1 - mix) + dark * mix
    ir = eq(ir, ("lp", damp), ("hp", 180))
    ir[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))[:, None]
    ir = np.vstack([np.zeros((int(pre * SR), 2)), ir])
    return ir / np.sqrt(np.sum(ir ** 2))


def reverb(x, ir):
    return signal.fftconvolve(x, ir, axes=0)[: len(x)]


def sat(x, drive=1.4):
    return np.tanh(x * drive) / np.tanh(drive)


L = int(SR * (DUR + 3))
get = lambda n: buses.get(n, np.zeros((L, 2)))

kickb = eq(get("kick"), ("hp", 32), ("peak", 62, 1.0, 2.5), ("peak", 380, 1.2, -4), ("peak", 3200, 1.2, 1.5), ("lp", 9000))
snareb = eq(get("snare"), ("hp", 110), ("peak", 220, 1.2, 1.5), ("peak", 900, 1.4, -2), ("highshelf", 7000, 0.7, -1), ("lp", 14000))
hatsb = eq(get("hats"), ("hp", 380), ("highshelf", 7500, 0.7, -2), ("lp", 14000))
tomsb = eq(get("toms"), ("hp", 60), ("peak", 600, 1.0, -3), ("lp", 9000))
cymb = eq(get("cym"), ("hp", 450), ("highshelf", 6500, 0.7, -3), ("lp", 13000))
percb = eq(get("perc"), ("hp", 45), ("highshelf", 7000, 0.7, -2), ("lp", 13000))
bassb = eq(get("bass"), ("hp", 30), ("peak", 90, 0.9, 1.5), ("peak", 280, 1.0, -2.5), ("peak", 900, 1.0, 1.5), ("lp", 3800))
bassb = comp(bassb, -20, 4, 0.003, 0.08, 4)
bassb = sat(bassb * 1.3, 1.2) / 1.3
gtrb = eq(get("gtr"), ("hp", 140), ("lowshelf", 300, 0.7, -2), ("peak", 2400, 0.9, 2.0), ("highshelf", 6000, 0.7, -2.5), ("lp", 11000))
gtrb = sat(gtrb * 1.6, 1.3) / 1.6
gtrb = comp(gtrb, -22, 3, 0.004, 0.1, 3)
keysb = eq(get("keys"), ("hp", 120), ("highshelf", 6000, 0.7, -2), ("lp", 12000))

drums = kickb + snareb + hatsb + tomsb
drums = comp(drums, -14, 2.5, 0.006, 0.12, 1.5)

room = make_ir(0.55, 0.006, 6500, 1.0, 11)
plate = make_ir(1.5, 0.018, 6000, 2.6, 5)

wet = reverb(snareb * 0.18 + tomsb * 0.15 + percb * 0.2 + kickb * 0.03, room) + reverb(gtrb * 0.22 + keysb * 0.32 + percb * 0.12 + snareb * 0.06 + cymb * 0.1, plate)
wet = eq(wet, ("hp", 200), ("lp", 9000))

if os.environ.get("STEMS"):
    for nm, b in [("kick", kickb), ("snare", snareb), ("hats", hatsb), ("toms", tomsb), ("cym", cymb), ("perc", percb), ("bass", bassb), ("gtr", gtrb), ("keys", keysb), ("wet", wet * 0.55)]:
        row = []
        for sec in range(20):
            sg = b[sec * SR:(sec + 1) * SR]
            row.append(f"{20 * np.log10(np.sqrt(np.mean(sg ** 2)) + 1e-9):5.0f}")
        print(nm.ljust(6), " ".join(row))
mix = (drums * 1.0 + cymb * 0.9 + percb * 0.95 + bassb * 1.0 + gtrb * 0.95 + keysb * 0.9) + wet * 0.55

# master: gentle glue, tone, loudness, true-peak-safe limiter
mix = eq(mix, ("hp", 26), ("lowshelf", 110, 0.7, 0.8), ("highshelf", 9000, 0.7, 0))
mix = comp(mix, -16, 1.8, 0.01, 0.2, 0)

try:
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(mix[: int(DUR * SR)])
except Exception:
    lufs = 20 * np.log10(np.sqrt(np.mean(mix ** 2)) + 1e-9)
target = -14.0
mix *= 10 ** ((target - lufs) / 20)


def limiter(x, ceil_db=-1.2, look=0.003, rel=0.09):
    ceil = 10 ** (ceil_db / 20)
    # 4x oversampled peak estimate for true-peak safety
    up = signal.resample_poly(x, 4, 1, axis=0)
    pk = np.max(np.abs(up), axis=1).reshape(-1, 4).max(axis=1)[: len(x)]
    need = np.minimum(1, ceil / np.maximum(pk, 1e-9))
    n = int(look * SR)
    # look-ahead min filter then smooth release
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, size=2 * n + 1, origin=0)
    a = np.exp(-1 / (rel * SR))
    out = np.empty_like(g); cur = 1.0
    for i in range(len(g)):
        cur = g[i] if g[i] < cur else a * cur + (1 - a) * g[i]
        out[i] = cur
    out = np.convolve(out, np.ones(n) / n, mode="same")
    return x * np.minimum(out, need)[:, None]


mix = limiter(mix)
mix = mix[: int(DUR * SR)]
# end: let the chord ring, fade the last 0.6 s
nf = int(0.6 * SR)
mix[-nf:] *= np.cos(np.linspace(0, np.pi / 2, nf))[:, None] ** 2
mix[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))[:, None]

sf.write(OUT, mix.astype(np.float32), SR, subtype="PCM_24")
try:
    print("LUFS", round(meter.integrated_loudness(mix), 2))
except Exception:
    pass
up = signal.resample_poly(mix, 4, 1, axis=0)
print("sample peak dBFS", round(20 * np.log10(np.max(np.abs(mix))), 2), "true peak dBTP", round(20 * np.log10(np.max(np.abs(up))), 2))
