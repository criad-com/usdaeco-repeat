"""aeco-repeat diff, takeoff and compose, runnable directly from source."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "tools"))
from pxr import Plug, Sdf, Usd


def register_plugins():
    repo=ROOT
    for variable,default in (
        ('CORE_PLUGIN_DIR',repo.parent/'usdaeco-core/out/plugins/usdAeco/resources'),
        ('AXIS_PLUGIN_DIR',repo.parent/'usdaeco-axis/out/plugins/usdAecoAxis/resources'),
        ('BUILDUP_PLUGIN_DIR',repo.parent/'usdaeco-buildup/usdAecoBuildUp')):
        path=Path(os.environ.get(variable,default)).resolve()
        if path.exists(): Plug.Registry().RegisterPlugins(str(path))
    Plug.Registry().RegisterPlugins(str(repo/'usdAecoRepeat'))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='command',required=True)
    for command in ('diff','takeoff','compose'):
        p=subs.add_parser(command);p.add_argument('stage',type=Path)
        if command=='takeoff':
            p.add_argument('--level',action='append',default=[])
            p.add_argument('--by-level',action='store_true')
            p.add_argument('--repeat-resolved',action='store_true')
            p.add_argument('--derived-layer',type=Path)
        else:
            p.add_argument('--instance',required=True)
            p.add_argument('--tolerance',type=float,default=1e-6)
        if command=='compose': p.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    register_plugins()
    from usdaeco_repeat.diff import compare
    from usdaeco_repeat.quantity import takeoff,derive
    from usdaeco_repeat.compose import compose
    from usdaeco_repeat.model import elements
    try:
        stage=Usd.Stage.Open(str(args.stage.resolve()))
        if not stage or stage.GetCompositionErrors(): raise ValueError('input stage does not compose')
        if args.command=='takeoff':
            levels=[stage.GetPrimAtPath(p) for p in args.level] if args.level else [p for p in stage.Traverse() if p.GetTypeName()=='AecoLevel']
            if not levels or not all(levels): raise ValueError('valid level scopes required')
            result=takeoff(levels,args.by_level,args.repeat_resolved)
            if args.derived_layer:
                # Session composition keeps source files read-only.
                path=args.derived_layer.resolve()
                if path.exists(): raise ValueError('derived output already exists')
                layer=Sdf.Layer.CreateNew(str(path));stage.GetSessionLayer().subLayerPaths=[str(path)]
                derive(stage,list(dict.fromkeys(p for l in levels for p in elements(l))),layer)
        else:
            instance=stage.GetPrimAtPath(args.instance)
            if not instance: raise ValueError('instance prim does not exist')
            if args.command=='diff': result=compare(instance,args.tolerance)
            else:
                _,result=compose(instance,args.output,args.tolerance)
        print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
        return 0
    except (ValueError,RuntimeError) as exc:
        parser.exit(1,str(exc)+'\n')

if __name__=='__main__':
    raise SystemExit(main())
