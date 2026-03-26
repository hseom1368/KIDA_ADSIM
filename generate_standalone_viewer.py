#!/usr/bin/env python3
"""CZML 데이터를 포함한 standalone HTML 파일 생성.

Usage:
    python generate_standalone_viewer.py                                    # S1 default
    python generate_standalone_viewer.py -s scenario_6_tot_mixed -d realistic
    python generate_standalone_viewer.py -s scenario_7_mlrs_saturation -d realistic
"""

import argparse
import json
import os
import sys

from modules.model import AirDefenseModel
from modules.exporters import CZMLExporter
from modules.config import SCENARIO_PARAMS, REALISTIC_DEPLOYMENT

DEFAULT_SEED = 42


def generate_czml(scenario, architecture, deployment_name="default", seed=DEFAULT_SEED):
    """시뮬레이션 실행 → CZML 데이터 반환."""
    deployment = REALISTIC_DEPLOYMENT if deployment_name == "realistic" else None
    realistic = deployment_name == "realistic"
    base_lat = 37.95 if realistic else 37.0

    m = AirDefenseModel(
        architecture=architecture, scenario=scenario,
        seed=seed, record_snapshots=True, deployment=deployment,
    )
    result = m.run_full()

    edges = [
        {"source": u, "target": v, "link_type": d.get("link_type", "")}
        for u, v, d in m.topology.edges(data=True)
    ]

    czml = CZMLExporter(
        result["snapshots"], result["config"],
        base_lat=base_lat,
        topology_edges=edges, architecture=architecture,
        realistic_coords=realistic,
    ).build_czml()

    return czml, result["metrics"]


def build_html(scenario, linear_czml, killweb_czml, linear_metrics, killweb_metrics,
               deployment_name="default"):
    """Standalone HTML 생성."""
    scenario_label = SCENARIO_PARAMS[scenario]["name"]
    dep_label = "REALISTIC" if deployment_name == "realistic" else "DEFAULT"

    # 메트릭 요약
    def fmt(m):
        return (f"leaker={m['leaker_rate']:.1f}%, "
                f"s2s={m['sensor_to_shooter_time']['mean']:.1f}s, "
                f"id_acc={m['threat_id_accuracy']:.1f}%, "
                f"dup={m['duplicate_engagement_rate']:.1f}%")

    linear_summary = fmt(linear_metrics)
    killweb_summary = fmt(killweb_metrics)

    linear_summary_js = linear_summary.replace("'", "\\'")
    killweb_summary_js = killweb_summary.replace("'", "\\'")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>KIDA ADSIM — {scenario_label} ({dep_label})</title>
<script src="https://cesium.com/downloads/cesiumjs/releases/1.130/Build/Cesium/Cesium.js"></script>
<link href="https://cesium.com/downloads/cesiumjs/releases/1.130/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0a0a0a; color: #00ff00; font-family: 'Consolas', monospace; }}
  #header {{ padding: 8px 16px; background: #111; border-bottom: 1px solid #333;
             display: flex; justify-content: space-between; align-items: center; }}
  #header h1 {{ font-size: 16px; color: #00cc00; }}
  #header .metrics {{ font-size: 11px; color: #888; }}
  #container {{ display: flex; height: calc(100vh - 40px); }}
  .viewer-panel {{ flex: 1; position: relative; border-right: 1px solid #333; }}
  .viewer-panel:last-child {{ border-right: none; }}
  .panel-label {{ position: absolute; top: 8px; left: 8px; z-index: 10;
                  background: rgba(0,0,0,0.7); padding: 4px 10px; border-radius: 4px;
                  font-size: 13px; font-weight: bold; }}
  .panel-label.linear {{ color: #ff6600; border: 1px solid #ff6600; }}
  .panel-label.killweb {{ color: #00ccff; border: 1px solid #00ccff; }}
  .metric-box {{ position: absolute; bottom: 8px; left: 8px; z-index: 10;
                 background: rgba(0,0,0,0.8); padding: 6px 10px; border-radius: 4px;
                 font-size: 10px; color: #aaa; line-height: 1.6; }}
  .cesium-viewer .cesium-viewer-bottom {{ display: none; }}
</style>
</head>
<body>
<div id="header">
  <h1>KIDA ADSIM — {scenario_label} ({dep_label})</h1>
  <div class="metrics">Linear: {linear_summary} | KillWeb: {killweb_summary}</div>
</div>
<div id="container">
  <div class="viewer-panel">
    <div class="panel-label linear">Linear C2 (3-Axis)</div>
    <div class="metric-box" id="linear-metrics"></div>
    <div id="cesium-linear" style="width:100%;height:100%;"></div>
  </div>
  <div class="viewer-panel">
    <div class="panel-label killweb">Kill Web (IAOC)</div>
    <div class="metric-box" id="killweb-metrics"></div>
    <div id="cesium-killweb" style="width:100%;height:100%;"></div>
  </div>
</div>
<script>
Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI3ZjQ5YzBiNy1kNWM1LTQ2NjAtOGRhZi00Yjg3YTI0YTljYzgiLCJpZCI6MjgzMTksInNjb3BlcyI6WyJhc3IiLCJnYyJdLCJpYXQiOjE1OTE3ODI0OTl9.uxePYJHy-Figc0FTaH0JpOkQxB5G-Y_X4MMxcHdJCBY';

const LINEAR_CZML = {json.dumps(linear_czml)};
const KILLWEB_CZML = {json.dumps(killweb_czml)};

const viewerLinear = new Cesium.Viewer('cesium-linear', {{
  timeline: true, animation: true, baseLayerPicker: false,
  geocoder: false, homeButton: false, sceneModePicker: false,
  navigationHelpButton: false, fullscreenButton: false,
}});
const dsLinear = new Cesium.CzmlDataSource();
dsLinear.load(LINEAR_CZML);
viewerLinear.dataSources.add(dsLinear);

const viewerKillweb = new Cesium.Viewer('cesium-killweb', {{
  timeline: true, animation: true, baseLayerPicker: false,
  geocoder: false, homeButton: false, sceneModePicker: false,
  navigationHelpButton: false, fullscreenButton: false,
}});
const dsKillweb = new Cesium.CzmlDataSource();
dsKillweb.load(KILLWEB_CZML);
viewerKillweb.dataSources.add(dsKillweb);

viewerLinear.camera.changed.addEventListener(function() {{
  viewerKillweb.camera.setView({{
    destination: viewerLinear.camera.positionWC.clone(),
    orientation: {{
      heading: viewerLinear.camera.heading,
      pitch: viewerLinear.camera.pitch,
      roll: viewerLinear.camera.roll,
    }}
  }});
}});

viewerLinear.camera.setView({{
  destination: Cesium.Cartesian3.fromDegrees(127.5, 36.5, 800000),
  orientation: {{ heading: 0, pitch: -Math.PI/2.5, roll: 0 }}
}});
viewerKillweb.camera.setView({{
  destination: Cesium.Cartesian3.fromDegrees(127.5, 36.5, 800000),
  orientation: {{ heading: 0, pitch: -Math.PI/2.5, roll: 0 }}
}});

viewerLinear.clock.onTick.addEventListener(function(clock) {{
  viewerKillweb.clock.currentTime = clock.currentTime.clone();
}});

viewerLinear.clock.multiplier = 5;
viewerKillweb.clock.multiplier = 5;

document.getElementById('linear-metrics').innerHTML = 'Linear: {linear_summary_js}';
document.getElementById('killweb-metrics').innerHTML = 'KillWeb: {killweb_summary_js}';
</script>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate standalone Cesium HTML viewer")
    parser.add_argument("-s", "--scenario", default="scenario_1_saturation")
    parser.add_argument("-d", "--deployment", choices=["default", "realistic"], default="default")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("-o", "--output", default=None, help="Output HTML path")
    args = parser.parse_args()

    if args.scenario not in SCENARIO_PARAMS:
        print(f"Error: unknown scenario '{args.scenario}'")
        sys.exit(1)

    print(f"Generating standalone viewer: {args.scenario} ({args.deployment})")

    print("  Running Linear...", end=" ", flush=True)
    linear_czml, linear_met = generate_czml(args.scenario, "linear", args.deployment, args.seed)
    print(f"OK ({len(linear_czml)} packets)")

    print("  Running KillWeb...", end=" ", flush=True)
    kw_czml, kw_met = generate_czml(args.scenario, "killweb", args.deployment, args.seed)
    print(f"OK ({len(kw_czml)} packets)")

    html = build_html(args.scenario, linear_czml, kw_czml, linear_met, kw_met, args.deployment)

    out_path = args.output or f"output/{args.scenario}_{args.deployment}_3d.html"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\nSaved: {out_path} ({size_mb:.1f} MB)")
    print(f"Open in browser to view 3D comparison.")


if __name__ == "__main__":
    main()
