"""Sticker rules (docs/ART_DIRECTION.md §E) against the real library."""
from app.stickers import color_fit, library, pick


def chosen(texts, palette=(), n=3):
    return [p.id for p in pick(list(texts), list(palette), n) if p.chosen]


def test_rainy_day_story_picks_umbrella_cloud_ginkgo():
    texts = ['a moody, rainy day', 'rain', 'Walk in the rain', 'umbrella', 'wet sidewalk', 'Hidden film shop', 'cozy', 'quiet', 'churros', 'trees']
    picks = {p.id: p for p in pick(texts, ['#504138', '#756e61', '#9d9d8d', '#c1c4cb', '#b37e55'])}
    assert [i for i, p in picks.items() if p.chosen] == ['umbrella-yellow', 'cloud-soft', 'ginkgo-leaf']
    assert picks['tree-green'].reason == 'already have one like it'


def test_moods_never_pull_in_a_specific_thing():
    assert 'statue-face-sketch' not in chosen(['quiet', 'pensive', 'calm'])        # a statue needs a museum, not a mood
    assert 'eggs-benedict-watercolor' not in chosen(['cozy', 'morning'])
    assert 'eggs-benedict-watercolor' in chosen(['brunch with eggs benedict'])


def test_colour_alone_only_admits_generic_decoration():
    beige = ['#a08a66', '#c2ac7e', '#7c6a53']
    by_colour = chosen([], beige)
    assert by_colour and all(next(s for s in library() if s['id'] == i)['generic'] for i in by_colour)
    assert chosen([], ['#1d3b8a', '#0b1a40']) == []
    assert color_fit(next(s for s in library() if s['id'] == 'pressed-wildflowers'), beige) > 0.8


def test_one_per_kind_and_one_photographic():
    ids = chosen(['picnic', 'fruit', 'cherries', 'tree', 'park', 'summer', 'apple'], n=4)
    kinds = [next(s for s in library() if s['id'] == i)['kind'] for i in ids]
    assert len(set(kinds)) == len(kinds)
    assert sum('photo' in next(s for s in library() if s['id'] == i)['medium'] for i in ids) <= 1


def test_content_beats_mood():
    # a voice note saying "a light on" and a "curious" mood must not push out the leaf that matches the walk
    texts = ['rain', 'walk', 'umbrella', 'moody', 'We ducked into the first place with a light on', 'curious', 'quiet']
    assert chosen(texts) == ['umbrella-yellow', 'cloud-soft', 'ginkgo-leaf']
