from pathlib import Path
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))
from pxr import Plug
Plug.Registry().RegisterPlugins(os.environ.get('CORE_PLUGIN_DIR', str(ROOT.parent / 'usdaeco-core/out/plugins/usdAeco/resources')))
Plug.Registry().RegisterPlugins(str(ROOT / 'usdAecoRepeat'))
Plug.Registry().RegisterPlugins(str(ROOT / 'usdAecoRepeatValidators'))
