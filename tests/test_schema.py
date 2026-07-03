from typing import Any

import pytest
from google.cloud import bigquery

from nfl_bigquery.schema import ColumnSpec, spec_names, to_bq_schema


def _spec(**kw: Any) -> ColumnSpec:
    base: dict[str, Any] = dict(
        name="epa", type="FLOAT64", mode="NULLABLE",
        short_description="Expected points added.",
        business_definition="EPA for the posteam on this play.",
        semantic_tags=["metric"], valid_range=(-15.0, 15.0), valid_values=None,
        example_value=0.42, gotchas=[], source_field="epa",
        dictionary_type="numeric", deprecated_in_year=None,
    )
    base.update(kw)
    return ColumnSpec(**base)


def test_invalid_type_raises():
    with pytest.raises(ValueError):
        _spec(type="STRUCT")


def test_empty_business_definition_raises():
    with pytest.raises(ValueError):
        _spec(business_definition="   ")


def test_to_bq_schema_maps_fields():
    fields = to_bq_schema([_spec()])
    assert isinstance(fields[0], bigquery.SchemaField)
    assert fields[0].name == "epa"
    assert fields[0].field_type == "FLOAT64"
    assert fields[0].mode == "NULLABLE"
    assert fields[0].description == "Expected points added."


def test_spec_names():
    assert spec_names([_spec(name="a"), _spec(name="b")]) == ["a", "b"]
