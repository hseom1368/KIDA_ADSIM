"""
network.py - 네트워크 토폴로지 빌더
NetworkX topology builder for Linear C2 and Kill Web architectures.
"""

import networkx as nx
from .config import DEFAULT_DEPLOYMENT, COMM_PARAMS


def build_linear_topology(sensors, c2_nodes, shooters):
    """
    선형 C2 토폴로지 구축.
    - MCRC가 단일 허브 (SPOF)
    - 센서-사수 쌍이 고정 (교차운용 불가)
    - 계층적 구조: 센서 → 전용 C2 → 전용 사수
    """
    G = nx.DiGraph()
    comm = COMM_PARAMS["linear"]

    # 노드 추가
    for s in sensors:
        G.add_node(s.agent_id, agent_type="sensor", pos=s.pos,
                   sensor_type=s.sensor_type)
    for c in c2_nodes:
        G.add_node(c.agent_id, agent_type="c2", pos=c.pos,
                   node_type=c.node_type)
    for sh in shooters:
        G.add_node(sh.agent_id, agent_type="shooter", pos=sh.pos,
                   weapon_type=sh.weapon_type)

    # ── 센서 → C2 엣지 ──
    # EWR → MCRC
    for s in sensors:
        if s.sensor_type == "EWR":
            _add_edge_if_exists(G, s.agent_id, "MCRC", comm)

    # PATRIOT_RADAR → TOC_PAT
    for s in sensors:
        if s.sensor_type == "PATRIOT_RADAR":
            _add_edge_if_exists(G, s.agent_id, "TOC_PAT", comm)

    # MSAM_MFR → TOC_MSAM
    for s in sensors:
        if s.sensor_type == "MSAM_MFR":
            _add_edge_if_exists(G, s.agent_id, "TOC_MSAM", comm)

    # SHORAD_RADAR → TOC_SHORAD (TOC_MSAM을 대리 사용)
    for s in sensors:
        if s.sensor_type == "SHORAD_RADAR":
            target = "TOC_SHORAD" if G.has_node("TOC_SHORAD") else "TOC_MSAM"
            _add_edge_if_exists(G, s.agent_id, target, comm)

    # ── C2 내부 엣지: MCRC → 하위 TOC ──
    for c in c2_nodes:
        if c.node_type == "BATTALION_TOC":
            _add_edge_if_exists(G, "MCRC", c.agent_id, comm)

    # ── C2 → 사수 엣지 ──
    # TOC_PAT → PATRIOT
    for sh in shooters:
        if sh.weapon_type == "PATRIOT_PAC3":
            _add_edge_if_exists(G, "TOC_PAT", sh.agent_id, comm)

    # TOC_MSAM → CHEONGUNG
    for sh in shooters:
        if sh.weapon_type == "CHEONGUNG2":
            _add_edge_if_exists(G, "TOC_MSAM", sh.agent_id, comm)

    # TOC_MSAM → BIHO (SHORAD)
    for sh in shooters:
        if sh.weapon_type == "BIHO":
            target = "TOC_SHORAD" if G.has_node("TOC_SHORAD") else "TOC_MSAM"
            _add_edge_if_exists(G, target, sh.agent_id, comm)

    # KF16 → MCRC 직접 (공군 계통)
    for sh in shooters:
        if sh.weapon_type == "KF16":
            _add_edge_if_exists(G, "MCRC", sh.agent_id, comm)

    return G


def build_killweb_topology(sensors, c2_nodes, shooters):
    """
    Kill Web 토폴로지 구축.
    - 완전 메시 연결 (모든 센서 → 모든 C2 → 모든 사수)
    - 자동 페일오버 (노드 손실 시 대체 경로)
    - 공유 COP (모든 C2 노드 동일 항적 보유)
    """
    G = nx.DiGraph()
    comm = COMM_PARAMS["killweb"]

    # 노드 추가
    for s in sensors:
        G.add_node(s.agent_id, agent_type="sensor", pos=s.pos,
                   sensor_type=s.sensor_type)
    for c in c2_nodes:
        G.add_node(c.agent_id, agent_type="c2", pos=c.pos,
                   node_type=c.node_type)
    for sh in shooters:
        G.add_node(sh.agent_id, agent_type="shooter", pos=sh.pos,
                   weapon_type=sh.weapon_type)

    # ── 센서 ↔ 모든 C2 (양방향) ──
    for s in sensors:
        for c in c2_nodes:
            if G.has_node(s.agent_id) and G.has_node(c.agent_id):
                G.add_edge(s.agent_id, c.agent_id,
                           latency=comm["sensor_to_c2_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="sensor_to_c2")
                G.add_edge(c.agent_id, s.agent_id,
                           latency=comm["sensor_to_c2_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="c2_to_sensor")

    # ── C2 ↔ C2 (상호 연결) ──
    for i, c1 in enumerate(c2_nodes):
        for c2 in c2_nodes[i + 1:]:
            if G.has_node(c1.agent_id) and G.has_node(c2.agent_id):
                G.add_edge(c1.agent_id, c2.agent_id,
                           latency=comm["c2_processing_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="c2_to_c2")
                G.add_edge(c2.agent_id, c1.agent_id,
                           latency=comm["c2_processing_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="c2_to_c2")

    # ── C2 ↔ 모든 사수 (양방향) ──
    for c in c2_nodes:
        for sh in shooters:
            if G.has_node(c.agent_id) and G.has_node(sh.agent_id):
                G.add_edge(c.agent_id, sh.agent_id,
                           latency=comm["c2_to_shooter_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="c2_to_shooter")
                G.add_edge(sh.agent_id, c.agent_id,
                           latency=comm["c2_to_shooter_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="shooter_to_c2")

    return G


def remove_node_from_topology(G, node_id):
    """노드 제거 (파괴 시뮬레이션). 연결된 모든 엣지도 제거."""
    if G.has_node(node_id):
        G.remove_node(node_id)
    return G


def get_available_paths(G, source, target):
    """source에서 target까지 사용 가능한 경로 목록"""
    try:
        return list(nx.all_simple_paths(G, source, target, cutoff=4))
    except (nx.NetworkXError, nx.NodeNotFound):
        return []


def get_connected_shooters(G, c2_node_id):
    """특정 C2 노드에 연결된 사수 목록"""
    if not G.has_node(c2_node_id):
        return []
    return [
        n for n in G.successors(c2_node_id)
        if G.nodes[n].get("agent_type") == "shooter"
    ]


def get_connected_c2_for_sensor(G, sensor_id):
    """특정 센서에 연결된 C2 노드 목록"""
    if not G.has_node(sensor_id):
        return []
    return [
        n for n in G.successors(sensor_id)
        if G.nodes[n].get("agent_type") == "c2"
    ]


def get_topology_stats(G):
    """토폴로지 통계 정보"""
    stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "sensors": len([n for n, d in G.nodes(data=True)
                        if d.get("agent_type") == "sensor"]),
        "c2_nodes": len([n for n, d in G.nodes(data=True)
                         if d.get("agent_type") == "c2"]),
        "shooters": len([n for n, d in G.nodes(data=True)
                         if d.get("agent_type") == "shooter"]),
    }

    # 약한 연결성 (방향 무시)
    undirected = G.to_undirected()
    stats["is_connected"] = nx.is_connected(undirected)
    stats["connected_components"] = nx.number_connected_components(undirected)

    # 평균 경로 길이 (연결된 경우)
    if stats["is_connected"]:
        stats["avg_path_length"] = nx.average_shortest_path_length(undirected)
    else:
        stats["avg_path_length"] = float("inf")

    return stats


def _add_edge_if_exists(G, source, target, comm):
    """노드가 존재하는 경우에만 엣지 추가"""
    if G.has_node(source) and G.has_node(target):
        G.add_edge(
            source, target,
            latency=comm["sensor_to_c2_delay"],
            bandwidth=comm["bandwidth_kbps"],
            link_type="directed",
        )


# =============================================================================
# v0.7 현실적 토폴로지 빌더 (3축 분리 / 통합 IAOC)
# =============================================================================

def _add_nodes(G, sensors, c2_nodes, shooters):
    """공통 노드 추가 헬퍼"""
    for s in sensors:
        G.add_node(s.agent_id, agent_type="sensor", pos=s.pos,
                   sensor_type=s.sensor_type)
    for c in c2_nodes:
        G.add_node(c.agent_id, agent_type="c2", pos=c.pos,
                   node_type=c.node_type)
    for sh in shooters:
        G.add_node(sh.agent_id, agent_type="shooter", pos=sh.pos,
                   weapon_type=sh.weapon_type)


def build_realistic_linear_topology(sensors, c2_nodes, shooters):
    """
    현실적 선형 C2 토폴로지 (v0.7 — 3축 분리).
    - MCRC: 지역방공 (FPS117 → MCRC → 천궁-I, KF-16)
    - KAMD_OPS: 탄도탄 전담 (GREEN_PINE → KAMD_OPS → PAC-3, THAAD, L-SAM, 천궁-II)
    - ARMY_LOCAL_AD: 육군 독자 (TPS880K → ARMY_AD → 천마, 비호)
    - 3축 간 부분 연결만 (위협정보 공유, 교전상태 미공유)
    """
    from .config import COMM_PARAMS, TOPOLOGY_RELATIONS
    G = nx.DiGraph()
    comm = COMM_PARAMS["linear"]
    _add_nodes(G, sensors, c2_nodes, shooters)

    s_to_c2 = TOPOLOGY_RELATIONS["sensor_to_c2"]
    sh_to_c2 = TOPOLOGY_RELATIONS["shooter_to_c2"]

    # 센서 → 지정 C2 (TOPOLOGY_RELATIONS 기반 자동 매핑)
    for s in sensors:
        target_c2_type = s_to_c2.get(s.sensor_type)
        if target_c2_type:
            # C2 인스턴스 중 해당 타입 찾기
            for c in c2_nodes:
                if c.node_type == target_c2_type:
                    _add_edge_if_exists(G, s.agent_id, c.agent_id, comm)
                    break
            else:
                # fallback: 기존 하드코딩 매핑 시도
                _add_edge_if_exists(G, s.agent_id, target_c2_type, comm)

    # C2 계층: BATTALION_TOC → MCRC
    for c in c2_nodes:
        if c.node_type == "BATTALION_TOC":
            for mc in c2_nodes:
                if mc.node_type == "MCRC":
                    _add_edge_if_exists(G, mc.agent_id, c.agent_id, comm)
                    break

    # C2 → 사수 (TOPOLOGY_RELATIONS 기반 자동 매핑)
    for sh in shooters:
        target_c2_type = sh_to_c2.get(sh.weapon_type)
        if target_c2_type:
            for c in c2_nodes:
                if c.node_type == target_c2_type:
                    _add_edge_if_exists(G, c.agent_id, sh.agent_id, comm)
                    break
            else:
                _add_edge_if_exists(G, target_c2_type, sh.agent_id, comm)

    # 3축 간 부분 연결 (위협정보만 공유, 느린 링크)
    c2_type_map = {}
    for c in c2_nodes:
        c2_type_map.setdefault(c.node_type, []).append(c)

    inter_c2_types = [("MCRC", "KAMD_OPS"), ("KAMD_OPS", "ARMY_LOCAL_AD")]
    for t1, t2 in inter_c2_types:
        for c1 in c2_type_map.get(t1, []):
            for c2 in c2_type_map.get(t2, []):
                if G.has_node(c1.agent_id) and G.has_node(c2.agent_id):
                    # 느린 양방향 링크 (정보 공유만, 교전 통제 불가)
                    G.add_edge(c1.agent_id, c2.agent_id,
                               latency=(10, 30), bandwidth=10,
                               link_type="inter_c2_info")
                    G.add_edge(c2.agent_id, c1.agent_id,
                               latency=(10, 30), bandwidth=10,
                               link_type="inter_c2_info")

    return G


def build_realistic_killweb_topology(sensors, c2_nodes, shooters):
    """
    현실적 Kill Web 토폴로지 (v0.7 — 통합 IAOC).
    - IAOC 중심 완전 메시
    - Any Sensor → Best Shooter 원칙
    - 모든 센서/사수가 IAOC와 직접 연결
    """
    from .config import COMM_PARAMS
    G = nx.DiGraph()
    comm = COMM_PARAMS["killweb"]
    _add_nodes(G, sensors, c2_nodes, shooters)

    # 센서 ↔ 모든 C2 (양방향)
    for s in sensors:
        for c in c2_nodes:
            if G.has_node(s.agent_id) and G.has_node(c.agent_id):
                G.add_edge(s.agent_id, c.agent_id,
                           latency=comm["sensor_to_c2_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="sensor_to_c2")
                G.add_edge(c.agent_id, s.agent_id,
                           latency=comm["sensor_to_c2_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="c2_to_sensor")

    # C2 ↔ C2 (상호 연결)
    for i, c1 in enumerate(c2_nodes):
        for c2_node in c2_nodes[i + 1:]:
            if G.has_node(c1.agent_id) and G.has_node(c2_node.agent_id):
                G.add_edge(c1.agent_id, c2_node.agent_id,
                           latency=comm["c2_processing_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="c2_to_c2")
                G.add_edge(c2_node.agent_id, c1.agent_id,
                           latency=comm["c2_processing_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="c2_to_c2")

    # C2 ↔ 모든 사수 (양방향)
    for c in c2_nodes:
        for sh in shooters:
            if G.has_node(c.agent_id) and G.has_node(sh.agent_id):
                G.add_edge(c.agent_id, sh.agent_id,
                           latency=comm["c2_to_shooter_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="c2_to_shooter")
                G.add_edge(sh.agent_id, c.agent_id,
                           latency=comm["c2_to_shooter_delay"],
                           bandwidth=comm["bandwidth_kbps"],
                           link_type="shooter_to_c2")

    return G
