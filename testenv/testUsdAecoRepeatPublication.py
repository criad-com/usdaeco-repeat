#!/pxrpythonsubst
import unittest
from pathlib import Path
import tempfile
from pxr import Sdf, Usd, UsdGeom
from fixtures import stage_pair, add_element
from usdaeco_repeat.publication import normalize_prototype_hints, verify_source


class TestPublication(unittest.TestCase):
    def test_exported_prototype_hint_keeps_its_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            stage=Usd.Stage.CreateNew(str(root/'example.usdc'))
            p=stage.DefinePrim('/Floor','Xform')
            p.CreateAttribute('aeco:props:DC_Source:Prototype',Sdf.ValueTypeNames.String).Set('prototype-level')
            stage.GetRootLayer().Save()
            self.assertEqual(normalize_prototype_hints(root),1)
            layer=Sdf.Layer.OpenAsAnonymous(str(root/'example.usdc'))
            self.assertEqual(layer.GetAttributeAtPath('/Floor.aeco:props:DC_Repeat:Prototype').default,'prototype-level')
            self.assertFalse(layer.GetAttributeAtPath('/Floor.aeco:props:DC_Source:Prototype'))
            self.assertEqual(normalize_prototype_hints(root),0)

    def test_full_source_retention(self):
        source,a,b=stage_pair()
        unrelated=add_element(source,Sdf.Path('/World/Site/YardEquipment'),'IfcBuildingElementProxy')
        result=Usd.Stage.Open(source.Flatten(addSourceFileComment=False))
        proof=verify_source(source,result)
        self.assertEqual(proof['source_prims'],len(list(source.TraverseAll())))
        result.RemovePrim(unrelated.GetPath())
        with self.assertRaisesRegex(ValueError,'source prim missing'):
            verify_source(source,result)

    def test_geometry_and_identity_preserved(self):
        source,a,b=stage_pair()
        p=a.GetChildren()[0]
        result=Usd.Stage.Open(source.Flatten(addSourceFileComment=False))
        q=result.GetPrimAtPath(p.GetPath())
        original=q.GetAttribute('aeco:id').Get()
        q.GetAttribute('aeco:id').Set('changed')
        with self.assertRaisesRegex(ValueError,'identity changed'):
            verify_source(source,result)
        q.GetAttribute('aeco:id').Set(original)
        UsdGeom.Xformable(q).AddTranslateOp().Set((1,0,0))
        with self.assertRaisesRegex(ValueError,'world placement changed'):
            verify_source(source,result)
        UsdGeom.Xformable(q).ClearXformOpOrder()
        mesh=UsdGeom.Mesh(q.GetChild('Body'))
        mesh.GetPointsAttr().Set([(0,0,0)])
        with self.assertRaisesRegex(ValueError,'source mesh changed'):
            verify_source(source,result)


if __name__=='__main__': unittest.main()
