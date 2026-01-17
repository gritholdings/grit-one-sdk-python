from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError


class OnboardingBaseView(LoginRequiredMixin, View):
    template_name = "home/onboarding.html"
    onboarding_steps = []
    def get_context(self, request):
        return {}
    def get_success_url(self) -> str:
        return "index"
    def get(self, request, step):
        step = self._validate_step(step)
        if step is None:
            return redirect("onboarding", step=1)
        total_steps = len(self.onboarding_steps)
        saved_data = request.user.metadata or {}
        context = {
            **get_onboarding_flow_context(step, self.onboarding_steps, saved_data),
            **self.get_context(request),
        }
        return render(request, self.template_name, context)
    def post(self, request, step):
        step = self._validate_step(step)
        if step is None:
            return redirect("onboarding", step=1)
        total_steps = len(self.onboarding_steps)
        form_data = clean_form_data_for_onboarding(request.POST.dict())
        try:
            update_model_metadata_from_form(request.user, form_data)
            request.user.save()
        except ValidationError as e:
            saved_data = request.user.metadata or {}
            context = {
                **get_onboarding_flow_context(step, self.onboarding_steps, saved_data),
                **self.get_context(request),
                "error": str(e),
            }
            return render(request, self.template_name, context)
        if "next" in request.POST and step < total_steps:
            return redirect("onboarding", step=step + 1)
        elif "previous" in request.POST and step > 1:
            return redirect("onboarding", step=step - 1)
        elif "next" in request.POST and step == total_steps:
            update_model_metadata_from_form(request.user, {'has_completed_onboarding': True})
            request.user.save()
            return redirect(self.get_success_url())
        elif "save" in request.POST:
            return redirect(self.get_success_url())
        return redirect("onboarding", step=step)
    def _validate_step(self, step):
        try:
            step = int(step)
        except (TypeError, ValueError):
            return None
        total_steps = len(self.onboarding_steps)
        if step < 1 or step > total_steps:
            return None
        return step


def update_model_metadata_from_form(instance, form_data):
    if instance.metadata is None:
        instance.metadata = {}
    checkbox_fields = {field for field, value in form_data.items() if value == 'true'}
    for field, value in form_data.items():
        if field not in checkbox_fields:
            instance.metadata[field] = value
    for field in checkbox_fields:
        instance.metadata[field] = True
    seen_checkboxes = {field for field in instance.metadata if isinstance(instance.metadata[field], bool)}
    for checkbox in seen_checkboxes:
        if checkbox not in form_data:
            instance.metadata[checkbox] = False


def clean_form_data_for_onboarding(form_data):
    cleaned = form_data.copy()
    cleaned.pop('csrfmiddlewaretoken', None)
    cleaned.pop('step', None)
    for btn in ['next', 'previous', 'save']:
        cleaned.pop(btn, None)
    return cleaned


def get_onboarding_flow_context(step, onboarding_steps, saved_data):
    total_steps = len(onboarding_steps)
    return {
        'step': step,
        'step_config': onboarding_steps[step - 1],
        'total_steps': total_steps,
        'saved_data': saved_data,
        'show_previous': step > 1,
        'is_last_step': step == total_steps,
    }
