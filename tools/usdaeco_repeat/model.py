"""Shared semantic reads; no names or exporter identifiers drive matching."""
import hashlib
import json
from collections import Counter
import math
from pxr import Gf, Sdf, Usd, UsdGeom


def value(prim, name, default=None):
    attr = prim.GetAttribute(name)
    got = attr.Get() if attr else None
    return default if got is None else got


def has_api(prim, name):
    authored = prim.GetMetadata('apiSchemas')
    return name in prim.GetAppliedSchemas() or bool(authored and name in authored.GetAppliedItems())


def elements(container):
    return sorted((p for p in Usd.PrimRange(container) if has_api(p, 'AecoElementAPI')), key=lambda p: str(p.GetPath()))


def classification(prim):
    return tuple((a.GetName(), a.Get()) for a in prim.GetAttributes()
                 if a.GetName().startswith('aeco:class:') and a.GetName().endswith(':code') and a.Get())


def type_key(prim):
    return tuple(str(p) for p in prim.GetInherits().GetAllDirectInherits())


def match_key(prim):
    return classification(prim), type_key(prim)


def world(prim):
    return UsdGeom.XformCache().GetLocalToWorldTransform(prim)


def matrix_error(a, b):
    return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))


def plain(v):
    if isinstance(v, (str, bool, int, float)) or v is None:
        return v
    try:
        return [plain(x) for x in v]
    except TypeError:
        return str(v)


def shape(prim):
    """Local geometry and drivers, excluding placement, identity and reports."""
    result = []
    for p in Usd.PrimRange(prim):
        if value(p, 'aeco:derived:role') not in (None, 'body'):
            continue
        if p != prim and has_api(p, 'AecoElementAPI'):
            continue
        if p.GetTypeName() == 'AecoPort':
            continue
        for a in p.GetAttributes():
            n = a.GetName()
            if not a.HasAuthoredValueOpinion() or a.GetMetadata('aecoDerived'):
                continue
            if n.startswith(('aeco:props:', 'aeco:class:', 'aeco:qto:', 'aeco:derived:', 'primvars:', 'visibility', 'purpose')) or n in ('aeco:id', 'aeco:axis:length'):
                continue
            if p == prim and n.startswith('xformOp'):
                continue
            result.append((str(p.GetPath().MakeRelativePath(prim.GetPath())), n, plain(a.Get())))
    return result


def close(a, b, tolerance):
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tolerance
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return len(a)==len(b) and all(close(x,y,tolerance) for x,y in zip(a,b))
    return a == b


def source_stamp(prim):
    """Hash resolved measurement inputs; stable across USD flattening.

    Authorship and inherits arcs disappear on flattening. Hash the values that
    affect measurement, including inherited widths, rather than the opinion
    stack or the presence of an authored fallback.
    """
    records = [('id', value(prim,'aeco:id','')),
               ('world',plain(world(prim))),
               ('metres',UsdGeom.GetStageMetersPerUnit(prim.GetStage()))]
    for n,default in [('aeco:axis:start',None),('aeco:axis:end',None),
                      ('aeco:axis:curve','line'),('aeco:axis:arcPoint',None),
                      ('aeco:buildUp:thicknesses',None)]:
        records.append((n,plain(value(prim,n,default))))
    for p in Usd.PrimRange(prim):
        if not p.IsA(UsdGeom.Mesh) or value(p,'aeco:derived:role') != 'body':
            continue
        record = [str(p.GetPath()), plain(world(p))]
        for n,default in [('points',None),('faceVertexCounts',None),('faceVertexIndices',None),
                          ('holeIndices',[]),('purpose','default'),
                          ('aeco:derived:source',''),('aeco:derived:stamp',''),
                          ('aeco:derived:approx','exact')]:
            record.append((n,plain(value(p,n,default))))
        records.append(record)
    return hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def prototype(instance):
    targets = instance.GetRelationship('aeco:repeat:prototype').GetTargets()
    if len(targets) != 1:
        raise ValueError('prototype must target exactly one spatial container')
    p = instance.GetStage().GetPrimAtPath(targets[0])
    if not p or p == instance or not p.IsA('AecoSpatialBase'):
        raise ValueError('prototype must be a different spatial container')
    seen = {instance.GetPath()}
    cursor = p
    while has_api(cursor, 'AecoRepeatAPI'):
        if cursor.GetPath() in seen:
            raise ValueError('prototype cycle')
        seen.add(cursor.GetPath())
        links = cursor.GetRelationship('aeco:repeat:prototype').GetTargets()
        if len(links) != 1 or not instance.GetStage().GetPrimAtPath(links[0]):
            raise ValueError('invalid prototype chain')
        cursor = instance.GetStage().GetPrimAtPath(links[0])
    return p


def offset_for(proto, instance):
    """Use container frames, or consensus registration for flat export frames.

    Some exports put datum translations on every child. In that case use the
    dominant translation among same-class/type, same-orientation placements.
    A tied registration is refused instead of choosing a floor arbitrarily.
    """
    a, b = world(proto), world(instance)
    if matrix_error(a, b) > 1e-9:
        return a.GetInverse() * b
    votes = Counter()
    for p in elements(proto):
        for q in elements(instance):
            if match_key(p) != match_key(q):
                continue
            x, y = world(p), world(q)
            if all(abs(x[i][j]-y[i][j]) < 1e-8 for i in range(3) for j in range(3)):
                delta = y.ExtractTranslation()-x.ExtractTranslation()
                votes[tuple(round(v, 6) for v in delta)] += 1
    if not votes:
        raise ValueError('cannot derive an offset without matching placements')
    best = votes.most_common(2)
    if len(best)>1 and best[0][1] == best[1][1]:
        raise ValueError('ambiguous prototype registration')
    return Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(*best[0][0]))


def deviation_members(instance):
    collection = Usd.CollectionAPI(instance, 'deviations')
    # Explicit targets also preserve dangling declarations for validation.
    return collection.GetIncludesRel().GetTargets()


def reason(prim):
    text = prim.GetCustomDataByKey('aeco:repeat:reason') if prim else None
    return text if isinstance(text, str) and text.strip() else None
