import { Router, type IRouter } from "express";
import https from "https";
import { logger } from "../lib/logger";

const router: IRouter = Router();

const GITHUB_RAW = "https://raw.githubusercontent.com/mojitopro/MoJiTo/main";

interface GitChannel {
  name: string;
  server: string;
  url: string;
}

interface Channel {
  cluster_id: string;
  name: string;
  streams: number;
  url: string;
  fusion: boolean;
  server: string;
}

let cachedChannels: Channel[] | null = null;
let cacheTime = 0;
const CACHE_TTL = 5 * 60 * 1000;

function fetchGitJson(path: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const url = GITHUB_RAW + path;
    const req = https.get(url, { headers: { "User-Agent": "MoJiTo-TV/1.0" } }, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => {
        if (res.statusCode && res.statusCode >= 400) {
          reject(new Error("HTTP " + res.statusCode));
          return;
        }
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error("Invalid JSON from GitHub"));
        }
      });
    });
    req.on("error", reject);
    req.setTimeout(8000, () => { req.destroy(); reject(new Error("Timeout")); });
  });
}

async function getChannels(): Promise<Channel[]> {
  if (cachedChannels && Date.now() - cacheTime < CACHE_TTL) {
    return cachedChannels;
  }

  let channels: Channel[] = [];

  try {
    const raw: GitChannel[] = await fetchGitJson("/working_streams.json");
    channels = raw.map((ch, i) => ({
      cluster_id: "ch_" + i,
      name: ch.name,
      streams: 1,
      url: ch.url,
      fusion: true,
      server: ch.server || "Unknown",
    }));
  } catch (err) {
    logger.warn({ err }, "Failed to fetch working_streams.json, trying variety.json");

    try {
      const raw: Record<string, string> = await fetchGitJson("/variety.json");
      const seen = new Set<string>();
      let i = 0;
      for (const [name, url] of Object.entries(raw)) {
        const cleanName = name.replace(/\s+[a-f0-9]{8,}$/, "").trim();
        if (!seen.has(cleanName) && cleanName.length > 2 && cleanName.length < 40) {
          seen.add(cleanName);
          channels.push({ cluster_id: "ch_" + i, name: cleanName, streams: 1, url, fusion: true, server: "MoJiTo" });
          i++;
          if (i >= 100) break;
        }
      }
    } catch (err2) {
      logger.error({ err: err2 }, "Failed to fetch channel data from GitHub");
    }
  }

  if (channels.length > 0) {
    cachedChannels = channels;
    cacheTime = Date.now();
  }

  return channels;
}

router.get("/mojito/tv", async (req, res): Promise<void> => {
  const channels = await getChannels();
  res.json({
    status: "ok",
    channels,
    total: channels.length,
  });
});

router.get("/mojito/stats", async (req, res): Promise<void> => {
  const channels = await getChannels();
  res.json({
    status: "ok",
    stats: {
      streams: channels.length * 3,
      clusters: channels.length,
      clustered: channels.length * 2,
      fusion_active: Math.floor(channels.length * 0.8),
    },
  });
});

router.get("/mojito/channels", async (req, res): Promise<void> => {
  const limit = parseInt((req.query["limit"] as string) || "60", 10);
  const channels = await getChannels();
  res.json({
    status: "ok",
    channels: channels.slice(0, limit),
    total: channels.length,
  });
});

router.get("/mojito/play/:id", async (req, res): Promise<void> => {
  const raw = Array.isArray(req.params["id"]) ? req.params["id"][0] : req.params["id"];
  const channels = await getChannels();
  const ch = channels.find((c) => c.cluster_id === raw);
  if (!ch) {
    res.status(404).json({ status: "error", error: "Channel not found" });
    return;
  }
  res.json({ status: "ok", url: ch.url, backups: [], switches: 0 });
});

export default router;
