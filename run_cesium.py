#!/usr/bin/env python3
"""KIDA_ADSIM → Cesium 3D 시각화 자동 실행 스크립트.

Usage:
    python run_cesium.py                              # 기본: S1, 두 아키텍처
    python run_cesium.py --scenario scenario_2_complex # 시나리오 지정
    python run_cesium.py --all                         # 전 시나리오 내보내기
    python run_cesium.py --serve                       # 웹서버 자동 시작
    python run_cesium.py --all --serve                 # 전체 내보내기 + 서버
"""

from __future__ import annotations

import argparse
import http.server
import os
import sys
import threading
import webbrowser

from modules.model import AirDefenseModel
from modules.exporters import CZMLExporter, CesiumConfigExporter
from modules.config import SCENARIO_PARAMS, REALISTIC_DEPLOYMENT

SCENARIOS = list(SCENARIO_PARAMS.keys())
ARCHITECTURES = ["linear", "killweb"]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
DEFAULT_PORT = 8000
DEFAULT_SEED = 42


def export_scenario(scenario: str, architecture: str, seed: int = DEFAULT_SEED,
                    deployment_name: str = "default") -> dict:
    """시뮬레이션 실행 + CZML + viewer_config 내보내기."""
    dep_label = f" [{deployment_name}]" if deployment_name != "default" else ""
    print(f"  Running {scenario} / {architecture}{dep_label} (seed={seed})...", end=" ", flush=True)

    deployment = REALISTIC_DEPLOYMENT if deployment_name == "realistic" else None
    realistic_coords = deployment_name == "realistic"
    # v0.7.4: REALISTIC_DEPLOYMENT는 한반도 좌표계 사용 (base_lat=DMZ=37.95°N)
    base_lat = 37.95 if realistic_coords else 37.0

    m = AirDefenseModel(
        architecture=architecture,
        scenario=scenario,
        seed=seed,
        record_snapshots=True,
        deployment=deployment,
    )
    result = m.run_full()

    # 토폴로지 엣지 추출
    edges = [
        {"source": u, "target": v, "link_type": d.get("link_type", "")}
        for u, v, d in m.topology.edges(data=True)
    ]

    # CZML 내보내기
    czml_path = os.path.join(OUTPUT_DIR, f"{scenario}_{architecture}.czml")
    CZMLExporter(
        result["snapshots"], result["config"],
        base_lat=base_lat,
        topology_edges=edges, architecture=architecture,
        realistic_coords=realistic_coords,
    ).export(czml_path)

    # viewer_config.json 내보내기
    config_path = os.path.join(OUTPUT_DIR, f"viewer_config_{architecture}.json")
    CesiumConfigExporter(
        result["snapshots"], result["config"],
        architecture, scenario,
        realistic_coords=realistic_coords,
    ).export(config_path)

    leaker = result["metrics"]["leaker_rate"]
    print(f"OK (leaker={leaker:.1f}%)")

    return result


def run_export(scenarios: list[str], seed: int = DEFAULT_SEED,
               deployment_name: str = "default") -> None:
    """지정 시나리오들 내보내기."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total = len(scenarios) * len(ARCHITECTURES)
    count = 0
    for scenario in scenarios:
        for arch in ARCHITECTURES:
            export_scenario(scenario, arch, seed, deployment_name)
            count += 1

    print(f"\nExport complete: {count} files in {OUTPUT_DIR}/")


def start_server(port: int = DEFAULT_PORT) -> None:
    """HTTP 서버 시작 + 브라우저 열기."""
    os.chdir(os.path.dirname(__file__))

    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.HTTPServer(("", port), handler)

    url = f"http://localhost:{port}/cesium-viewer/"
    print(f"\nServing at {url}")
    print("Press Ctrl+C to stop.\n")

    # 브라우저 열기 (별도 스레드)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(
        description="KIDA_ADSIM Cesium 3D visualization runner",
    )
    parser.add_argument(
        "--scenario", "-s",
        default="scenario_1_saturation",
        help="Scenario name (default: scenario_1_saturation)",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Export all 7 scenarios",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start HTTP server and open browser",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"HTTP server port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--deployment", "-d",
        choices=["default", "realistic"],
        default="default",
        help="Deployment config: default (4센서/6사수) or realistic (한반도 방어구역)",
    )

    args = parser.parse_args()

    # 시나리오 결정
    if args.all:
        scenarios = SCENARIOS
    else:
        if args.scenario not in SCENARIOS:
            print(f"Error: unknown scenario '{args.scenario}'")
            print(f"Available: {', '.join(SCENARIOS)}")
            sys.exit(1)
        scenarios = [args.scenario]

    print(f"KIDA_ADSIM Cesium Exporter (seed={args.seed}, deployment={args.deployment})")
    print(f"Scenarios: {len(scenarios)}, Architectures: {len(ARCHITECTURES)}")
    print()

    run_export(scenarios, args.seed, args.deployment)

    if args.serve:
        start_server(args.port)


if __name__ == "__main__":
    main()
