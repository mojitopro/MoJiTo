import { useEffect, useRef, useState } from "react";

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

type View = "tv" | "dashboard";

const BASE = "/api/mojito";

function MojitoTV() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [view, setView] = useState<View>("tv");
  const [loading, setLoading] = useState(true);
  const [playerState, setPlayerState] = useState<"idle" | "playing" | "error">("idle");
  const [searchTerm, setSearchTerm] = useState("");
  const [infoVisible, setInfoVisible] = useState(false);
  const [activeCategory, setActiveCategory] = useState("all");
  const videoRef = useRef<HTMLVideoElement>(null);
  const infoTimer = useRef<number | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(BASE + "/tv")
      .then((r) => r.json())
      .then((data) => {
        const chs: Channel[] = (data.channels || [])
          .filter((c: Channel) => c.fusion && c.streams > 0)
          .slice(0, 80);
        setChannels(chs);
        setLoading(false);
      })
      .catch(() => {
        fetch(BASE + "/channels?limit=80")
          .then((r) => r.json())
          .then((data) => {
            setChannels(data.channels || []);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });

    fetch(BASE + "/stats")
      .then((r) => r.json())
      .then((data) => setStats(data.stats || null))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (view !== "tv") return;
      if (e.keyCode === 40 || e.keyCode === 39) next();
      else if (e.keyCode === 38 || e.keyCode === 37) prev();
      else if (e.keyCode === 13) {
        if (currentIdx >= 0) playChannel(currentIdx);
      } else if (e.keyCode === 27) stopPlayer();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const filtered = channels.filter((c) => {
    if (searchTerm && !c.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    if (activeCategory === "fusion") return c.fusion;
    return true;
  });

  function playChannel(idx: number) {
    const ch = filtered[idx];
    if (!ch) return;
    setCurrentIdx(idx);
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
            }
          })
          .catch(() => setPlayerState("error"));
      });
    }
  }

  function next() {
    const next = (currentIdx + 1) % Math.max(filtered.length, 1);
    playChannel(next);
  }

  function prev() {
    const prev = (currentIdx - 1 + filtered.length) % Math.max(filtered.length, 1);
    playChannel(prev);
  }

  function stopPlayer() {
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.src = "";
    }
    setPlayerState("idle");
    setCurrentIdx(-1);
  }

  function showInfo() {
    setInfoVisible(true);
    if (infoTimer.current) clearTimeout(infoTimer.current);
    infoTimer.current = window.setTimeout(() => setInfoVisible(false), 4000);
  }

  const currentChannel = currentIdx >= 0 ? filtered[currentIdx] : null;

  return (
    <div style={{ background: "#000", minHeight: "100vh", color: "#fff", fontFamily: "Arial, sans-serif" }}>
      {/* Top Nav */}
      <div style={{
        background: "linear-gradient(135deg, #0a0a18 0%, #12122a 100%)",
        borderBottom: "2px solid #00d4ff",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        height: "52px",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{
            background: "linear-gradient(135deg, #00d4ff, #7b2cbf)",
            borderRadius: "6px",
            padding: "4px 12px",
            fontWeight: "bold",
            fontSize: "18px",
            letterSpacing: "2px",
          }}>MoJiTo</div>
          <span style={{ color: "#888", fontSize: "12px" }}>TV Streaming</span>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <NavButton active={view === "tv"} onClick={() => setView("tv")}>TV</NavButton>
          <NavButton active={view === "dashboard"} onClick={() => setView("dashboard")}>Dashboard</NavButton>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {stats && (
            <div style={{ fontSize: "12px", color: "#00d4ff" }}>
              <span style={{ color: "#0f0" }}>●</span> {stats.fusion_active} activos
            </div>
          )}
        </div>
      </div>

      {view === "tv" ? (
        <TVView
          channels={filtered}
          currentIdx={currentIdx}
          playerState={playerState}
          infoVisible={infoVisible}
          currentChannel={currentChannel}
          searchTerm={searchTerm}
          activeCategory={activeCategory}
          loading={loading}
          videoRef={videoRef}
          onPlay={playChannel}
          onNext={next}
          onPrev={prev}
          onStop={stopPlayer}
          onSearch={setSearchTerm}
          onCategory={setActiveCategory}
          onError={() => setPlayerState("error")}
        />
      ) : (
        <DashboardView stats={stats} channels={channels} />
      )}
    </div>
  );
}

function NavButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? "linear-gradient(90deg, #00d4ff22, #7b2cbf22)" : "transparent",
        border: active ? "1px solid #00d4ff55" : "1px solid #333",
        color: active ? "#00d4ff" : "#888",
        padding: "5px 16px",
        borderRadius: "4px",
        cursor: "pointer",
        fontSize: "13px",
        fontWeight: active ? "bold" : "normal",
        fontFamily: "Arial, sans-serif",
      }}
    >
      {children}
    </button>
  );
}

interface TVViewProps {
  channels: Channel[];
  currentIdx: number;
  playerState: "idle" | "playing" | "error";
  infoVisible: boolean;
  currentChannel: Channel | null;
  searchTerm: string;
  activeCategory: string;
  loading: boolean;
  videoRef: React.RefObject<HTMLVideoElement>;
  onPlay: (idx: number) => void;
  onNext: () => void;
  onPrev: () => void;
  onStop: () => void;
  onSearch: (v: string) => void;
  onCategory: (v: string) => void;
  onError: () => void;
}

function TVView({
  channels, currentIdx, playerState, infoVisible, currentChannel, searchTerm, activeCategory,
  loading, videoRef, onPlay, onNext, onPrev, onStop, onSearch, onCategory, onError,
}: TVViewProps) {
  return (
    <div style={{ display: "flex", height: "calc(100vh - 52px)", overflow: "hidden" }}>
      {/* Left Panel: Channel List */}
      <div style={{
        width: "280px",
        flexShrink: 0,
        background: "#080810",
        borderRight: "1px solid #1a1a30",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}>
        {/* Search */}
        <div style={{ padding: "10px", borderBottom: "1px solid #1a1a30" }}>
          <input
            type="text"
            placeholder="Buscar canal..."
            value={searchTerm}
            onChange={(e) => onSearch(e.target.value)}
            style={{
              width: "100%",
              background: "#12121a",
              border: "1px solid #2a2a4e",
              borderRadius: "4px",
              color: "#fff",
              padding: "7px 10px",
              fontSize: "13px",
              outline: "none",
              boxSizing: "border-box",
              fontFamily: "Arial, sans-serif",
            }}
          />
        </div>

        {/* Categories */}
        <div style={{ display: "flex", gap: "6px", padding: "8px 10px", borderBottom: "1px solid #1a1a30" }}>
          {[{ id: "all", label: "Todos" }, { id: "fusion", label: "Fusion" }].map((cat) => (
            <button
              key={cat.id}
              onClick={() => onCategory(cat.id)}
              style={{
                background: activeCategory === cat.id ? "#00d4ff22" : "#12121a",
                border: activeCategory === cat.id ? "1px solid #00d4ff" : "1px solid #2a2a4e",
                color: activeCategory === cat.id ? "#00d4ff" : "#888",
                padding: "4px 10px",
                borderRadius: "12px",
                cursor: "pointer",
                fontSize: "11px",
                fontFamily: "Arial, sans-serif",
              }}
            >
              {cat.label}
            </button>
          ))}
          <span style={{ marginLeft: "auto", color: "#444", fontSize: "11px", lineHeight: "26px" }}>
            {channels.length}
          </span>
        </div>

        {/* Channel List */}
        <div style={{ overflowY: "auto", flex: 1 }}>
          {loading && (
            <div style={{ textAlign: "center", padding: "40px 20px", color: "#444" }}>
              <div style={{ fontSize: "24px", marginBottom: "10px" }}>⟳</div>
              Cargando canales...
            </div>
          )}
          {!loading && channels.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px 20px", color: "#444", fontSize: "13px" }}>
              No hay canales disponibles.<br />Verifica la conexión al servidor MoJiTo.
            </div>
          )}
          {channels.map((ch, idx) => (
            <ChannelItem
              key={ch.cluster_id + idx}
              channel={ch}
              active={idx === currentIdx}
              onClick={() => onPlay(idx)}
            />
          ))}
        </div>

        {/* Controls */}
        <div style={{ borderTop: "1px solid #1a1a30", padding: "10px", display: "flex", gap: "6px", justifyContent: "center" }}>
          <ControlBtn onClick={onPrev} title="Anterior">◀</ControlBtn>
          <ControlBtn onClick={onStop} title="Detener" danger>■</ControlBtn>
          <ControlBtn onClick={onNext} title="Siguiente">▶</ControlBtn>
        </div>
      </div>

      {/* Right Panel: Player */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "#000", position: "relative", overflow: "hidden" }}>
        {/* Video */}
        <div style={{ flex: 1, background: "#000", position: "relative" }}>
          <video
            ref={videoRef}
            controls
            playsInline
            onError={onError}
            style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
          />

          {/* Idle overlay */}
          {playerState === "idle" && (
            <div style={{
              position: "absolute", inset: 0, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              background: "radial-gradient(ellipse at center, #0a0a20 0%, #000 100%)",
            }}>
              <div style={{
                background: "linear-gradient(135deg, #00d4ff, #7b2cbf)",
                borderRadius: "8px",
                padding: "6px 20px",
                fontWeight: "bold",
                fontSize: "32px",
                letterSpacing: "3px",
                marginBottom: "20px",
              }}>MoJiTo</div>
              <div style={{ color: "#444", fontSize: "14px" }}>Selecciona un canal para comenzar</div>
              <div style={{ marginTop: "30px", display: "flex", gap: "20px" }}>
                <KeyHint keys={["▲▼◀▶"]} label="Navegar" />
                <KeyHint keys={["ENTER"]} label="Reproducir" />
                <KeyHint keys={["ESC"]} label="Detener" />
              </div>
            </div>
          )}

          {/* Error overlay */}
          {playerState === "error" && (
            <div style={{
              position: "absolute", inset: 0, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              background: "rgba(0,0,0,0.85)",
            }}>
              <div style={{ fontSize: "36px", marginBottom: "12px" }}>⚠</div>
              <div style={{ color: "#ff4444", fontSize: "16px", marginBottom: "8px" }}>Stream no disponible</div>
              <div style={{ color: "#666", fontSize: "13px", marginBottom: "20px" }}>El canal puede estar offline temporalmente</div>
              <div style={{ display: "flex", gap: "10px" }}>
                <ActionBtn onClick={onNext}>Siguiente canal ▶</ActionBtn>
                <ActionBtn onClick={onStop} secondary>Detener</ActionBtn>
              </div>
            </div>
          )}

          {/* Info overlay */}
          {infoVisible && currentChannel && (
            <div style={{
              position: "absolute", bottom: "20px", left: "20px", right: "20px",
              background: "rgba(0,0,0,0.85)",
              border: "1px solid #00d4ff33",
              borderRadius: "8px", padding: "12px 16px",
              backdropFilter: "blur(4px)",
              transition: "opacity 0.3s",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ color: "#00d4ff", fontSize: "11px", marginBottom: "4px", letterSpacing: "1px" }}>
                    EN VIVO
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: "bold" }}>{currentChannel.name}</div>
                  <div style={{ color: "#888", fontSize: "12px", marginTop: "4px" }}>
                    {currentChannel.streams} streams · FUSION activa
                  </div>
                </div>
                <div style={{ color: "#444", fontSize: "12px" }}>
                  Canal {channels.indexOf(currentChannel) + 1} / {channels.length}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ChannelItem({ channel, active, onClick }: { channel: Channel; active: boolean; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: "10px 12px",
        cursor: "pointer",
        borderBottom: "1px solid #0f0f1a",
        background: active ? "linear-gradient(90deg, #00d4ff15, #7b2cbf15)" : "transparent",
        borderLeft: active ? "3px solid #00d4ff" : "3px solid transparent",
        transition: "background 0.15s",
        userSelect: "none",
      }}
    >
      <div style={{
        fontSize: "13px",
        fontWeight: active ? "bold" : "normal",
        color: active ? "#fff" : "#ccc",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}>
        {channel.name}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
        <span style={{ fontSize: "9px", color: "#0f0" }}>● FUSION</span>
        <span style={{ fontSize: "10px", color: "#555" }}>{channel.streams} streams</span>
      </div>
    </div>
  );
}

function ControlBtn({ onClick, title, children, danger }: { onClick: () => void; title?: string; children: React.ReactNode; danger?: boolean }) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        background: danger ? "#200a0a" : "#12121a",
        border: danger ? "1px solid #ff444433" : "1px solid #2a2a4e",
        color: danger ? "#ff6666" : "#aaa",
        width: "40px", height: "32px",
        borderRadius: "4px",
        cursor: "pointer",
        fontSize: "14px",
        fontFamily: "Arial, sans-serif",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {children}
    </button>
  );
}

function ActionBtn({ onClick, children, secondary }: { onClick: () => void; children: React.ReactNode; secondary?: boolean }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: secondary ? "#1a1a2e" : "linear-gradient(90deg, #00d4ff, #7b2cbf)",
        border: secondary ? "1px solid #00d4ff" : "none",
        color: "#fff",
        padding: "8px 18px",
        borderRadius: "5px",
        cursor: "pointer",
        fontSize: "13px",
        fontFamily: "Arial, sans-serif",
        fontWeight: "bold",
      }}
    >
      {children}
    </button>
  );
}

function KeyHint({ keys, label }: { keys: string[]; label: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ display: "flex", gap: "4px", justifyContent: "center", marginBottom: "6px" }}>
        {keys.map((k) => (
          <span key={k} style={{
            background: "#1a1a30",
            border: "1px solid #2a2a5e",
            borderRadius: "3px",
            padding: "2px 8px",
            fontSize: "11px",
            color: "#00d4ff",
          }}>{k}</span>
        ))}
      </div>
      <div style={{ fontSize: "11px", color: "#444" }}>{label}</div>
    </div>
  );
}

function DashboardView({ stats, channels }: { stats: Stats | null; channels: Channel[] }) {
  const fusionPct = stats && stats.clusters > 0
    ? Math.min(100, Math.round((stats.fusion_active / stats.clusters) * 100))
    : 0;

  return (
    <div style={{ overflowY: "auto", height: "calc(100vh - 52px)", padding: "24px", background: "#0a0a0f" }}>
      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: "28px" }}>
          <h2 style={{ fontSize: "22px", fontWeight: "bold", color: "#fff", margin: 0 }}>
            Sistema MoJiTo
          </h2>
          <p style={{ color: "#666", fontSize: "13px", marginTop: "6px" }}>
            Reconstruccion Adaptativa de Streams (Fusion Engine)
          </p>
        </div>

        {/* Stats */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", marginBottom: "28px" }}>
          <StatCard label="Streams Totales" value={stats?.streams ?? "–"} color="#00d4ff" desc="Todos los streams en la base de datos" />
          <StatCard label="Clusters" value={stats?.clusters ?? "–"} color="#7b2cbf" desc="Canales reales agrupados" />
          <StatCard label="En Clusters" value={stats?.clustered ?? "–"} color="#fff" desc="Streams agrupados logicamente" />
          <StatCard
            label="Fusion Activa"
            value={stats?.fusion_active ?? "–"}
            color="#ff8800"
            desc={"Monitoreados simultaneamente · " + fusionPct + "% cobertura"}
            progress={fusionPct}
          />
        </div>

        {/* Explain */}
        <div style={{
          background: "#12121a",
          border: "1px solid #2a2a4e",
          borderRadius: "10px",
          padding: "20px",
          marginBottom: "28px",
        }}>
          <h3 style={{ color: "#00d4ff", fontSize: "16px", marginBottom: "14px", marginTop: 0 }}>Como funciona MoJiTo</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "20px" }}>
            <ConceptCard title="Stream" icon="🌊" desc="Una URL que reproduce video en vivo. Cada canal puede tener docenas de links diferentes." />
            <ConceptCard title="Cluster" icon="📦" desc='Un "canal real". Todos los URLs que reproducen el mismo contenido se agrupan en un cluster.' />
            <ConceptCard title="Fusion" icon="⚡" desc="El motor que monitorea todos los streams en tiempo real y siempre sirve el mejor disponible." />
          </div>
        </div>

        {/* Top Channels */}
        <div>
          <h3 style={{ color: "#fff", fontSize: "16px", marginBottom: "14px" }}>Canales disponibles ({channels.length})</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            {channels.slice(0, 30).map((ch, i) => (
              <div key={i} style={{
                background: "#12121a",
                border: "1px solid #2a2a4e",
                borderRadius: "6px",
                padding: "10px 14px",
                minWidth: "180px",
                flex: "1 1 180px",
                maxWidth: "240px",
              }}>
                <div style={{ fontSize: "13px", fontWeight: "bold", color: "#fff", marginBottom: "6px",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {ch.name}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "10px", color: "#0f0" }}>● FUSION</span>
                  <span style={{ fontSize: "10px", color: "#555" }}>{ch.streams} streams</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color, desc, progress }: {
  label: string; value: number | string; color: string; desc: string; progress?: number;
}) {
  return (
    <div style={{
      background: "#12121a",
      border: "1px solid #2a2a4e",
      borderRadius: "10px",
      padding: "20px",
      flex: "1 1 200px",
      minWidth: "180px",
    }}>
      <div style={{ color: "#888", fontSize: "12px", marginBottom: "8px" }}>{label}</div>
      <div style={{ fontSize: "34px", fontWeight: "bold", color, marginBottom: "6px" }}>{value}</div>
      <div style={{ color: "#555", fontSize: "11px" }}>{desc}</div>
      {progress !== undefined && (
        <div style={{
          background: "#1a1a2e",
          borderRadius: "4px",
          height: "6px",
          overflow: "hidden",
          marginTop: "10px",
        }}>
          <div style={{
            background: "linear-gradient(90deg, #00d4ff, #7b2cbf)",
            height: "100%",
            width: progress + "%",
            borderRadius: "4px",
            transition: "width 0.5s",
          }} />
        </div>
      )}
    </div>
  );
}

function ConceptCard({ title, icon, desc }: { title: string; icon: string; desc: string }) {
  return (
    <div style={{ flex: "1 1 200px", minWidth: "180px" }}>
      <div style={{ fontSize: "20px", marginBottom: "6px" }}>{icon} {title}</div>
      <div style={{ color: "#888", fontSize: "13px", lineHeight: "1.5" }}>{desc}</div>
    </div>
  );
}

export default MojitoTV;
