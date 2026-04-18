#!/usr/bin/env python3
"""
Scheduler Service
Orchestrates all services in sequence
"""
import asyncio
import time
import signal
import sys
from typing import Optional

from runtime.db import Database
from services.scanner import ScannerService
from services.analyzer import AnalyzerService
from services.clusterer import ClustererService
from services.fusion_engine import FusionEngine


class Scheduler:
    def __init__(self):
        self.db = Database()
        self.scanner = ScannerService(self.db)
        self.analyzer = AnalyzerService(self.db)
        self.clusterer = ClustererService(self.db)
        self.fusion_engine = FusionEngine(self.db)
        
        self.running = False
        self.intervals = {
            'scan': 300,
            'analyze': 600,
            'cluster': 900,
            'fusion': 60
        }
        self.tasks: list[asyncio.Task] = []
    
    async def start(self):
        self.running = True
        
        await self.scanner.start()
        await self.analyzer.start()
        await self.fusion_engine.start()
        
        print("[Scheduler] Started all services")
    
    async def stop(self):
        self.running = False
        
        for task in self.tasks:
            task.cancel()
        
        await self.scanner.stop()
        await self.analyzer.stop()
        await self.fusion_engine.stop()
        
        print("[Scheduler] Stopped all services")
    
    async def run_ingest(self, path: str) -> int:
        if path.endswith('.m3u'):
            return await self.scanner.ingest_m3u(path)
        elif path.endswith('.json'):
            return await self.scanner.ingest_json(path)
        return 0
    
    async def run_scan(self) -> dict:
        print("[Scheduler] Running scan...")
        result = await self.scanner.scan_all(batch_size=100)
        print(f"[Scheduler] Scan result: {result}")
        return result
    
    async def run_analyze(self) -> dict:
        print("[Scheduler] Running analyze...")
        result = await self.analyzer.analyze_all(batch_size=20)
        print(f"[Scheduler] Analyze result: {result}")
        return result
    
    async def run_cluster(self) -> dict:
        print("[Scheduler] Running cluster...")
        result = await self.clusterer.cluster_all()
        print(f"[Scheduler] Cluster result: {result}")
        return result
    
    async def run_full_pipeline(self, m3u_path: str = None) -> None:
        print("[Scheduler] Running full pipeline...")
        
        if m3u_path:
            count = await self.run_ingest(m3u_path)
            print(f"[Scheduler] Ingested {count} streams")
        
        await self.run_scan()
        await self.run_analyze()
        await self.run_cluster()
        
        for cluster in self.db.get_all_clusters():
            self.fusion_engine.init_cluster(
                cluster.cluster_id,
                [cs.stream_url for cs in self.db.get_cluster_streams(cluster.cluster_id)]
            )
            self.fusion_engine.start_monitoring(cluster.cluster_id)
        
        stats = self.db.get_stats()
        print(f"[Scheduler] Pipeline complete: {stats}")
    
    async def loop(self):
        while self.running:
            try:
                await self.run_scan()
                await asyncio.sleep(self.intervals['scan'])
                
                await self.run_analyze()
                await asyncio.sleep(self.intervals['analyze'])
                
                await self.run_cluster()
                await asyncio.sleep(self.intervals['cluster'])
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Scheduler] Error: {e}")
                await asyncio.sleep(60)
    
    def get_stats(self) -> dict:
        db_stats = self.db.get_stats()
        
        fusion_stats = {}
        for cluster in self.db.get_all_clusters():
            fusion_stats[cluster.cluster_id] = self.fusion_engine.get_fusion_stats(cluster.cluster_id)
        
        return {
            'database': db_stats,
            'fusion': fusion_stats,
            'services': {
                'scanner': 'running' if self.scanner.running else 'stopped',
                'analyzer': 'running' if self.analyzer.running else 'stopped',
                'fusion_engine': 'running' if self.fusion_engine.running else 'stopped'
            }
        }


async def main():
    scheduler = Scheduler()
    
    def signal_handler(sig):
        print("\n[Scheduler] Shutting down...")
        asyncio.create_task(scheduler.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s))
    
    await scheduler.start()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            await scheduler.run_full_pipeline(sys.argv[2] if len(sys.argv) > 2 else None)
        elif sys.argv[1] == '--scan':
            await scheduler.run_scan()
        elif sys.argv[1] == '--analyze':
            await scheduler.run_analyze()
        elif sys.argv[1] == '--cluster':
            await scheduler.run_cluster()
    else:
        task = asyncio.create_task(scheduler.loop())
        await asyncio.Event().wait()
    
    stats = scheduler.get_stats()
    print(f"\n[Scheduler] Final stats: {stats}")


if __name__ == '__main__':
    asyncio.run(main())