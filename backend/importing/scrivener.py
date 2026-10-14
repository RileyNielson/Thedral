import os
import re
import xml.etree.ElementTree as ET
from backend.importing.text_cleaning import read_file_content, normalize_paragraphs

def parse_scrivener_project(scriv_path: str) -> dict:
    files_map = {}
    legacy_doc = re.compile(
        r"^(\d+)(?:_(synopsis|notes?|annotations?|comments?|references))?\.(?:rtf|txt)$", re.IGNORECASE
    )
    role_names = {
        "synopsis": "synopsis", "note": "notes", "notes": "notes",
        "annotation": "annotations", "annotations": "annotations",
        "comment": "comments", "comments": "comments", "references": "references",
    }
    for root, _, files in os.walk(scriv_path):
        relative_root = os.path.relpath(root, scriv_path).lower()
        if any(x in relative_root for x in ['settings', 'quicklook', 'snapshots']):
            continue
        data_id = os.path.basename(root)
        for f in files:
            full_p = os.path.join(root, f)
            fl = f.lower()
            legacy = legacy_doc.match(f) if data_id.lower() == "docs" else None
            if legacy:
                role = role_names.get((legacy.group(2) or "").lower(), "content")
                files_map.setdefault(legacy.group(1), {})[role] = full_p
            elif fl in ('content.rtf', 'content.txt'):
                files_map.setdefault(data_id, {})['content'] = full_p
            elif fl in ('synopsis.rtf', 'synopsis.txt'):
                files_map.setdefault(data_id, {})['synopsis'] = full_p
            elif fl in ('notes.rtf', 'notes.txt', 'note.rtf', 'note.txt'):
                files_map.setdefault(data_id, {})['notes'] = full_p
            elif fl in ('annotations.rtf', 'annotations.txt', 'annotation.rtf', 'annotation.txt'):
                files_map.setdefault(data_id, {})['annotations'] = full_p
            elif fl in ('comments.rtf', 'comments.txt', 'comment.rtf', 'comment.txt'):
                files_map.setdefault(data_id, {})['comments'] = full_p
            elif fl in ('references.rtf', 'references.txt'):
                files_map.setdefault(data_id, {})['references'] = full_p

    scrivx_files = sorted(f for f in os.listdir(scriv_path) if f.lower().endswith('.scrivx'))
    manuscript_tuples = []
    characters = []
    locations = []
    lore_entries = []
    project_metadata = {}

    if scrivx_files:
        scrivx_path = os.path.join(scriv_path, scrivx_files[0])
        try:
            tree = ET.parse(scrivx_path)
            root = tree.getroot()
            project_metadata.update({
                "scrivx_file": os.path.basename(scrivx_path),
                "project_attributes": dict(root.attrib),
            })

            def xml_value(element):
                children = list(element)
                value = (element.text or "").strip()
                if not children and not element.attrib:
                    return value
                result = {}
                if element.attrib:
                    result["@attributes"] = dict(element.attrib)
                if value:
                    result["#text"] = value
                for child in children:
                    child_value = xml_value(child)
                    if child.tag in result:
                        if not isinstance(result[child.tag], list):
                            result[child.tag] = [result[child.tag]]
                        result[child.tag].append(child_value)
                    else:
                        result[child.tag] = child_value
                return result

            def item_metadata(item_node, title, uuid_val, itype, source_path):
                metadata = {}
                for child in item_node:
                    if child.tag in ("Title", "Children"):
                        continue
                    value = xml_value(child)
                    if child.tag in metadata:
                        if not isinstance(metadata[child.tag], list):
                            metadata[child.tag] = [metadata[child.tag]]
                        metadata[child.tag].append(value)
                    else:
                        metadata[child.tag] = value
                return {
                    "uuid": uuid_val,
                    "type": itype,
                    "title": title,
                    "source_path": source_path,
                    "metadata": metadata,
                }

            project_metadata["metadata"] = {
                child.tag: xml_value(child)
                for child in root
                if child.tag != "Binder"
            }

            def attach_auxiliary_files(metadata, bundle):
                extras = {
                    role: read_file_content(bundle[role])
                    for role in ("annotations", "comments", "references")
                    if bundle.get(role)
                }
                if extras:
                    metadata["external_files"] = extras
                return metadata

            def traverse_folder(item_node, path=()):
                nonlocal manuscript_tuples, characters, locations, lore_entries
                title_node = item_node.find('Title')
                raw_title = title_node.text.strip() if title_node is not None and title_node.text else ""
                title_lower = raw_title.lower()
                itype = item_node.attrib.get('Type', '')
                uuid_val = str(
                    item_node.attrib.get('UUID') or item_node.attrib.get('ID')
                    or item_node.attrib.get('Id') or ""
                )
                item_path = (*path, raw_title) if raw_title else path
                source_metadata = item_metadata(item_node, raw_title, uuid_val, itype, list(item_path))

                is_char_folder = "character" in title_lower or "cast" in title_lower or "people" in title_lower
                is_loc_folder = "place" in title_lower or "location" in title_lower or "setting" in title_lower
                is_lore_folder = "research" in title_lower or "lore" in title_lower or "glossary" in title_lower or "world" in title_lower

                file_bundle = files_map.get(uuid_val, {})
                source_metadata = attach_auxiliary_files(source_metadata, file_bundle)
                content_text = read_file_content(file_bundle.get('content', ''), preserve_formatting=True)
                synopsis_text = read_file_content(file_bundle.get('synopsis', '')) or (item_node.findtext('Synopsis') or '').strip()
                notes_text = read_file_content(file_bundle.get('notes', '')) or (item_node.findtext('Notes') or '').strip()
                if itype.lower() == "folder":
                    project_metadata.setdefault("binder_folders", []).append(source_metadata)

                if is_char_folder:
                    def collect_characters(folder_node, folder_path):
                        children_node = folder_node.find('Children')
                        for child in children_node.findall('BinderItem') if children_node is not None else []:
                            child_title_node = child.find('Title')
                            child_title = child_title_node.text.strip() if child_title_node is not None and child_title_node.text else ""
                            child_uuid = str(child.attrib.get('UUID') or child.attrib.get('Id') or "")
                            child_type = child.attrib.get('Type', '')
                            child_path = (*folder_path, child_title) if child_title else folder_path
                            child_meta = item_metadata(child, child_title, child_uuid, child_type, list(child_path))
                            child_bundle = files_map.get(child_uuid, {})
                            child_meta = attach_auxiliary_files(child_meta, child_bundle)
                            child_content = read_file_content(child_bundle.get('content', ''))
                            child_notes = read_file_content(child_bundle.get('notes', '')) or (child.findtext('Notes') or '').strip()
                            child_synopsis = read_file_content(child_bundle.get('synopsis', '')) or (child.findtext('Synopsis') or '').strip()
                            grandchildren = child.find('Children')
                            if child_type == 'Folder' or grandchildren is not None:
                                collect_characters(child, child_path)
                            elif child_title:
                                characters.append({
                                    "name": child_title,
                                    "bio": child_content or child_notes,
                                    "synopsis": child_synopsis,
                                    "notes": child_notes,
                                    "metadata": child_meta,
                                })
                    collect_characters(item_node, item_path)
                    return

                if is_loc_folder:
                    def collect_locations(folder_node, folder_path):
                        children_node = folder_node.find('Children')
                        for child in children_node.findall('BinderItem') if children_node is not None else []:
                            child_title_node = child.find('Title')
                            child_title = child_title_node.text.strip() if child_title_node is not None and child_title_node.text else ""
                            child_uuid = str(child.attrib.get('UUID') or child.attrib.get('Id') or "")
                            child_type = child.attrib.get('Type', '')
                            child_path = (*folder_path, child_title) if child_title else folder_path
                            child_meta = item_metadata(child, child_title, child_uuid, child_type, list(child_path))
                            child_bundle = files_map.get(child_uuid, {})
                            child_meta = attach_auxiliary_files(child_meta, child_bundle)
                            child_content = read_file_content(child_bundle.get('content', ''))
                            child_notes = read_file_content(child_bundle.get('notes', '')) or (child.findtext('Notes') or '').strip()
                            child_synopsis = read_file_content(child_bundle.get('synopsis', '')) or (child.findtext('Synopsis') or '').strip()
                            grandchildren = child.find('Children')
                            if child_type == 'Folder' or grandchildren is not None:
                                collect_locations(child, child_path)
                            elif child_title:
                                locations.append({
                                    "name": child_title,
                                    "desc": child_content or child_notes,
                                    "synopsis": child_synopsis,
                                    "notes": child_notes,
                                    "metadata": child_meta,
                                })
                    collect_locations(item_node, item_path)
                    return

                if is_lore_folder:
                    def collect_lore(folder_node, folder_path):
                        children_node = folder_node.find('Children')
                        for child in children_node.findall('BinderItem') if children_node is not None else []:
                            child_title_node = child.find('Title')
                            child_title = child_title_node.text.strip() if child_title_node is not None and child_title_node.text else ""
                            child_uuid = str(child.attrib.get('UUID') or child.attrib.get('Id') or "")
                            child_type = child.attrib.get('Type', '')
                            child_path = (*folder_path, child_title) if child_title else folder_path
                            child_meta = item_metadata(child, child_title, child_uuid, child_type, list(child_path))
                            child_bundle = files_map.get(child_uuid, {})
                            child_meta = attach_auxiliary_files(child_meta, child_bundle)
                            child_content = read_file_content(child_bundle.get('content', ''))
                            child_notes = read_file_content(child_bundle.get('notes', '')) or (child.findtext('Notes') or '').strip()
                            child_synopsis = read_file_content(child_bundle.get('synopsis', '')) or (child.findtext('Synopsis') or '').strip()
                            grandchildren = child.find('Children')
                            if child_type == 'Folder' or grandchildren is not None:
                                collect_lore(child, child_path)
                            elif child_title:
                                definition = child_content or child_synopsis or child_notes
                                lore_entries.append({
                                    "term": child_title,
                                    "definition": definition,
                                    "notes": child_notes,
                                    "metadata": child_meta,
                                })
                    collect_lore(item_node, item_path)
                    return

                children = item_node.findall('Children/BinderItem') if item_node.find('Children') is not None else []
                if raw_title.lower() in ('draft', 'manuscript') and children:
                    for child in children:
                        traverse_folder(child, item_path)
                    return
                if itype == 'Folder' or (children and itype != 'Text'):
                    folder_name = raw_title or "Chapter"
                    manuscript_tuples.append((f"Chapter: {folder_name}", True, folder_name, synopsis_text, notes_text, source_metadata))
                    for child in children:
                        traverse_folder(child, item_path)
                elif itype in ['Text', 'Document'] or not children:
                    doc_title = raw_title or "Scene"
                    paras = normalize_paragraphs(content_text)
                    if paras or synopsis_text.strip() or notes_text.strip():
                        manuscript_tuples.append((f"### SCENE_TITLE: {doc_title}", False, doc_title, synopsis_text, notes_text, source_metadata))
                        for p in paras:
                            manuscript_tuples.append((p, False, doc_title, synopsis_text, notes_text))

            binder_node = root.find('Binder')
            target_root = binder_node if binder_node is not None else root
            top_items = target_root.findall('BinderItem')
            if not top_items:
                children_node = target_root.find('Children')
                top_items = children_node.findall('BinderItem') if children_node is not None else []
            for top_item in top_items:
                traverse_folder(top_item)

        except ET.ParseError as e:
            raise ValueError(f"Could not read Scrivener project metadata from {os.path.basename(scrivx_path)}: {e}") from e

    if not manuscript_tuples and files_map:
        for key, bundle in sorted(files_map.items()):
            content_text = read_file_content(bundle.get('content', ''), preserve_formatting=True)
            synopsis_text = read_file_content(bundle.get('synopsis', ''))
            notes_text = read_file_content(bundle.get('notes', ''))
            paras = normalize_paragraphs(content_text)
            if paras or synopsis_text.strip() or notes_text.strip():
                manuscript_tuples.append((f"### SCENE_TITLE: {key}", False, str(key), synopsis_text, notes_text))
                for p in paras:
                    manuscript_tuples.append((p, False, str(key), synopsis_text, notes_text))

    return {
        "manuscript": manuscript_tuples,
        "characters": characters,
        "locations": locations,
        "lore": lore_entries,
        "scrivener": project_metadata,
    }

