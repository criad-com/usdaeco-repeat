"""Deterministic geometric matching across a derived registration transform."""
import math
from .model import (close, deviation_members, elements, match_key, matrix_error,
                    offset_for, prototype, reason, shape, value, world)


def compare(instance, tolerance=1e-6):
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('tolerance must be positive and finite')
    proto = prototype(instance)
    offset = offset_for(proto, instance)
    left, right = elements(proto), elements(instance)
    shapes = {p.GetPath(): shape(p) for p in left+right}
    pairs, changes = [], []
    # Closest equal placements first, then equal shapes (movement), then changes.
    # Sorting makes deterministic tie-breaking visible in the path pairs.
    for mode in ('placement', 'shape', 'remaining'):
        candidates = []
        for a in left:
            for b in right:
                if match_key(a) != match_key(b):
                    continue
                distance = matrix_error(world(a)*offset, world(b))
                same = close(shapes[a.GetPath()], shapes[b.GetPath()], tolerance)
                if mode == 'placement' and distance > tolerance:
                    continue
                if mode == 'shape' and not same:
                    continue
                candidates.append((distance, str(a.GetPath()), str(b.GetPath()), a, b, same))
        for distance, _, _, a, b, same in sorted(candidates, key=lambda c:c[:3]):
            if a not in left or b not in right:
                continue
            left.remove(a); right.remove(b)
            pairs.append((a,b))
            if distance <= tolerance and same:
                continue
            kind = 'moved' if same else 'changed'
            changes.append(_finding(kind, a, b, distance, instance))
    changes += [_finding('missing', a, None, None, instance) for a in left]
    changes += [_finding('extra', None, b, None, instance) for b in right]
    return {'prototype': str(proto.GetPath()), 'instance': str(instance.GetPath()),
            'offset': [list(row) for row in offset],
            'matches': [{'prototype':str(a.GetPath()), 'instance':str(b.GetPath())} for a,b in pairs],
            'declared_deviations': len(deviation_members(instance)),
            'changes': sorted(changes, key=lambda x:(x['kind'],x['instance'] or x['prototype']))}


def _finding(kind, a, b, distance, instance):
    members = deviation_members(instance)
    matching = [p for p in (a,b) if p and p.GetPath() in members and reason(p)]
    prim = b or a
    return {'kind':kind, 'prototype':str(a.GetPath()) if a else None,
            'instance':str(b.GetPath()) if b else None,
            'classification': value(prim, 'aeco:class:ifc:code', ''),
            'distance': distance, 'declared':bool(matching),
            'reason': str(reason(matching[0])) if matching else ''}
