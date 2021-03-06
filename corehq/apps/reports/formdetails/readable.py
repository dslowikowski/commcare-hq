from pydoc import html
from django.http import Http404
from django.utils.safestring import mark_safe
from jsonobject import *
from jsonobject.base import DefaultProperty
from corehq.apps.app_manager.models import get_app, Application
from corehq.apps.app_manager.xform import VELLUM_TYPES
from corehq.apps.reports.formdetails.exceptions import QuestionListNotFound
from django.utils.translation import ugettext_lazy as _


class FormQuestionOption(JsonObject):
    label = StringProperty()
    value = StringProperty()


class FormQuestion(JsonObject):
    label = StringProperty()
    tag = StringProperty()
    type = StringProperty(choices=VELLUM_TYPES.keys())
    value = StringProperty()
    repeat = StringProperty()
    group = StringProperty()
    options = ListProperty(FormQuestionOption, exclude_if_none=True)

    @property
    def icon(self):
        try:
            return VELLUM_TYPES[self.type]['icon']
        except KeyError:
            return 'icon-question-sign'

    @property
    def relative_value(self):
        if self.group:
            prefix = self.group + '/'
            if self.value.startswith(prefix):
                return self.value[len(prefix):]
        return '/'.join(self.value.split('/')[2:])


class FormQuestionResponse(FormQuestion):
    response = DefaultProperty()
    children = ListProperty(lambda: FormQuestionResponse, exclude_if_none=True)


SYSTEM_FIELD_NAMES = (
    "drugs_prescribed", "case", "meta", "clinic_ids", "drug_drill_down", "tmp",
    "info_hack_done"
)


def form_key_filter(key):
    if key in SYSTEM_FIELD_NAMES:
        return False

    if key.startswith(('#', '@', '_')):
        return False

    return True


def get_questions(domain, app_id, xmlns):
    if not app_id:
        raise QuestionListNotFound(
            _("This form is not associated with an app")
        )
    try:
        app = get_app(domain, app_id)
    except Http404:
        raise QuestionListNotFound(
            _("No app could be found")
        )
    if not isinstance(app, Application):
        raise QuestionListNotFound(
            _("Remote apps are not supported")
        )

    form = app.get_form_by_xmlns(xmlns)
    if not form:
        if xmlns == 'http://code.javarosa.org/devicereport':
            raise QuestionListNotFound(
                _("This is a Device Report")
            )
        else:
            raise QuestionListNotFound(
                _("We could not find the question list "
                  "associated with this form")
            )
    # Search for 'READABLE FORMS TEST' for more info
    # to bootstrap a test and have it print out your form xml
    # uncomment this line. Ghetto but it works.
    # print form.wrapped_xform().render()
    return get_questions_from_xform_node(form.wrapped_xform(), app.langs)


def get_questions_from_xform_node(xform, langs):
    questions = xform.get_questions(
        langs, include_triggers=True, include_groups=True)
    return [FormQuestionResponse(q) for q in questions]


def get_questions_for_submission(xform):
    app_id = xform.build_id or xform.app_id
    domain = xform.domain
    xmlns = xform.xmlns

    try:
        questions = get_questions(domain, app_id, xmlns)
        questions_error = None
    except QuestionListNotFound as e:
        questions = []
        questions_error = e
    return questions, questions_error


def get_readable_data_for_submission(xform):
    questions, questions_error = get_questions_for_submission(xform)
    return get_readable_form_data(
        xform.form,
        questions,
        process_label=_html_interpolate_output_refs
    ), questions_error


def get_readable_form_data(xform_data, questions, process_label=None):
    return zip_form_data_and_questions(
        strip_form_data(xform_data),
        questions_in_hierarchy(questions),
        path_context='/%s/' % xform_data.get('#type', 'data'),
        process_label=process_label,
    )


def strip_form_data(data):
    data = data.copy()
    # remove all case, meta, attribute nodes from the top level
    for key in data.keys():
        if not form_key_filter(key) or key in ('meta', 'case'):
            data.pop(key)
    return data


def pop_from_form_data(relative_data, absolute_data, path):
    path = path.split('/')
    if path and path[0] == '':
        data = absolute_data
        # path[:2] will be ['', 'data'] so remove
        path = path[2:]
    else:
        data = relative_data

    while path and data:
        key, path = path[0], path[1:]
        try:
            if path:
                data = data[key]
            else:
                return data.pop(key)
        except KeyError:
            return None


def path_relative_to_context(path, path_context):
    assert path_context.endswith('/')
    if path.startswith(path_context):
        return path[len(path_context):]
    elif path + '/' == path_context:
        return ''
    else:
        return path


def absolute_path_from_context(path, path_context):
    assert path_context.endswith('/')
    if path.startswith('/'):
        return path
    else:
        return path_context + path


def _html_interpolate_output_refs(itext_value, context):
    if hasattr(itext_value, 'with_refs'):
        underline_template = u'<u>&nbsp;&nbsp;%s&nbsp;&nbsp;</u>'
        return mark_safe(
            itext_value.with_refs(
                context,
                processor=lambda x: underline_template % (
                    html.escape(x)
                    if x is not None
                    else u'<i class="icon-question-sign"></i>'
                ),
                escape=html.escape,
            )
        )
    else:
        return itext_value


def _group_question_has_response(question):
    return any(child.response for child in question.children)


def zip_form_data_and_questions(relative_data, questions, path_context='',
                                output_context=None, process_label=None,
                                absolute_data=None):
    """
    The strategy here is to loop through the questions, and at every point
    pull in the corresponding piece of data, removing it from data
    and adding it to the question. At the end, any remain piece of data are
    added to the end as unknown questions.

    Repeats are matched up with their entry node in the data,
    and then this function is applied recursively to each of the elements in
    the list, using the repeat's children as the question list.

    """
    assert path_context
    absolute_data = absolute_data or relative_data
    if not path_context.endswith('/'):
        path_context += '/'
    if not output_context:
        output_context = {
            '%s%s' % (path_context, '/'.join(map(unicode, key))): unicode(value)
            for key, value in _flatten_json(relative_data).items()
        }

    result = []
    for question in questions:
        path = path_relative_to_context(question.value, path_context)
        absolute_path = absolute_path_from_context(question.value, path_context)
        node = pop_from_form_data(relative_data, absolute_data, path)
        # response=True on a question with children indicates that one or more
        # child has a response, i.e. that the entire group wasn't skipped
        question_data = dict(question)
        question_data.pop('response')
        if question.type in ('Group', 'FieldList'):
            children = question_data.pop('children')
            form_question = FormQuestionResponse(
                children=zip_form_data_and_questions(
                    node,
                    children,
                    path_context=absolute_path,
                    output_context=output_context,
                    process_label=process_label,
                    absolute_data=absolute_data,
                ),
                **question_data
            )
            if _group_question_has_response(form_question):
                form_question.response = True
        elif question.type == 'Repeat':
            if not isinstance(node, list):
                node = [node]
            children = question_data.pop('children')
            form_question = FormQuestionResponse(
                children=[
                    FormQuestionResponse(
                        children=zip_form_data_and_questions(
                            entry,
                            children,
                            path_context=absolute_path,
                            output_context=output_context,
                            process_label=process_label,
                            absolute_data=absolute_data,
                        ),
                    )
                    for entry in node
                ],
                **question_data
            )
            for child in form_question.children:
                if _group_question_has_response(child):
                    child.response = True
            if _group_question_has_response(form_question):
                form_question.response = True
        else:
            if (question.type == 'DataBindOnly'
                    and question.label == question.value):
                question_data['label'] = '/'.join(
                    question.value.split('/')[2:])

            if process_label:
                question_data['label'] = process_label(question_data['label'],
                                                       output_context)

            form_question = FormQuestionResponse(response=node,
                                                 **question_data)
        result.append(form_question)

    if relative_data:
        for key, response in sorted(_flatten_json(relative_data).items()):
            joined_key = '/'.join(map(unicode, key))
            result.append(
                FormQuestionResponse(
                    label=joined_key,
                    value='%s%s' % (path_context, joined_key),
                    response=response,
                )
            )

    return result


def _flatten_json(json, result=None, path=()):
    if result is None:
        result = {}
    if isinstance(json, dict):
        for key, value in json.items():
            _flatten_json(value, result, path + (key,))
    elif isinstance(json, list):
        for i, value in enumerate(json):
            _flatten_json(value, result, path + (i,))
    else:
        result[path] = json
    return result


def questions_in_hierarchy(questions):
    # It turns out that questions isn't quite enough to reconstruct
    # the hierarchy if there are groups that share the same ref
    # as their parent (like for grouping on the screen but not the data).
    # In this case, ignore nesting and put all sub questions on the top level,
    # along with the group itself.
    # Real solution is to get rid of this function and instead have
    # get_questions preserve hierarchy to begin with
    result = []
    question_lists_by_group = {None: result}
    for question in questions:
        question_lists_by_group[question.group].append(question)
        if question.type in ('Group', 'Repeat', 'FieldList') \
                and question.value not in question_lists_by_group:
            question_lists_by_group[question.value] = question.children
    return question_lists_by_group[None]
