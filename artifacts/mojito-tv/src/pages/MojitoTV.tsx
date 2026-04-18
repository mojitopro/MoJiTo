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

const CATEGORIES = ["Deportes", "Cine", "Noticias", "Infantil", "Todos"];

function getCategory(name: string): string {
  const n = name.toLowerCase();
  if (/espn|fox sport|tyc|win sport|gol|directv sport|bein|sport|futbol|deportes|movistar dep/.test(n)) return "Deportes";
  if (/hbo|cinemax|star|cinema|golden|warner|tnt|fx|axn|studio|paramount|universal|sony|cine|amc|starz/.test(n)) return "Cine";
  if (/cnn|bbc|dw|telesur|noticias|news|info|telam/.test(n)) return "Noticias";
  if (/disney|nick|cartoon|kids|junior|jr|discovery kid|baby/.test(n)) return "Infantil";
  return "Todos";
}

export default function MojitoTV() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [playingIdx, setPlayingIdx] = useState(-1);   // canal que está reproduciendo
  const [focusedIdx, setFocusedIdx] = useState(0);    // canal resaltado (cursor de navegación)
  const [loading, setLoading] = useState(true);
  const [playerState, setPlayerState] = useState<"idle" | "playing" | "error">("idle");
  const [infoVisible, setInfoVisible] = useState(false);
  const [catIdx, setCatIdx] = useState(CATEGORIES.length - 1); // "Todos"
  const [showList, setShowList] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const infoTimer = useRef<number | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    fetch(BASE + "/tv")
      .then((r) => r.json())
      .then((data) => { setChannels(data.channels || []); setLoading(false); })
      .catch(() => {
        fetch(BASE + "/channels?limit=80")
          .then((r) => r.json())
          .then((data) => { setChannels(data.channels || []); setLoading(false); })
          .catch(() => setLoading(false));
      });
    fetch(BASE + "/stats")
      .then((r) => r.json())
      .then((data) => setStats(data.stats || null))
      .catch(() => {});
  }, []);

  const activeCat = CATEGORIES[catIdx];
  const filtered = channels.filter((c) => {
    if (activeCat === "Todos") return true;
    return getCategory(c.name) === activeCat;
  });

  const showInfo = useCallback(() => {
    setInfoVisible(true);
    if (infoTimer.current) clearTimeout(infoTimer.current);
    infoTimer.current = window.setTimeout(() => setInfoVisible(false), 5000);
  }, []);

  const scrollFocusedIntoView = useCallback((idx: number) => {
    setTimeout(() => {
      const el = listRef.current?.querySelectorAll("[data-channel]")[idx] as HTMLElement | null;
      el?.scrollIntoView({ block: "nearest" });
    }, 30);
  }, []);

  // Play the channel at given index in filtered list
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
          .then((data) => {
            if (data.url && videoRef.current) {
              videoRef.current.src = data.url;
              videoRef.current.load();
              videoRef.current.play().catch(() => setPlayerState("error"));
            } else setPlayerState("error");
          })
          .catch(() => setPlayerState("error"));
      });
    }
    scrollFocusedIntoView(idx);
  }, [filtered, showInfo, scrollFocusedIntoView]);

  // Move cursor UP — keyCode 38 (↑) or 37 (←)
  const movePrev = useCallback(() => {
    setFocusedIdx((i) => {
      const next = (i - 1 + Math.max(filtered.length, 1)) % Math.max(filtered.length, 1);
      scrollFocusedIntoView(next);
      return next;
    });
  }, [filtered.length, scrollFocusedIntoView]);

  // Move cursor DOWN — keyCode 40 (↓) or 39 (→)
  const moveNext = useCallback(() => {
    setFocusedIdx((i) => {
      const next = (i + 1) % Math.max(filtered.length, 1);
      scrollFocusedIntoView(next);
      return next;
    });
  }, [filtered.length, scrollFocusedIntoView]);

  // Play+jump to next channel (CH+ button)
  const chNext = useCallback(() => {
    const next = (playingIdx + 1) % Math.max(filtered.length, 1);
    playChannel(next);
  }, [playingIdx, filtered.length, playChannel]);

  // Play+jump to prev channel (CH- button)
  const chPrev = useCallback(() => {
    const prev = (playingIdx - 1 + filtered.length) % Math.max(filtered.length, 1);
    playChannel(prev);
  }, [playingIdx, filtered.length, playChannel]);

  const catNext = useCallback(() => {
    setCatIdx((i) => (i + 1) % CATEGORIES.length);
    setPlayingIdx(-1);
    setFocusedIdx(0);
    setPlayerState("idle");
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
  }, []);

  const catPrev = useCallback(() => {
    setCatIdx((i) => (i - 1 + CATEGORIES.length) % CATEGORIES.length);
    setPlayingIdx(-1);
    setFocusedIdx(0);
    setPlayerState("idle");
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
  }, []);

  const stopPlayer = useCallback(() => {
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.src = ""; }
    setPlayerState("idle");
    setPlayingIdx(-1);
  }, []);

  // ENTER — reproduce el canal enfocado actualmente
  const playFocused = useCallback(() => {
    playChannel(focusedIdx);
  }, [focusedIdx, playChannel]);

  // ── Keyboard handler — keycodes reales del control Philco ──
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      switch (e.keyCode) {
        case 38: // ↑ — mover cursor arriba
        case 37: // ← — mover cursor arriba
          e.preventDefault();
          movePrev();
          break;
        case 40: // ↓ — mover cursor abajo
        case 39: // → — mover cursor abajo
          e.preventDefault();
          moveNext();
          break;
        case 13: // ENTER/OK — reproducir el canal enfocado
          e.preventDefault();
          playFocused();
          break;
        case 33: // PageUp — categoría anterior
          e.preventDefault();
          catPrev();
          break;
        case 34: // PageDown — categoría siguiente
          e.preventDefault();
          catNext();
          break;
        case 27: // ESC/BACK — detener
          e.preventDefault();
          stopPlayer();
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [movePrev, moveNext, playFocused, catPrev, catNext, stopPlayer]);

  const playingChannel = playingIdx >= 0 ? filtered[playingIdx] : null;
  const focusedChannel = filtered[focusedIdx] || null;

  return (
    <div style={{
      background: "#000",
      height: "100vh",
      color: "#fff",
      fontFamily: "Arial, Helvetica, sans-serif",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    }}>
      {/* TOP BAR */}
      <div style={{
        background: "#0a0a18",
        borderBottom: "2px solid #00d4ff",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        height: "56px",
        flexShrink: 0,
        justifyContent: "space-between",
      }}>
        <div style={{
          background: "linear-gradient(135deg, #00d4ff, #7b2cbf)",
          borderRadius: "6px",
          padding: "6px 14px",
          fontWeight: "bold",
          fontSize: "20px",
          letterSpacing: "2px",
          lineHeight: 1,
        }}>MoJiTo</div>

        {/* Category nav — PageUp / PageDown / click */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <TvBtn onClick={catPrev} wide={false} title="Categoria anterior (PageUp)">&#9664;</TvBtn>
          <div style={{
            background: "#12122a",
            border: "1px solid #00d4ff",
            borderRadius: "6px",
            padding: "6px 20px",
            fontSize: "15px",
            fontWeight: "bold",
            color: "#00d4ff",
            minWidth: "110px",
            textAlign: "center",
            margin: "0 6px",
          }}>{activeCat}</div>
          <TvBtn onClick={catNext} wide={false} title="Categoria siguiente (PageDown)">&#9654;</TvBtn>
        </div>

        <div style={{ display: "flex", alignItems: "center" }}>
          {stats && (
            <div style={{ fontSize: "13px", color: "#00d4ff", marginRight: "12px" }}>
              <span style={{ color: "#0f0" }}>●</span> {stats.fusion_active} activos
            </div>
          )}
          <TvBtn onClick={() => setShowList((v) => !v)} wide={false} title="Mostrar/ocultar lista">
            {showList ? "[ ]" : "[=]"}
          </TvBtn>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* CHANNEL LIST PANEL */}
        {showList && (
          <div style={{
            width: "290px",
            flexShrink: 0,
            background: "#08080f",
            borderRight: "2px solid #1a1a35",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}>
            {/* Status bar */}
            <div style={{
              padding: "8px 14px",
              borderBottom: "1px solid #1a1a35",
              fontSize: "12px",
              display: "flex",
              justifyContent: "space-between",
              color: "#555",
            }}>
              <span>{activeCat}</span>
              <span>{filtered.length} canales</span>
            </div>

            {/* Focused channel preview — shows what's highlighted */}
            {focusedChannel && playerState !== "playing" && (
              <div style={{
                padding: "10px 14px",
                borderBottom: "1px solid #1a1a35",
                background: "#0e0e20",
              }}>
                <div style={{ fontSize: "11px", color: "#00d4ff", letterSpacing: "1px", marginBottom: "4px" }}>
                  ► SELECCIONADO
                </div>
                <div style={{ fontSize: "14px", fontWeight: "bold", color: "#fff" }}>
                  {focusedChannel.name}
                </div>
                <div style={{ fontSize: "11px", color: "#555", marginTop: "2px" }}>
                  Presiona ENTER u OK para reproducir
                </div>
              </div>
            )}

            {/* Scrollable channel list */}
            <div ref={listRef} style={{ flex: 1, overflowY: "auto", overflowX: "hidden" }}>
              {loading && (
                <div style={{ textAlign: "center", padding: "50px 16px", color: "#444" }}>
                  Cargando canales...
                </div>
              )}
              {!loading && filtered.length === 0 && (
                <div style={{ textAlign: "center", padding: "50px 16px", color: "#444", fontSize: "13px" }}>
                  Sin canales en esta categoria
                </div>
              )}
              {filtered.map((ch, idx) => (
                <ChannelRow
                  key={ch.cluster_id}
                  number={idx + 1}
                  channel={ch}
                  playing={idx === playingIdx}
                  focused={idx === focusedIdx}
                  onClick={() => playChannel(idx)}
                />
              ))}
            </div>

            {/* Remote-style controls at bottom */}
            <div style={{
              borderTop: "2px solid #1a1a35",
              padding: "12px",
              background: "#050508",
            }}>
              {/* Play focused = ENTER equivalent */}
              <div style={{ display: "flex", justifyContent: "center", marginBottom: "8px" }}>
                <TvBtn onClick={playFocused} wide accent title="Reproducir canal seleccionado (ENTER)">
                  &#9654; REPRODUCIR
                </TvBtn>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <TvBtn onClick={movePrev} wide={false} title="Canal anterior en lista (↑)">&#9650; Subir</TvBtn>
                <TvBtn onClick={moveNext} wide={false} title="Canal siguiente en lista (↓)">&#9660; Bajar</TvBtn>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <TvBtn onClick={chPrev} wide={false} title="Reproducir canal anterior">&#9650;&#9650; CH-</TvBtn>
                <TvBtn onClick={chNext} wide={false} title="Reproducir canal siguiente">CH+ &#9660;&#9660;</TvBtn>
              </div>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <TvBtn onClick={stopPlayer} wide danger title="Detener (ESC)">&#9632; STOP</TvBtn>
              </div>
            </div>
          </div>
        )}

        {/* VIDEO PLAYER PANEL */}
        <div style={{ flex: 1, background: "#000", position: "relative", overflow: "hidden" }}>
          <video
            ref={videoRef}
            controls
            playsInline
            onError={() => setPlayerState("error")}
            style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
          />

          {/* IDLE SCREEN */}
          {playerState === "idle" && (
            <div style={{
              position: "absolute",
              top: 0, left: 0, right: 0, bottom: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              background: "radial-gradient(ellipse at center, #080820 0%, #000 100%)",
            }}>
              <div style={{
                background: "linear-gradient(135deg, #00d4ff, #7b2cbf)",
                borderRadius: "10px",
                padding: "8px 28px",
                fontWeight: "bold",
                fontSize: "42px",
                letterSpacing: "4px",
                marginBottom: "24px",
              }}>MoJiTo</div>
              <div style={{ color: "#555", fontSize: "15px", marginBottom: "36px" }}>
                Navega con ↑↓ y presiona OK para reproducir
              </div>

              {/* Remote keycode reference */}
              <div style={{
                background: "#0a0a18",
                border: "1px solid #2a2a4e",
                borderRadius: "12px",
                padding: "16px 24px",
              }}>
                <div style={{ color: "#444", fontSize: "11px", textAlign: "center", marginBottom: "14px", letterSpacing: "2px" }}>
                  CONTROL REMOTO PHILCO
                </div>
                <RemoteHintRow keycode="38/40" icon="&#9650;&#9660;" label="Navegar lista" note="Arriba / Abajo sin reproducir" />
                <RemoteHintRow keycode="13" icon="OK" label="ENTER / OK" note="Reproducir canal seleccionado" />
                <RemoteHintRow keycode="27" icon="&#9632;" label="ESC / BACK" note="Detener reproduccion" />
                <RemoteHintRow keycode="33/34" icon="&#9664;&#9654;" label="PgUp / PgDn" note="Cambiar categoria" />
              </div>
            </div>
          )}

          {/* ERROR SCREEN */}
          {playerState === "error" && (
            <div style={{
              position: "absolute",
              top: 0, left: 0, right: 0, bottom: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(0,0,0,0.9)",
            }}>
              <div style={{ fontSize: "48px", marginBottom: "16px" }}>⚠</div>
              <div style={{ color: "#ff4444", fontSize: "20px", fontWeight: "bold", marginBottom: "8px" }}>
                Stream no disponible
              </div>
              <div style={{ color: "#666", fontSize: "14px", marginBottom: "30px" }}>
                El canal puede estar offline
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <TvBtn onClick={chNext} wide title="Siguiente canal (↓ + OK)">&#9660; Siguiente canal</TvBtn>
                <div style={{ height: "10px" }} />
                <TvBtn onClick={chPrev} wide title="Canal anterior (↑ + OK)">&#9650; Canal anterior</TvBtn>
                <div style={{ height: "10px" }} />
                <TvBtn onClick={stopPlayer} wide danger title="Detener (ESC)">&#9632; Detener</TvBtn>
              </div>
            </div>
          )}

          {/* NOW PLAYING banner */}
          {infoVisible && playingChannel && (
            <div style={{
              position: "absolute",
              bottom: "20px",
              left: "20px",
              right: "20px",
              background: "rgba(8,8,24,0.92)",
              border: "1px solid #00d4ff44",
              borderRadius: "10px",
              padding: "14px 18px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}>
              <div>
                <div style={{ color: "#00d4ff", fontSize: "11px", letterSpacing: "2px", marginBottom: "6px" }}>
                  ● EN VIVO
                </div>
                <div style={{ fontSize: "22px", fontWeight: "bold" }}>{playingChannel.name}</div>
                <div style={{ color: "#666", fontSize: "12px", marginTop: "4px" }}>
                  {getCategory(playingChannel.name)} · FUSION activa
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ color: "#00d4ff", fontSize: "28px", fontWeight: "bold" }}>
                  {playingIdx + 1}
                </div>
                <div style={{ color: "#555", fontSize: "12px" }}>/ {filtered.length}</div>
              </div>
            </div>
          )}

          {/* Floating remote — top right when playing */}
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

/* ── Floating on-screen remote ── */
function FloatingRemote({ onPrev, onNext, onStop, onInfo }: {
  onPrev: () => void; onNext: () => void; onStop: () => void; onInfo: () => void;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div style={{ position: "absolute", top: "12px", right: "12px" }}>
      <button
        onClick={() => setVisible((v) => !v)}
        style={{
          background: "rgba(10,10,24,0.85)",
          border: "1px solid #2a2a5e",
          color: "#00d4ff",
          borderRadius: "6px",
          width: "44px",
          height: "44px",
          fontSize: "18px",
          cursor: "pointer",
          fontFamily: "Arial, sans-serif",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        title="Control remoto"
      >
        &#9635;
      </button>
      {visible && (
        <div style={{
          marginTop: "6px",
          background: "rgba(8,8,20,0.95)",
          border: "1px solid #2a2a5e",
          borderRadius: "10px",
          padding: "10px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}>
          <RemBtn onClick={onPrev} title="CH anterior">&#9650;</RemBtn>
          <div style={{ height: "6px" }} />
          <RemBtn onClick={onInfo} title="Info">i</RemBtn>
          <div style={{ height: "6px" }} />
          <RemBtn onClick={onNext} title="CH siguiente">&#9660;</RemBtn>
          <div style={{ height: "6px" }} />
          <RemBtn onClick={onStop} title="Detener" danger>&#9632;</RemBtn>
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
        background: danger ? "#300a0a" : "#12122a",
        border: danger ? "2px solid #ff4444" : "2px solid #2a2a5e",
        color: danger ? "#ff6666" : "#fff",
        borderRadius: "8px",
        width: "54px",
        height: "54px",
        fontSize: "20px",
        cursor: "pointer",
        fontFamily: "Arial, sans-serif",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: "bold",
      }}
    >
      {children}
    </button>
  );
}

/* ── Channel row ── */
function ChannelRow({ number, channel, playing, focused, onClick }: {
  number: number; channel: Channel; playing: boolean; focused: boolean; onClick: () => void;
}) {
  const isHighlighted = playing || focused;
  return (
    <div
      onClick={onClick}
      data-channel="true"
      style={{
        padding: "12px 14px",
        cursor: "pointer",
        borderBottom: "1px solid #0f0f1e",
        background: playing
          ? "linear-gradient(90deg, #001830, #100a20)"
          : focused
          ? "#0e0e1e"
          : "transparent",
        borderLeft: playing
          ? "4px solid #00d4ff"
          : focused
          ? "4px solid #7b2cbf"
          : "4px solid transparent",
        display: "flex",
        alignItems: "center",
        minHeight: "56px",
      }}
    >
      <div style={{
        color: playing ? "#00d4ff" : focused ? "#7b2cbf" : "#333",
        fontSize: "12px",
        fontWeight: "bold",
        width: "28px",
        flexShrink: 0,
        textAlign: "right",
        marginRight: "10px",
      }}>
        {number}
      </div>
      <div style={{ flex: 1, overflow: "hidden" }}>
        <div style={{
          fontSize: "15px",
          fontWeight: isHighlighted ? "bold" : "normal",
          color: playing ? "#fff" : focused ? "#ddd" : "#aaa",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}>
          {channel.name}
        </div>
        <div style={{
          fontSize: "11px",
          color: playing ? "#00d4ff88" : focused ? "#7b2cbf88" : "#333",
          marginTop: "3px",
        }}>
          {getCategory(channel.name)} · FUSION
        </div>
      </div>
      <div style={{ flexShrink: 0, marginLeft: "8px" }}>
        {playing && (
          <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#0f0" }} />
        )}
        {!playing && focused && (
          <div style={{ color: "#7b2cbf", fontSize: "14px" }}>&#9654;</div>
        )}
      </div>
    </div>
  );
}

/* ── Large TV button ── */
function TvBtn({ onClick, children, wide, danger, accent, title }: {
  onClick: () => void; children: React.ReactNode; wide: boolean; danger?: boolean; accent?: boolean; title?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        background: danger ? "#200808" : accent ? "linear-gradient(90deg, #00d4ff22, #7b2cbf22)" : "#0e0e20",
        border: danger ? "2px solid #ff4444" : accent ? "2px solid #00d4ff" : "2px solid #2a2a5e",
        color: danger ? "#ff6666" : accent ? "#00d4ff" : "#ccc",
        borderRadius: "8px",
        padding: wide ? "12px 0" : "10px 14px",
        width: wide ? "240px" : "auto",
        fontSize: "15px",
        fontWeight: "bold",
        cursor: "pointer",
        fontFamily: "Arial, sans-serif",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        letterSpacing: "1px",
        minHeight: "48px",
      }}
    >
      {children}
    </button>
  );
}

/* ── Remote hint row ── */
function RemoteHintRow({ keycode, icon, label, note }: { keycode: string; icon: string; label: string; note: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: "10px", width: "300px" }}>
      <div style={{
        background: "#1a1a35",
        border: "1px solid #2a2a5e",
        borderRadius: "5px",
        padding: "4px 8px",
        fontSize: "13px",
        color: "#00d4ff",
        minWidth: "54px",
        textAlign: "center",
        fontWeight: "bold",
        marginRight: "10px",
        flexShrink: 0,
      }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: "13px", color: "#fff", fontWeight: "bold" }}>{label}</div>
        <div style={{ fontSize: "10px", color: "#444" }}>{note} · keyCode {keycode}</div>
      </div>
    </div>
  );
}
