from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import Component, CheckEvent
from .services import DEMO_FILES, verify_component


@require_http_methods(["GET", "POST"])
@csrf_protect
def index(request):
    if request.method == "POST":
        operation = request.POST.get("operation", "")
        actor = (
            request.user.get_username()
            if request.user.is_authenticated
            else "anonymous"
        )

        if operation == "CHECK_ALL":
            results = [verify_component(name, actor=actor) for name in DEMO_FILES]
            request.session.pop("last_demo", None)
        elif operation in {"CHECK", "DEMO_START"}:
            name = request.POST.get("component", "")
            if name not in DEMO_FILES:
                return HttpResponseBadRequest("Неизвестный компонент.")
            event = verify_component(name, actor=actor, operation=operation)
            results = [event]

            if operation == "DEMO_START":
                allowed = event.verdict == "TRUSTED" and event.action == "ALLOWED"
                count = request.session.get("demo_count", 0)
                if allowed:
                    count += 1
                    request.session["demo_count"] = count
                request.session["last_demo"] = {
                    "allowed": allowed,
                    "component": name,
                    "number": count,
                }
            else:
                request.session.pop("last_demo", None)
        else:
            return HttpResponseBadRequest("Неизвестная операция.")

        request.session["last_check_ids"] = [event.pk for event in results]
        return redirect("integrity:index")

    components = {
        component.name: component
        for component in Component.objects.filter(name__in=DEMO_FILES)
    }
    rows = []
    summary = {"total": len(DEMO_FILES), "trusted": 0, "untrusted": 0, "errors": 0}
    verdict_keys = {
        "TRUSTED": "trusted",
        "UNTRUSTED": "untrusted",
        "VERIFICATION_ERROR": "errors",
    }

    for name in DEMO_FILES:
        event = CheckEvent.objects.filter(component_name=name).first()
        rows.append({"name": name, "component": components.get(name), "last_event": event})
        if event and event.verdict in verdict_keys:
            summary[verdict_keys[event.verdict]] += 1

    recent_results = CheckEvent.objects.filter(
        pk__in=request.session.get("last_check_ids", [])
    ).order_by("component_name")

    return render(request, "integrity/index.html", {
        "rows": rows,
        "summary": summary,
        "recent_results": recent_results,
        "events": CheckEvent.objects.all()[:20],
        "last_demo": request.session.get("last_demo"),
    })
