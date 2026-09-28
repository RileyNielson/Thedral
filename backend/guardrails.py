import re

# =============================================================================
# 1. CLUTTER & AMBIENT NOUN LEXICONS
# =============================================================================

# Everyday objects, furniture, foodstuffs, and materials that local models
# commonly mistake for named characters or significant plot artifacts.
CLUTTER_NOUNS = {
    'crutches', 'crutch', 'table', 'chair', 'bed', 'door', 'latch', 'carpet', 'rug',
    'window', 'balcony', 'glass', 'mirror', 'candle', 'tallow', 'tea', 'pie', 'meat pie',
    'bread', 'ale', 'wine', 'meat', 'stew', 'plate', 'cup', 'bottle', 'boots', 'boot',
    'gloves', 'glove', 'coat', 'cloak', 'hat', 'shirt', 'pants', 'trousers', 'collar',
    'scabbard', 'holster', 'bandage', 'bandages', 'wound', 'blood', 'stone', 'flagstone',
    'wall', 'ceiling', 'floor', 'roof', 'rooftop', 'chimney', 'bell', 'bells', 'rope',
    'twine', 'chain', 'iron', 'brass', 'copper', 'gold', 'silver', 'slate', 'marble',
    'carriage', 'wagon', 'horse', 'cart', 'ship', 'airship', 'hull', 'valve', 'engine',
    'pipe', 'lantern', 'lamp', 'desk', 'bench', 'steps', 'stairs', 'hall', 'hallway'
}

# Generic non-specific descriptors that lack distinct persistent identity
GENERIC_DESCRIPTORS = {
    'man', 'woman', 'boy', 'girl', 'child', 'someone', 'guard', 'guards',
    'watchmen', 'watchman', 'soldier', 'soldiers', 'stranger', 'strangers',
    'officer', 'officers', 'crew', 'sailor', 'sailors', 'clerk', 'clerks'
}

# =============================================================================
# 2. VALIDATION & SANITIZATION ENGINE
# =============================================================================

def is_valid_character_name(name: str) -> bool:
    """
    Verifies that an extracted candidate string represents an actual sentient persona.
    Rejects common objects, food, furniture, body parts, and generic un-named mobs.
    """
    if not name or len(name.strip()) < 2:
        return False
        
    clean = name.strip().lower()
    
    # Strip leading English articles
    clean = re.sub(r'^(the|a|an)\s+', '', clean).strip()
    
    # Direct blacklist check
    if clean in CLUTTER_NOUNS or clean in GENERIC_DESCRIPTORS:
        return False
        
    # Check regular English plural inflections (e.g. 'crutches' -> 'crutch')
    if clean.endswith('es') and clean[:-2] in CLUTTER_NOUNS:
        return False
    if clean.endswith('s') and clean[:-1] in CLUTTER_NOUNS:
        return False

    return True

def sanitize_entity_type(name: str, proposed_type: str | None = None) -> str:
    """
    Normalizes and classifies an entity string into an authoritative taxonomy:
    - 'CHARACTER': Verified sentient individuals.
    - 'ITEM': Crucial plot devices, weapons, keys, documents.
    - 'LOCATION': Named physical environments or structures.
    - 'CLUTTER': Rejected ambient noise (food, furniture, common nouns).
    """
    if not name or not name.strip():
        return "CLUTTER"

    clean = name.strip().lower()
    clean = re.sub(r'^(the|a|an)\s+', '', clean).strip()

    if clean in CLUTTER_NOUNS:
        return "CLUTTER"

    raw_type = (proposed_type or "CHARACTER").strip().upper()
    if raw_type not in ["CHARACTER", "ITEM", "LOCATION"]:
        raw_type = "CHARACTER"

    # Demote invalid character names to CLUTTER
    if raw_type == "CHARACTER" and not is_valid_character_name(name):
        return "CLUTTER"

    return raw_type
