"""
voice.ai TTS Example - Pronunciation Dictionary Management

This atomic example demonstrates the managed pronunciation-dictionary endpoints:
- `GET /api/v1/tts/pronunciation-dictionaries`
- `POST /api/v1/tts/pronunciation-dictionaries/add-from-file`
- `POST /api/v1/tts/pronunciation-dictionaries/add-from-rules`
- `GET /api/v1/tts/pronunciation-dictionaries/{dictionary_id}`
- `PATCH /api/v1/tts/pronunciation-dictionaries/{dictionary_id}`
- `DELETE /api/v1/tts/pronunciation-dictionaries/{dictionary_id}`
- `GET /api/v1/tts/pronunciation-dictionaries/{dictionary_id}/{version}/download`
- `POST /api/v1/tts/pronunciation-dictionaries/{dictionary_id}/set-rules`
- `POST /api/v1/tts/pronunciation-dictionaries/{dictionary_id}/add-rules`
- `POST /api/v1/tts/pronunciation-dictionaries/{dictionary_id}/remove-rules`

What this file shows:
- how to create a pronunciation dictionary from rules
- how to optionally create one from a `.pls` file
- how to list and fetch dictionaries
- how to rename, replace rules, add rules, and remove rules by `rule_id`
- how to download a specific version as a `.pls` file
- how to optionally delete the created dictionaries

Usage:
    python tts_pronunciation_dictionary_crud.py
"""

from pathlib import Path

import requests

# Configuration
API_BASE_URL = "https://dev.voice.ai"
# API_BASE_URL = "http://localhost:8000"  # Local/self-hosted override
API_KEY = "YOUR_API_KEY_HERE"

# Create-from-rules request
CREATE_FROM_RULES_NAME = "Dictionary Example"
CREATE_FROM_RULES_LANGUAGE = "en"
INITIAL_RULES = [
    {
        "word": "Thailand",
        "replacement": "tie-land",
        "case_sensitive": True,
    },
    {
        "word": "router",
        "replacement": "row-ter",
        "ipa": "ˈraʊtɚ",
        "case_sensitive": False,
    },
]

# Optional create-from-file request. Leave as None to skip the upload example.
PLS_FILE_PATH = None
PLS_DICTIONARY_NAME = "Imported Dictionary"
PLS_DICTIONARY_LANGUAGE = "en"

# Rename example
RENAMED_DICTIONARY_NAME = "Dictionary Example Renamed"

# Rule mutation examples
SET_RULES = [
    {
        "word": "SQL",
        "replacement": "sequel",
        "case_sensitive": False,
    },
    {
        "word": "gif",
        "replacement": "ghif",
        "case_sensitive": False,
    },
]
ADDITIONAL_RULES = [
    {
        "word": "gif",
        "replacement": "jif",
        "case_sensitive": False,
    },
]
REMOVE_RULE_MATCH = {
    "word": "gif",
    "replacement": "jif",
}

DOWNLOAD_OUTPUT_DIR = Path(".")
DELETE_DICTIONARIES_AT_END = False

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
}


def create_dictionary_from_rules(name: str, language: str, rules: list[dict]) -> dict:
    """Create a managed pronunciation dictionary from rule input."""
    print(f"Creating dictionary from rules: {name}")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/add-from-rules",
        headers=HEADERS,
        json={
            "name": name,
            "language": language,
            "rules": rules,
        },
    )
    response.raise_for_status()
    dictionary = response.json()
    print(
        f"✓ Created dictionary {dictionary['id']} "
        f"(current_version={dictionary['current_version']})"
    )
    return dictionary


def create_dictionary_from_file(file_path: str, name: str, language: str) -> dict:
    """Create a managed pronunciation dictionary from a local PLS file."""
    print(f"Creating dictionary from PLS file: {file_path}")
    with open(file_path, "rb") as file_handle:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/add-from-file",
            headers=HEADERS,
            files={"file": (Path(file_path).name, file_handle, "application/pls+xml")},
            data={
                "name": name,
                "language": language,
            },
        )
    response.raise_for_status()
    dictionary = response.json()
    print(
        f"✓ Imported dictionary {dictionary['id']} "
        f"(current_version={dictionary['current_version']})"
    )
    return dictionary


def list_dictionaries() -> list[dict]:
    """List pronunciation dictionaries accessible to the authenticated user."""
    print("Listing pronunciation dictionaries...")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries",
        headers=HEADERS,
    )
    response.raise_for_status()
    dictionaries = response.json()
    print(f"✓ Found {len(dictionaries)} dictionary(ies)")
    for dictionary in dictionaries:
        print(
            f"  - {dictionary['id']}: {dictionary['name']} "
            f"(language={dictionary['language']}, version={dictionary['current_version']})"
        )
    return dictionaries


def get_dictionary(dictionary_id: str) -> dict:
    """Fetch one pronunciation dictionary by ID."""
    print(f"Getting dictionary: {dictionary_id}")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/{dictionary_id}",
        headers=HEADERS,
    )
    response.raise_for_status()
    dictionary = response.json()
    print(
        f"✓ Dictionary {dictionary['id']} has {len(dictionary.get('rules', []))} rule(s) "
        f"and {len(dictionary.get('versions', []))} version(s)"
    )
    return dictionary


def rename_dictionary(dictionary_id: str, name: str) -> dict:
    """Rename a pronunciation dictionary."""
    print(f"Renaming dictionary {dictionary_id} -> {name}")
    response = requests.patch(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/{dictionary_id}",
        headers=HEADERS,
        json={"name": name},
    )
    response.raise_for_status()
    dictionary = response.json()
    print(f"✓ Renamed dictionary to {dictionary['name']}")
    return dictionary


def set_rules(dictionary_id: str, rules: list[dict]) -> dict:
    """Replace the active rule set."""
    print(f"Replacing rules for dictionary: {dictionary_id}")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/{dictionary_id}/set-rules",
        headers=HEADERS,
        json={"rules": rules},
    )
    response.raise_for_status()
    dictionary = response.json()
    print(
        f"✓ Replaced rules. Current version is now {dictionary['current_version']} "
        f"with {len(dictionary.get('rules', []))} rule(s)"
    )
    return dictionary


def add_rules(dictionary_id: str, rules: list[dict]) -> dict:
    """Append rules to the active rule set."""
    print(f"Adding rules to dictionary: {dictionary_id}")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/{dictionary_id}/add-rules",
        headers=HEADERS,
        json={"rules": rules},
    )
    response.raise_for_status()
    dictionary = response.json()
    print(
        f"✓ Added rules. Current version is now {dictionary['current_version']} "
        f"with {len(dictionary.get('rules', []))} rule(s)"
    )
    return dictionary


def remove_rules(dictionary_id: str, rule_ids: list[str]) -> dict:
    """Remove rules by stable rule ID."""
    print(f"Removing {len(rule_ids)} rule(s) from dictionary: {dictionary_id}")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/{dictionary_id}/remove-rules",
        headers=HEADERS,
        json={"rule_ids": rule_ids},
    )
    response.raise_for_status()
    dictionary = response.json()
    print(
        f"✓ Removed rules. Current version is now {dictionary['current_version']} "
        f"with {len(dictionary.get('rules', []))} rule(s)"
    )
    return dictionary


def download_dictionary_version(dictionary_id: str, version: int, output_dir: Path) -> Path:
    """Download one dictionary version as a `.pls` file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{dictionary_id}-v{version}.pls"
    print(f"Downloading dictionary {dictionary_id} version {version} -> {output_path}")
    response = requests.get(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/{dictionary_id}/{version}/download",
        headers=HEADERS,
        stream=True,
    )
    response.raise_for_status()
    with output_path.open("wb") as file_handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_handle.write(chunk)
    print(f"✓ Downloaded {output_path} ({output_path.stat().st_size} bytes)")
    return output_path


def delete_dictionary(dictionary_id: str) -> None:
    """Delete a pronunciation dictionary."""
    print(f"Deleting dictionary: {dictionary_id}")
    response = requests.delete(
        f"{API_BASE_URL}/api/v1/tts/pronunciation-dictionaries/{dictionary_id}",
        headers=HEADERS,
    )
    response.raise_for_status()
    print(f"✓ Deleted dictionary {dictionary_id}")


def find_rule_ids(dictionary: dict, *, word: str, replacement: str) -> list[str]:
    """Return rule IDs matching one word/replacement pair from the current detail payload."""
    rule_ids = []
    for rule in dictionary.get("rules", []):
        if rule.get("word") == word and rule.get("replacement") == replacement:
            rule_ids.append(rule["id"])
    return rule_ids


def main() -> None:
    print("=" * 60)
    print("voice.ai TTS Example: Pronunciation Dictionary Management")
    print("=" * 60)

    created_dictionary_ids: list[str] = []

    try:
        dictionary = create_dictionary_from_rules(
            name=CREATE_FROM_RULES_NAME,
            language=CREATE_FROM_RULES_LANGUAGE,
            rules=INITIAL_RULES,
        )
        created_dictionary_ids.append(dictionary["id"])

        list_dictionaries()
        dictionary = get_dictionary(dictionary["id"])
        dictionary = rename_dictionary(dictionary["id"], RENAMED_DICTIONARY_NAME)
        dictionary = set_rules(dictionary["id"], SET_RULES)
        dictionary = add_rules(dictionary["id"], ADDITIONAL_RULES)

        rule_ids_to_remove = find_rule_ids(
            dictionary,
            word=REMOVE_RULE_MATCH["word"],
            replacement=REMOVE_RULE_MATCH["replacement"],
        )
        if rule_ids_to_remove:
            dictionary = remove_rules(dictionary["id"], [rule_ids_to_remove[0]])
        else:
            print("! Skipping remove-rules because no matching rule ID was found")

        download_dictionary_version(
            dictionary_id=dictionary["id"],
            version=dictionary["current_version"],
            output_dir=DOWNLOAD_OUTPUT_DIR,
        )

        if PLS_FILE_PATH is not None:
            imported_dictionary = create_dictionary_from_file(
                file_path=PLS_FILE_PATH,
                name=PLS_DICTIONARY_NAME,
                language=PLS_DICTIONARY_LANGUAGE,
            )
            created_dictionary_ids.append(imported_dictionary["id"])
            get_dictionary(imported_dictionary["id"])

        if DELETE_DICTIONARIES_AT_END:
            for dictionary_id in reversed(created_dictionary_ids):
                delete_dictionary(dictionary_id)

        print("\n" + "=" * 60)
        print("Pronunciation dictionary operations complete!")
        print("=" * 60)

    except requests.exceptions.HTTPError as exc:
        print(f"✗ HTTP Error: {exc}")
        if exc.response is not None:
            print(f"  Response: {exc.response.text}")
    except FileNotFoundError:
        print(f"✗ PLS file not found: {PLS_FILE_PATH}")
        print("  Please update PLS_FILE_PATH at the top of the script")
    except Exception as exc:
        print(f"✗ Error: {exc}")


if __name__ == "__main__":
    main()
