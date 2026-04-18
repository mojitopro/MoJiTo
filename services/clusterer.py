#!/usr/bin/env python3
"""
Clusterer Service
Groups streams into clusters based on structural + perceptual fingerprint
"""
import asyncio
import hashlib
import time
import json
from typing import Optional
from collections import defaultdict

from runtime.db import Database, Cluster, ClusterStream
from runtime.utils import (
    normalize_channel_name, extract_domain, extract_base_path, 
    detect_stream_type, string_similarity
)


class ClustererService:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
    
    def generate_cluster_id(self, name: str, domain: str) -> str:
        key = f"{normalize_channel_name(name)}:{extract_domain(domain)}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]
    
    async def cluster_stream(self, url: str, name: str, confidence: float = 0.5) -> str:
        domain = extract_domain(url)
        base_path = extract_base_path(url)
        stream_type = detect_stream_type(url)
        
        cluster_id = self.generate_cluster_id(name, domain)
        canonical = normalize_channel_name(name)
        
        cluster = Cluster(
            cluster_id=cluster_id,
            canonical_name=canonical,
            confidence=confidence,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        self.db.insert_cluster(cluster)
        
        cs = ClusterStream(
            cluster_id=cluster_id,
            stream_url=url,
            priority=confidence,
            is_primary=True,
            last_check=int(time.time())
        )
        self.db.insert_cluster_stream(cs)
        
        return cluster_id
    
    async def add_to_cluster(self, url: str, cluster_id: str, priority: float = 0.5) -> bool:
        cs = ClusterStream(
            cluster_id=cluster_id,
            stream_url=url,
            priority=priority,
            is_primary=False,
            last_check=int(time.time())
        )
        return self.db.insert_cluster_stream(cs)
    
    async def find_best_cluster(self, url: str, name: str) -> Optional[str]:
        canonical = normalize_channel_name(name)
        domain = extract_domain(url)
        
        clusters = self.db.get_all_clusters()
        
        best_cluster = None
        best_score = 0
        
        for cluster in clusters:
            if cluster.canonical_name != canonical:
                name_sim = string_similarity(canonical, cluster.canonical_name)
            else:
                name_sim = 1.0
            
            cluster_streams = self.db.get_cluster_streams(cluster.cluster_id)
            
            domain_sim = 0
            if cluster_streams:
                for cs in cluster_streams:
                    cs_domain = extract_domain(cs.stream_url)
                    if cs_domain == domain:
                        domain_sim = 1.0
                    elif cs_domain and domain:
                        domain_sim = max(domain_sim, string_similarity(cs_domain, domain))
            
            total_score = (name_sim * 0.6) + (domain_sim * 0.4)
            
            if total_score > best_score and total_score > 0.3:
                best_score = total_score
                best_cluster = cluster.cluster_id
        
        return best_cluster
    
    async def cluster_all(self) -> dict:
        streams = self.db.get_all_streams(status='online')
        clusters_created = 0
        streams_clustered = 0
        
        stream_to_cluster = {}
        
        for stream in streams:
            cluster_id = await self.find_best_cluster(stream.url, stream.channel or 'unknown')
            
            if cluster_id:
                stream_to_cluster[stream.url] = cluster_id
                streams_clustered += 1
            else:
                cluster_id = await self.cluster_stream(
                    stream.url, 
                    stream.channel or 'unknown',
                    confidence=0.7
                )
                stream_to_cluster[stream.url] = cluster_id
                clusters_created += 1
                streams_clustered += 1
        
        for url, cid in stream_to_cluster.items():
            if cid:
                await self.add_to_cluster(url, cid, priority=0.5)
        
        for cluster in self.db.get_all_clusters():
            cluster_streams = self.db.get_cluster_streams(cluster.cluster_id)
            
            total_priority = sum(cs.priority for cs in cluster_streams)
            avg_priority = total_priority / len(cluster_streams) if cluster_streams else 0
            
            cluster.confidence = min(1.0, avg_priority + 0.1)
            cluster.updated_at = int(time.time())
            self.db.insert_cluster(cluster)
        
        return {
            'clusters': clusters_created,
            'clustered': streams_clustered
        }
    
    def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        return self.db.get_cluster(cluster_id)
    
    def get_cluster_streams(self, cluster_id: str) -> list[ClusterStream]:
        return self.db.get_cluster_streams(cluster_id)
    
    def get_all_clusters(self) -> list[Cluster]:
        return self.db.get_all_clusters()
    
    def get_stream_cluster(self, url: str) -> Optional[str]:
        clusters = self.db.get_all_clusters()
        
        for cluster in clusters:
            for cs in self.db.get_cluster_streams(cluster.cluster_id):
                if cs.stream_url == url:
                    return cluster.cluster_id
        
        return None
    
    def get_similar_streams(self, url: str, threshold: float = 0.6) -> list[tuple[str, float]]:
        similar = []
        
        domain = extract_domain(url)
        stream_type = detect_stream_type(url)
        
        all_streams = self.db.get_all_streams()
        
        for stream in all_streams:
            if stream.url == url:
                continue
            
            score = 0
            
            stream_domain = extract_domain(stream.url)
            if stream_domain and domain:
                domain_sim = string_similarity(stream_domain, domain)
                score += domain_sim * 0.5
            
            stream_type_match = detect_stream_type(stream.url) == stream_type
            if stream_type_match:
                score += 0.3
            
            if stream.channel:
                name_sim = string_similarity(
                    normalize_channel_name(stream.channel),
                    normalize_channel_name(url)
                )
                score += name_sim * 0.2
            
            if score >= threshold:
                similar.append((stream.url, score))
        
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar[:10]


async def main():
    import sys
    
    clusterer = ClustererService()
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        name = sys.argv[2] if len(sys.argv) > 2 else 'Test'
        
        cluster_id = await clusterer.find_best_cluster(url, name)
        
        if not cluster_id:
            cluster_id = await clusterer.cluster_stream(url, name)
        
        print(f"[Clusterer] Cluster: {cluster_id}")
    
    else:
        results = await clusterer.cluster_all()
        print(f"[Clusterer] Results: {results}")


if __name__ == '__main__':
    asyncio.run(main())