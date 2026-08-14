#!/usr/bin/env python3
"""
Dunk Rush Arena - 오리지널 오디오/이미지 에셋 생성기
전부 절차적으로 합성한 독자 콘텐츠 (외부 음원/이미지 사용 없음, 저작권 문제 없음).
로컬에서는 --quick 플래그로 짧게 테스트하고, CI(GitHub Actions)에서는 기본(풀 길이)로 실행합니다.
"""
import numpy as np
import wave, os, math, random, argparse, json

SR = 48000

def to_wav(path, stereo):
    stereo = np.clip(stereo, -1.0, 1.0)
    pcm = (stereo * 32767.0).astype('<i2')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())
    size = os.path.getsize(path)
    print(f"  wrote {path}  ({size/1e6:.2f} MB)")
    return size

def mono_to_stereo(m, pan=0.0):
    l = m * (1.0 - max(0.0, pan))
    r = m * (1.0 + min(0.0, pan))
    return np.stack([l, r], axis=1)

def square(freq, t, duty=0.5):
    ph = (t*freq) % 1.0
    return np.where(ph < duty, 1.0, -1.0)

def tri(freq, t):
    ph = (t*freq) % 1.0
    return 2*np.abs(2*ph-1)-1

def sine(freq, t):
    return np.sin(2*np.pi*freq*t)

def saw(freq, t):
    ph = (t*freq) % 1.0
    return 2*ph-1

def adsr(n, a, d, s_lvl, r, sr=SR):
    a=int(a*sr); d=int(d*sr); r=int(r*sr)
    env = np.ones(n)
    a=min(a,n); 
    if a>0: env[:a] = np.linspace(0,1,a)
    d_end = min(a+d, n)
    if d_end>a: env[a:d_end] = np.linspace(1, s_lvl, d_end-a)
    if d_end < n: env[d_end:] = s_lvl
    if r>0 and r<n:
        env[-r:] *= np.linspace(1,0,r)
    return env

def note(freq, dur, wave_fn, vol=0.22, a=0.005,d=0.05,s=0.6,r=0.05):
    n = int(SR*dur)
    if n<=0: return np.zeros(0)
    t = np.arange(n)/SR
    w = wave_fn(freq, t)
    env = adsr(n, a, d, s, r)
    return w*env*vol

def silence(dur):
    return np.zeros(int(SR*dur))

# 5음 펜타토닉 스케일 (아케이드 느낌의 경쾌한 멜로디에 적합)
PENTA = [0,2,4,7,9,12,14,16,19,21,24]

def freq_of(root, semis):
    return root * (2**(semis/12))

def build_chiptune_track(path, root=261.63, bpm=132, bars=16, seed=1, energy=1.0):
    rnd = random.Random(seed)
    beat = 60.0/bpm
    step = beat/2  # 8분음표 단위
    steps_per_bar = 8
    total_steps = bars*steps_per_bar
    dur = total_steps*step + 1.0

    melody = np.zeros(int(SR*dur)+SR)
    bass = np.zeros_like(melody)
    drums = np.zeros_like(melody)

    chord_roots = [0,0,7,7,9,9,5,5]  # 8마디 순환 코드 루트(반음)
    for i in range(total_steps):
        bar = (i//steps_per_bar) % len(chord_roots)
        croot = chord_roots[bar]
        t0 = i*step
        idx0 = int(t0*SR)
        # 멜로디: 코드톤 주변 펜타토닉 워크
        if rnd.random() < 0.82:
            semis = croot + rnd.choice(PENTA[:6])
            f = freq_of(root*2, semis)
            n = note(f, step*rnd.choice([0.9,1.8]), square, vol=0.16*energy, a=0.003,d=0.04,s=0.5,r=0.05)
            end = min(len(melody), idx0+len(n))
            melody[idx0:end] += n[:end-idx0]
        # 베이스: 마디 시작에 루트음
        if i % steps_per_bar == 0:
            f = freq_of(root/2, croot)
            n = note(f, beat*1.9, tri, vol=0.22*energy, a=0.005,d=0.08,s=0.7,r=0.15)
            end = min(len(bass), idx0+len(n))
            bass[idx0:end] += n[:end-idx0]
        # 드럼: 킥/하이햇 패턴
        if i % 4 == 0:
            nn = int(SR*0.12)
            tt = np.arange(nn)/SR
            kick = sine(60, tt)*np.exp(-tt*28)*0.5*energy
            end=min(len(drums), idx0+nn); drums[idx0:end]+=kick[:end-idx0]
        if i % 2 == 1:
            nn = int(SR*0.05)
            hat = (np.random.rand(nn)*2-1)*np.exp(-np.arange(nn)/SR*60)*0.12*energy
            end=min(len(drums), idx0+nn); drums[idx0:end]+=hat[:end-idx0]

    mix = melody*0.9 + bass*0.9 + drums*0.8
    mix = mix / max(1.0, np.max(np.abs(mix))*1.15)
    stereo = mono_to_stereo(mix, pan=0.0)
    # 살짝 스테레오감을 위해 좌우 미세 딜레이
    delay = int(SR*0.012)
    stereo2 = stereo.copy()
    stereo2[delay:,1] = stereo[:-delay,1]
    return to_wav(path, stereo2)

def build_crowd_ambience(path, minutes=3.0, seed=2):
    rnd = np.random.RandomState(seed)
    n = int(SR*60*minutes)
    # 브라운노이즈 기반 웅성거림
    white = rnd.randn(n).astype(np.float32)
    brown = np.cumsum(white)
    brown -= np.mean(brown)
    brown /= (np.max(np.abs(brown))+1e-6)
    # 대역 통과 느낌을 위한 간단 이동평균 필터 두 개 결합(로우패스 - 하이패스 근사)
    def moving_avg(x,w):
        c = np.cumsum(np.insert(x,0,0))
        return (c[w:]-c[:-w])/w
    lp = moving_avg(brown, 400)
    lp = np.pad(lp, (0, n-len(lp)))
    bandish = brown - lp*0.6
    t = np.arange(n)/SR
    swell = 0.55 + 0.25*np.sin(2*np.pi*t/23.0) + 0.1*np.sin(2*np.pi*t/7.3)
    sig = bandish*swell*0.35
    # 가끔 환호성 스웰
    cheer_times = np.arange(15, 60*minutes-10, 27)
    for ct in cheer_times:
        idx0 = int(ct*SR); ln=int(SR*4.5)
        if idx0+ln>n: continue
        tt = np.arange(ln)/SR
        env = np.sin(np.pi*tt/tt[-1])**1.5
        cheer = (rnd.randn(ln)*0.5) * env * 0.5
        sig[idx0:idx0+ln] += cheer
    sig = sig/ (np.max(np.abs(sig))*1.2+1e-6)
    stereo = mono_to_stereo(sig)
    delay = int(SR*0.02)
    stereo2 = stereo.copy(); stereo2[delay:,1]=stereo[:-delay,1]
    return to_wav(path, stereo2)

def sfx_whistle(path):
    dur=0.55; n=int(SR*dur); t=np.arange(n)/SR
    f = 2200 + 300*np.sin(2*np.pi*3*t)
    ph = np.cumsum(2*np.pi*f/SR)
    w = np.sin(ph)*adsr(n,0.01,0.05,0.85,0.25)*0.35
    return to_wav(path, mono_to_stereo(w))

def sfx_buzzer(path):
    dur=0.9; n=int(SR*dur); t=np.arange(n)/SR
    w = saw(196,t)*0.5 + saw(196.5,t)*0.5
    w *= adsr(n,0.01,0.05,0.9,0.3)*0.4
    return to_wav(path, mono_to_stereo(w))

def sfx_cheer(path, seed=3):
    rnd=np.random.RandomState(seed); dur=2.2; n=int(SR*dur)
    t=np.arange(n)/SR
    noise=rnd.randn(n)
    env = np.sin(np.pi*np.clip(t/dur,0,1))**1.2
    w = noise*env*0.4
    return to_wav(path, mono_to_stereo(w))

def sfx_groan(path, seed=4):
    rnd=np.random.RandomState(seed); dur=1.0; n=int(SR*dur); t=np.arange(n)/SR
    base = sine(140,t)*0.3*np.exp(-t*1.2)
    noise = rnd.randn(n)*0.05*np.exp(-t*2)
    w=(base+noise)*adsr(n,0.02,0.1,0.6,0.3)
    return to_wav(path, mono_to_stereo(w))

def sfx_bounce(path):
    dur=0.25; n=int(SR*dur); t=np.arange(n)/SR
    w = sine(180,t)*np.exp(-t*22)*0.5
    return to_wav(path, mono_to_stereo(w))

def sfx_dunk(path):
    dur=0.5; n=int(SR*dur); t=np.arange(n)/SR
    thump = sine(70,t)*np.exp(-t*10)*0.6
    crack = (np.random.RandomState(5).randn(n))*np.exp(-t*30)*0.25
    w = thump+crack
    return to_wav(path, mono_to_stereo(w))

def sfx_stinger(path, base=440, seed=6):
    n_notes=4; dur_each=0.09
    parts=[]
    for i in range(n_notes):
        f = base*(2**((i*3)/12))
        parts.append(note(f, dur_each, square, vol=0.25,a=0.003,d=0.02,s=0.6,r=0.04))
    w = np.concatenate(parts)
    return to_wav(path, mono_to_stereo(w))

def sfx_click(path):
    dur=0.05; n=int(SR*dur); t=np.arange(n)/SR
    w = sine(1200,t)*np.exp(-t*80)*0.3
    return to_wav(path, mono_to_stereo(w))

TEAM_ROOTS = {
    'jets':      293.66,
    'titans':    220.00,
    'snipers':   329.63,
    'unity':     261.63,
    'tricksters':349.23,
    'guardians': 246.94,
}

def build_image_assets(outdir, quick=False):
    from PIL import Image
    total = 0
    W,H = (480,270) if quick else (2560,1440)
    rnd = np.random.RandomState(42)

    def noisy_gradient(w,h,c1,c2,grain=14, vertical=True):
        t = np.linspace(0,1,h if vertical else w)
        grad = np.array(c1)[None,:] + (np.array(c2)-np.array(c1))[None,:]*t[:,None]
        if vertical:
            img = np.tile(grad[:,None,:], (1,w,1))
        else:
            img = np.tile(grad[None,:,:], (h,1,1))
        noise = rnd.randint(-grain,grain+1,size=(h,w,3))
        img = np.clip(img+noise,0,255).astype('uint8')
        return img

    def wood_texture(w,h):
        x = np.linspace(0,40,w)[None,:]
        y = np.arange(h)[:,None]
        stripes = 0.5+0.5*np.sin(x*2.3 + np.sin(y*0.05)*3 + rnd.rand()*10)
        base = np.array([170,120,70])
        top = np.array([210,160,100])
        img = base[None,None,:] + (top-base)[None,None,:]*stripes[:,:,None]
        grain = rnd.randint(-10,10,size=(h,w,1))
        img = np.clip(img+grain,0,255).astype('uint8')
        return img

    print("=== 이미지 에셋 (고해상도 절차적 텍스처) ===")
    bg = noisy_gradient(W,H,(7,10,26),(16,24,52),grain=10)
    Image.fromarray(bg).save(f"{outdir}/bg_menu.png"); total+=os.path.getsize(f"{outdir}/bg_menu.png")

    court = wood_texture(W,H)
    Image.fromarray(court).save(f"{outdir}/bg_court.png"); total+=os.path.getsize(f"{outdir}/bg_court.png")

    splash = noisy_gradient(W,H,(5,7,20),(20,60,90),grain=16)
    Image.fromarray(splash).save(f"{outdir}/splash.png"); total+=os.path.getsize(f"{outdir}/splash.png")

    for i in range(1 if quick else 3):
        variant = noisy_gradient(W,H,(10+i*20,8,30),(40,10+i*15,80),grain=20)
        Image.fromarray(variant).save(f"{outdir}/bg_variant_{i+1}.png")
        total += os.path.getsize(f"{outdir}/bg_variant_{i+1}.png")

    for p,sz in [("icon-1024.png", 1024 if not quick else 128)]:
        cx,cy = sz//2, sz//2
        yy,xx = np.mgrid[0:sz,0:sz]
        dist = np.sqrt((xx-cx)**2+(yy-cy)**2)
        icon = np.zeros((sz,sz,3),dtype='uint8')
        icon[...,0] = np.clip(255-dist*0.35,20,255)
        icon[...,1] = np.clip(140-dist*0.15,10,200)
        icon[...,2] = np.clip(60+dist*0.05,10,255)
        ring = (np.abs(dist-sz*0.32) < sz*0.02)
        icon[ring] = [255,140,30]
        Image.fromarray(icon).save(p)
        total += os.path.getsize(p)

    print(f"  이미지 합계: {total/1e6:.2f} MB")
    return total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true', help='짧은 길이로 빠르게 테스트')
    ap.add_argument('--outdir', default='www/assets/audio')
    ap.add_argument('--imgdir', default='www/assets/img')
    args = ap.parse_args()

    music_bars = 4 if args.quick else 224
    ambience_minutes = 0.15 if args.quick else 18.0

    total = 0
    print("=== 배경음악 ===")
    total += build_chiptune_track(f"{args.outdir}/music_menu.wav", root=261.63, bpm=118, bars=music_bars, seed=10, energy=0.8)
    total += build_chiptune_track(f"{args.outdir}/music_game_a.wav", root=277.18, bpm=138, bars=music_bars, seed=11, energy=1.0)
    total += build_chiptune_track(f"{args.outdir}/music_game_b.wav", root=246.94, bpm=150, bars=music_bars, seed=12, energy=1.1)
    total += build_chiptune_track(f"{args.outdir}/music_result.wav", root=293.66, bpm=104, bars=max(2,music_bars//2), seed=13, energy=0.7)

    print("=== 팀별 테마 징글 (6팀) ===")
    for tid, root in TEAM_ROOTS.items():
        total += build_chiptune_track(f"{args.outdir}/team_{tid}.wav", root=root, bpm=140, bars=max(2,music_bars//4), seed=hash(tid)%1000, energy=1.0)

    print("=== 관중 앰비언스 (2종) ===")
    total += build_crowd_ambience(f"{args.outdir}/crowd_ambience_calm.wav", minutes=ambience_minutes, seed=2)
    total += build_crowd_ambience(f"{args.outdir}/crowd_ambience_hype.wav", minutes=ambience_minutes, seed=7)

    print("=== 효과음 ===")
    total += sfx_whistle(f"{args.outdir}/sfx_whistle.wav")
    total += sfx_buzzer(f"{args.outdir}/sfx_buzzer.wav")
    total += sfx_cheer(f"{args.outdir}/sfx_cheer.wav")
    total += sfx_groan(f"{args.outdir}/sfx_groan.wav")
    total += sfx_bounce(f"{args.outdir}/sfx_bounce.wav")
    total += sfx_dunk(f"{args.outdir}/sfx_dunk_impact.wav")
    total += sfx_click(f"{args.outdir}/sfx_click.wav")
    for i,b in enumerate([440,554,659]):
        total += sfx_stinger(f"{args.outdir}/sfx_combo_{i+1}.wav", base=b, seed=20+i)

    os.makedirs(args.imgdir, exist_ok=True)
    total += build_image_assets(args.imgdir, quick=args.quick)

    print(f"\nTOTAL ASSET SIZE: {total/1e6:.2f} MB")

if __name__=='__main__':
    main()
