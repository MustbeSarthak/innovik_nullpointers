import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import PageHead from '../components/PageHead';
import UiButton from '../components/UiButton';
import { AiCareAPI } from '../lib/api';
import { IcChat, IcCamera, IcSpark, IcWarn } from '../components/Icons';

/* ---------------- camera scan analysis (client-side heuristics) ---------------- */

function samplePixels(img) {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0, size, size);
  const { data } = ctx.getImageData(0, 0, size, size);
  const step = 4;
  const pixels = [];
  for (let i = 0; i < data.length; i += step * 4) {
    pixels.push({ r: data[i], g: data[i + 1], b: data[i + 2] });
  }
  return pixels;
}

function analyze(img) {
  const px = samplePixels(img);
  const n = px.length;
  let sr = 0, sg = 0, sb = 0;
  for (const p of px) {
    sr += p.r;
    sg += p.g;
    sb += p.b;
  }
  const avg = { r: sr / n, g: sg / n, b: sb / n };

  let rv = 0, gv = 0, bv = 0;
  for (const p of px) {
    rv += (p.r - avg.r) ** 2;
    gv += (p.g - avg.g) ** 2;
    bv += (p.b - avg.b) ** 2;
  }
  const variance = Math.sqrt((rv + gv + bv) / (n * 3));
  const brightness = (avg.r + avg.g + avg.b) / 3;
  const redness = avg.r - (avg.g + avg.b) / 2;
  const warm = px.filter((p) => p.r > p.g + 38 && p.r > p.b + 38).length / n;

  const findings = [];

  if (redness > 26 && warm > 0.25) {
    findings.push({
      title: 'Possible redness / inflammation',
      confidence: Math.min(94, Math.round(58 + warm * 40 + redness)),
      advice:
        'The area looks warmer and redder than surrounding skin. This can happen with irritation, allergies, heat or minor inflammation.\n\nGently clean with cool water, avoid scratching, and watch for spread, pain or fever. An antihistamine may help if it feels allergic.',
    });
  } else if (redness > 12) {
    findings.push({
      title: 'Mild skin redness',
      confidence: Math.round(45 + redness),
      advice:
        'A slight reddish tone was detected. This often settles quickly with rest, cooling and moisturising. Keep the area clean and avoid harsh soaps.',
    });
  }

  if (brightness < 92) {
    findings.push({
      title: 'Dull / darker patch possible',
      confidence: Math.min(90, Math.round(40 + (110 - brightness))),
      advice:
        'The sampled tone is on the darker side, which may be a normal skin shade, a dry patch, or pigmentation building up.\n\nMoisturise daily, use sunscreen, and don’t scrub the area.',
    });
  }

  if (variance > 34 && findings.length < 3) {
    findings.push({
      title: 'Uneven tone / pigmentation',
      confidence: Math.min(88, Math.round(38 + variance)),
      advice:
        'Colour differences were detected across the area, which is often just shadow or light changes — but can be early pigmentation.\n\nWear sunscreen daily and keep the area moisturised.',
    });
  }

  if (findings.length === 0) {
    findings.push({
      title: 'Looks generally even & healthy',
      confidence: 76,
      advice:
        'No strong redness, dryness or pigmentation markers were picked up from this photo.\n\nIf you still feel a symptom (itching, pain, texture change), a doctor’s in-person check is the best next step.',
    });
  }

  return findings;
}

/* ------------------------------------------------------------------ */

function Scanner() {
  const videoRef = useRef(null);
  const imgRef = useRef(null);
  const streamRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [captured, setCaptured] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setStream(null);
  };

  const startCamera = async () => {
    setError('');
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = s;
      setStream(s);
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          videoRef.current.play().catch(() => {});
        }
      }, 50);
    } catch {
      setError('Camera not available right now. Try uploading a photo instead.');
    }
  };

  const capture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    stopCamera();
    setCaptured(canvas.toDataURL('image/jpeg', 0.92));
  };

  const useImageFile = (file) => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      stopCamera();
      setCaptured(url);
    };
    img.src = url;
  };

  const runScan = () => {
    const img = imgRef.current;
    if (!img) return;
    setScanning(true);
    setResult(null);
    setTimeout(() => {
      setResult(analyze(img));
      setScanning(false);
    }, 2600);
  };

  const reset = () => {
    setCaptured(null);
    setResult(null);
    setScanning(false);
    startCamera();
  };

  return (
    <div className="fade-in">
      {captured === null && (
        <>
          <div className="scan-stage">
            {stream ? (
              <>
                <video ref={videoRef} playsInline muted />
                <span className="scan-corner tl" />
                <span className="scan-corner tr" />
                <span className="scan-corner bl" />
                <span className="scan-corner br" />
              </>
            ) : (
              <div className="empty" style={{ color: '#cbd5e1' }}>
                <div className="logo-box" style={{ width: 66, height: 66, borderRadius: 20, margin: '0 auto 12px', background: 'rgba(255,255,255,0.08)', boxShadow: 'none' }}>
                  <IcCamera size={30} />
                </div>
                <h3 style={{ color: '#e2e8f0' }}>Ready to scan your skin</h3>
                <p>Point the camera at the affected area (rash, redness, spot).</p>
              </div>
            )}
          </div>

          <div className="btn-row">
            <UiButton className="btn-primary" onClick={capture} disabled={!stream}>
              <IcCamera size={17} /> Take Photo
            </UiButton>
            <UiButton className="btn-ghost" onClick={() => fileRef.current?.click()}>
              Upload Image
            </UiButton>
          </div>
          <UiButton className="btn-outline btn-sm" style={{ marginTop: 10 }} onClick={startCamera}>
            {stream ? 'Restart camera' : 'Open camera'}
          </UiButton>
          <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => useImageFile(e.target.files?.[0])} />
          {error && (
            <div className="disclaimer" style={{ borderColor: 'var(--danger-soft)' }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <IcWarn size={16} style={{ color: 'var(--danger)', flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            </div>
          )}
        </>
      )}

      {captured && (
        <>
          <div className="scan-stage">
            <img ref={imgRef} src={captured} alt="Capture" />
            {scanning && <span className="scan-line" />}
            {scanning && (
              <>
                <span className="scan-corner tl" />
                <span className="scan-corner tr" />
                <span className="scan-corner bl" />
                <span className="scan-corner br" />
              </>
            )}
          </div>

          {!scanning && !result && (
            <div className="btn-row">
              <UiButton className="btn-primary" onClick={runScan}>
                <IcSpark size={17} /> Analyze Photo
              </UiButton>
              <UiButton className="btn-ghost" onClick={reset}>
                Retake
              </UiButton>
            </div>
          )}

          {scanning && (
            <div className="card empty" style={{ padding: 26 }}>
              <p style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, fontWeight: 700 }}>
                <span className="spinner" /> AI is scanning your photo…
              </p>
              <p className="hint" style={{ marginTop: 8 }}>Looking at colour, redness and skin tone patterns</p>
            </div>
          )}

          {result && (
            <div className="fade-in">
              <div className="split" style={{ margin: '16px 0 10px' }}>
                <h3 style={{ fontSize: 16, fontWeight: 800 }}>Scan Results</h3>
                <span className="badge badge-low">
                  <span className="pulse-dot" /> Complete
                </span>
              </div>

              {result.map((f, i) => (
                <div className="card find-card" key={i} style={{ marginTop: 10 }}>
                  <div className="split">
                    <p style={{ fontWeight: 800, fontSize: 14.5 }}>{f.title}</p>
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--primary)' }}>{f.confidence}%</span>
                  </div>
                  <div className="conf-bar">
                    <span style={{ width: f.confidence + '%' }} />
                  </div>
                  <p className="sub" style={{ fontSize: 13, marginTop: 10, whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{f.advice}</p>
                </div>
              ))}

              <UiButton className="btn-ghost" style={{ marginTop: 16 }} onClick={reset}>
                <IcCamera size={17} /> Scan Another Photo
              </UiButton>
            </div>
          )}
        </>
      )}

      <div className="disclaimer" style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <IcWarn size={16} style={{ color: 'var(--warn)', flexShrink: 0 }} />
        <span>
          This scan uses simple on-device colour analysis as an educational guide. It cannot
          diagnose any medical condition. For persistent, painful or spreading symptoms always
          consult a doctor or dermatologist.
        </span>
      </div>
    </div>
  );
}

function ChatPanel() {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text:
        "Hi! I'm your health assistant 👋\n\nTell me what's bothering you — e.g. \"I have a rash on my arm\", \"mild fever\", \"sore throat\" — and I'll share some simple guidance and when to see a doctor.",
    },
  ]);
  const [text, setText] = useState('');
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, typing]);

  const send = async (raw) => {
    const msg = (raw ?? text).trim();
    if (!msg || typing) return;
    setText('');
    setMessages((m) => [...m, { role: 'user', text: msg }]);
    setTyping(true);

    try {
      const response = await AiCareAPI.chat(msg);
      const sourceNote = response.context_used
        ? `\n\nContext used from: ${response.sources.map((source) => source.filename || 'uploaded report').join(', ')}`
        : '';
      setMessages((m) => [...m, {
        role: 'bot',
        text: `${response.answer}${sourceNote}\n\n${response.disclaimer}`,
        grounded: response.context_used,
      }]);
    } catch (error) {
      setMessages((m) => [...m, {
        role: 'bot',
        text: `AI Care is temporarily unavailable. Please try again shortly.\n\n${error.message || ''}`,
      }]);
    } finally {
      setTyping(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="chat-box">
        <div className="chat-scroll" ref={scrollRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              {m.role === 'bot' && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontWeight: 800, fontSize: 12, color: 'var(--primary)', marginBottom: 4 }}>
                  <IcSpark size={13} /> HEALTH AI{m.grounded ? ' · RECORD CONTEXT USED' : ''}
                </span>
              )}
              {m.role === 'bot' ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
              ) : (
                m.text
              )}
            </div>
          ))}
          {typing && (
            <div className="msg bot">
              <span className="typing">
                <span />
                <span />
                <span />
              </span>
            </div>
          )}
        </div>
        <form
          className="chat-input"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <input
            className="input"
            placeholder="Describe your symptom…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <UiButton type="submit" className="btn-primary" style={{ width: 'auto', padding: '12px 18px' }}>
            <IcChat size={17} />
          </UiButton>
        </form>
      </div>
    </div>
  );
}

export default function Assistant() {
  const [params] = useSearchParams();
  const [mode, setMode] = useState(params.get('mode') === 'scan' ? 'scan' : 'chat');

  useEffect(() => {
    setMode(params.get('mode') === 'scan' ? 'scan' : 'chat');
  }, [params]);

  return (
    <div className="page">
      <PageHead title="AI Health Assistant" backTo="/" />

      <div className="card ai-hero fade-in">
        <div className="split">
          <div>
            <span className="badge" style={{ background: 'rgba(255,255,255,0.2)', color: '#fff' }}>
              <IcSpark size={13} /> Smart guide
            </span>
            <h2 style={{ fontSize: 21, marginTop: 10 }}>Ask or scan, we've got you covered</h2>
            <p style={{ fontSize: 13.5, marginTop: 6, opacity: 0.92, lineHeight: 1.55 }}>
              Understand everyday symptoms like rashes, fever, cold, cough and more — or scan a
              photo of a skin concern. Same-day, on your device.
            </p>
          </div>
        </div>
      </div>

      <div className="ai-tabs">
        <button className={`ai-tab ${mode === 'chat' ? 'on' : ''}`} onClick={() => setMode('chat')}>
          <IcChat size={17} /> Ask AI
        </button>
        <button className={`ai-tab ${mode === 'scan' ? 'on' : ''}`} onClick={() => setMode('scan')}>
          <IcCamera size={17} /> Scan Photo
        </button>
      </div>

      {mode === 'chat' ? <ChatPanel /> : <Scanner />}
    </div>
  );
}