"""Verify that a published view retains the complete source facility."""
from pxr import Sdf, UsdGeom
from .model import matrix_error, value


def normalize_prototype_hints(directory):
    """Use the current public spelling for exported prototype hint properties.

    Source layers remain immutable. USD cannot rename a weaker-layer property
    through an overlay, so normalize this ad-hoc export field after flattening
    and in the archived own layers. The source value is retained verbatim.
    """
    changed=0
    for path in sorted(directory.rglob('*')):
        if path.suffix not in ('.usda','.usdc'): continue
        layer=Sdf.Layer.OpenAsAnonymous(str(path))
        paths=[]
        layer.Traverse(Sdf.Path.absoluteRootPath,paths.append)
        dirty=False
        for property_path in paths:
            if not property_path.IsPropertyPath(): continue
            name=property_path.name
            canonical='aeco:props:DC_Repeat:Prototype'
            if name.startswith('aeco:props:DC_') and name.endswith(':Prototype') and name!=canonical:
                spec=layer.GetPropertyAtPath(property_path)
                spec.name=canonical
                dirty=True;changed+=1
        if dirty: layer.Export(str(path))
    return changed


def verify_source(source, result, tolerance=1e-6):
    """Reject missing or changed source prims, identities, meshes and placements.

    Presentation colours and visibility may differ. Comparison uses the source
    itself, including unrelated floors and site equipment, not a minimum count.
    """
    source_xforms=UsdGeom.XformCache()
    result_xforms=UsdGeom.XformCache()
    prims=meshes=identities=0
    maximum=0.0
    for p in source.TraverseAll():
        q=result.GetPrimAtPath(p.GetPath())
        if not q or not q.IsActive() or p.GetTypeName()!=q.GetTypeName():
            raise ValueError('source prim missing, inactive or retyped: '+str(p.GetPath()))
        prims+=1
        identity=value(p,'aeco:id')
        if identity:
            if identity!=value(q,'aeco:id'):
                raise ValueError('source identity changed: '+str(p.GetPath()))
            identities+=1
        if p.IsA(UsdGeom.Xformable):
            maximum=max(maximum,matrix_error(source_xforms.GetLocalToWorldTransform(p),
                                             result_xforms.GetLocalToWorldTransform(q)))
        if p.IsA(UsdGeom.Mesh):
            for name in ('points','faceVertexCounts','faceVertexIndices'):
                if p.GetAttribute(name).Get()!=q.GetAttribute(name).Get():
                    raise ValueError('source mesh changed: '+str(p.GetPath()))
            meshes+=1
    if maximum>tolerance:
        raise ValueError('source world placement changed')
    return {'source_prims':prims,'source_identities':identities,'source_meshes':meshes,
            'max_world_error':maximum}
