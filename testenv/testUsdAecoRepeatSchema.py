#!/pxrpythonsubst
import unittest
from pathlib import Path
from pxr import Plug, Usd

ROOT = Path(__file__).resolve().parents[1]
Plug.Registry().RegisterPlugins(str(ROOT / 'usdAecoRepeat'))

class TestSchema(unittest.TestCase):
    def test_registry_and_restrictions(self):
        stage = Usd.Stage.CreateInMemory()
        level = stage.DefinePrim('/Level', 'AecoLevel')
        self.assertTrue(level.CanApplyAPI('AecoRepeatAPI'))
        self.assertFalse(stage.DefinePrim('/Cube', 'Cube').CanApplyAPI('AecoRepeatAPI'))
        self.assertTrue(stage.GetPrimAtPath('/Cube').CanApplyAPI('AecoQuantityAPI'))
        self.assertFalse(stage.DefinePrim('/Material', 'Material').CanApplyAPI('AecoQuantityAPI'))
        level.ApplyAPI('AecoRepeatAPI')
        self.assertIn('CollectionAPI:deviations', level.GetAppliedSchemas())
        self.assertEqual(Usd.CollectionAPI(level,'deviations').GetExpansionRuleAttr().Get(), 'explicitOnly')

    def test_derived_contract(self):
        registry = Usd.SchemaRegistry()
        for schema, names in [('AecoRepeatAPI',['aeco:repeat:offset']),('AecoQuantityAPI',['aeco:qto:'+n for n in ('length','area','volume','count')])]:
            definition = registry.FindAppliedAPIPrimDefinition(schema)
            for name in names:
                self.assertIs(definition.GetPropertyMetadata(name,'aecoDerived'), True)

if __name__ == '__main__':
    unittest.main()
