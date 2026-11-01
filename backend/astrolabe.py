import json
import math
import re
import sqlite3
from backend.entity_names import text_mentions_entity
from backend.telemetry import calculate_text_telemetry
from backend.text_utils import html_to_text
from backend.config import TENSION_KEYWORDS


def _mentions_entity(text: str, entity) -> bool:
    return text_mentions_entity(text, entity["name"], entity["aliases"])


# =============================================================================
# 1. MICRO CHAPTER LENS (Beat-by-Beat Narrative Waveform + Live Location)
# =============================================================================

def build_chapter_micro_lens(
    conn: sqlite3.Connection,
    chapter_id: str,
    focus_scene_id: str | None = None,
    projection_mode: str = "ALL"
) -> dict:
    c = conn.cursor()
    c.execute("""
        SELECT s.id, s.title, s.content, s.word_count, s.sort_order,
               ch.id as ch_id, ch.title as ch_title
        FROM binder_nodes s
        JOIN binder_nodes ch ON s.parent_id = ch.id
        WHERE ch.id = ? AND s.node_type = 'SCENE'
        ORDER BY s.sort_order ASC
    """, (chapter_id,))
    scene_rows = c.fetchall()

    if not scene_rows:
        return {"data": [], "layout": {}, "locations": {}, "anomalies": []}

    c.execute("SELECT entity_id, name, aliases, entity_type FROM canonical_entities")
    all_entities = c.fetchall()
    location_entities = [e for e in all_entities if e["entity_type"] == "LOCATION"]

    all_chapter_text = " ".join(html_to_text(sc["content"] or "") for sc in scene_rows)
    chapter_locations = [loc for loc in location_entities if _mentions_entity(all_chapter_text, loc)]
    chapter_location_names = [loc["name"] for loc in chapter_locations]

    use_geographic_y = len(chapter_locations) >= 2
    if use_geographic_y:
        loc_to_y = {loc: idx for idx, loc in enumerate(chapter_location_names)}
        loc_to_y["Unspecified"] = len(loc_to_y)
        y_tick_text = list(loc_to_y.keys())
        y_tick_vals = list(loc_to_y.values())
        y_axis_title = "Chapter Geography"
    else:
        loc_to_y = {"Non-dialogue passage": 0, "Dialogue": 1, "Action cue": 2}
        y_tick_text = ["Non-dialogue", "Dialogue", "Action cue"]
        y_tick_vals = [0, 1, 2]
        y_axis_title = "Text pattern"

    beats_x = []
    beats_y = []
    beats_z = []
    beats_sizes = []
    beats_colors = []
    beats_text = []
    beats_customdata = []

    entity_markers = {}
    global_beat_idx = 0
    current_loc = "Unspecified" if use_geographic_y else "Scene Setting"

    for sc in scene_rows:
        current_loc = "Unspecified" if use_geographic_y else "Scene Setting"
        sc_id = sc["id"]
        sc_title = sc["title"]
        content = html_to_text(sc["content"] or "")
        is_active_scene = (focus_scene_id and sc_id == focus_scene_id)

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [sc_title]

        for p_idx, para in enumerate(paragraphs, 1):
            global_beat_idx += 1
            para_lower = para.lower()
            words = len(para.split())

            if use_geographic_y:
                for loc in chapter_locations:
                    if _mentions_entity(para, loc):
                        current_loc = loc["name"]
                        break
                y_val = float(loc_to_y.get(current_loc, 0))
                mode_label = f"Location: {current_loc}"
            else:
                has_dialogue = ('"' in para or '“' in para or '”' in para)
                tension_hits = sum(len(re.findall(r"\b" + re.escape(k) + r"\b", para_lower)) for k in TENSION_KEYWORDS)
                has_action = (tension_hits > 0) or (words < 10 and not has_dialogue)
                if has_action and not has_dialogue:
                    y_val = 2.0
                    mode_label = "Action cue"
                elif has_dialogue:
                    y_val = 1.0
                    mode_label = "Dialogue"
                else:
                    y_val = 0.0
                    mode_label = "Non-dialogue passage"

            tension_estimate = calculate_text_telemetry(para)["tension_elevation"]

            if is_active_scene:
                node_color = "#22d3ee"
                node_size = max(8, min(16, int(7 + (words / 35))))
            else:
                node_color = "#f59e0b"
                node_size = max(5, min(11, int(4 + (words / 50))))

            snippet = (para[:85] + "...") if len(para) > 85 else para

            beats_x.append(global_beat_idx)
            beats_y.append(y_val)
            beats_z.append(tension_estimate)
            beats_sizes.append(node_size)
            beats_colors.append(node_color)
            
            beats_customdata.append({
                "scene_id": sc_id,
                "beat_idx": p_idx,
                "snippet": snippet
            })

            hover_info = (
                f"<b>{sc_title}</b> (Beat {p_idx})<br>"
                f"{mode_label}<br>"
                f"Tension estimate: <b>{tension_estimate:.2f}</b> ({words}w)<br>"
                f"<i>\"{snippet}\"</i>"
            )
            beats_text.append(hover_info)

            for ent in all_entities:
                if ent["entity_type"] == "CHARACTER" and _mentions_entity(para, ent):
                    ent_name = ent["name"]
                    if ent_name not in entity_markers:
                        entity_markers[ent_name] = {"x": [], "y": [], "z": [], "text": []}
                    entity_markers[ent_name]["x"].append(global_beat_idx)
                    entity_markers[ent_name]["y"].append(y_val)
                    entity_markers[ent_name]["z"].append(tension_estimate + 0.04)
                    entity_markers[ent_name]["text"].append(f"<b>{ent_name}</b> in Beat {global_beat_idx}")

    traces = [
        {
            "type": "scatter3d",
            "mode": "lines+markers",
            "name": "Chapter Arc",
            "x": beats_x,
            "y": beats_y,
            "z": beats_z,
            "customdata": beats_customdata,
            "text": beats_text,
            "hoverinfo": "text",
            "line": {"color": "#38bdf8" if focus_scene_id else "#fbbf24", "width": 5},
            "marker": {"size": beats_sizes, "color": beats_colors, "symbol": "circle", "opacity": 0.95}
        }
    ]

    char_palette = ["#ec4899", "#a855f7", "#10b981", "#fb923c"]
    for idx, (ent_name, edata) in enumerate(entity_markers.items()):
        traces.append({
            "type": "scatter3d",
            "mode": "markers",
            "name": f"Cast: {ent_name}",
            "x": edata["x"],
            "y": edata["y"],
            "z": edata["z"],
            "text": edata["text"],
            "hoverinfo": "text",
            "marker": {"size": 8, "symbol": "diamond", "color": char_palette[idx % len(char_palette)], "opacity": 0.9}
        })

    layout = {
        "autosize": True,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "showlegend": False,
        "scene": {
            "xaxis": {"title": "Chapter Beats", "color": "#71717a", "gridcolor": "#27272a", "showticklabels": True},
            "yaxis": {"title": y_axis_title, "tickvals": y_tick_vals, "ticktext": y_tick_text, "color": "#a1a1aa", "gridcolor": "#27272a"},
            "zaxis": {"title": "Tension estimate", "range": [0, 1], "color": "#71717a", "gridcolor": "#27272a"},
            "camera": {"eye": {"x": 1.1, "y": -1.5, "z": 0.8}}
        },
        "margin": {"l": 0, "r": 0, "b": 0, "t": 0}
    }

    return {"data": traces, "layout": layout, "locations": loc_to_y, "anomalies": []}


# =============================================================================
# 2. MACRO COSMOGRAPH (100% Deterministic Prose-Derived Spacetime)
# =============================================================================

def build_astrolabe_manifest(
    conn: sqlite3.Connection, 
    book_id: str | None = None, 
    projection_mode: str = "ALL", 
    time_mode: str = "chronological",
    chapter_id: str | None = None,
    focus_scene_id: str | None = None
) -> dict:
    if chapter_id:
        return build_chapter_micro_lens(conn, chapter_id, focus_scene_id, projection_mode)

    scene_telemetry: dict = {}
    c = conn.cursor()

    b_row = None
    if book_id:
        c.execute("SELECT id, title FROM binder_nodes WHERE id = ? AND node_type = 'BOOK' AND (is_archived IS NULL OR is_archived = 0)", (book_id,))
        b_row = c.fetchone()

    if not b_row:
        c.execute("SELECT id, title FROM binder_nodes WHERE node_type = 'BOOK' AND (is_archived IS NULL OR is_archived = 0) ORDER BY sort_order ASC LIMIT 1")
        b_row = c.fetchone()

    if not b_row:
        c.execute("SELECT id, title FROM binder_nodes WHERE node_type = 'BOOK' LIMIT 1")
        b_row = c.fetchone()

    if not b_row:
        return {"data": [], "layout": {}, "locations": {}, "anomalies": [], "transit_matrix": {}}

    book_id = b_row["id"]

    c.execute("""
        SELECT s.id, s.title, s.content, s.word_count, s.sort_order, s.synopsis,
               ch.id as ch_id, ch.title as ch_title, ch.sort_order as ch_sort
        FROM binder_nodes s
        JOIN binder_nodes ch ON s.parent_id = ch.id
        WHERE ch.parent_id = ? AND s.node_type = 'SCENE'
        ORDER BY ch.sort_order ASC, s.sort_order ASC
    """, (book_id,))
    scene_rows = c.fetchall()

    if not scene_rows:
        return {"data": [], "layout": {}, "locations": {}, "anomalies": [], "transit_matrix": {}}

    total_scenes = len(scene_rows)
    scene_seq_map = {r["id"]: idx + 1 for idx, r in enumerate(scene_rows)}

    # Fetch canonical entities
    c.execute("SELECT entity_id, name, aliases, entity_type FROM canonical_entities WHERE entity_type = 'LOCATION' ORDER BY rowid ASC")
    location_entities = [dict(r) for r in c.fetchall()]

    c.execute("SELECT entity_id, name, aliases, entity_type FROM canonical_entities WHERE entity_type = 'CHARACTER' ORDER BY rowid ASC")
    character_entities = [dict(r) for r in c.fetchall()]

    # 1. Map Each Scene to an Inhabited Geographic Location (from prose or title)
    scene_location_map = {}
    active_locations = []

    for sc in scene_rows:
        sc_id = sc["id"]
        sc_content = html_to_text(sc["content"] or "")
        matched_loc = None

        # Check prose for confirmed locations
        for loc in location_entities:
            if _mentions_entity(sc_content, loc) or _mentions_entity(sc["title"], loc):
                matched_loc = loc["name"]
                break

        final_loc = matched_loc or "Unspecified"
        scene_location_map[sc_id] = final_loc
        if final_loc not in active_locations:
            active_locations.append(final_loc)

    if not active_locations:
        active_locations = ["Unspecified"]

    loc_to_y = {loc: idx for idx, loc in enumerate(active_locations)}

    # 2. Compute Pacing Telemetry & Tension Estimates across scenes
    tension_estimates = []
    prev_tens = 0.35
    for sc in scene_rows:
        metric = calculate_text_telemetry(sc["content"] or "", prev_tens)
        scene_telemetry[sc["id"]] = metric
        prev_tens = metric["tension_elevation"]
        tension_estimates.append(metric["tension_elevation"])

    # 3. AUTOMATED CHARACTER WORLDLINES (Extracted directly from prose mentions)
    character_trajectories = {}
    co_locations = {}
    anomalies = []

    for char in character_entities:
        c_id = char["entity_id"]
        c_name = char["name"]
        points = []

        for idx, sc in enumerate(scene_rows, 1):
            sc_id = sc["id"]
            sc_text = html_to_text(sc["content"] or "")

            if _mentions_entity(sc_text, char):
                loc_name = scene_location_map[sc_id]
                y_val = loc_to_y[loc_name]
                z_val = tension_estimates[idx - 1]
                x_val = float(idx)

                points.append({
                    "x": x_val, "y": y_val, "z": z_val,
                    "scene_id": sc_id, "scene_title": sc["title"],
                    "chapter_title": sc["ch_title"], "loc_name": loc_name,
                    "name": c_name
                })

                coord_key = (idx, y_val)
                co_locations.setdefault(coord_key, []).append(c_name)

        if points:
            character_trajectories[c_id] = {"name": c_name, "points": points}

            # Detect Spatial Teleportation: character jumps location with 0 elapsed narrative beats
            for i in range(1, len(points)):
                prev_p, curr_p = points[i-1], points[i]
                if prev_p["loc_name"] != curr_p["loc_name"] and (curr_p["x"] - prev_p["x"]) <= 1.0:
                    anomalies.append({
                        "type": "SPATIAL_JUMP",
                        "entity": c_name,
                        "scene_id": curr_p["scene_id"],
                        "desc": f"{c_name} transitions from '{prev_p['loc_name']}' to '{curr_p['loc_name']}' in consecutive scenes without travel transition."
                    })

    # 4. Construct Plotly 3D Traces
    traces = []
    palette = ["#f59e0b", "#38bdf8", "#ec4899", "#a855f7", "#10b981", "#fb923c", "#34d399", "#818cf8"]

    # Layer 1: Continuous Character Trajectory Ribbons
    for idx, (cid, cdata) in enumerate(character_trajectories.items()):
        pts = cdata["points"]
        color = palette[idx % len(palette)]
        
        # Ribbons for characters with 2+ points
        if len(pts) >= 2:
            traces.append({
                "type": "scatter3d", "mode": "lines+markers", "name": f"Cast: {cdata['name']}",
                "x": [p["x"] for p in pts], "y": [p["y"] for p in pts], "z": [p["z"] for p in pts],
                "customdata": [p["scene_id"] for p in pts],
                "text": [f"<b>{p['name']}</b><br>Scene: {p['scene_title']}<br>Setting: <b>{p['loc_name']}</b>" for p in pts],
                "hoverinfo": "text",
                "line": {"color": color, "width": 5},
                "marker": {"size": 7, "color": color, "opacity": 0.95}
            })
        else:
            # Standalone point marker for single scene appearances
            traces.append({
                "type": "scatter3d", "mode": "markers", "name": f"Cast: {cdata['name']}",
                "x": [p["x"] for p in pts], "y": [p["y"] for p in pts], "z": [p["z"] for p in pts],
                "customdata": [p["scene_id"] for p in pts],
                "text": [f"<b>{p['name']}</b><br>Scene: {p['scene_title']}<br>Setting: <b>{p['loc_name']}</b>" for p in pts],
                "hoverinfo": "text",
                "marker": {"size": 8, "symbol": "diamond", "color": color, "opacity": 0.95}
            })

    # Layer 2: Physical Convergence Knots (Characters sharing the same room)
    conv_x, conv_y, conv_z, conv_text = [], [], [], []
    for coord, names in co_locations.items():
        unique_names = list(set(names))
        if len(unique_names) >= 2:
            x_val, y_val = coord
            conv_x.append(x_val)
            conv_y.append(y_val)
            conv_z.append(0.55)
            conv_text.append(f"<b>Convergence Knot</b><br>Characters Present: {', '.join(unique_names)}<br>Setting: <b>{active_locations[y_val]}</b>")

    if conv_x and projection_mode in ["ALL", "KINEMATIC"]:
        traces.append({
            "type": "scatter3d", "mode": "markers", "name": "Shared Scenes",
            "x": conv_x, "y": conv_y, "z": conv_z,
            "text": conv_text, "hoverinfo": "text",
            "marker": {"size": 11, "symbol": "diamond", "color": "#22d3ee", "opacity": 0.95}
        })

    # Layer 3: Chekhov Foreshadowing Gravity Wells
    c.execute("""
        SELECT promise_desc, target_tick, target_location, status 
        FROM promises_ledger 
        WHERE book_id = ? AND status != 'DROPPED'
    """, (book_id,))
    promises = c.fetchall()

    for p in promises:
        px = float(p["target_tick"])
        py = loc_to_y.get(p["target_location"], 0)
        traces.append({
            "type": "scatter3d", "mode": "markers", "name": f"Chekhov: {p['promise_desc'][:16]}...",
            "x": [px], "y": [py], "z": [0.92],
            "text": [f"<b>Chekhov Promise</b><br>Promise: {p['promise_desc']}<br>Target Beat: {px}<br>Status: {p['status']}"],
            "hoverinfo": "text",
            "marker": {"size": 12, "symbol": "diamond-open", "color": "#34d399" if p["status"] == "PAID_OFF" else "#ec4899", "line": {"width": 3, "color": "#10b981" if p["status"] == "PAID_OFF" else "#f43f5e"}, "opacity": 0.95}
        })

    # Layer 4: Manuscript Narrative Pacing Spine
    spine_x, spine_y, spine_z, spine_sizes, spine_colors, spine_text = [], [], [], [], [], []
    scene_id_list = []

    for idx, (r, tension) in enumerate(zip(scene_rows, tension_estimates), 1):
        loc_name = scene_location_map[r["id"]]
        y_val = loc_to_y[loc_name]
        is_focal = (focus_scene_id and r["id"] == focus_scene_id)

        spine_x.append(idx)
        spine_y.append(y_val)
        spine_z.append(tension)
        spine_sizes.append(18 if is_focal else max(6, min(14, int(5 + ((r["word_count"] or 0) / 160)))))
        spine_colors.append("#22d3ee" if is_focal else "#f59e0b")
        scene_id_list.append(r["id"])

        hover = (
            f"<b>{r['title']}</b> ({r['ch_title']})<br>"
            f"Setting: <b>{loc_name}</b><br>"
            f"Words: {r['word_count']:,} | Tension: <b>{tension:.2f}</b>"
        )
        spine_text.append(hover)

    traces.append({
        "type": "scatter3d", "mode": "lines+markers",
        "name": "Pacing Spine",
        "x": spine_x, "y": spine_y, "z": spine_z,
        "customdata": scene_id_list,
        "text": spine_text, "hoverinfo": "text",
        "line": {"color": "#fbbf24", "width": 5},
        "marker": {"size": spine_sizes, "color": spine_colors, "symbol": "circle", "opacity": 0.95}
    })

    layout = {
        "autosize": True,
        "paper_bgcolor": "rgba(9, 9, 11, 1)",
        "plot_bgcolor": "rgba(9, 9, 11, 1)",
        "scene": {
            "xaxis": {"title": "Scene Sequence", "color": "#71717a", "gridcolor": "#27272a"},
            "yaxis": {
                "title": "Story Geography",
                "tickvals": list(loc_to_y.values()),
                "ticktext": list(loc_to_y.keys()),
                "color": "#a1a1aa",
                "gridcolor": "#27272a"
            },
            "zaxis": {"title": "Tension Elevation", "range": [0, 1], "color": "#71717a", "gridcolor": "#27272a"},
            "camera": {"eye": {"x": 0.1, "y": -2.3, "z": 1.0}}
        },
        "margin": {"l": 0, "r": 0, "b": 0, "t": 10},
        "legend": {"font": {"color": "#a1a1aa", "size": 11}, "bgcolor": "rgba(18, 18, 20, 0.75)"}
    }

    # 5. Build 2D Subway-Style Transit Matrix Payload
    transit_scenes = [
        {"idx": idx + 1, "id": sc["id"], "title": sc["title"], "chapter": sc["ch_title"], "location": scene_location_map[sc["id"]]}
        for idx, sc in enumerate(scene_rows)
    ]
    transit_characters = [
        {
            "id": cid, "name": cdata["name"],
            "color": palette[idx % len(palette)],
            "stops": [{"scene_idx": p["x"], "scene_title": p["scene_title"], "location": p["loc_name"]} for p in cdata["points"]]
        }
        for idx, (cid, cdata) in enumerate(character_trajectories.items())
    ]

    transit_matrix = {
        "locations": active_locations,
        "scenes": transit_scenes,
        "characters": transit_characters,
    }

    return {
        "data": traces,
        "layout": layout,
        "locations": loc_to_y,
        "anomalies": anomalies,
        "transit_matrix": transit_matrix
    }
