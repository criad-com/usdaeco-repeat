"""Small independent mesh and container fixtures for defect drills."""
import uuid
from pxr import Gf,Sdf,Usd,UsdGeom,Vt


def stage_pair():
    s=Usd.Stage.CreateInMemory()
    s.SetMetadata('fallbackPrimTypes', {n:Vt.TokenArray(['Xform']) for n in ('AecoSite','AecoFacility','AecoLevel')})
    UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,'Z')
    root=s.DefinePrim('/World','Xform');s.SetDefaultPrim(root)
    for path,type_name in [('/World/Site','AecoSite'),('/World/Site/Facility','AecoFacility'),('/World/Site/Facility/L01','AecoLevel'),('/World/Site/Facility/L02','AecoLevel')]:
        p=s.DefinePrim(path,type_name);p.CreateAttribute('aeco:id',Sdf.ValueTypeNames.String).Set(str(uuid.uuid5(uuid.NAMESPACE_URL,path)))
        if type_name=='AecoLevel':
            z=0.0 if path.endswith('L01') else 3.0
            p.CreateAttribute('aeco:elevation',Sdf.ValueTypeNames.Double).Set(z)
            UsdGeom.Xformable(p).AddTranslateOp().Set((0,0,z))
    a=s.GetPrimAtPath('/World/Site/Facility/L01');b=s.GetPrimAtPath('/World/Site/Facility/L02')
    b.ApplyAPI('AecoRepeatAPI');b.CreateRelationship('aeco:repeat:prototype').SetTargets([a.GetPath()])
    for level in (a,b): add_element(s,level.GetPath().AppendChild('Partition'))
    return s,a,b


def add_element(s,path,code='IfcWall.PARTITIONING'):
    p=s.DefinePrim(path,'Xform');p.ApplyAPI('AecoElementAPI');p.ApplyAPI('AecoClassificationAPI','ifc')
    p.CreateAttribute('aeco:id',Sdf.ValueTypeNames.String).Set(str(uuid.uuid5(uuid.NAMESPACE_URL,str(path))))
    p.CreateAttribute('aeco:class:ifc:code',Sdf.ValueTypeNames.String).Set(code)
    p.CreateAttribute('aeco:axis:start',Sdf.ValueTypeNames.Point3d).Set((0,0,0))
    p.CreateAttribute('aeco:axis:end',Sdf.ValueTypeNames.Point3d).Set((4,0,0))
    mesh=UsdGeom.Mesh.Define(s,path.AppendChild('Body'))
    mesh.CreatePointsAttr([(0,0,0),(4,0,0),(4,.2,0),(0,.2,0),(0,0,3),(4,0,3),(4,.2,3),(0,.2,3)])
    mesh.CreateFaceVertexCountsAttr([4]*6)
    mesh.CreateFaceVertexIndicesAttr([0,3,2,1,4,5,6,7,0,1,5,4,1,2,6,5,2,3,7,6,3,0,4,7])
    mesh.CreateSubdivisionSchemeAttr('none')
    mesh.GetPrim().ApplyAPI('AecoDerivedGeometryAPI')
    for n,v in [('source',p.GetAttribute('aeco:id').Get()),('role','body'),('approx','tessellated'),('stamp','fixture-v1')]:
        mesh.GetPrim().CreateAttribute('aeco:derived:'+n,Sdf.ValueTypeNames.String if n in ('source','stamp') else Sdf.ValueTypeNames.Token).Set(v)
    return p
