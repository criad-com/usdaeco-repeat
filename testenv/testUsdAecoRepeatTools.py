#!/pxrpythonsubst
import math
import tempfile
import unittest
from pxr import Sdf,Usd,UsdGeom
from fixtures import stage_pair,add_element
from usdaeco_repeat.compose import compose
from usdaeco_repeat.diff import compare
from usdaeco_repeat.quantity import measure,takeoff,derive,stale

class TestTools(unittest.TestCase):
    def test_missing_extra_changed_and_tolerance(self):
        s,a,b=stage_pair();p=b.GetChildren()[0]
        UsdGeom.Xformable(p).AddTranslateOp().Set((0.0000001,0,0))
        self.assertEqual(compare(b)['changes'],[])
        p.GetAttribute('aeco:axis:end').Set((5,0,0))
        self.assertEqual(compare(b)['changes'][0]['kind'],'changed')
        s.RemovePrim(p.GetPath());add_element(s,b.GetPath().AppendChild('Door'),'IfcDoor.DOOR')
        self.assertEqual({c['kind'] for c in compare(b)['changes']},{'missing','extra'})
        with self.assertRaises(ValueError): compare(b,float('nan'))

    def test_quantity_body_and_build_up(self):
        s,a,b=stage_pair();p=a.GetChildren()[0]
        q,m=measure(p)
        self.assertAlmostEqual(q['length'],4)
        self.assertAlmostEqual(q['volume'],2.4,places=6)
        self.assertAlmostEqual(q['area'],26.8,places=6)
        p.CreateAttribute('aeco:buildUp:thicknesses',Sdf.ValueTypeNames.DoubleArray).Set([.1,.1])
        q,m=measure(p)
        self.assertAlmostEqual(q['area'],12)
        self.assertAlmostEqual(q['volume'],2.4)
        self.assertEqual(m['volume'],'axis-build-up-body-height-gross')
        add_element(s,b.GetPath().AppendChild('Door'),'IfcDoor.DOOR')
        self.assertEqual(sum(r['count'] for r in takeoff([a,b])),3)
        self.assertEqual(sum(r['count'] for r in takeoff([a,b],repeat_resolved=True)),2)
        self.assertEqual(sum(r['count'] for r in takeoff([a,a])),1)

    def test_compose_real_reference_and_identity(self):
        s,a,b=stage_pair();p=b.GetChildren()[0]
        UsdGeom.Xformable(p).AddTranslateOp().Set((1,0,0))
        add_element(s,b.GetPath().AppendChild('Door'),'IfcDoor.DOOR')
        with tempfile.TemporaryDirectory() as d:
            result,proof=compose(b,d)
            self.assertLessEqual(proof['max_error'],1e-6)
            self.assertGreater(proof['vertices_checked'],0)
            self.assertEqual(proof['reference_count'],1)
            self.assertEqual(result.GetPrimAtPath(p.GetPath()).GetAttribute('aeco:id').Get(),p.GetAttribute('aeco:id').Get())
            proto=result.GetPrimAtPath(a.GetPath().AppendChild('Partition'))
            proto.CreateAttribute('aeco:phase',Sdf.ValueTypeNames.Token).Set('existing')
            self.assertEqual(result.GetPrimAtPath(p.GetPath()).GetAttribute('aeco:phase').Get(),'existing')
            self.assertEqual(result.GetCompositionErrors(),[])

    def test_quantity_stamp_survives_flattening(self):
        s,a,b=stage_pair();p=a.GetChildren()[0]
        catalog=s.CreateClassPrim('/Catalog/Wall');catalog.CreateAttribute('aeco:buildUp:thicknesses',Sdf.ValueTypeNames.DoubleArray).Set([.2])
        p.GetInherits().AddInherit(catalog.GetPath())
        with tempfile.TemporaryDirectory() as d:
            layer=Sdf.Layer.CreateNew(str(__import__('pathlib').Path(d)/'quantities.usda'))
            s.GetRootLayer().subLayerPaths=[layer.identifier]
            derive(s,[p],layer)
            flat=Usd.Stage.Open(s.Flatten(addSourceFileComment=False))
            self.assertFalse(stale(flat.GetPrimAtPath(p.GetPath())))
            catalog.GetAttribute('aeco:buildUp:thicknesses').Set([.3])
            self.assertTrue(stale(p))

    def test_world_scaled_measurement_and_stage_units(self):
        s,a,b=stage_pair();p=a.GetChildren()[0]
        UsdGeom.Xformable(p).AddScaleOp().Set((2,2,2))
        q,_=measure(p)
        self.assertAlmostEqual(q['length'],8)
        self.assertAlmostEqual(q['volume'],19.2,places=5)
        UsdGeom.SetStageMetersPerUnit(s,.001)
        q,_=measure(p)
        self.assertAlmostEqual(q['length'],.008)
        self.assertAlmostEqual(q['volume'],19.2e-9,places=12)

    def test_major_arc_and_open_body(self):
        s,a,b=stage_pair();p=a.GetChildren()[0]
        p.GetAttribute('aeco:axis:start').Set((1,0,0))
        p.GetAttribute('aeco:axis:end').Set((0,1,0))
        p.CreateAttribute('aeco:axis:arcPoint',Sdf.ValueTypeNames.Point3d).Set((-1,0,0))
        p.CreateAttribute('aeco:axis:curve',Sdf.ValueTypeNames.Token).Set('arc')
        q,_=measure(p);self.assertAlmostEqual(q['length'],1.5*math.pi)
        op=UsdGeom.Xformable(p).AddScaleOp();op.Set((2,1,1))
        with self.assertRaisesRegex(ValueError,'uniform scale'): measure(p)
        op.Set((1,1,1))
        mesh=UsdGeom.Mesh(p.GetChild('Body'))
        mesh.GetFaceVertexCountsAttr().Set([4]*5)
        mesh.GetFaceVertexIndicesAttr().Set(list(mesh.GetFaceVertexIndicesAttr().Get())[:20])
        q,_=measure(p);self.assertNotIn('volume',q)

    def test_composition_does_not_overwrite_source(self):
        s,a,b=stage_pair()
        with tempfile.TemporaryDirectory() as d:
            result,proof=compose(b,d)
            with self.assertRaisesRegex(ValueError,'overwrite'):
                compose(result.GetPrimAtPath(b.GetPath()),d)

    def test_rotation_offset(self):
        s,a,b=stage_pair()
        UsdGeom.Xformable(b).AddRotateZOp().Set(90)
        self.assertEqual(compare(b)['changes'],[])

    def test_flat_export_frames_and_ancestor_classification(self):
        from usdaeco_repeat.model import world
        s,a,b=stage_pair()
        parent=a.GetParent();parent.ApplyAPI('AecoClassificationAPI','ifc')
        parent.CreateAttribute('aeco:class:ifc:code',Sdf.ValueTypeNames.String).Set('IfcBuilding')
        for level,z in ((a,4.0),(b,7.0)):
            UsdGeom.Xformable(level).ClearXformOpOrder()
            level.GetAttribute('aeco:elevation').Set(z)
            UsdGeom.Xformable(level.GetChildren()[0]).AddTranslateOp().Set((0,0,z))
        with tempfile.TemporaryDirectory() as d:
            result,proof=compose(b,d)
            self.assertLessEqual(proof['max_error'],1e-6)
            self.assertEqual(world(result.GetPrimAtPath(a.GetPath())).ExtractTranslation()[2],4)
            self.assertEqual(world(result.GetPrimAtPath(b.GetPath())).ExtractTranslation()[2],7)
            self.assertEqual(result.GetPrimAtPath(parent.GetPath()).GetAttribute('aeco:class:ifc:code').Get(),'IfcBuilding')

if __name__=='__main__': unittest.main()
