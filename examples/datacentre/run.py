#!/usr/bin/env python3
"""Compose, compare, measure and publish the pinned floors example."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(os.environ.get('TOOLCHAIN_DIR',ROOT.parent/'usdaeco-toolchain'))/'tools'))
sys.path.insert(0,str(ROOT/'tools'))
from usdaeco_repeat.cli import register_plugins
register_plugins()
from usdaeco_check.example import run_example
from usdaeco_repeat.example import hook
from usdaeco_repeat.publication import normalize_prototype_hints
from usdaeco_check.example_result import record_result
from usdaeco_render import render


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    if not os.environ.get('AECO_DATACENTRE_ROOT'):
        parser.error('AECO_DATACENTRE_ROOT must name the pinned data checkout')
    example=Path(__file__).parent
    manifest=run_example(example,hook,variant='floors',publish=False,keywords=[])
    print('== stage: floor-plan studies',flush=True)
    records=render(example/'out/study/example.usda',output=example/'out/renders',views=['l01','l02'])
    manifest['renders']=sorted(manifest['renders']+records,key=lambda r:r['path'])
    migrated=normalize_prototype_hints(example/'out/result')
    print(f'== stage: normalize exported prototype hints ({migrated} authored properties)',flush=True)
    manifest['result']=record_result(example/'out/result')
    (example/'out/manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    if args.publish:
        for name in ('result','renders'):
            destination=example/name
            if destination.is_symlink(): raise ValueError('publication target must not be a symlink')
            if destination.exists(): shutil.rmtree(destination)
            shutil.copytree(example/'out'/name,destination)
        shutil.copyfile(example/'out/manifest.json',example/'manifest.json')

if __name__=='__main__': main()
