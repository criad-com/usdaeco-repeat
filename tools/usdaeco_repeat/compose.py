"""Rebuild a repeated container from a reference plus explicit differing opinions."""
import os
from pathlib import Path
from pxr import Gf, Sdf, Usd, UsdGeom, UsdUtils
from .diff import compare
from .model import close, matrix_error, plain, prototype, value, world


def _new_layer(path):
    existing = Sdf.Layer.Find(str(path))
    if existing:
        existing.Clear()
        return existing
    return Sdf.Layer.CreateNew(str(path))


def _attr(prim, name, original):
    attr=prim.CreateAttribute(name,original.GetTypeName(),custom=original.IsCustom(),variability=original.GetVariability())
    if original.Get() is not None:
        attr.Set(original.Get())
    for t in original.GetTimeSamples():
        attr.Set(original.Get(t),t)
    for k,v in original.GetAllAuthoredMetadata().items():
        if k not in ('typeName','custom','variability','default','timeSamples'):
            attr.SetMetadata(k,v)
    return attr


def compose(instance, output, tolerance=1e-6):
    """Write a self-contained two-container study and return identity/path evidence.

    The reference retains prototype names. The path map is a report, while the
    occurrence's existing aeco:id remains its sole identity. Separate identity
    and additions layers keep their costs visible beside the deviations layer.
    """
    out=Path(output).resolve()
    source_paths={Path(l.realPath).resolve() for l in instance.GetStage().GetUsedLayers() if l.realPath}
    if any(out/name in source_paths for name in ('prototype.usda','occurrences.usda','additions.usda','deviations.usda','composed.usda')):
        raise ValueError('composition output must not overwrite an input layer')
    for p in Usd.PrimRange(instance):
        if p.IsInstance() or any(a.GetNumTimeSamples() for a in p.GetAttributes()):
            raise ValueError('composition requires static, non-instanced inputs')
    out.mkdir(parents=True,exist_ok=True)
    source=instance.GetStage();proto=prototype(instance);report=compare(instance,tolerance)
    ppath,ipath=proto.GetPath(),instance.GetPath()
    flat=UsdUtils.FlattenLayerStack(source)
    base=_new_layer(out/'prototype.usda')
    # Preserve the existing neutral ancestor chain, without unrelated floors.
    for p in ppath.GetPrefixes()[:-1]:
        spec=Sdf.CreatePrimInLayer(base,p);spec.specifier=Sdf.SpecifierDef
        original=source.GetPrimAtPath(p)
        if original:
            spec.typeName=original.GetTypeName()
            names=['aeco:id','aeco:project:id','aeco:project:name']
            names += [a.GetName() for a in original.GetAttributes() if a.GetName().startswith('aeco:class:')]
            for n in names:
                prop=flat.GetAttributeAtPath(p.AppendProperty(n))
                if prop: Sdf.CopySpec(flat,prop.path,base,prop.path)
            for n in ('apiSchemas',):
                if original.HasAuthoredMetadata(n): spec.SetInfo(n,original.GetMetadata(n))
    Sdf.CopySpec(flat,ppath,base,ppath)
    # Catalogs are class prims; keep the authored inherits contract.
    for p in source.TraverseAll():
        if p.IsAbstract() and p.GetParent() and not p.GetParent().IsAbstract():
            Sdf.CreatePrimInLayer(base,p.GetPath().GetParentPath())
            Sdf.CopySpec(flat,p.GetPath(),base,p.GetPath())
    base.defaultPrim=source.GetDefaultPrim().GetName()
    for name in ('metersPerUnit','upAxis','fallbackPrimTypes'):
        base.pseudoRoot.SetInfo(name,source.GetMetadata(name))
    # Canonicalize flat exported level frames without moving any descendant.
    # This makes the reference's level datum agree with its authored placement.
    base_stage=Usd.Stage.Open(base)
    copied=base_stage.GetPrimAtPath(ppath)
    if (proto.GetTypeName()=='AecoLevel' and proto.GetParent().GetTypeName()=='AecoFacility'
            and value(proto,'aeco:elevation') is not None
            and not UsdGeom.Xformable(proto).GetOrderedXformOps()
            and all(p.IsA(UsdGeom.Xformable) for p in proto.GetChildren())):
        frame=Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(0,0,value(proto,'aeco:elevation')))
        before={p.GetPath():world(p) for p in copied.GetChildren()}
        UsdGeom.Xformable(copied).AddTransformOp().Set(frame)
        for path,old_world in before.items():
            child=base_stage.GetPrimAtPath(path)
            local=old_world*world(copied).GetInverse()
            xf=UsdGeom.Xformable(child);xf.ClearXformOpOrder()
            attr=child.GetAttribute('xformOp:transform')
            if attr: xf.SetXformOpOrder([UsdGeom.XformOp(attr)]);attr.Set(local)
            else: xf.AddTransformOp().Set(local)
    base.Save()
    delta=_new_layer(out/'deviations.usda')
    ids=_new_layer(out/'occurrences.usda')
    additions=_new_layer(out/'additions.usda')
    root=_new_layer(out/'composed.usda')
    root.subLayerPaths=['deviations.usda','occurrences.usda','additions.usda','prototype.usda']
    root.defaultPrim=base.defaultPrim
    for name in ('metersPerUnit','upAxis','fallbackPrimTypes'):
        root.pseudoRoot.SetInfo(name,source.GetMetadata(name))
    stage=Usd.Stage.Open(root)
    with Usd.EditContext(stage,ids):
        target=stage.DefinePrim(ipath,instance.GetTypeName())
        target.GetReferences().AddInternalReference(ppath)
        target.ApplyAPI('AecoRepeatAPI')
        target.CreateRelationship('aeco:repeat:prototype',custom=False).SetTargets([ppath])
        parent_world=world(target.GetParent())
        proto_parent=world(proto.GetParent())
        offset=Gf.Matrix4d(*[v for row in report['offset'] for v in row])
        local=UsdGeom.Xformable(stage.GetPrimAtPath(ppath)).GetLocalTransformation()*proto_parent*offset*parent_world.GetInverse()
        xf=UsdGeom.Xformable(target);xf.ClearXformOpOrder()
        attr=target.GetAttribute('xformOp:transform')
        if attr: xf.SetXformOpOrder([UsdGeom.XformOp(attr)]);attr.Set(local)
        else: xf.AddTransformOp().Set(local)
        target.CreateAttribute('aeco:repeat:offset',Sdf.ValueTypeNames.Matrix4d,custom=False).Set(offset)
    # Longest-prefix map from original occurrence paths to referenced paths.
    mapping={ipath:ipath}
    matches={Sdf.Path(p['instance']):Sdf.Path(p['prototype']).ReplacePrefix(ppath,ipath) for p in report['matches']}
    mapping.update(matches)
    extras=[Sdf.Path(c['instance']) for c in report['changes'] if c['kind']=='extra']
    missing=[Sdf.Path(c['prototype']).ReplacePrefix(ppath,ipath) for c in report['changes'] if c['kind']=='missing']
    def mapped(path):
        for old in sorted(mapping,key=lambda x:len(str(x)),reverse=True):
            if path.HasPrefix(old): return path.ReplacePrefix(old,mapping[old])
        return path
    # Copy genuine additions, including their representation, separately.
    for p in extras:
        dest=p
        mapping[p]=dest
        Sdf.CreatePrimInLayer(additions,dest.GetParentPath())
        Sdf.CopySpec(flat,p,additions,dest)
    with Usd.EditContext(stage,delta):
        for p in missing: stage.OverridePrim(p).SetActive(False)
    # Spaces and representation subtrees use their existing relative namespace.
    # Every authored property difference is compared; no geometric guess hides it.
    original_prims=list(Usd.PrimRange(instance))
    for old in original_prims:
        newpath=mapped(old.GetPath())
        current=stage.GetPrimAtPath(newpath)
        if not current:
            Sdf.CreatePrimInLayer(additions,newpath.GetParentPath())
            Sdf.CopySpec(flat,old.GetPath(),additions,newpath)
            current=stage.GetPrimAtPath(newpath)
        for a in old.GetAttributes():
            n=a.GetName()
            if not a.HasAuthoredValueOpinion() or n.startswith(('xformOp','aeco:repeat:','aeco:qto:')):
                continue
            got=current.GetAttribute(n)
            if got and close(plain(a.Get()),plain(got.Get()),tolerance) and a.GetCustomData()==got.GetCustomData():
                continue
            identity=n in ('aeco:id','aeco:derived:source') or n.startswith('aeco:props:DC_Identity:')
            with Usd.EditContext(stage,ids if identity else delta): _attr(current,n,a)
        # Remove inherited authored values absent in the original occurrence.
        for a in current.GetAttributes():
            n=a.GetName()
            if n.startswith(('xformOp','aeco:repeat:','aeco:qto:')): continue
            if a.HasAuthoredValueOpinion() and not old.GetAttribute(n).HasAuthoredValueOpinion():
                with Usd.EditContext(stage,delta): current.GetAttribute(n).Block()
        for rel in old.GetRelationships():
            if rel.GetName().startswith(('aeco:repeat:','collection:deviations:')): continue
            targets=[mapped(p) for p in rel.GetTargets()]
            existing=current.GetRelationship(rel.GetName())
            if not existing or existing.GetTargets()!=targets:
                with Usd.EditContext(stage,ids): current.CreateRelationship(rel.GetName(),custom=rel.IsCustom()).SetTargets(targets)
        if old != instance and old.IsA(UsdGeom.Xformable):
            desired=world(old)*world(current.GetParent()).GetInverse()
            if matrix_error(world(old),world(current))>tolerance:
                with Usd.EditContext(stage,delta):
                    xf=UsdGeom.Xformable(current);xf.ClearXformOpOrder()
                    attr=current.GetAttribute('xformOp:transform')
                    if attr: xf.SetXformOpOrder([UsdGeom.XformOp(attr)]);attr.Set(desired)
                    else: xf.AddTransformOp().Set(desired)
        if old.GetTypeName()!=current.GetTypeName():
            with Usd.EditContext(stage,delta): current.SetTypeName(old.GetTypeName())
    # A declared exception is explicit author intent, never inferred by the diff.
    with Usd.EditContext(stage,ids):
        collection=Usd.CollectionAPI(stage.GetPrimAtPath(ipath),'deviations')
        collection.CreateIncludesRel().SetTargets([mapped(p) for p in Usd.CollectionAPI(instance,'deviations').GetIncludesRel().GetTargets()])
        for old in original_prims:
            if old.GetCustomData(): stage.GetPrimAtPath(mapped(old.GetPath())).SetCustomData(old.GetCustomData())
    for layer in (base,ids,additions,delta,root): layer.Save()
    proof=verify(instance,stage.GetPrimAtPath(ipath),mapping,tolerance)
    proof.update(root='composed.usda',over_lines=len(delta.ExportToString().splitlines()),
                 occurrence_lines=len(ids.ExportToString().splitlines()),addition_lines=len(additions.ExportToString().splitlines()),
                 path_map={str(p.GetPath()):str(mapped(p.GetPath())) for p in original_prims},
                 reference_count=len(stage.GetPrimAtPath(ipath).GetMetadata('references').GetAppliedItems()))
    return stage,proof


def verify(original, composed, mapping, tolerance=1e-6):
    """Compare all occurrence prims, world transforms, mesh vertices and topology."""
    def mapped(path):
        for old in sorted(mapping,key=lambda x:len(str(x)),reverse=True):
            if path.HasPrefix(old): return path.ReplacePrefix(old,mapping[old])
        return path
    maximum=0.0;points=0;checked=0
    expected=set()
    for p in Usd.PrimRange(original):
        target=mapped(p.GetPath());expected.add(target)
        q=composed.GetStage().GetPrimAtPath(target)
        if not q or q.GetTypeName()!=p.GetTypeName(): raise ValueError('composed prim missing or retyped: '+str(target))
        if value(p,'aeco:id') != value(q,'aeco:id'): raise ValueError('occurrence identity differs')
        if p != original and p.IsA(UsdGeom.Xformable):
            maximum=max(maximum,matrix_error(world(p),world(q)))
        if p.IsA(UsdGeom.Mesh):
            a,b=UsdGeom.Mesh(p),UsdGeom.Mesh(q)
            for get in ('GetFaceVertexCountsAttr','GetFaceVertexIndicesAttr'):
                if getattr(a,get)().Get()!=getattr(b,get)().Get(): raise ValueError('composed topology differs')
            ap,bp=a.GetPointsAttr().Get(),b.GetPointsAttr().Get()
            if len(ap)!=len(bp): raise ValueError('composed vertex count differs')
            for x,y in zip(ap,bp):
                maximum=max(maximum,(world(p).Transform(Gf.Vec3d(x))-world(q).Transform(Gf.Vec3d(y))).GetLength());points+=1
        checked+=1
    actual={p.GetPath() for p in Usd.PrimRange(composed)}
    if actual!=expected: raise ValueError('composed subtree has extra or missing prims')
    if maximum>tolerance: raise ValueError('composition exceeds tolerance')
    return {'max_error':maximum,'prims_checked':checked,'vertices_checked':points,'tolerance':tolerance}
