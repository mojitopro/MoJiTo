import { useEffect, useRef, useState, useCallback } from "react";

interface Channel {
  cluster_id: string;
  name: string;
  streams: number;
  url: string;
  fusion: boolean;
}

const BASE = "/api/mojito";
const CATEGORIES = ["DEPORTES", "CINE", "NOTICIAS", "INFANTIL", "TODOS"];
const LAST_CH_KEY = "mojito_last_ch";
const LAST_CAT_KEY = "mojito_last_cat";
const AUTO_SKIP_DELAY = 4000; // ms before auto-skip on error

function getCategory(name: string): string {
  const n = name.toLowerCase();
  if (/espn|fox sport|tyc|win sport|gol|directv sport|bein|sport|futbol|deportes|movistar dep/.test(n)) return "DEPORTES";
  if (/hbo|cinemax|star|cinema|golden|warner|tnt|fx|axn|studio|paramount|universal|sony|cine|amc|starz/.test(n)) return "CINE";
  if (/cnn|bbc|dw|telesur|noticias|news|info/.test(n)) return "NOTICIAS";
  if (/disney|nick|cartoon|kids|junior|jr|discovery kid|baby/.test(n)) return "INFANTIL";
  return "TODOS";
}

const C = {
  bg:        "#050800",
  panel:     "#060900",
  green:     "#c8ff00",
  greenDim:  "#4a5e00",
  greenFade: "#1a2200",
  amber:     "#ff8c00",
  amberDim:  "#4a2800",
  red:       "#ff2200",
  white:     "#e8f0c0",
  dim:       "#2a3300",
  border:    "#1a2200",
};

function nowStr(): string {
  const d = new Date();
  return (
    String(d.getHours()).padStart(2, "0") + ":" +
    String(d.getMinutes()).padStart(2, "0") + ":" +
    String(d.getSeconds()).padStart(2, "0")
  );
}

function saveLastChannel(catIdx: number, chIdx: number) {
  try {
    localStorage.setItem(LAST_CAT_KEY, String(catIdx));
    localStorage.setItem(LAST_CH_KEY, String(chIdx));
  } catch (_) {}
}

function loadLastChannel(): { catIdx: number; chIdx: number } {
  try {
    const cat = parseInt(localStorage.getItem(LAST_CAT_KEY) || "") || CATEGORIES.length - 1;
    const ch  = parseInt(localStorage.getItem(LAST_CH_KEY)  || "") || 0;
    return { catIdx: cat, chIdx: ch };
  } catch (_) {
    return { catIdx: CATEGORIES.length - 1, chIdx: 0 };
  }
}

export default function MojitoTV() {
  const saved = loadLastChannel();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [playingIdx, setPlayingIdx] = useState(-1);
  const [focusedIdx, setFocusedIdx] = useState(saved.chIdx);
  const [loading, setLoading] = useState(true);
  const [playerState, setPlayerState] = useState<"idle" | "playing" | "error" | "seeking">("idle");
  const [infoVisible, setInfoVisible] = useState(false);
  const [catIdx, setCatIdx] = useState(saved.catIdx);
  const [showList, setShowList] = useState(false); // hidden by default
  const [clock, setClock] = useState(nowStr());
  const [skipCountdown, setSkipCountdown] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const infoTimer = useRef<number | null>(null);
  const skipTimer = useRef<number | null>(null);
  const skipCountdownTimer = useRef<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  // track if we've auto-started
  const autoStarted = useRef(false);

  useEffect(() => {
    const t = setInterval(() => setClock(nowStr()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(BASE + "/tv")
      .then((r) => r.json())
      .then((d) => {
        const chs: Channel[] = d.channels || [];
        setChannels(chs);
        setLoading(false);
      })
      .catch(() => {
        fetch(BASE + "/channels?limit=80")
          .then((r) => r.json())
          .then((d) => { setChannels(d.channels || []); setLoading(false); })
          .catch(() => setLoading(false));
      });
  }, []);

  const activeCat = CATEGORIES[catIdx];
  const filtered = channels.filter((c) =>
    activeCat === "TODOS" ? true : getCategory(c.name) === activeCat
  );

  // Auto-start once channels are ready
  useEffect(() => {
    if (!loading && filtered.length > 0 && !autoStarted.current) {
      autoStarted.current = true;
      const startIdx = Math.min(saved.chIdx, filtered.length - 1);
      setFocusedIdx(startIdx);
      // slight delay so video element is mounted
      setTimeout(() => playChannelDirect(startIdx, filtered), 300);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, filtered.length]);

  const showInfo = useCallback(() => {
    setInfoVisible(true);
    if (infoTimer.current) clearTimeout(infoTimer.current);
    infoTimer.current = window.setTimeout(() => setInfoVisible(false), 5000);
  }, []);

  const scrollTo = useCallback((idx: number) => {
    setTimeout(() => {
      const el = listRef.current?.querySelectorAll("[data-ch]")[idx] as HTMLElement | null;
      el?.scrollIntoView({ block: "nearest" });
    }, 30);
  }, []);

  // Internal play — accepts filtered list directly to avoid stale closure
  function playChannelDirect(idx: number, list: Channel[]) {
    const ch = list[idx];
    if (!ch) return;
    if (skipTimer.current) { clearTimeout(skipTimer.current); skipTimer.current = null; }
    if (skipCountdownTimer.current) { clearInterval(skipCountdownTimer.current); skipCountdownTimer.current = null; }
    setPlayingIdx(idx);
    setFocusedIdx(idx);
    setPlayerState("seeking");
    setSkipCountdown(0);
    saveLastChannel(catIdx, idx);

    if (videoRef.current) {
      videoRef.current.src = ch.url;
      videoRef.current.load();
      videoRef.current.play()
        .then(() => setPlayerState("playing"))
        .catch(() => {
          // Try via API
          fetch(BASE + "/play/" + ch.cluster_id)
            .then((r) => r.json())
            .then((d) => {
              if (d.url && videoRef.current) {
                videoRef.current.src = d.url;
                videoRef.current.load();
                videoRef.current.play()
                  .then(() => setPlayerState("playing"))
                  .catch(() => triggerAutoSkip(idx, list));
              } else triggerAutoSkip(idx, list);
            })
            .catch(() => triggerAutoSkip(idx, list));
        });
    }
    scrollTo(idx);
  }

  // Auto-skip with countdown
  function triggerAutoSkip(failedIdx: number, list: Channel[]) {
    setPlayerState("error");
    let remaining = Math.round(AUTO_SKIP_DELAY / 1000);
    setSkipCountdown(remaining);
    skipCountdownTimer.current = window.setInterval(() => {
      remaining -= 1;
      setSkipCountdown(remaining);
    }, 1000);
    skipTimer.current = window.setTimeout(() => {
      if (skipCountdownTimer.current) clearInterval(skipCountdownTimer.current);
      const next = (failedIdx + 1) % Math.max(list.length, 1);
      playChannelDirect(next, list);
    }, AUTO_SKIP_DELAY);
  }

  const playChannel = useCallback((idx: number) => {
    playChannelDirect(idx, filtered);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtered, catIdx]);

  const movePrev = useCallback(() => {
    setFocusedIdx((i) => {
      const n = (i - 1 + Math.max(filtered.length, 1)) % Math.max(filtered.length, 1);
      scrollTo(n);
      return n;
    });
  }, [filtered.length, scrollTo]);

  const moveNext = useCallback(() => {
    setFocusedIdx((i) => {
      const n = (i + 1) % Math.max(filtered.length, 1);
      scrollTo(n);
      return n;
    });
  }, [filtered.length, scrollTo]);

  const chNext = useCallback(() => {
    playChannel((playingIdx + 1) % Math.max(filtered.length, 1));
  }, [playingIdx, filtered.length, playChannel]);

  const chPrev = useCallback(() => {
    playChannel((playingIdx - 1 + filtered.length) % Math.max(filtered.length, 1));
  }, [playingIdx, filtered.length, playChannel]);

  const catNext = useCallback(() => {
    autoStarted.current = false;
    setCatIdx((i) => (i + 1) % CATEGORIES.length);
    setPlayingIdx(-1); setFocusedIdx(0); setPlayerState("idle");
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
    if (skipTimer.current) clearTimeout(skipTimer.current);
    if (skipCountdownTimer.current) clearInterval(skipCountdownTimer.current);
  }, []);

  const catPrev = useCallback(() => {
    autoStarted.current = false;
    setCatIdx((i) => (i - 1 + CATEGORIES.length) % CATEGORIES.length);
    setPlayingIdx(-1); setFocusedIdx(0); setPlayerState("idle");
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
    if (skipTimer.current) clearTimeout(skipTimer.current);
    if (skipCountdownTimer.current) clearInterval(skipCountdownTimer.current);
  }, []);

  const stopPlayer = useCallback(() => {
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
    if (skipTimer.current) { clearTimeout(skipTimer.current); skipTimer.current = null; }
    if (skipCountdownTimer.current) { clearInterval(skipCountdownTimer.current); skipCountdownTimer.current = null; }
    setPlayerState("idle"); setPlayingIdx(-1); setSkipCountdown(0);
  }, []);

  const playFocused = useCallback(() => playChannel(focusedIdx), [focusedIdx, playChannel]);

  // Handle video error event (separate from play() rejection)
  const handleVideoError = useCallback(() => {
    if (playerState !== "error") {
      triggerAutoSkip(playingIdx, filtered);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerState, playingIdx, filtered]);

  // Show info banner when playing and info is hidden (tap anywhere on video)
  const handleVideoClick = useCallback(() => {
    if (playerState === "playing") showInfo();
  }, [playerState, showInfo]);

  // Keyboard — real Philco keycodes
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      switch (e.keyCode) {
        case 38: case 37: e.preventDefault(); movePrev(); break;
        case 40: case 39: e.preventDefault(); moveNext(); break;
        case 13: e.preventDefault(); playFocused(); break;
        case 33: e.preventDefault(); catPrev(); break;
        case 34: e.preventDefault(); catNext(); break;
        case 27: e.preventDefault(); stopPlayer(); break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [movePrev, moveNext, playFocused, catPrev, catNext, stopPlayer]);

  const playingCh = playingIdx >= 0 ? filtered[playingIdx] : null;
  const focusedCh = filtered[focusedIdx] || null;
  const isLive = playerState === "playing";

  return (
    <div className="crt-flicker" style={{
      background: C.bg,
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      fontFamily: "'Courier New', Courier, monospace",
      color: C.green,
      position: "relative",
    }}>
      {/* Scanline sweep */}
      <div style={{
        position: "fixed", left: 0, right: 0, height: "4px",
        background: "linear-gradient(to bottom, transparent, rgba(200,255,0,0.04), transparent)",
        zIndex: 9998, pointerEvents: "none",
        animation: "hscan 6s linear infinite",
        WebkitAnimation: "hscan 6s linear infinite",
      }} />

      {/* TOP BAR */}
      <div style={{
        background: C.panel,
        borderBottom: "1px solid " + C.greenDim,
        display: "flex",
        alignItems: "center",
        padding: "0 14px",
        height: "46px",
        flexShrink: 0,
        justifyContent: "space-between",
      }}>
        {/* Station ID */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <div style={{
            border: "1px solid " + C.green,
            padding: "2px 10px",
            fontSize: "15px",
            fontWeight: "bold",
            letterSpacing: "4px",
            color: C.green,
            textShadow: "0 0 6px " + C.green + ", 0 0 14px " + C.green,
            marginRight: "10px",
          }}>LOCAL 58</div>
          <div style={{ fontSize: "9px", color: C.greenDim, letterSpacing: "2px", lineHeight: "1.5" }}>
            MOJITO TV<br />TRANSMISION EN VIVO
          </div>
        </div>

        {/* Center — category or channel info */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <CrtBtn onClick={catPrev} title="PageUp">&#9664;</CrtBtn>
          <div style={{
            border: "1px solid " + C.greenDim,
            padding: "3px 14px",
            fontSize: "12px",
            fontWeight: "bold",
            color: C.green,
            letterSpacing: "3px",
            margin: "0 6px",
            minWidth: "110px",
            textAlign: "center",
            textShadow: "0 0 4px " + C.green,
          }}>{activeCat}</div>
          <CrtBtn onClick={catNext} title="PageDown">&#9654;</CrtBtn>
        </div>

        {/* Right — live indicator + clock + list toggle */}
        <div style={{ display: "flex", alignItems: "center" }}>
          {isLive && (
            <div style={{ display: "flex", alignItems: "center", marginRight: "14px" }}>
              <div style={{
                width: "7px", height: "7px", borderRadius: "50%",
                background: C.red, boxShadow: "0 0 5px " + C.red,
                animation: "pulse-red 1s infinite", WebkitAnimation: "pulse-red 1s infinite",
                marginRight: "6px",
              }} />
              <span style={{ fontSize: "10px", color: C.red, letterSpacing: "2px" }}>ON AIR</span>
            </div>
          )}
          {loading && (
            <span style={{ fontSize: "10px", color: C.greenDim, marginRight: "14px", letterSpacing: "2px", animation: "blink 1s step-end infinite", WebkitAnimation: "blink 1s step-end infinite" }}>
              BUSCANDO...
            </span>
          )}
          <div style={{
            fontSize: "14px", color: C.white,
            letterSpacing: "3px", fontWeight: "bold",
            textShadow: "0 0 4px " + C.white,
            marginRight: "10px",
          }}>{clock}</div>
          <CrtBtn onClick={() => setShowList((v) => !v)} title="Lista de canales">
            {showList ? "OCULTAR" : "CANALES"}
          </CrtBtn>
        </div>
      </div>

      {/* MAIN */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* CHANNEL LIST — slides in */}
        {showList && (
          <div style={{
            width: "280px",
            flexShrink: 0,
            background: C.panel,
            borderRight: "1px solid " + C.border,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}>
            <div style={{
              padding: "6px 12px",
              borderBottom: "1px solid " + C.border,
              fontSize: "9px", color: C.greenDim, letterSpacing: "2px",
              display: "flex", justifyContent: "space-between",
            }}>
              <span>GUIA DE CANALES</span>
              <span>{filtered.length} SENALES</span>
            </div>

            {/* Focused channel label */}
            {focusedCh && playerState !== "playing" && playerState !== "seeking" && (
              <div style={{
                padding: "7px 12px",
                borderBottom: "1px solid " + C.border,
                background: C.greenFade,
              }}>
                <div style={{ fontSize: "8px", color: C.greenDim, letterSpacing: "3px", marginBottom: "3px" }}>SELECCIONADO</div>
                <div style={{
                  fontSize: "12px", fontWeight: "bold", color: C.green,
                  textShadow: "0 0 4px " + C.green,
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>{focusedCh.name.toUpperCase()}</div>
                <div style={{
                  fontSize: "8px", color: C.greenDim, marginTop: "2px", letterSpacing: "1px",
                  animation: "blink 1.2s step-end infinite", WebkitAnimation: "blink 1.2s step-end infinite",
                }}>ENTER = SINTONIZAR_</div>
              </div>
            )}

            {/* Channel list */}
            <div ref={listRef} style={{ flex: 1, overflowY: "auto", overflowX: "hidden" }}>
              {loading && (
                <div style={{ textAlign: "center", padding: "40px 12px", color: C.greenDim, fontSize: "10px", letterSpacing: "2px" }}>
                  BUSCANDO SENAL...
                </div>
              )}
              {filtered.map((ch, idx) => (
                <GuideRow
                  key={ch.cluster_id}
                  number={idx + 1}
                  channel={ch}
                  playing={idx === playingIdx}
                  focused={idx === focusedIdx}
                  onClick={() => playChannel(idx)}
                />
              ))}
            </div>

            {/* Controls */}
            <div style={{ borderTop: "1px solid " + C.border, padding: "8px", background: C.panel }}>
              <div style={{ display: "flex", justifyContent: "center", marginBottom: "6px" }}>
                <CrtBtnWide onClick={playFocused} accent title="ENTER">&#9654; SINTONIZAR</CrtBtnWide>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <CrtBtn onClick={movePrev} title="↑">&#9650; SUBIR</CrtBtn>
                <CrtBtn onClick={moveNext} title="↓">&#9660; BAJAR</CrtBtn>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <CrtBtn onClick={chPrev} title="CH-">CH-</CrtBtn>
                <CrtBtn onClick={chNext} title="CH+">CH+</CrtBtn>
              </div>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <CrtBtnWide onClick={stopPlayer} danger title="ESC">&#9632; CORTAR SENAL</CrtBtnWide>
              </div>
            </div>
          </div>
        )}

        {/* VIDEO PLAYER — always full area */}
        <div
          onClick={handleVideoClick}
          style={{ flex: 1, background: "#000", position: "relative", overflow: "hidden", cursor: isLive ? "none" : "default" }}
        >
          <video
            ref={videoRef}
            playsInline
            autoPlay
            onError={handleVideoError}
            onPlaying={() => setPlayerState("playing")}
            style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
          />

          {/* SEEKING / TUNING */}
          {playerState === "seeking" && (
            <div style={{
              position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
              background: "rgba(5,8,0,0.7)",
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
            }}>
              <div style={{
                fontSize: "12px", letterSpacing: "6px", color: C.greenDim, marginBottom: "12px",
                animation: "blink 0.8s step-end infinite", WebkitAnimation: "blink 0.8s step-end infinite",
              }}>SINTONIZANDO...</div>
              {playingCh && (
                <div style={{
                  fontSize: "20px", fontWeight: "bold", color: C.green,
                  textShadow: "0 0 8px " + C.green, letterSpacing: "3px",
                }}>{playingCh.name.toUpperCase()}</div>
              )}
            </div>
          )}

          {/* IDLE — only shown if no channel has been attempted yet */}
          {playerState === "idle" && (
            <div style={{
              position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
              background: C.bg,
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
            }}>
              <ColorBars />
              <div style={{ marginTop: "28px", textAlign: "center" }}>
                <div style={{ fontSize: "10px", letterSpacing: "6px", color: C.greenDim, marginBottom: "6px" }}>WCLV</div>
                <div style={{
                  fontSize: "34px", fontWeight: "bold", letterSpacing: "8px",
                  color: C.green, textShadow: "0 0 10px " + C.green + ", 0 0 28px " + C.green,
                  animation: "glitch 5s infinite", WebkitAnimation: "glitch 5s infinite",
                }}>LOCAL 58</div>
                <div style={{ fontSize: "9px", letterSpacing: "4px", color: C.greenDim, marginTop: "5px" }}>
                  MOJITO TV · TRANSMISION CONTINUA
                </div>
              </div>
              {loading ? (
                <div style={{
                  marginTop: "30px", fontSize: "10px", color: C.greenDim, letterSpacing: "4px",
                  animation: "blink 1s step-end infinite", WebkitAnimation: "blink 1s step-end infinite",
                }}>CARGANDO SENALES...</div>
              ) : (
                <div style={{ marginTop: "30px", fontSize: "9px", color: C.dim, letterSpacing: "4px", animation: "blink 2s step-end infinite", WebkitAnimation: "blink 2s step-end infinite" }}>
                  SELECCIONE UN CANAL
                </div>
              )}
            </div>
          )}

          {/* ERROR + AUTO-SKIP COUNTDOWN */}
          {playerState === "error" && (
            <div style={{
              position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
              background: C.bg,
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
            }}>
              <StaticNoise />
              <div style={{
                position: "relative", zIndex: 2, textAlign: "center",
                padding: "18px 24px",
                border: "1px solid " + C.amberDim,
                background: "rgba(5,8,0,0.94)",
              }}>
                <div style={{ fontSize: "10px", color: C.amber, letterSpacing: "4px", marginBottom: "8px" }}>
                  DIFICULTADES TECNICAS
                </div>
                <div style={{
                  fontSize: "24px", fontWeight: "bold", color: C.amber,
                  textShadow: "0 0 6px " + C.amber, letterSpacing: "3px", marginBottom: "4px",
                }}>SENAL PERDIDA</div>
                {playingCh && (
                  <div style={{ fontSize: "10px", color: C.amberDim, letterSpacing: "2px", marginBottom: "14px" }}>
                    {playingCh.name.toUpperCase()}
                  </div>
                )}
                <div style={{
                  fontSize: "12px", color: C.amber, letterSpacing: "2px", marginBottom: "16px",
                  animation: "blink 0.5s step-end infinite", WebkitAnimation: "blink 0.5s step-end infinite",
                }}>
                  BUSCANDO SIGUIENTE SENAL EN {skipCountdown}s...
                </div>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <CrtBtnWide onClick={chNext} title="Saltar ya">&#9654; SALTAR AHORA</CrtBtnWide>
                  <div style={{ height: "6px" }} />
                  <CrtBtnWide onClick={stopPlayer} danger title="ESC">&#9632; CORTAR</CrtBtnWide>
                </div>
              </div>
            </div>
          )}

          {/* NOW PLAYING banner — appears on channel change, click to show again */}
          {infoVisible && playingCh && (
            <div style={{
              position: "absolute", bottom: 0, left: 0, right: 0,
              background: "rgba(5,8,0,0.94)",
              borderTop: "1px solid " + C.greenDim,
              padding: "10px 16px",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", marginBottom: "3px" }}>
                  <div style={{
                    width: "6px", height: "6px", borderRadius: "50%",
                    background: C.red, boxShadow: "0 0 4px " + C.red,
                    animation: "pulse-red 1s infinite", WebkitAnimation: "pulse-red 1s infinite",
                    marginRight: "6px",
                  }} />
                  <span style={{ fontSize: "8px", color: C.red, letterSpacing: "4px" }}>EN VIVO</span>
                </div>
                <div style={{
                  fontSize: "18px", fontWeight: "bold", color: C.green,
                  textShadow: "0 0 5px " + C.green, letterSpacing: "2px",
                }}>{playingCh.name.toUpperCase()}</div>
                <div style={{ fontSize: "9px", color: C.greenDim, marginTop: "2px", letterSpacing: "2px" }}>
                  {getCategory(playingCh.name)} · FUSION · {playingCh.streams} STREAMS
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{
                  fontSize: "28px", fontWeight: "bold", color: C.green,
                  textShadow: "0 0 8px " + C.green, letterSpacing: "2px",
                }}>CH {String(playingIdx + 1).padStart(2, "0")}</div>
                <div style={{ fontSize: "9px", color: C.dim, letterSpacing: "1px" }}>/ {filtered.length}</div>
              </div>
            </div>
          )}

          {/* Floating remote — only when playing, no info banner */}
          {isLive && !infoVisible && (
            <FloatingRemote
              onPrev={chPrev}
              onNext={chNext}
              onStop={stopPlayer}
              onInfo={showInfo}
              onToggleList={() => setShowList((v) => !v)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Color bars ── */
function ColorBars() {
  const bars = ["#c8c8c8", "#c8c800", "#00c8c8", "#00c800", "#c800c8", "#c80000", "#0000c8"];
  return (
    <div style={{ display: "flex", width: "300px", height: "50px", border: "1px solid " + C.border }}>
      {bars.map((color, i) => <div key={i} style={{ flex: 1, background: color }} />)}
    </div>
  );
}

/* ── Static noise ── */
function StaticNoise() {
  return (
    <div style={{
      position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
      backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.15'/%3E%3C/svg%3E\")",
      opacity: 0.18,
      animation: "static-noise 0.1s steps(1) infinite",
      WebkitAnimation: "static-noise 0.1s steps(1) infinite",
    }} />
  );
}

/* ── Guide row ── */
function GuideRow({ number, channel, playing, focused, onClick }: {
  number: number; channel: Channel; playing: boolean; focused: boolean; onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      data-ch="true"
      style={{
        padding: "9px 12px",
        cursor: "pointer",
        borderBottom: "1px solid " + C.border,
        background: playing ? C.greenFade : focused ? "rgba(200,255,0,0.03)" : "transparent",
        borderLeft: playing ? "3px solid " + C.green : focused ? "3px solid " + C.greenDim : "3px solid transparent",
        display: "flex",
        alignItems: "center",
        minHeight: "50px",
      }}
    >
      <div style={{
        fontSize: "11px", fontWeight: "bold",
        color: playing ? C.green : focused ? C.greenDim : C.dim,
        width: "24px", flexShrink: 0, textAlign: "right", marginRight: "10px", letterSpacing: "1px",
      }}>{String(number).padStart(2, "0")}</div>
      <div style={{ flex: 1, overflow: "hidden" }}>
        <div style={{
          fontSize: "12px",
          fontWeight: playing || focused ? "bold" : "normal",
          color: playing ? C.green : focused ? C.white : "#6a7a40",
          textShadow: playing ? "0 0 4px " + C.green : "none",
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", letterSpacing: "1px",
        }}>{channel.name.toUpperCase()}</div>
        <div style={{ fontSize: "8px", color: playing ? C.greenDim : C.dim, marginTop: "2px", letterSpacing: "2px" }}>
          {getCategory(channel.name)} · FUSION
        </div>
      </div>
      {playing && (
        <div style={{
          fontSize: "8px", color: C.red, letterSpacing: "1px", marginLeft: "6px",
          animation: "pulse-red 1s infinite", WebkitAnimation: "pulse-red 1s infinite",
        }}>●</div>
      )}
      {!playing && focused && (
        <div style={{ color: C.greenDim, fontSize: "11px", marginLeft: "6px" }}>&#9654;</div>
      )}
    </div>
  );
}

/* ── Floating remote ── */
function FloatingRemote({ onPrev, onNext, onStop, onInfo, onToggleList }: {
  onPrev: () => void; onNext: () => void; onStop: () => void; onInfo: () => void; onToggleList: () => void;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div style={{ position: "absolute", top: "8px", right: "8px", zIndex: 10 }}>
      <button
        onClick={() => setVisible((v) => !v)}
        style={{
          background: "rgba(5,8,0,0.85)",
          border: "1px solid " + C.greenDim,
          color: C.greenDim,
          width: "38px", height: "38px",
          fontSize: "11px", letterSpacing: "1px",
          cursor: "pointer", fontFamily: "'Courier New', monospace",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
        title="Control"
      >RC</button>
      {visible && (
        <div style={{
          marginTop: "4px", background: "rgba(5,8,0,0.96)",
          border: "1px solid " + C.border, padding: "8px",
          display: "flex", flexDirection: "column", alignItems: "center",
        }}>
          <RemBtn onClick={onPrev} title="CH-">&#9650;</RemBtn>
          <div style={{ height: "4px" }} />
          <RemBtn onClick={onInfo} title="Info">INF</RemBtn>
          <div style={{ height: "4px" }} />
          <RemBtn onClick={onNext} title="CH+">&#9660;</RemBtn>
          <div style={{ height: "4px" }} />
          <RemBtn onClick={onToggleList} title="Lista">LST</RemBtn>
          <div style={{ height: "4px" }} />
          <RemBtn onClick={onStop} title="STOP" danger>&#9632;</RemBtn>
        </div>
      )}
    </div>
  );
}

function RemBtn({ onClick, title, children, danger }: {
  onClick: () => void; title: string; children: React.ReactNode; danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        background: "transparent",
        border: "1px solid " + (danger ? C.red : C.greenDim),
        color: danger ? C.red : C.greenDim,
        width: "48px", height: "48px",
        fontSize: "15px", cursor: "pointer",
        fontFamily: "'Courier New', monospace",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontWeight: "bold", letterSpacing: "1px",
      }}
    >{children}</button>
  );
}

function CrtBtnWide({ onClick, children, danger, accent, title }: {
  onClick: () => void; children: React.ReactNode; danger?: boolean; accent?: boolean; title?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        background: "transparent",
        border: "1px solid " + (danger ? C.red : accent ? C.green : C.greenDim),
        color: danger ? C.red : accent ? C.green : C.greenDim,
        textShadow: accent ? "0 0 4px " + C.green : "none",
        padding: "9px 0", width: "240px",
        fontSize: "12px", fontWeight: "bold",
        cursor: "pointer", fontFamily: "'Courier New', monospace",
        display: "flex", alignItems: "center", justifyContent: "center",
        letterSpacing: "3px", minHeight: "40px",
      }}
    >{children}</button>
  );
}

function CrtBtn({ onClick, children, title }: {
  onClick: () => void; children: React.ReactNode; title?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        background: "transparent",
        border: "1px solid " + C.greenDim,
        color: C.greenDim,
        padding: "5px 10px", fontSize: "11px",
        cursor: "pointer", fontFamily: "'Courier New', monospace",
        letterSpacing: "2px", minHeight: "32px", minWidth: "56px",
      }}
    >{children}</button>
  );
}

// Declare missing CSS variable for TypeScript
declare module "react" {
  interface CSSProperties {
    WebkitAnimation?: string;
  }
}
