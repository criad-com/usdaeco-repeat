"""The pinned floors study: measured findings and USD plan representations."""
import json
import os
from pathlib import Path
from collections import Counter
from pxr import Gf,Sdf,Usd,UsdGeom
from .compose import compose
from .diff import compare
from .model import elements,has_api,value,world
from .quantity import derive,takeoff


def _json(path,data):
    path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')


def hook(stage,out):
    root=Path(os.environ['AECO_DATACENTRE_ROOT'])
    manifest=json.loads((root/'dist/floors/dc.manifest.json').read_text())
    levels=[p for p in stage.Traverse() if p.GetTypeName()=='AecoLevel']
    counts={'elements':sum(has_api(p,'AecoElementAPI') for p in stage.Traverse()),
            'levels':len(levels),'spaces':sum(p.GetTypeName()=='AecoSpace' for p in stage.Traverse()),
            'meshes':sum(p.IsA(UsdGeom.Mesh) for p in stage.Traverse()),
            'ports':sum(p.GetTypeName()=='AecoPort' for p in stage.Traverse())}
    for name,count in counts.items():
        if count!=manifest['counts'][name]: raise ValueError('source manifest count mismatch: '+name)
    a,b=[p for p in levels if value(p,'aeco:elevation') in (4.0,7.0)]
    diff=compare(b)
    schedules={'by_level':takeoff([a,b],by_level=True),'unkeyed':takeoff([a,b]),
               'repeat_resolved':takeoff([a,b],repeat_resolved=True)}
    _json(out/'diff.json',diff);_json(out/'schedule.json',schedules)
    result,proof=compose(b,out/'composition')
    _json(out/'composition.json',proof)
    # Preserve the complete source and its paths. The reconstruction is a
    # separate study; its prototype child names must not duplicate occurrences
    # over the original facility's independently named children.
    context=Sdf.Layer.CreateNew(str(out/'context.usda'))
    context.subLayerPaths=['../inputs/source/dist/floors/dc.usda']
    context.customLayerData={'description':'Full floors source with derived repeat registration; source alias is recreated by run.py.'}
    stage.GetRootLayer().subLayerPaths[-1]='context.usda'
    with Usd.EditContext(stage,context):
        b.CreateAttribute('aeco:repeat:offset',Sdf.ValueTypeNames.Matrix4d,custom=False).Set(
            Gf.Matrix4d(*[v for row in diff['offset'] for v in row]))
    context.Save()
    quantity=Sdf.Layer.CreateNew(str(out/'quantities.usda'))
    stage.GetRootLayer().subLayerPaths.insert(0,'quantities.usda')
    derive(stage,elements(a)+elements(b),quantity)
    highlight_facility(stage,b,diff,out)
    # Plan drawings use the reconstruction only, away from the full result.
    study_dir=out/'study';study_dir.mkdir()
    study_layer=Sdf.Layer.CreateNew(str(study_dir/'example.usda'))
    study_layer.subLayerPaths=['../composition/composed.usda','../../inputs/studies/cameras.usda']
    study=Usd.Stage.Open(study_layer)
    for name in ('defaultPrim','metersPerUnit','upAxis','fallbackPrimTypes'):
        study.SetMetadata(name,stage.GetMetadata(name))
    render_plan(study,[study.GetPrimAtPath(p.GetPath()) for p in (a,b)],diff,proof,study_dir)
    study_layer.Save()
    parts=lambda rows:sum(r['length'] for r in rows if r['classification']=='IfcWall.PARTITIONING')
    doors=lambda rows:sum(r['count'] for r in rows if r['classification']=='IfcDoor.DOOR')
    summary=Counter(c['kind'] for c in diff['changes'])
    findings = [
        {'name':'SourceCensus','counts':counts,'expected':{k:manifest['counts'][k] for k in counts}},
        {'name':'FloorDrift','moved_walls':sum(c['kind']=='moved' and c['classification'].startswith('IfcWall') for c in diff['changes']),
         'extra_doors':sum(c['kind']=='extra' and c['classification']=='IfcDoor.DOOR' for c in diff['changes']),
         'declared_deviations':diff['declared_deviations'],'all_changes':dict(summary)},
        {'name':'ScheduleDelta','doors':doors(schedules['unkeyed'])-doors(schedules['repeat_resolved']),
         'partition_length_m':parts(schedules['unkeyed'])-parts(schedules['repeat_resolved']),
         'partition_length_L01_m':parts([r for r in schedules['by_level'] if r['level']==str(a.GetPath())]),
         'partition_length_L02_m':parts([r for r in schedules['by_level'] if r['level']==str(b.GetPath())])},
        {'name':'Composition','max_error':proof['max_error'],'prims_checked':proof['prims_checked'],
         'vertices_checked':proof['vertices_checked'],'over_lines':proof['over_lines'],
         'occurrence_lines':proof['occurrence_lines'],'addition_lines':proof['addition_lines'],
         'reference_count':proof['reference_count']},
    ]
    # USD 26.8 exposes GetPrim(), while the shared harness expects GetPath().
    # Run the same registered validators here and serialize their public sites.
    from usdaeco_check.validation import run
    for error in run(stage,['UsdAecoRepeatValidators']):
        findings.append({'name':error.GetName(),'severity':str(error.GetType()).split('.')[-1].lower(),
                         'message':error.GetMessage(),
                         'paths':[str(site.GetPrim().GetPath()) for site in error.GetSites()]})
    return findings


def highlight_facility(stage,level,diff,out):
    """Expose the office roof and tint the actual changed bodies in context."""
    layer=Sdf.Layer.CreateNew(str(out/'presentation.usda'))
    layer.customLayerData={'description':'Office cutaway: only its roof is hidden; amber is the changed partition, green the extra door. Source geometry and identity are preserved; derived outlines emphasize the subjects.'}
    stage.GetRootLayer().subLayerPaths.insert(0,'presentation.usda')
    bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render'])
    office=bounds.ComputeWorldBound(level).ComputeAlignedRange()
    with Usd.EditContext(stage,layer):
        for p in stage.Traverse():
            if p.IsA(UsdGeom.Mesh) and value(p,'aeco:derived:role')=='body':
                code=value(p.GetParent(),'aeco:class:ifc:code','')
                colour=(.055,.075,.10) if code=='IfcSlab.ROOF' else (.16,.20,.24)
                UsdGeom.Gprim(p).CreateDisplayColorAttr([colour])
            if value(p,'aeco:class:ifc:code','')=='IfcSlab.ROOF':
                roof=bounds.ComputeWorldBound(p).ComputeAlignedRange()
                center=roof.GetMidpoint()
                if office.GetMin()[0]<=center[0]<=office.GetMax()[0] and office.GetMin()[1]<=center[1]<=office.GetMax()[1]:
                    UsdGeom.Imageable(p).CreateVisibilityAttr('invisible')
        for change in diff['changes']:
            colour=(.95,.45,.035) if change['kind']=='changed' else (.02,.85,.25)
            for path in (change['prototype'],change['instance']):
                if not path: continue
                owner=stage.GetPrimAtPath(path)
                box=Gf.Range3d();sources=[]
                for p in Usd.PrimRange(owner):
                    if p.IsA(UsdGeom.Mesh) and value(p,'aeco:derived:role')=='body':
                        UsdGeom.Gprim(p).CreateDisplayColorAttr([colour])
                        box.UnionWith(bounds.ComputeRelativeBound(p,owner).ComputeAlignedRange())
                        sources.append(p.GetPath())
                if box.IsEmpty(): continue
                lo,hi=box.GetMin(),box.GetMax();pad=.18;z=hi[2]+.08
                outline=UsdGeom.BasisCurves.Define(stage,owner.GetPath().AppendChild('RepeatHighlight'))
                outline.CreateTypeAttr('linear');outline.CreateWrapAttr('periodic')
                outline.CreateCurveVertexCountsAttr([4])
                outline.CreatePointsAttr([(lo[0]-pad,lo[1]-pad,z),(hi[0]+pad,lo[1]-pad,z),
                                         (hi[0]+pad,hi[1]+pad,z),(lo[0]-pad,hi[1]+pad,z)])
                outline.CreateWidthsAttr([.18]);outline.SetWidthsInterpolation('constant')
                outline.CreateDisplayColorAttr([colour])
                mark=outline.GetPrim();mark.ApplyAPI('AecoDerivedGeometryAPI')
                for n,v in [('source',value(owner,'aeco:id')),('role','symbol'),('approx','bbox'),('stamp','repeat-highlight-v1')]:
                    mark.CreateAttribute('aeco:derived:'+n,Sdf.ValueTypeNames.String if n in ('source','stamp') else Sdf.ValueTypeNames.Token,custom=False).Set(v)
                mark.CreateRelationship('aeco:derived:from',custom=False).SetTargets(sources)
    layer.Save()


def render_plan(stage,levels,diff,proof,out):
    layer=Sdf.Layer.CreateNew(str(out/'plans.usda'))
    stage.GetRootLayer().subLayerPaths.insert(0,'plans.usda')
    colours={}
    palette={'moved':(.95,.18,.10),'extra':(.04,.62,.37),'changed':(.95,.60,.08),'missing':(.55,.22,.7)}
    for finding in diff['changes']:
        for path in (finding['prototype'],finding['instance']):
            if path: colours[proof['path_map'].get(path,path)]=palette[finding['kind']]
    cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render'])
    with Usd.EditContext(stage,layer):
        for level in levels:
            for p in list(Usd.PrimRange(level)):
                if p.IsA(UsdGeom.Gprim): UsdGeom.Imageable(p).CreateVisibilityAttr('invisible')
            for p in elements(level):
                code=value(p,'aeco:class:ifc:code','')
                if not code.startswith(('IfcWall.','IfcDoor.')): continue
                bodies=[c for c in Usd.PrimRange(p) if c.IsA(UsdGeom.Mesh) and value(c,'aeco:derived:role')=='body']
                bounds=Gf.Range3d()
                for body in bodies: bounds.UnionWith(cache.ComputeRelativeBound(body,p).ComputeAlignedRange())
                if bounds.IsEmpty(): continue
                lo,hi=bounds.GetMin(),bounds.GetMax();z=lo[2]+.03
                footprint=UsdGeom.Mesh.Define(stage,p.GetPath().AppendChild('RepeatPlan'))
                footprint.CreatePointsAttr([(lo[0],lo[1],z),(hi[0],lo[1],z),(hi[0],hi[1],z),(lo[0],hi[1],z)])
                footprint.CreateFaceVertexCountsAttr([4]);footprint.CreateFaceVertexIndicesAttr([0,1,2,3]);footprint.CreateSubdivisionSchemeAttr('none')
                footprint.CreateDoubleSidedAttr(True)
                footprint.CreateDisplayColorAttr([colours.get(str(p.GetPath()),(.20,.27,.34))])
                mark=footprint.GetPrim();mark.ApplyAPI('AecoDerivedGeometryAPI')
                for n,v in [('source',value(p,'aeco:id')),('role','footprint'),('approx','bbox'),('stamp','repeat-plan-v1')]:
                    mark.CreateAttribute('aeco:derived:'+n,Sdf.ValueTypeNames.String if n in ('source','stamp') else Sdf.ValueTypeNames.Token,custom=False).Set(v)
    layer.Save()
