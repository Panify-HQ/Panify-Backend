from typing import Any

from pydantic import BaseModel


def build_openapi_examples(
    schema: type[BaseModel],
    labels: dict[str, str],
) -> dict[str, dict[str, Any]]:
    schema_examples = schema.model_config.get("json_schema_extra", {}).get(
        "examples", []
    )
    if len(schema_examples) != len(labels):
        raise ValueError(
            f"{schema.__name__} has {len(schema_examples)} schema examples "
            f"but {len(labels)} OpenAPI labels."
        )

    return {
        name: {"summary": summary, "value": example}
        for (name, summary), example in zip(labels.items(), schema_examples)
    }
