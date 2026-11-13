import json
from pathlib import Path

from copilot.models import ExtractionResult

Path("docs/schemas").mkdir(parents=True, exist_ok=True)
Path("docs/schemas/extraction_result.json").write_text(
    json.dumps(ExtractionResult.model_json_schema(), indent=2)
)
