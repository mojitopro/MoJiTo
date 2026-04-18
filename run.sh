#!/bin/bash
# MoJiTo Control Script
# Usage: ./run.sh [start|stop|restart|status|pipeline]

cd "$(dirname "$0")"

case "$1" in
    start)
        echo "[MoJiTo] Starting daemon..."
        nohup python3 services/daemon.py start > /tmp/mojito.log 2>&1 &
        echo "Started. Use './run.sh status' to check."
        ;;
    stop)
        echo "[MoJiTo] Stopping daemon..."
        python3 services/daemon.py stop
        ;;
    restart)
        echo "[MoJiTo] Restarting..."
        python3 services/daemon.py stop
        sleep 2
        nohup python3 services/daemon.py start > /tmp/mojito.log 2>&1 &
        echo "Restarted."
        ;;
    status)
        python3 services/daemon.py status
        ;;
    pipeline)
        echo "[MoJiTo] Running single pipeline..."
        python3 -c "
import asyncio
from services.cluster_batch import run_full_clustering
from services.level_manager import LevelManager
from services.analyze_prioritized import PrioritizedAnalyzer
from services.fusion_runner import FusionRunner
from runtime.db import Database

async def run():
    db = Database()
    print('1. Clustering...')
    await run_full_clustering(db)
    print('2. Levels...')
    lm = LevelManager(db)
    lm.update_all_levels()
    print('3. Analysis...')
    a = PrioritizedAnalyzer()
    await a.start()
    try:
        await a.analyze_by_priority(max_clusters=10)
    finally:
        await a.stop()
    print('4. Fusion...')
    f = FusionRunner(db)
    await f.start()
    try:
        await f.run_monitoring_cycle()
    finally:
        await f.stop()
    print('Done!')

asyncio.run(run())
"
        ;;
    ingest)
        shift
        if [ -z "$1" ]; then
            echo "[MoJiTo] Ingesting all JSON/M3U files..."
            python3 services/ingest_massive.py --all
        else
            echo "[MoJiTo] Ingesting $1..."
            python3 services/ingest_massive.py "$1"
        fi
        ;;
    add)
        shift
        if [ -z "$1" ]; then
            echo "Usage: $0 add <file.json>"
        else
            echo "[MoJiTo] Adding streams from $1..."
            python3 services/ingest_massive.py "$1"
            echo "Run './run.sh pipeline' to process new streams"
        fi
        ;;
    *)
        echo "MoJiTo Control"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|pipeline|ingest}"
        echo ""
        echo "Commands:"
        echo "  start    - Start daemon (auto-runs every 5 min)"
        echo "  stop    - Stop daemon"
        echo "  restart - Restart daemon"
        echo "  status  - Show system status"
        echo "  pipeline - Run one-time pipeline"
        echo "  ingest  - Ingest all JSON/M3U files"
        echo "  add     - Add streams from specific file"
        ;;
esac