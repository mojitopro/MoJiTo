#!/usr/bin/env python3
"""
MoJiTo Daemon Controller
On/Off toggle for automated pipeline
"""
import asyncio
import signal
import sys
import os
import time
import json
from pathlib import Path

PID_FILE = '/tmp/mojito_daemon.pid'
STATE_FILE = '/tmp/mojito_state.json'


class DaemonController:
    def __init__(self):
        self.running = False
        self.tasks = []
        self.config = {
            'enabled': False,
            'started_at': None,
            'stats': {}
        }
    
    def is_running(self) -> bool:
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                return True
            except:
                self.cleanup()
        return False
    
    def cleanup(self):
        for f in [PID_FILE, STATE_FILE]:
            if os.path.exists(f):
                os.remove(f)
    
    def start(self):
        if self.is_running():
            print("[Daemon] Already running")
            return
        
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        self.config['enabled'] = True
        self.config['started_at'] = int(time.time())
        self.save_state()
        
        print("[Daemon] Started")
        self.run_pipeline()
    
    def stop(self):
        if not self.is_running():
            print("[Daemon] Not running")
            return
        
        self.config['enabled'] = False
        self.save_state()
        self.cleanup()
        
        print("[Daemon] Stopped")
    
    def save_state(self):
        with open(STATE_FILE, 'w') as f:
            json.dump(self.config, f)
    
    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                self.config = json.load(f)
    
    def run_pipeline(self):
        from runtime.db import Database
        
        db = Database()
        
        print(f"[Daemon] Pipeline running... {time.strftime('%H:%M:%S')}")
        
        print("[1/5] Running clustering...")
        self._run_clustering(db)
        
        print("[2/5] Updating levels...")
        self._run_levels(db)
        
        print("[3/5] Analyzing priority clusters...")
        self._run_analysis(db)
        
        print("[4/5] Starting fusion...")
        self._run_fusion(db)
        
        print("[5/5] Final stats...")
        stats = db.get_stats()
        self.config['stats'] = stats
        self.save_state()
        
        print(f"[Daemon] Complete: {stats}")
        
        if self.config['enabled']:
            asyncio.get_event_loop().call_later(300, self.run_pipeline)
    
    def _run_clustering(self, db):
        from services.cluster_batch import run_full_clustering
        asyncio.run(run_full_clustering(db))
    
    def _run_levels(self, db):
        from services.level_manager import LevelManager
        lm = LevelManager(db)
        lm.update_all_levels()
    
    def _run_analysis(self, db):
        from services.analyze_prioritized import PrioritizedAnalyzer
        
        analyzer = PrioritizedAnalyzer(db)
        asyncio.run(analyzer.start())
        
        try:
            result = asyncio.run(analyzer.analyze_by_priority(max_clusters=20))
            self.config['stats']['analysis'] = result
        finally:
            asyncio.run(analyzer.stop())
    
    def _run_fusion(self, db):
        from services.fusion_runner import FusionRunner
        
        runner = FusionRunner(db)
        asyncio.run(runner.start())
        
        try:
            result = asyncio.run(runner.run_monitoring_cycle())
            self.config['stats']['fusion'] = result
        finally:
            asyncio.run(runner.stop())
    
    def status(self):
        self.load_state()
        
        if self.is_running():
            print(f"[Daemon] RUNNING")
            print(f"  Started: {time.ctime(self.config.get('started_at', 0))}")
        else:
            print(f"[Daemon] STOPPED")
        
        from runtime.db import Database
        db = Database()
        stats = db.get_stats()
        print(f"\n[DB Stats]")
        print(f"  Streams: {stats.get('streams', 0)}")
        print(f"  Clusters: {stats.get('clusters', 0)}")
        print(f"  Metrics: {stats.get('metrics', 0)}")


def main():
    daemon = DaemonController()
    
    def signal_handler(sig, frame):
        print("\n[Daemon] Shutting down...")
        daemon.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'start':
            daemon.start()
        elif cmd == 'stop':
            daemon.stop()
        elif cmd == 'restart':
            daemon.stop()
            time.sleep(1)
            daemon.start()
        elif cmd == 'status':
            daemon.status()
        else:
            print(f"Usage: {sys.argv[0]} [start|stop|restart|status]")
    else:
        daemon.status()


if __name__ == '__main__':
    main()