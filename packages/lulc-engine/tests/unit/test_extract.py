from unittest import mock

from lulc_engine.classify.extract import _iter_feature_pages


def test_pagination_follows_tokens():
    pages = [
        {"features": [{"properties": {"a": 1}}, {"properties": {"a": 2}}], "nextPageToken": "t1"},
        {"features": [{"properties": {"a": 3}}], "nextPageToken": "t2"},
        {"features": [{"properties": {"a": 4}}]},  # no token -> last page
    ]
    calls = []

    def fake_compute(request):
        calls.append(request)
        return pages[len(calls) - 1]

    with mock.patch("ee.data.computeFeatures", side_effect=fake_compute):
        feats = list(_iter_feature_pages("fake_collection", page_size=2))

    assert [f["properties"]["a"] for f in feats] == [1, 2, 3, 4]
    # first call has no token; later calls carry the previous page's token
    assert "pageToken" not in calls[0]
    assert calls[1]["pageToken"] == "t1"
    assert calls[2]["pageToken"] == "t2"


def test_single_page_no_token():
    with mock.patch(
        "ee.data.computeFeatures",
        return_value={"features": [{"properties": {"a": 1}}]},
    ) as m:
        feats = list(_iter_feature_pages("fake_collection"))
    assert len(feats) == 1
    assert m.call_count == 1
