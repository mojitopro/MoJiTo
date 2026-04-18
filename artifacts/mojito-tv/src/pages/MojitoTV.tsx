import { useEffect, useRef, useState, useCallback } from "react";

interface Channel {
  cluster_id: string;
  name: string;
  streams: number;
  url: string;
  fusion: boolean;
}

interface Stats {
  streams: number;
  clusters: number;
  clustered: number;
  fusion_active: number;
}

const BASE = "/api/mojito";
const CATEGORIES = ["DEPORTES", "CINE", "NOTICIAS", "INFANTIL", "TODOS"];

function getCategory(name: string): string {
  const n = name.toLowerCase();
  if (/espn|fox sport|tyc|win sport|gol|directv sport|bein|sport|futbol|deportes|movistar dep/.test(n)) return "DEPORTES";
  if (/hbo|cinemax|star|cinema|golden|warner|tnt|fx|axn|studio|paramount|universal|sony|cine|amc|starz/.test(n)) return "CINE";
  if (/cnn|bbc|dw|telesur|noticias|news|info/.test(n)) return "NOTICIAS";
  if (/disney|nick|cartoon|kids|junior|jr|discovery kid|baby/.test(n)) return "INFANTIL";
  return "TODOS";
}

// Phosphor green palette
const C = {
  bg:       "#050800",
  panel:    "#060900",
  green:    "#c8ff00",
  greenDim: "#4a5e00",
  greenFade:"#1a2200",
  amber:    "#ff8c00",
  amberDim: "#4a2800",
  red:      "#ff2200",
  redDim:   "#3a0800",
  white:    "#e8f0c0",
  dim:      "#2a3300",
  border:   "#1a2200",
  scan:     "rgba(0,0,0,0.22)",
};

function now(): string {
  const d = new Date();
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  const s = String(d.getSeconds()).padStart(2, "0");
  return h + ":" + m + ":" + s;
}

export default function MojitoTV() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [playingIdx, setPlayingIdx] = useState(-1);
  const [focusedIdx, setFocusedIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [playerState, setPlayerState] = useState<"idle" | "playing" | "error">("idle");
  const [infoVisible, setInfoVisible] = useState(false);
  const [catIdx, setCatIdx] = useState(CATEGORIES.length - 1);
  const [showList, setShowList] = useState(true);
  const [clock, setClock] = useState(now());
  const videoRef = useRef<HTMLVideoElement>(null);
  const infoTimer = useRef<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Clock tick
  useEffect(() => {
    const t = setInterval(() => setClock(now()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(BASE + "/tv")
      .then((r) => r.json())
      .then((d) => { setChannels(d.channels || []); setLoading(false); })
      .catch(() => {
        fetch(BASE + "/channels?limit=80")
          .then((r) => r.json())
          .then((d) => { setChannels(d.channels || []); setLoading(false); })
          .catch(() => setLoading(false));
      });
    fetch(BASE + "/stats")
      .then((r) => r.json())
      .then((d) => setStats(d.stats || null))
      .catch(() => {});
  }, []);

  const activeCat = CATEGORIES[catIdx];
  const filtered = channels.filter((c) =>
    activeCat === "TODOS" ? true : getCategory(c.name) === activeCat
  );

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

  const playChannel = useCallback((idx: number) => {
    const ch = filtered[idx];
    if (!ch) return;
    setPlayingIdx(idx);
    setFocusedIdx(idx);
    setPlayerState("playing");
    showInfo();
    if (videoRef.current) {
      videoRef.current.src = ch.url;
      videoRef.current.load();
      videoRef.current.play().catch(() => {
        fetch(BASE + "/play/" + ch.cluster_id)
          .then((r) => r.json())
          .then((d) => {
            if (d.url && videoRef.current) {
              videoRef.current.src = d.url;
              videoRef.current.load();
              videoRef.current.play().catch(() => setPlayerState("error"));
            } else setPlayerState("error");
          })
          .catch(() => setPlayerState("error"));
      });
    }
    scrollTo(idx);
  }, [filtered, showInfo, scrollTo]);

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
    setCatIdx((i) => (i + 1) % CATEGORIES.length);
    setPlayingIdx(-1); setFocusedIdx(0); setPlayerState("idle");
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
  }, []);

  const catPrev = useCallback(() => {
    setCatIdx((i) => (i - 1 + CATEGORIES.length) % CATEGORIES.length);
    setPlayingIdx(-1); setFocusedIdx(0); setPlayerState("idle");
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
  }, []);

  const stopPlayer = useCallback(() => {
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
    setPlayerState("idle"); setPlayingIdx(-1);
  }, []);

  const playFocused = useCallback(() => playChannel(focusedIdx), [focusedIdx, playChannel]);

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
      {/* Horizontal scan line sweep */}
      <div style={{
        position: "fixed",
        left: 0, right: 0,
        height: "4px",
        background: "linear-gradient(to bottom, transparent, rgba(200,255,0,0.04), transparent)",
        zIndex: 9998,
        pointerEvents: "none",
        animation: "hscan 6s linear infinite",
        WebkitAnimation: "hscan 6s linear infinite",
      }} />

      {/* TOP BAR — station header */}
      <div style={{
        background: C.panel,
        borderBottom: "1px solid " + C.greenDim,
        display: "flex",
        alignItems: "center",
        padding: "0 14px",
        height: "48px",
        flexShrink: 0,
        justifyContent: "space-between",
      }}>
        {/* Station ID */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <div style={{
            border: "1px solid " + C.green,
            padding: "2px 10px",
            fontSize: "16px",
            fontWeight: "bold",
            letterSpacing: "4px",
            color: C.green,
            textShadow: "0 0 6px " + C.green + ", 0 0 14px " + C.green,
            marginRight: "12px",
          }}>LOCAL 58</div>
          <div style={{
            fontSize: "10px",
            color: C.greenDim,
            letterSpacing: "2px",
            lineHeight: "1.4",
          }}>
            MOJITO TV<br />TRANSMISION EN VIVO
          </div>
        </div>

        {/* Category selector */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <CrtBtn onClick={catPrev} title="Categoria anterior (PageUp)">&#9664;</CrtBtn>
          <div style={{
            border: "1px solid " + C.greenDim,
            padding: "4px 16px",
            fontSize: "13px",
            fontWeight: "bold",
            color: C.green,
            letterSpacing: "3px",
            margin: "0 6px",
            minWidth: "120px",
            textAlign: "center",
            textShadow: "0 0 5px " + C.green,
          }}>{activeCat}</div>
          <CrtBtn onClick={catNext} title="Categoria siguiente (PageDown)">&#9654;</CrtBtn>
        </div>

        {/* Clock + status */}
        <div style={{ display: "flex", alignItems: "center" }}>
          {playerState === "playing" && (
            <div style={{
              display: "flex", alignItems: "center", marginRight: "14px",
            }}>
              <div style={{
                width: "8px", height: "8px", borderRadius: "50%",
                background: C.red,
                boxShadow: "0 0 6px " + C.red,
                animation: "pulse-red 1s infinite",
                WebkitAnimation: "pulse-red 1s infinite",
                marginRight: "6px",
              }} />
              <span style={{ fontSize: "11px", color: C.red, letterSpacing: "2px" }}>ON AIR</span>
            </div>
          )}
          {stats && playerState !== "playing" && (
            <div style={{ fontSize: "11px", color: C.greenDim, marginRight: "14px", letterSpacing: "1px" }}>
              {stats.fusion_active} ACTIVOS
            </div>
          )}
          <div style={{
            fontSize: "14px",
            color: C.white,
            letterSpacing: "3px",
            fontWeight: "bold",
            textShadow: "0 0 4px " + C.white,
          }}>{clock}</div>
          <div style={{ marginLeft: "12px" }}>
            <CrtBtn onClick={() => setShowList((v) => !v)} title="Lista">{showList ? "=]" : "[="}</CrtBtn>
          </div>
        </div>
      </div>

      {/* MAIN */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* CHANNEL LIST PANEL */}
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
            {/* Guide header */}
            <div style={{
              padding: "6px 12px",
              borderBottom: "1px solid " + C.border,
              display: "flex",
              justifyContent: "space-between",
              fontSize: "10px",
              color: C.greenDim,
              letterSpacing: "2px",
            }}>
              <span>GUIA DE CANALES</span>
              <span>{filtered.length} SENAL{filtered.length !== 1 ? "ES" : ""}</span>
            </div>

            {/* Focused preview */}
            {focusedCh && playerState !== "playing" && (
              <div style={{
                padding: "8px 12px",
                borderBottom: "1px solid " + C.border,
                background: C.greenFade,
              }}>
                <div style={{ fontSize: "9px", color: C.greenDim, letterSpacing: "3px", marginBottom: "3px" }}>
                  SELECCIONADO
                </div>
                <div style={{
                  fontSize: "13px",
                  fontWeight: "bold",
                  color: C.green,
                  textShadow: "0 0 5px " + C.green,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}>{focusedCh.name}</div>
                <div style={{ fontSize: "9px", color: C.greenDim, marginTop: "2px", letterSpacing: "1px", animation: "blink 1.2s step-end infinite", WebkitAnimation: "blink 1.2s step-end infinite" }}>
                  PRESIONE OK PARA SINTONIZAR_
                </div>
              </div>
            )}

            {/* Channel list */}
            <div ref={listRef} style={{ flex: 1, overflowY: "auto", overflowX: "hidden" }}>
              {loading && (
                <div style={{ textAlign: "center", padding: "40px 12px", color: C.greenDim, fontSize: "11px", letterSpacing: "2px" }}>
                  BUSCANDO SENAL...
                </div>
              )}
              {!loading && filtered.length === 0 && (
                <div style={{ textAlign: "center", padding: "40px 12px", color: C.greenDim, fontSize: "11px", letterSpacing: "2px" }}>
                  SIN SENAL EN<br />ESTA CATEGORIA
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

            {/* Control panel */}
            <div style={{
              borderTop: "1px solid " + C.border,
              padding: "10px",
              background: C.panel,
            }}>
              <div style={{ display: "flex", justifyContent: "center", marginBottom: "6px" }}>
                <CrtBtnWide onClick={playFocused} accent title="Reproducir (ENTER)">
                  &#9654; SINTONIZAR
                </CrtBtnWide>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <CrtBtn onClick={movePrev} title="Subir (↑)">&#9650; SUBIR</CrtBtn>
                <CrtBtn onClick={moveNext} title="Bajar (↓)">&#9660; BAJAR</CrtBtn>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <CrtBtn onClick={chPrev} title="CH anterior">CH-</CrtBtn>
                <CrtBtn onClick={chNext} title="CH siguiente">CH+</CrtBtn>
              </div>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <CrtBtnWide onClick={stopPlayer} danger title="Detener (ESC)">
                  &#9632; CORTAR SENAL
                </CrtBtnWide>
              </div>
            </div>
          </div>
        )}

        {/* PLAYER */}
        <div style={{ flex: 1, background: "#000", position: "relative", overflow: "hidden" }}>
          <video
            ref={videoRef}
            controls
            playsInline
            onError={() => setPlayerState("error")}
            style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
          />

          {/* NO SIGNAL / IDLE */}
          {playerState === "idle" && (
            <div style={{
              position: "absolute",
              top: 0, left: 0, right: 0, bottom: 0,
              background: C.bg,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}>
              {/* Color bars */}
              <ColorBars />

              <div style={{ marginTop: "32px", textAlign: "center" }}>
                <div style={{
                  fontSize: "11px",
                  letterSpacing: "6px",
                  color: C.greenDim,
                  marginBottom: "8px",
                }}>WCLV</div>
                <div style={{
                  fontSize: "36px",
                  fontWeight: "bold",
                  letterSpacing: "8px",
                  color: C.green,
                  textShadow: "0 0 10px " + C.green + ", 0 0 30px " + C.green,
                  animation: "glitch 5s infinite",
                  WebkitAnimation: "glitch 5s infinite",
                }}>LOCAL 58</div>
                <div style={{
                  fontSize: "10px",
                  letterSpacing: "4px",
                  color: C.greenDim,
                  marginTop: "6px",
                }}>MOJITO TV · TRANSMISION CONTINUA</div>
              </div>

              <div style={{
                marginTop: "36px",
                border: "1px solid " + C.border,
                padding: "14px 20px",
                background: C.greenFade,
                textAlign: "left",
              }}>
                <div style={{ fontSize: "9px", color: C.greenDim, letterSpacing: "3px", marginBottom: "12px", textAlign: "center" }}>
                  INSTRUCCIONES DE OPERACION
                </div>
                <RemoteRef keycode="38 / 40" keys="↑ / ↓" desc="NAVEGAR LISTA SIN SINTONIZAR" />
                <RemoteRef keycode="13"      keys="OK"    desc="SINTONIZAR CANAL SELECCIONADO" />
                <RemoteRef keycode="27"      keys="ESC"   desc="CORTAR SENAL" />
                <RemoteRef keycode="33 / 34" keys="PG"    desc="CAMBIAR CATEGORIA" />
              </div>

              <div style={{
                marginTop: "20px",
                fontSize: "9px",
                color: C.dim,
                letterSpacing: "3px",
                animation: "blink 2s step-end infinite",
                WebkitAnimation: "blink 2s step-end infinite",
              }}>
                SELECCIONE UN CANAL PARA INICIAR TRANSMISION
              </div>
            </div>
          )}

          {/* TECHNICAL DIFFICULTIES */}
          {playerState === "error" && (
            <div style={{
              position: "absolute",
              top: 0, left: 0, right: 0, bottom: 0,
              background: C.bg,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}>
              <StaticNoise />
              <div style={{
                position: "relative",
                zIndex: 2,
                textAlign: "center",
                padding: "20px",
                border: "1px solid " + C.amberDim,
                background: "rgba(5,8,0,0.92)",
              }}>
                <div style={{
                  fontSize: "11px",
                  color: C.amber,
                  letterSpacing: "4px",
                  marginBottom: "10px",
                }}>DIFICULTADES TECNICAS</div>
                <div style={{
                  fontSize: "28px",
                  fontWeight: "bold",
                  color: C.amber,
                  textShadow: "0 0 8px " + C.amber,
                  letterSpacing: "3px",
                  marginBottom: "6px",
                }}>SENAL PERDIDA</div>
                <div style={{ fontSize: "10px", color: C.amberDim, letterSpacing: "2px", marginBottom: "20px" }}>
                  ESTE CANAL PUEDE ESTAR FUERA DE AIRE
                </div>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <CrtBtnWide onClick={chNext} title="Siguiente">&#9660; SIGUIENTE SENAL</CrtBtnWide>
                  <div style={{ height: "8px" }} />
                  <CrtBtnWide onClick={chPrev} title="Anterior">&#9650; SENAL ANTERIOR</CrtBtnWide>
                  <div style={{ height: "8px" }} />
                  <CrtBtnWide onClick={stopPlayer} danger title="Detener">&#9632; CORTAR</CrtBtnWide>
                </div>
              </div>
            </div>
          )}

          {/* NOW PLAYING / ON AIR BANNER */}
          {infoVisible && playingCh && (
            <div style={{
              position: "absolute",
              bottom: 0, left: 0, right: 0,
              background: "rgba(5,8,0,0.94)",
              borderTop: "1px solid " + C.greenDim,
              padding: "12px 16px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", marginBottom: "4px" }}>
                  <div style={{
                    width: "7px", height: "7px", borderRadius: "50%",
                    background: C.red,
                    boxShadow: "0 0 5px " + C.red,
                    animation: "pulse-red 1s infinite",
                    WebkitAnimation: "pulse-red 1s infinite",
                    marginRight: "7px",
                  }} />
                  <span style={{ fontSize: "9px", color: C.red, letterSpacing: "4px" }}>EN VIVO</span>
                </div>
                <div style={{
                  fontSize: "20px",
                  fontWeight: "bold",
                  color: C.green,
                  textShadow: "0 0 6px " + C.green,
                  letterSpacing: "2px",
                }}>{playingCh.name.toUpperCase()}</div>
                <div style={{ fontSize: "10px", color: C.greenDim, marginTop: "3px", letterSpacing: "2px" }}>
                  {getCategory(playingCh.name)} · FUSION ACTIVA · {playingCh.streams} STREAM{playingCh.streams !== 1 ? "S" : ""}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{
                  fontSize: "30px",
                  fontWeight: "bold",
                  color: C.green,
                  textShadow: "0 0 8px " + C.green,
                  letterSpacing: "2px",
                }}>CH {String(playingIdx + 1).padStart(2, "0")}</div>
                <div style={{ fontSize: "10px", color: C.dim, letterSpacing: "1px" }}>
                  / {filtered.length}
                </div>
              </div>
            </div>
          )}

          {/* Floating remote — shown when playing */}
          {playerState === "playing" && !infoVisible && (
            <FloatingRemote
              onPrev={chPrev}
              onNext={chNext}
              onStop={stopPlayer}
              onInfo={showInfo}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Color bars — test pattern ── */
function ColorBars() {
  const bars = [
    "#c8c8c8", "#c8c800", "#00c8c8", "#00c800",
    "#c800c8", "#c80000", "#0000c8",
  ];
  return (
    <div style={{ display: "flex", width: "320px", height: "60px", border: "1px solid #1a2200" }}>
      {bars.map((color, i) => (
        <div key={i} style={{ flex: 1, background: color }} />
      ))}
    </div>
  );
}

/* ── Static noise overlay ── */
function StaticNoise() {
  return (
    <div style={{
      position: "absolute",
      top: 0, left: 0, right: 0, bottom: 0,
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
        padding: "10px 12px",
        cursor: "pointer",
        borderBottom: "1px solid " + C.border,
        background: playing ? C.greenFade : focused ? "rgba(200,255,0,0.03)" : "transparent",
        borderLeft: playing ? "3px solid " + C.green : focused ? "3px solid " + C.greenDim : "3px solid transparent",
        display: "flex",
        alignItems: "center",
        minHeight: "52px",
      }}
    >
      <div style={{
        fontSize: "12px",
        fontWeight: "bold",
        color: playing ? C.green : focused ? C.greenDim : C.dim,
        width: "26px",
        flexShrink: 0,
        textAlign: "right",
        marginRight: "10px",
        letterSpacing: "1px",
      }}>
        {String(number).padStart(2, "0")}
      </div>
      <div style={{ flex: 1, overflow: "hidden" }}>
        <div style={{
          fontSize: "13px",
          fontWeight: playing || focused ? "bold" : "normal",
          color: playing ? C.green : focused ? C.white : "#7a8a50",
          textShadow: playing ? "0 0 5px " + C.green : "none",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          letterSpacing: "1px",
        }}>
          {channel.name.toUpperCase()}
        </div>
        <div style={{
          fontSize: "9px",
          color: playing ? C.greenDim : C.dim,
          marginTop: "3px",
          letterSpacing: "2px",
        }}>
          {getCategory(channel.name)} · FUSION
        </div>
      </div>
      {playing && (
        <div style={{
          flexShrink: 0,
          fontSize: "9px",
          color: C.red,
          letterSpacing: "2px",
          marginLeft: "6px",
          animation: "pulse-red 1s infinite",
          WebkitAnimation: "pulse-red 1s infinite",
        }}>●</div>
      )}
      {!playing && focused && (
        <div style={{ flexShrink: 0, color: C.greenDim, fontSize: "12px", marginLeft: "6px" }}>&#9654;</div>
      )}
    </div>
  );
}

/* ── Floating on-screen remote ── */
function FloatingRemote({ onPrev, onNext, onStop, onInfo }: {
  onPrev: () => void; onNext: () => void; onStop: () => void; onInfo: () => void;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div style={{ position: "absolute", top: "10px", right: "10px" }}>
      <button
        onClick={() => setVisible((v) => !v)}
        style={{
          background: "rgba(5,8,0,0.9)",
          border: "1px solid " + C.greenDim,
          color: C.greenDim,
          borderRadius: "0",
          width: "40px", height: "40px",
          fontSize: "14px",
          cursor: "pointer",
          fontFamily: "'Courier New', monospace",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          letterSpacing: "1px",
        }}
        title="Control"
      >RC</button>
      {visible && (
        <div style={{
          marginTop: "4px",
          background: "rgba(5,8,0,0.95)",
          border: "1px solid " + C.border,
          padding: "8px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}>
          <RemBtn onClick={onPrev} title="CH-">&#9650;</RemBtn>
          <div style={{ height: "4px" }} />
          <RemBtn onClick={onInfo} title="Info">INF</RemBtn>
          <div style={{ height: "4px" }} />
          <RemBtn onClick={onNext} title="CH+">&#9660;</RemBtn>
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
        borderRadius: "0",
        width: "50px", height: "50px",
        fontSize: "16px",
        cursor: "pointer",
        fontFamily: "'Courier New', monospace",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: "bold",
        letterSpacing: "1px",
      }}
    >{children}</button>
  );
}

/* ── Wide CRT button ── */
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
        textShadow: accent ? "0 0 5px " + C.green : "none",
        padding: "10px 0",
        width: "240px",
        fontSize: "13px",
        fontWeight: "bold",
        cursor: "pointer",
        fontFamily: "'Courier New', monospace",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        letterSpacing: "3px",
        minHeight: "42px",
      }}
    >{children}</button>
  );
}

/* ── Small CRT button ── */
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
        padding: "6px 12px",
        fontSize: "12px",
        cursor: "pointer",
        fontFamily: "'Courier New', monospace",
        letterSpacing: "2px",
        minHeight: "34px",
        minWidth: "60px",
      }}
    >{children}</button>
  );
}

/* ── Remote keycode reference row ── */
function RemoteRef({ keycode, keys, desc }: { keycode: string; keys: string; desc: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}>
      <div style={{
        border: "1px solid " + C.greenDim,
        padding: "2px 8px",
        fontSize: "11px",
        color: C.green,
        minWidth: "44px",
        textAlign: "center",
        marginRight: "10px",
        flexShrink: 0,
        letterSpacing: "1px",
      }}>{keys}</div>
      <div>
        <div style={{ fontSize: "10px", color: C.white, letterSpacing: "1px" }}>{desc}</div>
        <div style={{ fontSize: "9px", color: C.dim, letterSpacing: "1px" }}>keyCode {keycode}</div>
      </div>
    </div>
  );
}
