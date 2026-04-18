#!/usr/bin/env python3
"""
MoJiTo Pipeline Orchestrator
Fase 7 - Orquestación completa del flujo
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ingest.parser import M3UParser
from core.ingest.normalizer import ChannelNormalizer
from core.fingerprint.network import NetworkFingerprinter
from core.fingerprint.temporal import TemporalFingerprinter
from core.evaluation.stream_evaluator import StreamEvaluator
from core.fusion.stream_fuser import StreamFuser
from core.output.stream_output import OutputManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

        self.parser = M3UParser()
        self.normalizer = ChannelNormalizer()
        self.net_fp = NetworkFingerprinter()
        self.temp_fp = TemporalFingerprinter()
        self.evaluator = StreamEvaluator()
        self.fuser = StreamFuser()
        self.output = OutputManager()

        self.channels: dict = {}
        self.metrics: dict = {}

    def run_ingest(self, m3u_path: str) -> dict:
        logger.info(f"Fase 1 - Ingestando M3U: {m3u_path}")

        channels = self.parser.parse_file(m3u_path)
        logger.info(f"  Parseados {len(channels)} canales")

        return channels

    def run_normalization(self, channels: dict) -> dict:
        logger.info("Fase 1 - Normalizando canales")

        normalized = {}
        for name, channel in channels.items():
            norm_name = self.normalizer.normalize(name)
            aliases = self.normalizer.get_aliases(name)

            normalized[norm_name] = {
                'name': name,
                'normalized': norm_name,
                'aliases': aliases,
                'streams': [
                    {
                        'url': s.url,
                        'type': self._detect_stream_type(s.url)
                    }
                    for s in channel.streams
                ]
            }

        logger.info(f"  Normalizados {len(normalized)} canales")
        return normalized

    def run_fingerprint(self, normalized: dict) -> dict:
        logger.info("Fase 2 - Generando fingerprints")

        fingerprints = {}
        for ch_name, ch_data in normalized.items():
            for stream in ch_data.get('streams', []):
                url = stream.get('url')
                if not url:
                    continue

                net_fp = self.net_fp.fingerprint(url)
                if net_fp:
                    fingerprints[url] = {
                        'domain': net_fp.domain,
                        'base_path': net_fp.base_path,
                        'hash': net_fp.full_hash,
                        'provider': self.net_fp.get_provider_hint(url)
                    }

        logger.info(f"  Fingerprinted {len(fingerprints)} streams")
        return fingerprints

    async def run_evaluation(self, normalized: dict) -> dict:
        logger.info("Fase 3 - Evaluando streams")

        metrics = {}
        count = 0

        for ch_name, ch_data in normalized.items():
            for stream in ch_data.get('streams', []):
                url = stream.get('url')
                if not url or url in metrics:
                    continue

                m = await self.evaluator.evaluate_async(url)
                metrics[url] = {
                    'startup_time': m.startup_time,
                    'freeze_events': m.freeze_events,
                    'motion_score': m.motion_score,
                    'stability': m.stability,
                    'valid_stream': m.valid_stream,
                    'error': m.error
                }
                count += 1

                if count % 10 == 0:
                    logger.info(f"  Evaluados {count} streams...")

        logger.info(f"  Evaluación completa: {count} streams")
        return metrics

    def run_fusion(self, normalized: dict, metrics: dict) -> dict:
        logger.info("Fase 5 - Fusión de streams")

        grouped = {}

        for ch_name, ch_data in normalized.items():
            for stream in ch_data.get('streams', []):
                url = stream.get('url')
                if not url:
                    continue

                ch_id = self.normalizer.generate_channel_id(ch_name)

                if ch_id not in grouped:
                    grouped[ch_id] = {
                        'name': ch_name,
                        'channel_id': ch_id,
                        'streams': []
                    }

                grouped[ch_id]['streams'].append(url)

        for ch_id, ch_data in grouped.items():
            streams = ch_data.get('streams', [])
            if streams:
                primary = streams[0]
                fallbacks = streams[1:]

                self.fuser.add_stream_option(ch_id, primary)
                for fb in fallbacks:
                    self.fuser.add_stream_option(ch_id, fb)

                best = self.fuser.select_best_stream(ch_id, metrics)

                self.output.add_channel(
                    channel_id=ch_id,
                    name=ch_data['name'],
                    url=best or primary,
                    fallback=fallbacks
                )

        logger.info(f"  Fusionados {len(grouped)} canales")
        return grouped

    def run_output(self, output_path: str, format: str = 'json') -> None:
        logger.info(f"Fase 6 - Generando output: {output_path}")

        if format == 'json':
            self.output.export_json(output_path)
        elif format == 'm3u':
            self.output.export_m3u(output_path)

        logger.info(f"  Exportado: {output_path}")

    async def full_pipeline(
        self,
        m3u_input: str,
        output_path: str,
        output_format: str = 'json'
    ) -> None:
        try:
            channels = self.run_ingest(m3u_input)
            normalized = self.run_normalization(channels)
            fingerprints = self.run_fingerprint(normalized)
            metrics = await self.run_evaluation(normalized)
            self.run_fusion(normalized, metrics)
            self.run_output(output_path, output_format)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            raise

    def _detect_stream_type(self, url: str) -> str:
        if not url:
            return 'unknown'
        lower = url.lower()
        if '.m3u8' in lower or 'manifest' in lower:
            return 'm3u8'
        elif '.ts' in lower:
            return 'ts'
        elif '.mp4' in lower:
            return 'mp4'
        return 'ts'


def main():
    parser = argparse.ArgumentParser(description='MoJiTo Pipeline')
    parser.add_argument('--input', '-i', required=True, help='Input M3U file')
    parser.add_argument('--output', '-o', required=True, help='Output file')
    parser.add_argument('--format', '-f', default='json', choices=['json', 'm3u'],
                      help='Output format')
    parser.add_argument('--config', '-c', help='Config file (YAML)')

    args = parser.parse_args()

    config = {}
    if args.config:
        import yaml
        with open(args.config) as f:
            config = yaml.safe_load(f)

    pipeline = Pipeline(config)

    logger.info("=== MoJiTo Pipeline Starting ===")

    asyncio.run(pipeline.full_pipeline(
        args.input,
        args.output,
        args.format
    ))

    logger.info("=== Pipeline Complete ===")


if __name__ == '__main__':
    main()