#!/usr/bin/env python3
"""
Fusion Runner - Fase 5
Fusion with strict concurrency limits
"""
import asyncio
import aiohttp
import time
import json
from typing import Optional
from collections import deque

from runtime.db import Database, FusionState, StreamMetrics
from runtime.utils import calculate_stream_score
from services.level_manager import LevelManager


MAX_ACTIVE_CLUSTERS = 50
CHECK_INTERVAL = 10
BUFFER_SECONDS = 15


class FusionRunner:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.active_tasks: dict[str, asyncio.Task] = {}
        self.fusion_states: dict[str, dict] = {}
        self.buffers: dict[str, deque] = {}
    
    async def start(self):
        self.session = aiohttp.ClientSession()
        self.running = True
        
        priority = self._get_top_clusters()
        
        for cluster_id in priority[:MAX_ACTIVE_CLUSTERS]:
            self._init_cluster(cluster_id)
        
        print(f"[FusionRunner] Started with {len(self.fusion_states)} active clusters")
    
    async def stop(self):
        self.running = False
        
        for task in self.active_tasks.values():
            task.cancel()
        
        if self.session:
            await self.session.close()
        
        print("[FusionRunner] Stopped")
    
    def _get_top_clusters(self) -> list[str]:
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT c.cluster_id,
                   COALESCE(f.switch_count, 0) as switches,
                   (SELECT COUNT(*) FROM cluster_streams WHERE cluster_id = c.cluster_id) as stream_count
            FROM clusters c
            LEFT JOIN fusion_state f ON f.cluster_id = c.cluster_id
            ORDER BY switches DESC, stream_count DESC
            LIMIT ?
        """, (MAX_ACTIVE_CLUSTERS * 2,))
        
        clusters = []
        for row in cursor.fetchall():
            clusters.append(row[0])
        
        return clusters
    
    def _init_cluster(self, cluster_id: str):
        if cluster_id in self.fusion_states:
            return
        
        streams = self.db.get_cluster_streams(cluster_id)
        
        if not streams:
            return
        
        active = streams[0].stream_url
        backups = [s.stream_url for s in streams[1:6]]
        
        self.fusion_states[cluster_id] = {
            'active': active,
            'backups': backups,
            'switch_count': 0,
            'last_switch': 0
        }
        
        self.buffers[cluster_id] = deque(maxlen=BUFFER_SECONDS)
        
        fusion_state = FusionState(
            cluster_id=cluster_id,
            active_stream=active,
            backup_streams=json.dumps(backups),
            buffer_ms=BUFFER_SECONDS * 1000
        )
        self.db.insert_fusion_state(fusion_state)
    
    async def monitor_stream(self, url: str) -> dict:
        result = {'url': url, 'online': False, 'latency': 999, 'stable': True}
        
        if not self.session:
            return result
        
        try:
            start = time.time()
            timeout = aiohttp.ClientTimeout(total=8)
            
            async with self.session.head(url, timeout=timeout) as resp:
                result['latency'] = (time.time() - start) * 1000
                
                if resp.status in [200, 206]:
                    result['online'] = True
                
                ct = resp.headers.get('Content-Type', '')
                if 'video' not in ct and 'application' not in ct:
                    result['stable'] = False
        
        except asyncio.TimeoutError:
            result['stable'] = False
        except Exception as e:
            result['error'] = str(e)[:20]
            result['stable'] = False
        
        return result
    
    async def evaluate_stream(self, url: str) -> float:
        metrics = self.db.get_stream_metrics(url)
        
        if not metrics:
            return 50.0
        
        score = calculate_stream_score(
            metrics.startup_time * 1000,
            metrics.avg_frame_delta,
            metrics.freeze_duration,
            metrics.black_ratio,
            metrics.motion_score,
            metrics.stability
        )
        
        return score
    
    async def check_cluster(self, cluster_id: str) -> dict:
        if cluster_id not in self.fusion_states:
            return {'status': 'not_active'}
        
        state = self.fusion_states[cluster_id]
        
        current_result = await self.monitor_stream(state['active'])
        
        monitor = {
            'active': state['active'],
            'online': current_result['online'],
            'latency': current_result['latency'],
            'stable': current_result['stable']
        }
        
        if current_result['stable'] and current_result['online']:
            monitor['status'] = 'ok'
            return monitor
        
        for backup_url in state['backups']:
            result = await self.monitor_stream(backup_url)
            
            if result['stable'] and result['online']:
                old_active = state['active']
                state['active'] = backup_url
                state['backups'].remove(backup_url)
                state['backups'].append(old_active)
                state['switch_count'] += 1
                state['last_switch'] = int(time.time())
                
                self.db.update_fusion_active(cluster_id, backup_url)
                
                monitor['status'] = 'switched'
                monitor['new_active'] = backup_url
                return monitor
        
        monitor['status'] = 'failed'
        return monitor
    
    async def monitor_loop(self, cluster_id: str):
        while self.running and cluster_id in self.fusion_states:
            try:
                await self.check_cluster(cluster_id)
                await asyncio.sleep(CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(CHECK_INTERVAL)
    
    def start_cluster(self, cluster_id: str):
        if cluster_id in self.active_tasks:
            return
        
        self._init_cluster(cluster_id)
        
        task = asyncio.create_task(self.monitor_loop(cluster_id))
        self.active_tasks[cluster_id] = task
    
    def stop_cluster(self, cluster_id: str):
        if cluster_id in self.active_tasks:
            self.active_tasks[cluster_id].cancel()
            del self.active_tasks[cluster_id]
    
    def get_active_stream(self, cluster_id: str) -> Optional[str]:
        if cluster_id in self.fusion_states:
            return self.fusion_states[cluster_id]['active']
        return None
    
    def get_output_m3u8(self, cluster_id: str) -> str:
        if cluster_id not in self.fusion_states:
            return ''
        
        state = self.fusion_states[cluster_id]
        
        lines = ['#EXTM3U']
        
        cluster = self.db.get_cluster(cluster_id)
        name = cluster.canonical_name if cluster else cluster_id
        
        lines.append(f'#EXTINF:-1 tvg-name="{name}",{name}')
        lines.append(state['active'])
        
        for backup in state['backups'][:3]:
            lines.append(backup)
        
        return '\n'.join(lines)
    
    async def run_monitoring_cycle(self):
        for cluster_id in list(self.fusion_states.keys()):
            if len(self.active_tasks) >= MAX_ACTIVE_CLUSTERS:
                break
            
            if cluster_id not in self.active_tasks:
                self.start_cluster(cluster_id)
        
        result = {
            'active_monitors': len(self.active_tasks),
            'clusters': len(self.fusion_states)
        }
        
        return result
    
    def get_stats(self) -> dict:
        return {
            'active_monitors': len(self.active_tasks),
            'active_clusters': len(self.fusion_states),
            'max_allowed': MAX_ACTIVE_CLUSTERS
        }


async def main():
    import sys
    
    runner = FusionRunner()
    await runner.start()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--status':
            print(f"[Status]: {runner.get_stats()}")
        elif sys.argv[1].startswith('--cluster='):
            cluster_id = sys.argv[1].split('=')[1]
            m3u8 = runner.get_output_m3u8(cluster_id)
            print(f"\n{m3u8}")
    else:
        await runner.run_monitoring_cycle()
        print(f"[Status]: {runner.get_stats()}")
    
    await runner.stop()


if __name__ == '__main__':
    asyncio.run(main())