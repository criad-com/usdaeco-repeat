#!/pxrpythonsubst
import tempfile
import unittest
from pathlib import Path
from pxr import Plug,Sdf,Usd,UsdGeom,UsdValidation
from fixtures import stage_pair,add_element
from usdaeco_repeat.diff import compare
from usdaeco_repeat.quantity import derive
from usdAecoRepeatValidators import validatorTokens as tokens

ROOT=Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoRepeatValidators'))


def errors(stage,token):
    validator=UsdValidation.ValidationRegistry().GetOrLoadValidatorByName(token)
    assert validator,'validator must load'
    return list(UsdValidation.ValidationContext([validator]).Validate(stage))

class TestValidators(unittest.TestCase):
    def test_RepeatDrift(self):
        s,a,b=stage_pair()
        self.assertEqual(errors(s,tokens.REPEAT_DRIFT_CHECKER),[])
        p=s.GetPrimAtPath(b.GetPath().AppendChild('Partition'))
        UsdGeom.Xformable(p).AddTranslateOp().Set((1,0,0))
        self.assertEqual(compare(b)['changes'][0]['kind'],'moved')
        self.assertEqual([e.GetName() for e in errors(s,tokens.REPEAT_DRIFT_CHECKER)],['RepeatDrift'])
        Usd.CollectionAPI(b,'deviations').CreateIncludesRel().SetTargets([p.GetPath()])
        p.SetCustomDataByKey('aeco:repeat:reason','   ')
        self.assertEqual(len(errors(s,tokens.REPEAT_DRIFT_CHECKER)),1)
        self.assertEqual(len(errors(s,tokens.DEVIATION_WITHOUT_REASON_CHECKER)),1)
        p.SetCustomDataByKey('aeco:repeat:reason','Meeting room adjusted')
        self.assertEqual(errors(s,tokens.REPEAT_DRIFT_CHECKER),[])

    def test_DeviationWithoutReason(self):
        s,a,b=stage_pair();p=b.GetChildren()[0]
        Usd.CollectionAPI(b,'deviations').CreateIncludesRel().SetTargets([p.GetPath()])
        self.assertIsNone(p.GetCustomDataByKey('aeco:repeat:reason'))
        self.assertEqual(errors(s,tokens.DEVIATION_WITHOUT_REASON_CHECKER)[0].GetName(),'DeviationWithoutReason')
        p.SetCustomDataByKey('aeco:repeat:reason','Agreed exception')
        self.assertEqual(errors(s,tokens.DEVIATION_WITHOUT_REASON_CHECKER),[])
        Usd.CollectionAPI(b,'deviations').GetIncludesRel().SetTargets([b.GetPath().AppendChild('Absent')])
        self.assertEqual(len(errors(s,tokens.DEVIATION_WITHOUT_REASON_CHECKER)),1)

    def test_QuantityStale(self):
        s,a,b=stage_pair();p=a.GetChildren()[0]
        with tempfile.TemporaryDirectory() as d:
            layer=Sdf.Layer.CreateNew(str(Path(d)/'quantities.usda'));s.GetRootLayer().subLayerPaths=[layer.identifier]
            derive(s,[p],layer)
            self.assertEqual(errors(s,tokens.QUANTITY_STALE_CHECKER),[])
            p.GetAttribute('aeco:axis:end').Set((5,0,0))
            self.assertEqual(p.GetAttribute('aeco:qto:length').Get(),4)
            self.assertEqual(errors(s,tokens.QUANTITY_STALE_CHECKER)[0].GetName(),'QuantityStale')
            derive(s,[p],layer)
            self.assertEqual(errors(s,tokens.QUANTITY_STALE_CHECKER),[])
            p.GetAttribute('aeco:qto:count').Set(99)
            self.assertEqual(len(errors(s,tokens.QUANTITY_STALE_CHECKER)),1)

    def test_cycle_and_missing_prototype(self):
        s,a,b=stage_pair();a.ApplyAPI('AecoRepeatAPI');a.CreateRelationship('aeco:repeat:prototype').SetTargets([b.GetPath()])
        self.assertEqual(len(errors(s,tokens.REPEAT_DRIFT_CHECKER)),2)
        a.GetRelationship('aeco:repeat:prototype').SetTargets([])
        self.assertEqual(len(errors(s,tokens.REPEAT_DRIFT_CHECKER)),2)

if __name__=='__main__': unittest.main()
