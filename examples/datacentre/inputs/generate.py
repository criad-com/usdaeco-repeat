#!/usr/bin/env python3
"""Generate small consumer overlays from the pinned floors stage, read-only."""
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from usdaeco_repeat.cli import register_plugins
register_plugins()
from pxr import Gf,Sdf,Usd,UsdGeom
from usdaeco_repeat.model import elements,value


def main():
    source=Path(os.environ['AECO_DATACENTRE_ROOT'])/'dist/floors/dc.usda'
    s=Usd.Stage.Open(str(source))
    levels={value(p,'aeco:elevation'):p for p in s.Traverse() if p.GetTypeName()=='AecoLevel'}
    a,b=levels[4.0],levels[7.0]
    out=Path(__file__).resolve().parent
    intent=Usd.Stage.CreateNew(str(out/'repeat.usda'))
    q=intent.OverridePrim(b.GetPath());q.ApplyAPI('AecoRepeatAPI')
    q.CreateRelationship('aeco:repeat:prototype',custom=False).SetTargets([a.GetPath()])
    intent.GetRootLayer().customLayerData={'description':'L02 repeats L01; no deviations have been declared.'}
    intent.GetRootLayer().Save()
    sections=Usd.Stage.CreateNew(str(out/'sections.usda'))
    widths={}
    for p in elements(a)+elements(b):
        width=value(p,'aeco:props:Qto_WallBaseQuantities:Width')
        if width is None: continue
        for typepath in p.GetInherits().GetAllDirectInherits():
            if typepath in widths and abs(widths[typepath]-width)>1e-9: raise ValueError('inconsistent type widths')
            widths[typepath]=width
    for path,width in sorted(widths.items()):
        p=sections.OverridePrim(path);p.ApplyAPI('AecoBuildUpAPI')
        p.CreateAttribute('aeco:buildUp:thicknesses',Sdf.ValueTypeNames.DoubleArray,custom=False).Set([width])
        p.CreateAttribute('aeco:buildUp:functions',Sdf.ValueTypeNames.TokenArray,custom=False).Set(['other'])
        p.CreateAttribute('aeco:buildUp:materials',Sdf.ValueTypeNames.StringArray,custom=False).Set(['unspecified'])
        p.CreateAttribute('aeco:buildUp:priorities',Sdf.ValueTypeNames.IntArray,custom=False).Set([0])
    sections.GetRootLayer().customLayerData={'description':'Homogeneous sections from exported Qto wall Width. Material composition is unspecified; widths are measured source values.'}
    sections.GetRootLayer().Save()
    cameras=Usd.Stage.CreateNew(str(out/'cameras.usda'))
    c=UsdGeom.Camera.Define(cameras,'/Renders/overview')
    c.CreateProjectionAttr('orthographic')
    box=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render']).ComputeWorldBound(s.GetDefaultPrim()).ComputeAlignedRange()
    center=box.GetMidpoint()
    view=Gf.Matrix4d().SetLookAt(center+Gf.Vec3d(44,-88,135),center,Gf.Vec3d(0,0,1))
    projected=Gf.Range3d()
    for x in (box.GetMin()[0],box.GetMax()[0]):
        for y in (box.GetMin()[1],box.GetMax()[1]):
            for z in (box.GetMin()[2],box.GetMax()[2]):
                projected.UnionWith(view.Transform(Gf.Vec3d(x,y,z)))
    size=projected.GetSize()
    aperture=10*1.08*max(size[0],size[1]*1.6)
    c.CreateHorizontalApertureAttr(aperture);c.CreateVerticalApertureAttr(aperture/1.6)
    c.CreateClippingRangeAttr((.1,1000))
    c.AddTransformOp().Set(view.GetInverse())
    cameras.GetRootLayer().Save()
    (out/'studies').mkdir(exist_ok=True)
    cameras=Usd.Stage.CreateNew(str(out/'studies/cameras.usda'))
    for name,z in [('l01',6.5),('l02',9.5)]:
        c=UsdGeom.Camera.Define(cameras,'/Renders/'+name)
        c.CreateProjectionAttr('orthographic')
        c.CreateHorizontalApertureAttr(230);c.CreateVerticalApertureAttr(143.75)
        c.CreateClippingRangeAttr((0.01,2.9))
        c.AddTranslateOp().Set((21,-6,z))
    cameras.GetRootLayer().Save()

if __name__=='__main__': main()
