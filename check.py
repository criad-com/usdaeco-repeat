#!/usr/bin/env python3
"""Run real registry and example gates; print N checks, M failed."""
import json
import math
import os
from pathlib import Path
import sys
from collections import Counter
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(os.environ.get('TOOLCHAIN_DIR',ROOT.parent/'usdaeco-toolchain'))/'tools'))
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT))
from usdaeco_check import Report,can_apply,plugin_requires,registry_probe,validate_examples
from usdaeco_check.structure import check_structure
from usdaeco_check.example import check_example
from usdaeco_repeat.cli import register_plugins


def main():
    report=Report()
    register_plugins()
    from pxr import Plug,Usd,UsdValidation
    core=Path(os.environ.get('CORE_DIR',ROOT.parent/'usdaeco-core'))
    Plug.Registry().RegisterPlugins(str(core/'usdAecoValidators'))
    Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoRepeatValidators'))
    print('== stage: core validator import',flush=True)
    try:
        import usdAecoValidators
    except ImportError:
        report.check('core validators import',False,'usdAecoValidators must be importable; set PYTHONPATH to the core checkout and this repository')
        return report.finish()
    report.check('core validators import',True)
    deps=[os.environ.get('CORE_PLUGIN_DIR',str(core/'out/plugins/usdAeco/resources')),
          os.environ.get('AXIS_PLUGIN_DIR',str(ROOT.parent/'usdaeco-axis/out/plugins/usdAecoAxis/resources')),
          os.environ.get('BUILDUP_PLUGIN_DIR',str(ROOT.parent/'usdaeco-buildup/usdAecoBuildUp'))]
    print('== stage: structure',flush=True)
    for result in check_structure(ROOT,deps=deps): report.add(result)
    print('== stage: registry',flush=True)
    report.add(plugin_requires(deps+[ROOT/'usdAecoRepeat']))
    pins=json.loads((ROOT/'dependencies.json').read_text())['repos']
    report.check('runtime versions match pinned evidence',all(
        Plug.Registry().GetPluginWithName(pin['library']).metadata['aeco']['version']==pin['ref'].removeprefix('v')
        for pin in pins.values() if pin['library']))
    report.add(registry_probe(['AecoRepeatAPI','AecoQuantityAPI'],['AecoLevel']))
    report.add(can_apply([('AecoLevel','AecoRepeatAPI',True),('Xform','AecoRepeatAPI',False),('Mesh','AecoQuantityAPI',True),('Material','AecoQuantityAPI',False)]))
    registry=UsdValidation.ValidationRegistry()
    for keyword,count in [('UsdAecoRepeatValidators',3),('UsdAecoValidators',8)]:
        metadata=registry.GetValidatorMetadataForKeyword(keyword)
        report.check(keyword+' listing',len(metadata)==count and all(registry.GetOrLoadValidatorByName(m.name) for m in metadata))
    from usdaeco_check.validation import run
    report.add(validate_examples(ROOT/'usdAecoRepeat/examples',[],validators=[lambda s:run(s,['UsdAecoRepeatValidators','UsdAecoValidators'])]))
    print('== stage: published example',flush=True)
    report.add(check_example(ROOT/'examples/datacentre'))
    stage=Usd.Stage.Open(str(ROOT/'examples/datacentre/result/example.usdc'))
    source=Usd.Stage.Open(str(Path(os.environ['AECO_DATACENTRE_ROOT'])/'dist/floors/dc.usda'))
    from usdaeco_repeat.publication import verify_source
    try:
        preservation=verify_source(source,stage)
        report.check('full floors source retained',True,json.dumps(preservation,sort_keys=True))
    except ValueError as exc:
        report.check('full floors source retained',False,str(exc))
    errors=run(stage,['UsdAecoValidators'])
    counts={name:sum(str(e.GetType()).endswith(name) for e in errors) for name in ('Error','Warn','Info')}
    baseline=run(source,['UsdAecoValidators'])
    fingerprint=lambda items:Counter((e.GetName(),str(e.GetType()),e.GetMessage()) for e in items)
    report.check('published core conformance',counts['Error']==0 and fingerprint(errors)==fingerprint(baseline),
                 json.dumps(counts,sort_keys=True)+'; warnings must equal the pinned source baseline')
    repeat=run(stage,['UsdAecoRepeatValidators'])
    expected=json.loads((ROOT/'examples/datacentre/expected/findings.json').read_text())
    planned=sum(f['name']=='RepeatDrift' for f in expected)
    report.check('seeded example validator findings',len(repeat)==planned and all(e.GetName()=='RepeatDrift' for e in repeat),f'{len(repeat)} expected drift errors; no stale quantities or missing reasons')
    findings=json.loads((ROOT/'examples/datacentre/out/findings.json').read_text())
    keyed={f['name']:f for f in findings if f['name']!='RepeatDrift'}
    drift=keyed['FloorDrift'];q=keyed['ScheduleDelta'];proof=keyed['Composition']
    # The pinned floor partition is both shifted and extended: diff reports changed.
    report.check('changed wall and extra door',drift['all_changes']=={'changed':1,'extra':1} and drift['moved_walls']==0 and drift['extra_doors']==1 and drift['declared_deviations']==0)
    report.check('measured schedule delta',q['doors']==1 and math.isclose(q['partition_length_m'],3.2,abs_tol=1e-6) and math.isclose(q['partition_length_L01_m'],43.0,abs_tol=1e-6) and math.isclose(q['partition_length_L02_m'],46.2,abs_tol=1e-6),json.dumps(q,sort_keys=True))
    report.check('reference composition equivalence',proof['max_error']<=1e-6 and proof['vertices_checked']>0 and proof['reference_count']==1,json.dumps(proof,sort_keys=True))
    return report.finish()

if __name__=='__main__': raise SystemExit(main())
