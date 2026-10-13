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
            
            # Pack scene_id, beat number, and text snippet for click navigation
            beats_customdata.append({
                "scene_id": sc_id,
                "beat_idx": p_idx,
                "snippet": snippet
            })

            hover_info = (
                f"<b>{sc_title}</b> (Beat {p_idx})<br>"
                f"{mode_label}<br>"
                f"Text-derived tension estimate: <b>{tension_estimate:.2f}</b> ({words}w)<br>"
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
            "zaxis": {"title": "Text-derived tension estimate", "range": [0, 1], "color": "#71717a", "gridcolor": "#27272a"},
            "camera": {"eye": {"x": 1.1, "y": -1.5, "z": 0.8}}
        },
        "margin": {"l": 0, "r": 0, "b": 0, "t": 0}
    }

    return {"data": traces, "layout": layout, "locations": loc_to_y, "anomalies": []}


# =============================================================================
# 2. MACRO COSMOGRAPH (Full Manuscript 8-Layer Spacetime)
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
        return {"data": [], "layout": {}, "locations": {}, "anomalies": []}

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
        return {"data": [], "layout": {}, "locations": {}, "anomalies": []}

    total_scenes = len(scene_rows)
    scene_seq_map = {r["id"]: idx + 1 for idx, r in enumerate(scene_rows)}

    # Fetch canonical locations
    c.execute("SELECT entity_id, name, aliases, entity_type FROM canonical_entities WHERE entity_type = 'LOCATION' ORDER BY rowid ASC")
    location_entities = [dict(r) for r in c.fetchall()]
    canonical_locations = [entity["name"].strip() for entity in location_entities]

    scene_ids = [r["id"] for r in scene_rows]
    placeholders = ",".join(["?"] * len(scene_ids))
    
    c.execute(f"""
        SELECT w.event_id, w.entity_id, w.timeline_tick, w.scene_id, w.state_delta, w.epistemic_tier, w.carrier_id, 
               e.name, e.entity_type
        FROM canonical_worldlines w
        JOIN canonical_entities e ON w.entity_id = e.entity_id
        WHERE w.scene_id IN ({placeholders})
        ORDER BY w.timeline_tick ASC
    """, scene_ids)
    events = c.fetchall()

    worldline_locations = []
    scene_actual_ticks = {}

    for ev in events:
        try:
            d = json.loads(ev["state_delta"])
            raw_location = d.get("location", "").strip()
            known_location = next(
                (loc["name"] for loc in location_entities if _mentions_entity(raw_location, loc)),
                None,
            )
            loc_val = known_location or raw_location.title()
            if loc_val and loc_val not in worldline_locations and loc_val not in canonical_locations:
                worldline_locations.append(loc_val)
            # Record actual chronological tick for each scene
            sc_id = ev["scene_id"]
            if sc_id not in scene_actual_ticks:
                scene_actual_ticks[sc_id] = float(ev["timeline_tick"])
        except Exception:
            pass

    locations = []
    for loc in canonical_locations + worldline_locations:
        if loc and loc not in locations:
            locations.append(loc)

    if not locations:
        locations = ["Unspecified"]
    elif "Unspecified" not in locations:
        locations.append("Unspecified")

    loc_to_y = {loc: idx for idx, loc in enumerate(locations)}

    scene_location_map = {}

    for sc in scene_rows:
        sc_id = sc["id"]
        sc_content = html_to_text(sc["content"] or "")
        matched_loc = None

        for loc in location_entities:
            if _mentions_entity(sc_content, loc) or _mentions_entity(sc["title"], loc):
                matched_loc = loc["name"]
                break

        if not matched_loc:
            for ev in events:
                if ev["scene_id"] == sc_id:
                    try:
                        d = json.loads(ev["state_delta"])
                        if "location" in d:
                            canonical_location = next(
                                (loc["name"] for loc in location_entities if _mentions_entity(d["location"], loc)),
                                d["location"],
                            )
                            if canonical_location in loc_to_y:
                                matched_loc = canonical_location
                                break
                    except Exception:
                        pass

        scene_location_map[sc_id] = matched_loc or "Unspecified"

    # The arc reflects text-derived telemetry; it does not model reader response.
    tension_estimates = []
    prev_tens = 0.35

    for sc in scene_rows:
        metric = calculate_text_telemetry(sc["content"] or "", prev_tens)
        scene_telemetry[sc["id"]] = metric
        prev_tens = metric["tension_elevation"]
        tension_estimates.append(metric["tension_elevation"])

    character_events = {}
    artifact_events = {}
    co_locations = {}
    anomalies = []

    for ev in events:
        eid = ev["entity_id"]
        etype = ev["entity_type"]
        tick = float(ev["timeline_tick"])
        x_val = tick if time_mode == "chronological" else float(scene_seq_map.get(ev["scene_id"], 1.0))

        loc_name = scene_location_map.get(ev["scene_id"], locations[0])
        health_val = 1.0
        try:
            d = json.loads(ev["state_delta"])
            if "location" in d:
                canonical_location = next(
                    (loc["name"] for loc in location_entities if _mentions_entity(d["location"], loc)),
                    d["location"],
                )
                if canonical_location in loc_to_y:
                    loc_name = canonical_location
            health_val = float(d.get("health_score", 1.0))
        except Exception:
            pass

        y_val = loc_to_y.get(loc_name, 0)
        sc_idx = scene_seq_map.get(ev["scene_id"], 1) - 1
        z_val = tension_estimates[sc_idx] if 0 <= sc_idx < len(tension_estimates) else 0.45

        pt = {
            "x": x_val, "y": y_val, "z": z_val, "tick": tick,
            "scene_id": ev["scene_id"], "loc_name": loc_name,
            "health": health_val, "name": ev["name"], "tier": ev["epistemic_tier"]
        }

        if etype == "CHARACTER":
            if eid not in character_events:
                character_events[eid] = {"name": ev["name"], "points": []}
            character_events[eid]["points"].append(pt)

            coord_key = (round(x_val, 2), y_val)
            if coord_key not in co_locations:
                co_locations[coord_key] = []
            co_locations[coord_key].append(ev["name"])

            if health_val < 0.40 and z_val > 0.70:
                anomalies.append({
                    "type": "POTENTIAL_STRAIN_CONTINUITY", "entity": ev["name"], "scene_id": ev["scene_id"],
                    "desc": f"Mapped state data places {ev['name']} in a scene with a text-derived tension estimate of {z_val:.2f} while vitality is {int(health_val*100)}%. Check whether that combination matches the prose."
                })

        elif etype == "ITEM":
            if eid not in artifact_events:
                artifact_events[eid] = {"name": ev["name"], "points": [], "carrier": ev["carrier_id"]}
            artifact_events[eid]["points"].append(pt)

    c.execute("SELECT entity_id, name, aliases, entity_type FROM canonical_entities WHERE entity_type = 'CHARACTER' ORDER BY rowid ASC")
    text_traces = {}
    for entity in c.fetchall():
        mapped_scenes = {
            point["scene_id"]
            for point in character_events.get(entity["entity_id"], {}).get("points", [])
        }
        points = []
        for scene in scene_rows:
            scene_text = html_to_text(scene["content"] or "")
            if scene["id"] in mapped_scenes or not _mentions_entity(scene_text, entity):
                continue
            scene_id = scene["id"]
            tick = scene_actual_ticks.get(scene_id, float(scene_seq_map[scene_id]))
            scene_index = scene_seq_map[scene_id] - 1
            tension = tension_estimates[scene_index] if 0 <= scene_index < len(tension_estimates) else 0.45
            loc_name = scene_location_map.get(scene_id, "Unspecified")
            points.append({
                "x": tick if time_mode == "chronological" else float(scene_seq_map[scene_id]),
                "y": loc_to_y.get(loc_name, loc_to_y["Unspecified"]),
                "z": tension,
                "scene_id": scene_id,
                "name": entity["name"],
                "loc_name": loc_name,
            })
        if points:
            text_traces[entity["entity_id"]] = {"name": entity["name"], "points": points}

    traces = []
    palette = ["#f59e0b", "#38bdf8", "#ec4899", "#a855f7", "#10b981", "#fb923c", "#34d399"]

    # Layer 1: Character Trajectory Ribbons
    for idx, (eid, cdata) in enumerate(character_events.items()):
        pts = cdata["points"]
        if not pts: continue

        for i in range(1, len(pts)):
            prev, curr = pts[i-1], pts[i]
            if prev["y"] != curr["y"] and (curr["tick"] - prev["tick"]) <= 0.05:
                anomalies.append({
                    "type": "SPATIAL_TELEPORTATION", "entity": cdata["name"], "scene_id": curr["scene_id"],
                    "desc": f"{cdata['name']} traversed between '{prev['loc_name']}' and '{curr['loc_name']}' with 0.0 elapsed story days."
                })

        color = palette[idx % len(palette)]
        is_focal = (projection_mode in ["ALL", "KINEMATIC", "SOMATIC", "SYNAPTIC"])
        opacity = 1.0 if is_focal else 0.08
        width = 6 if is_focal else 2

        traces.append({
            "type": "scatter3d", "mode": "lines+markers", "name": f"Actor: {cdata['name']}",
            "x": [p["x"] for p in pts], "y": [p["y"] for p in pts], "z": [p["z"] for p in pts],
            "customdata": [p["scene_id"] for p in pts],
            "text": [f"<b>{p['name']}</b><br>Location: {p['loc_name']}<br>Day: {p['tick']:.1f}<br>Vitality: {int(p['health']*100)}%" for p in pts],
            "hoverinfo": "text",
            "line": {"color": color, "width": width},
            "marker": {"size": 7, "color": color, "opacity": opacity},
            "opacity": opacity
        })

    for idx, cdata in enumerate(text_traces.values()):
        pts = cdata["points"]
        traces.append({
            "type": "scatter3d", "mode": "markers", "name": f"Text mentions: {cdata['name']}",
            "x": [point["x"] for point in pts],
            "y": [point["y"] for point in pts],
            "z": [point["z"] for point in pts],
            "customdata": [point["scene_id"] for point in pts],
            "text": [
                f"<b>{point['name']}</b> is named in this scene<br>Text-matched setting: {point['loc_name']}"
                for point in pts
            ],
            "hoverinfo": "text",
            "marker": {"size": 6, "symbol": "circle-open", "color": palette[idx % len(palette)], "opacity": 0.8},
        })

    # Layer 2: Relic Custody Braiding
    for idx, (aid, adata) in enumerate(artifact_events.items()):
        pts = adata["points"]
        if not pts: continue
        is_focal = (projection_mode in ["ALL", "CUSTODY"])
        opacity = 1.0 if is_focal else 0.05

        traces.append({
            "type": "scatter3d", "mode": "lines+markers", "name": f"Relic: {adata['name']}",
            "x": [p["x"] for p in pts], "y": [p["y"] for p in pts], "z": [p["z"] for p in pts],
            "customdata": [p["scene_id"] for p in pts],
            "text": [f"<b>Relic: {adata['name']}</b><br>Held in: {p['loc_name']}<br>Day: {p['tick']:.1f}" for p in pts],
            "hoverinfo": "text",
            "line": {"color": "#f8fafc", "width": 4, "dash": "dash"},
            "marker": {"size": 6, "color": "#f8fafc", "symbol": "diamond", "opacity": opacity},
            "opacity": opacity
        })

    # Layer 3: Physical Convergence Knots
    conv_x, conv_y, conv_z, conv_text = [], [], [], []
    for coord, names in co_locations.items():
        if len(set(names)) >= 2:
            x_val, y_val = coord
            conv_x.append(x_val)
            conv_y.append(y_val)
            conv_z.append(0.55)
            conv_text.append(f"<b>Convergence Knot</b><br>Meeting: {', '.join(set(names))}<br>Location: <b>{locations[y_val]}</b>")

    if conv_x and projection_mode in ["ALL", "KINEMATIC"]:
        traces.append({
            "type": "scatter3d", "mode": "markers", "name": "Convergence Knots",
            "x": conv_x, "y": conv_y, "z": conv_z,
            "text": conv_text, "hoverinfo": "text",
            "marker": {"size": 11, "symbol": "diamond", "color": "#38bdf8", "opacity": 0.95}
        })

    # Layer 4: Chekhov Foreshadowing Gravity Wells
    c.execute("""
        SELECT promise_desc, target_tick, target_location, status 
        FROM promises_ledger 
        WHERE book_id = ? OR series_id = 'default'
    """, (book_id,))
    promises = c.fetchall()

    for p in promises:
        px = float(p["target_tick"]) if time_mode == "chronological" else 5.0
        py = loc_to_y.get(p["target_location"], 0)
        is_focal = (projection_mode in ["ALL", "FORESHADOW"])
        opacity = 0.95 if is_focal else 0.08

        traces.append({
            "type": "scatter3d", "mode": "markers", "name": f"Chekhov: {p['promise_desc'][:16]}...",
            "x": [px], "y": [py], "z": [0.92],
            "text": [f"<b>Chekhov Gravity Well</b><br>Promise: {p['promise_desc']}<br>Target Day: {px}<br>Status: {p['status']}"],
            "hoverinfo": "text",
            "marker": {"size": 13, "symbol": "diamond-open", "color": "#ec4899", "line": {"width": 3, "color": "#f43f5e"}, "opacity": opacity}
        })

    # Layer 5: Dynamic Event Horizon Deadlines
    if projection_mode in ["ALL", "DEADLINES"] and time_mode == "chronological":
        c.execute("SELECT title, deadline_tick, urgency_level FROM story_deadlines WHERE book_id = ? AND status = 'ACTIVE'", (book_id,))
        deadlines = c.fetchall()
        for dl in deadlines:
            dl_tick = float(dl["deadline_tick"])
            dl_name = dl["title"]
            traces.append({
                "type": "scatter3d", "mode": "lines", "name": f"Deadline: {dl_name}",
                "x": [dl_tick, dl_tick, dl_tick, dl_tick],
                "y": [0, len(locations)-1, len(locations)-1, 0],
                "z": [0.05, 0.05, 0.95, 0.95],
                "line": {"color": "#ef4444", "width": 4, "dash": "dot"},
                "text": [f"<b>Event Horizon:</b> {dl_name}<br>Tick: Day {dl_tick:.1f}"] * 4,
                "hoverinfo": "text"
            })

    # Layer 6: Text-derived tension-estimate spine
    spine_x, spine_y, spine_z, spine_sizes, spine_colors, spine_text = [], [], [], [], [], []
    scene_id_list = []

    for idx, (r, tension_estimate) in enumerate(zip(scene_rows, tension_estimates), 1):
        # In chronological mode, leap to actual story tick if known (handles flashbacks!)
        if time_mode == "chronological":
            x_story = scene_actual_ticks.get(r["id"], idx * 0.5)
        else:
            x_story = idx

        loc_name = scene_location_map.get(r["id"], locations[0])
        y_val = loc_to_y.get(loc_name, 0)
        metric = scene_telemetry.get(r["id"]) or calculate_text_telemetry(r["content"] or "")

        point_color = "#22d3ee" if (focus_scene_id and r["id"] == focus_scene_id) else "#f59e0b"
        node_size = 20 if (focus_scene_id and r["id"] == focus_scene_id) else max(6, min(16, int(6 + ((r["word_count"] or 0) / 160))))

        spine_x.append(x_story)
        spine_y.append(y_val)
        spine_z.append(tension_estimate)
        spine_sizes.append(node_size)
        spine_colors.append(point_color)
        scene_id_list.append(r["id"])

        hover = (
            f"<b>{r['title']}</b><br>"
            f"Corridor: <b>{loc_name}</b><br>"
            f"Words: {r['word_count']:,} | Text-derived tension estimate: <b>{tension_estimate:.2f}</b>"
        )
        spine_text.append(hover)

    # Narrative Spacetime Spine
    traces.append({
        "type": "scatter3d", "mode": "lines+markers",
        "name": "Narrative Spacetime Spine",
        "x": spine_x, "y": spine_y, "z": spine_z,
        "customdata": scene_id_list,
        "text": spine_text, "hoverinfo": "text",
        "line": {"color": "#fbbf24", "width": 6},
        "marker": {
            "size": spine_sizes,
            "color": spine_colors,
            "symbol": "circle",
            "opacity": 0.95
        }
    })

    layout = {
        "autosize": True,
        "paper_bgcolor": "rgba(9, 9, 11, 1)",
        "plot_bgcolor": "rgba(9, 9, 11, 1)",
        "scene": {
            "xaxis": {"title": "Story Timeline (Days)" if time_mode == "chronological" else "Reading Sequence", "color": "#71717a", "gridcolor": "#27272a"},
            "yaxis": {
                "title": "Story Geography",
                "tickvals": list(loc_to_y.values()),
                "ticktext": list(loc_to_y.keys()),
                "color": "#a1a1aa",
                "gridcolor": "#27272a"
            },
            "zaxis": {"title": "Text-derived tension estimate (heuristic)", "range": [0, 1], "color": "#71717a", "gridcolor": "#27272a"},
            "camera": {"eye": {"x": 0.1, "y": -2.3, "z": 1.0}}
        },
        "margin": {"l": 0, "r": 0, "b": 0, "t": 10},
        "legend": {"font": {"color": "#a1a1aa", "size": 11}, "bgcolor": "rgba(18, 18, 20, 0.75)"}
    }

    return {"data": traces, "layout": layout, "locations": loc_to_y, "anomalies": anomalies}