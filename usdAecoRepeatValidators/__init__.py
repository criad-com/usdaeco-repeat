"""Python validator registration following the UsdValidation plugin pattern."""
from pathlib import Path
import sys
from pxr import Sdf, UsdValidation
# Source-tree operation does not require setuptools or an editable install.
_tools = Path(__file__).resolve().parents[1] / 'tools'
if _tools.is_dir():
    sys.path.insert(0,str(_tools))
from usdaeco_repeat.diff import compare
from usdaeco_repeat.model import deviation_members, has_api, reason
from usdaeco_repeat.quantity import stale
from . import validatorTokens as tokens


def error(name, prim, message):
    return UsdValidation.ValidationError(name,UsdValidation.ValidationErrorType.Error,
        [UsdValidation.ValidationErrorSite(prim.GetStage(),prim.GetPath())],message)


def drift_task(stage, time_range):
    findings=[]
    for prim in stage.Traverse():
        if not has_api(prim,'AecoRepeatAPI'):
            continue
        try:
            result=compare(prim)
            for change in result['changes']:
                if not change['declared']:
                    findings.append(error(tokens.REPEAT_DRIFT,prim,
                        change['kind']+': '+(change['instance'] or change['prototype'])))
        except ValueError as exc:
            findings.append(error(tokens.REPEAT_DRIFT,prim,str(exc)))
    return findings


def deviation_task(prim, time_range):
    findings=[]
    for path in deviation_members(prim):
        member=prim.GetStage().GetPrimAtPath(path)
        text=reason(member)
        if not isinstance(text,str) or not text.strip():
            findings.append(error(tokens.DEVIATION_WITHOUT_REASON,prim,
                'Deviation member requires a nonblank reason: '+str(path)))
    return findings


def quantity_task(prim, time_range):
    try:
        invalid=stale(prim)
    except (ValueError,RuntimeError):
        invalid=True
    return [error(tokens.QUANTITY_STALE,prim,'Recompute quantities: measured inputs, value or source stamp differ.')] if invalid else []

_registry=UsdValidation.ValidationRegistry()
_registry.RegisterPluginStageValidator(tokens.REPEAT_DRIFT_CHECKER,drift_task)
_registry.RegisterPluginPrimValidator(tokens.DEVIATION_WITHOUT_REASON_CHECKER,deviation_task)
_registry.RegisterPluginPrimValidator(tokens.QUANTITY_STALE_CHECKER,quantity_task)
