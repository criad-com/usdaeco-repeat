"""SI takeoff from resolved axes, build-ups and closed tessellated bodies."""
import math
from collections import defaultdict
from pxr import Gf, Sdf, Usd, UsdGeom
from .model import elements, has_api, plain, source_stamp, type_key, value, world


def _mesh_measure(mesh, metres):
    if mesh.GetHoleIndicesAttr().Get():
        raise ValueError('mesh holes require prior tessellation')
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    if points is None or counts is None or indices is None or sum(counts) != len(indices):
        raise ValueError('mesh topology is incomplete')
    transform = world(mesh.GetPrim())
    pts = [transform.Transform(Gf.Vec3d(p))*metres for p in points]
    # An origin near the body reduces cancellation at large site coordinates.
    origin = pts[0] if pts else Gf.Vec3d(0)
    area, volume, cursor = 0.0, 0.0, 0
    edges = defaultdict(list)
    for count in counts:
        face = list(indices[cursor:cursor+count]); cursor += count
        if count < 3 or any(i < 0 or i >= len(pts) for i in face):
            raise ValueError('invalid mesh face')
        for a,b in zip(face,face[1:]+face[:1]):
            edges[tuple(sorted((a,b)))].append((a,b))
        for i in range(1,count-1):
            a,b,c = [pts[j]-origin for j in (face[0],face[i],face[i+1])]
            area += Gf.Cross(b-a,c-a).GetLength()/2
            volume += Gf.Dot(a,Gf.Cross(b,c))/6
    closed = bool(edges) and all(len(v)==2 and v[0] == v[1][::-1] for v in edges.values())
    return area, abs(volume) if closed else None


def measure(prim):
    metres = UsdGeom.GetStageMetersPerUnit(prim.GetStage())
    quantities = {'count':1.0}
    methods = {'count':'element-occurrence'}
    start, end = value(prim,'aeco:axis:start'), value(prim,'aeco:axis:end')
    xf = world(prim)
    if start is not None and end is not None:
        curve = value(prim,'aeco:axis:curve','line')
        a,b = xf.Transform(Gf.Vec3d(start)),xf.Transform(Gf.Vec3d(end))
        if curve == 'line':
            length = (b-a).GetLength()*metres
        elif curve == 'arc':
            basis=[xf.TransformDir(Gf.Vec3d(*(1 if i==j else 0 for j in range(3)))) for i in range(3)]
            scales=[v.GetLength() for v in basis]
            if (min(scales)<=0 or max(scales)-min(scales)>1e-9*max(scales)
                    or any(abs(Gf.Dot(basis[i],basis[j]))>1e-9*max(scales)**2 for i in range(3) for j in range(i))):
                raise ValueError('arc axes require uniform scale and orthogonal transforms')
            mid = value(prim,'aeco:axis:arcPoint')
            if mid is None:
                raise ValueError('arc axis needs an arcPoint')
            c = xf.Transform(Gf.Vec3d(mid))
            u,v = c-a,b-a
            cross = Gf.Cross(u,v)
            if cross.GetLength() <= 1e-12:
                raise ValueError('degenerate arc axis')
            centre = a + (Gf.Cross(v,cross)*Gf.Dot(u,u)+Gf.Cross(cross,u)*Gf.Dot(v,v))/(2*Gf.Dot(cross,cross))
            radius = (a-centre).GetLength()
            normal = cross / cross.GetLength()
            va,vb = a-centre,b-centre
            sweep = math.atan2(Gf.Dot(normal,Gf.Cross(va,vb)),Gf.Dot(va,vb)) % (2*math.pi)
            length = radius*sweep*metres
        else:
            raise ValueError('unsupported axis curve')
        quantities['length'] = length
        methods['length'] = 'axis-'+curve
    bodies = [p for p in Usd.PrimRange(prim) if p.IsA(UsdGeom.Mesh)
              and value(p,'aeco:derived:role')=='body'
              and value(p,'purpose','default') in ('default','render')]
    if bodies:
        areas, volumes = [], []
        for body in bodies:
            a,v = _mesh_measure(UsdGeom.Mesh(body),metres)
            areas.append(a); volumes.append(v)
        quantities['area'] = sum(areas); methods['area'] = 'body-surface-tessellated'
        if all(v is not None for v in volumes):
            quantities['volume'] = sum(volumes); methods['volume'] = 'body-volume-closed-tessellated'
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default','render'])
        bounds = Gf.Range3d()
        for body in bodies:
            bbox = cache.ComputeRelativeBound(body,prim).ComputeAlignedRange()
            bounds.UnionWith(bbox)
        size = bounds.GetSize()
        if 'length' not in quantities:
            # Transform each local dimension independently; supports scaled occurrences.
            lengths = [(xf.TransformDir(Gf.Vec3d(*(size[i] if j==i else 0 for j in range(3))))).GetLength()*metres for i in range(3)]
            quantities['length'] = max(lengths); methods['length'] = 'body-local-major-dimension'
        thicknesses = value(prim,'aeco:buildUp:thicknesses')
        if thicknesses is not None and len(thicknesses) and start is not None:
            if any(not math.isfinite(t) or t < 0 for t in thicknesses) or sum(thicknesses)<=0:
                raise ValueError('invalid build-up thicknesses')
            # Section widths are SI; body height supplies extrusion, gross before openings.
            height = xf.TransformDir(Gf.Vec3d(0,0,size[2])).GetLength()*metres
            quantities['area'] = quantities['length']*height
            quantities['volume'] = quantities['area']*sum(thicknesses)
            methods['area'] = 'axis-body-height-gross'
            methods['volume'] = 'axis-build-up-body-height-gross'
    if not all(math.isfinite(q) and q >= 0 for q in quantities.values()):
        raise ValueError('quantities must be finite and nonnegative')
    return quantities, methods


def derive(stage, prims, layer):
    """Author only in the supplied derived layer; no source layer is edited."""
    with Usd.EditContext(stage,layer):
        for p in prims:
            quantities, methods = measure(p)
            p.ApplyAPI('AecoQuantityAPI')
            stamp = source_stamp(p)
            for key in ('length','area','volume'):
                if key not in quantities and p.GetAttribute('aeco:qto:'+key).HasAuthoredValueOpinion():
                    p.GetAttribute('aeco:qto:'+key).Block()
            for key,v in quantities.items():
                attr = p.CreateAttribute('aeco:qto:'+key,Sdf.ValueTypeNames.Double,custom=False)
                attr.Set(v)
                attr.SetCustomDataByKey('aeco:qto:source',value(p,'aeco:id',''))
                attr.SetCustomDataByKey('aeco:qto:stamp',stamp)
                attr.SetCustomDataByKey('aeco:qto:method',methods[key])
    layer.Save()


def stale(prim):
    stamp = source_stamp(prim)
    quantities, methods = measure(prim)
    for name in ('length','area','volume','count'):
        attr = prim.GetAttribute('aeco:qto:'+name)
        authored = bool(attr and attr.HasAuthoredValueOpinion())
        if name in quantities:
            if not authored or attr.GetCustomDataByKey('aeco:qto:stamp') != stamp or attr.GetCustomDataByKey('aeco:qto:source') != value(prim,'aeco:id','') or attr.GetCustomDataByKey('aeco:qto:method') != methods[name]:
                return True
            v = attr.Get()
            if v is None or not math.isfinite(v) or abs(v-quantities[name]) > 1e-6:
                return True
        elif authored:
            return True
    return False


def takeoff(containers, by_level=False, repeat_resolved=False):
    from .model import prototype
    rows = {}
    visited = set()
    for container in containers:
        source = prototype(container) if repeat_resolved and has_api(container,'AecoRepeatAPI') else container
        for p in elements(source):
            # Overlapping requested scopes must never double-count an occurrence.
            occurrence = (str(container.GetPath()) if repeat_resolved else '',str(p.GetPath()))
            if occurrence in visited:
                continue
            visited.add(occurrence)
            key = (str(container.GetPath()) if by_level else '',value(p,'aeco:class:ifc:code','unclassified'),type_key(p))
            row = rows.setdefault(key,{'level':key[0],'classification':key[1],'type':list(key[2]),'count':0.0,'length':0.0,'area':0.0,'volume':0.0,'unavailable':{'length':0,'area':0,'volume':0},'methods':set()})
            qs, ms = measure(p)
            row['methods'].update(ms.values())
            for n in ('count','length','area','volume'):
                if n in qs: row[n] += qs[n]
                else: row['unavailable'][n] += 1
    return [{**row,'methods':sorted(row['methods'])} for _,row in sorted(rows.items())]
