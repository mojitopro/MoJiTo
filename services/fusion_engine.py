#!/usr/bin/env python3
"""
Fusion Engine Service
Maintains stream stability using multiple sources with failover
"""
import asyncio
import aiohttp
import time
import json
from typing import Optional
from collections import deque

from runtime.db import Database, FusionState, StreamMetrics
from runtime.utils import calculate_stream_score


class FusionEngine:
    def __init__(
        self, 
        db: Optional[Database] = None,
        buffer_seconds: int = 20,
        check_interval: float = 5.0
    ):
        self.db = db or Database()
        self.buffer_seconds = buffer_seconds
        self.check_interval = check_interval
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.active_monitors: dict[str, asyncio.Task] = {}
        self.fusion_states: dict[str, dict] = {}
        self.buffers: dict[str, deque] = {}
    
    async def start(self):
        self.session = aiohttp.ClientSession()
        self.running = True
        
        states = self._load_fusion_states()
        for cluster_id, state in states.items():
            self.fusion_states[cluster_id] = state
            self.buffers[cluster_id] = deque(maxlen=self.buffer_seconds)
        
        print(f"[FusionEngine] Started with {len(states)} clusters")
    
    async def stop(self):
        self.running = False
        
        for task in self.active_monitors.values():
            task.cancel()
        
        if self.session:
            await self.session.close()
        
        print("[FusionEngine] Stopped")
    
    def _load_fusion_states(self) -> dict:
        states = {}
        
        for cluster in self.db.get_all_clusters():
            state = self.db.get_fusion_state(cluster.cluster_id)
            if state:
                states[cluster.cluster_id] = {
                    'active': state.active_stream,
                    'backups': json.loads(state.backup_streams) if state.backup_streams != '[]' else [],
                    'switch_count': state.switch_count,
                    'last_switch': state.last_switch,
                    'buffer_ms': state.buffer_ms
                }
            
            cluster_streams = self.db.get_cluster_streams(cluster.cluster_id)
            
            if cluster_streams:
                primary = [cs for cs in cluster_streams if cs.is_primary]
                backups = [cs for cs in cluster_streams if not cs.is_primary]
                
                if primary and cluster.cluster_id not in states:
                    first = primary[0]
                    states[cluster.cluster_id] = {
                        'active': first.stream_url,
                        'backups': [cs.stream_url for cs in backups],
                        'switch_count': 0,
                        'last_switch': 0,
                        'buffer_ms': self.buffer_seconds * 1000
                    }
                
                elif cluster.cluster_id in states:
                    states[cluster.cluster_id]['backups'].extend([
                        cs.stream_url for cs in backup 
                        if cs.stream_url not in states[cluster.cluster_id]['backups']
                    ])
        
        return states
    
    def init_cluster(self, cluster_id: str, urls: list[str]) -> None:
        if cluster_id not in self.fusion_states:
            self.fusion_states[cluster_id] = {
                'active': urls[0] if urls else None,
                'backups': urls[1:] if len(urls) > 1 else [],
                'switch_count': 0,
                'last_switch': 0,
                'buffer_ms': self.buffer_seconds * 1000
            }
            self.buffers[cluster_id] = deque(maxlen=self.buffer_seconds)
            
            self._save_fusion_state(cluster_id)
    
    def _save_fusion_state(self, cluster_id: str) -> None:
        if cluster_id not in self.fusion_states:
            return
        
        state = self.fusion_states[cluster_id]
        
        fs = FusionState(
            cluster_id=cluster_id,
            active_stream=state['active'],
            backup_streams=json.dumps(state['backups']),
            switch_count=state['switch_count'],
            last_switch=state['last_switch'],
            buffer_ms=state['buffer_ms']
        )
        
        self.db.insert_fusion_state(fs)
    
    def add_backup(self, cluster_id: str, url: str) -> None:
        if cluster_id not in self.fusion_states:
            return
        
        if url not in self.fusion_states[cluster_id]['backups']:
            self.fusion_states[cluster_id]['backups'].append(url)
            self._save_fusion_state(cluster_id)
    
    async def monitor_stream(self, cluster_id: str, url: str) -> dict:
        result = {
            'url': url,
            'online': False,
            'latency': 999,
            'freeze_count': 0,
            'last_check': 0
        }
        
        if not self.session:
            return result
        
        try:
            start = time.time()
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with self.session.head(url, timeout=timeout) as resp:
                result['latency'] = (time.time() - start) * 1000
                result['last_check'] = int(time.time())
                
                if resp.status in [200, 206]:
                    result['online'] = True
            
            metrics = self.db.get_stream_metrics(url)
            if metrics:
                result['freeze_count'] = metrics.freeze_count
                result['stability'] = metrics.stability
                result['motion_score'] = metrics.motion_score
        
        except Exception as e:
            result['error'] = str(e)[:30]
        
        return result
    
    async def select_best_stream(self, cluster_id: str) -> Optional[str]:
        if cluster_id not in self.fusion_states:
            return None
        
        state = self.fusion_states[cluster_id]
        candidates = []
        
        if state['active']:
            candidates.append(state['active'])
        
        candidates.extend(state['backups'])
        
        if not candidates:
            return None
        
        best_url = None
        best_score = -1
        
        for url in candidates:
            monitor_result = await self.monitor_stream(cluster_id, url)
            
            score = self._calculate_monitor_score(monitor_result)
            
            if score > best_score:
                best_score = score
                best_url = url
        
        return best_url
    
    def _calculate_monitor_score(self, result: dict) -> float:
        score = 0
        
        if result.get('online'):
            score += 50
        
        latency = result.get('latency', 999)
        if latency < 100:
            score += 20
        elif latency < 500:
            score += 10
        
        freeze_count = result.get('freeze_count', 0)
        if freeze_count == 0:
            score += 15
        elif freeze_count < 3:
            score += 5
        
        stability = result.get('stability', 0)
        score += stability * 10
        
        motion_score = result.get('motion_score', 0)
        score += motion_score * 5
        
        return score
    
    async def switch_stream(self, cluster_id: str, new_url: str) -> bool:
        if cluster_id not in self.fusion_states:
            return False
        
        old_url = self.fusion_states[cluster_id]['active']
        
        self.fusion_states[cluster_id]['active'] = new_url
        
        if old_url and old_url not in self.fusion_states[cluster_id]['backups']:
            self.fusion_states[cluster_id]['backups'].append(old_url)
        
        if new_url in self.fusion_states[cluster_id]['backups']:
            self.fusion_states[cluster_id]['backups'].remove(new_url)
        
        self.fusion_states[cluster_id]['switch_count'] += 1
        self.fusion_states[cluster_id]['last_switch'] = int(time.time())
        
        self._save_fusion_state(cluster_id)
        
        print(f"[FusionEngine] Switched cluster {cluster_id}: {old_url} -> {new_url}")
        
        return True
    
    async def failover(self, cluster_id: str) -> bool:
        if cluster_id not in self.fusion_states:
            return False
        
        state = self.fusion_states[cluster_id]
        
        if not state['backups']:
            return False
        
        best_backup = None
        best_score = -1
        
        for url in state['backups']:
            result = await self.monitor_stream(cluster_id, url)
            score = self._calculate_monitor_score(result)
            
            if score > best_score:
                best_score = score
                best_backup = url
        
        if best_backup and best_score > 0:
            return await self.switch_stream(cluster_id, best_backup)
        
        return False
    
    async def auto_fusion_loop(self, cluster_id: str) -> None:
        while self.running and cluster_id in self.fusion_states:
            try:
                current = self.fusion_states[cluster_id]['active']
                
                result = await self.monitor_stream(cluster_id, current)
                score = self._calculate_monitor_score(result)
                
                if score < 30:
                    success = await self.failover(cluster_id)
                    if not success:
                        best = await self.select_best_stream(cluster_id)
                        if best and best != current:
                            await self.switch_stream(cluster_id, best)
                
                await asyncio.sleep(self.check_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[FusionEngine] Error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def start_monitoring(self, cluster_id: str) -> None:
        if cluster_id in self.active_monitors:
            return
        
        task = asyncio.create_task(self.auto_fusion_loop(cluster_id))
        self.active_monitors[cluster_id] = task
    
    def stop_monitoring(self, cluster_id: str) -> None:
        if cluster_id in self.active_monitors:
            self.active_monitors[cluster_id].cancel()
            del self.active_monitors[cluster_id]
    
    def get_active_stream(self, cluster_id: str) -> Optional[str]:
        if cluster_id in self.fusion_states:
            return self.fusion_states[cluster_id]['active']
        return None
    
    def get_fusion_stats(self, cluster_id: str) -> dict:
        if cluster_id not in self.fusion_states:
            return {}
        
        state = self.fusion_states[cluster_id]
        return {
            'active_stream': state['active'],
            'backup_count': len(state['backups']),
            'switch_count': state['switch_count'],
            'last_switch': state['last_switch'],
            'buffer_ms': state['buffer_ms']
        }


async def main():
    import sys
    
    engine = FusionEngine()
    await engine.start()
    
    if len(sys.argv) > 1:
        cluster_id = sys.argv[1]
        
        if len(sys.argv) > 2:
            urls = sys.argv[2].split(',')
            engine.init_cluster(cluster_id, urls)
        
        stream = await engine.select_best_stream(cluster_id)
        print(f"[FusionEngine] Best stream: {stream}")
    
    await engine.stop()


if __name__ == '__main__':
    asyncio.run(main())