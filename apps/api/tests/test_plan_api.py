import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app, load_demo_plan
from app.models import ResolvedVisualPlan

client = TestClient(app)


def test_api_serves_validated_resolved_fixture():
    response = client.get('/api/plans/demo')
    assert response.status_code == 200
    plan = ResolvedVisualPlan.model_validate(response.json())
    assert plan == load_demo_plan()
    assert plan.canvas.width == 1600 and plan.canvas.height == 1000
    assert any(element.kind == 'photo' for element in plan.elements)
    assert all(element.source_ids for element in plan.elements if element.kind != 'decoration')


@pytest.mark.parametrize('case', [
    'draft', 'unresolved_asset', 'missing_source', 'chrome_source', 'duplicate_id',
    'outside_canvas', 'gutter', 'small_type', 'overlap', 'extend_without_mask', 'nonfinite',
])
def test_rejects_unrenderable_plans(case):
    data = deepcopy(load_demo_plan().model_dump())
    photo, title, quote, motif = (data['elements'][i] for i in [1, 2, 3, 5])
    if case == 'draft': data['status'] = 'draft'
    elif case == 'unresolved_asset': del motif['asset_ref']
    elif case == 'missing_source': photo['source_ids'] = []
    elif case == 'chrome_source': data['elements'][0]['source_ids'] = ['invented']
    elif case == 'duplicate_id': quote['id'] = title['id']
    elif case == 'outside_canvas': photo['bounds']['x'] = 1599
    elif case == 'gutter': title['bounds']['x'] = 790
    elif case == 'small_type': title['font_size_px'] = 19
    elif case == 'overlap': quote['bounds'] = title['bounds']
    elif case == 'extend_without_mask': photo['treatment'] = 'EXTEND'
    elif case == 'nonfinite': photo['bounds']['x'] = float('nan')
    with pytest.raises(ValidationError):
        ResolvedVisualPlan.model_validate(data)


def test_exported_openapi_matches_canonical_models():
    saved = Path(__file__).parents[1] / 'openapi.json'
    assert json.loads(saved.read_text()) == app.openapi()
