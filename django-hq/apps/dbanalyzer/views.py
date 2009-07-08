# Create your views here.
from django.http import HttpResponse
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.core.exceptions import *

from rapidsms.webui.utils import render_to_response
#from django.shortcuts import render_to_response, get_object_or_404
from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.utils.translation import ugettext_lazy as _
from django.db.models.query_utils import Q
from django.core.urlresolvers import reverse
from xformmanager.models import *
from dbanalyzer import dbhelper
from django.utils.encoding import *
from organization.models import *

import organization.utils as utils

from datetime import timedelta
from django.db import transaction
import uuid

from models import *
import logging
import hashlib
import settings
import traceback
import sys
import os
import string


def inspector(request, table_name, template_name="dbanalyzer/table_inspector.html"):
    context = {}
    context['table_name'] = table_name
    
    str_column = None
    str_column_value = None
    datetime_column = None
    data_column = None
    display_mode = None    
    
    for item in request.GET.items():
        if item[0] == 'str_column':
            str_column = item[1]                    
        if item[0] == 'str_column_value':
            str_column_value = item[1] 
        if item[0] == 'datetime_column':
            datetime_column = item[1]   
        if item[0] == 'data_column':
            data_column = item[1]        
        if item[0] == 'display_mode':
            display_mode = item[1]    
            
    context['str_column'] = str_column
    context['str_column_value'] = str_column_value
    context['datetime_column'] = datetime_column
    context['data_column'] = data_column
    context['display_mode'] = display_mode    
    
    return render_to_response(request, template_name, context)




@login_required()
def view_graph(request, graph_id, template_name="dbanalyzer/view_graph.html"):
    context = {}    
    graph = RawGraph.objects.all().get(id=graph_id)
    
    #get the root group
    extuser = ExtUser.objects.all().get(id=request.user.id)    
    # inject some stuff into the rawgraph.  we can also do more
    # here but for now we'll just work with the domain and set 
    # some dates.  these can be templated down to the sql
    graph.domain = extuser.domain.name
    startdate, enddate = utils.get_dates(request, graph.default_interval)
    graph.startdate = startdate.strftime("%Y-%m-%d")
    graph.enddate = (enddate + timedelta(days=1)).strftime("%Y-%m-%d")
    
    context['chart_title'] = graph.title
    context['chart_data'] = graph.get_flot_data()
    context['thegraph'] = graph
    
    rootgroup = utils.get_chart_group(extuser)    
    graphtree = get_graphgroup_children(rootgroup)    
    context['graphtree'] = graphtree
    context['view_name'] = 'dbanalyzer.views.view_graph'
    context['width'] = graph.width
    context['height'] = graph.height
    
    for item in request.GET.items():
        if item[0] == 'bare':
            template_name = 'dbanalyzer/view_graph_bare.html'
        elif item[0] == 'data':
            context['datatable'] = graph.convert_data_to_table(context['chart_data'])
            template_name='dbanalyzer/view_graph_data.html'            
    
    return render_to_response(request, template_name, context)

@login_required()
def show_allgraphs(request, template_name="dbanalyzer/show_allgraphs.html"):
    context = {}    
    context['allgraphs'] = RawGraph.objects.all()    
    return render_to_response(request, template_name, context)

@login_required()
def show_multi(request, template_name="dbanalyzer/multi_graph.html"):
    context = {}    
    context['width'] = 900
    context['height'] = 350
    context['charts_to_show'] = RawGraph.objects.all()
    return render_to_response(request, template_name, context)


@login_required()
def view_groups(request, template_name="dbanalyzer/view_groups.html"):
    context = {}    
    context['groups'] = GraphGroup.objects.all()
    return render_to_response(request, template_name, context)

    context = {}


def get_graphgroup_children(graph_group):
    ret = {}
    children = GraphGroup.objects.all().filter(parent_group=graph_group)
    for child in children:
        ret[child] = get_graphgroup_children(child)
    return ret
    
@login_required()
def view_group(request, group_id, template_name="dbanalyzer/view_group.html"):
    context = {}
    group = GraphGroup.objects.all().get(id=group_id)
    context['group'] = group  
    context['group_charts'] = []
    context['width'] = 900
    context['height'] = 350
    
    for thegraph in group.graphs.all():
        if hasattr(thegraph,'rawgraph'):
            context['group_charts'].append(thegraph.rawgraph)
        else:
            context['group_charts'].append(thegraph)    
    
    context['child_groups'] = GraphGroup.objects.all().filter(parent_group=group)
    
    #get the root group
    extuser = ExtUser.objects.all().get(id=request.user.id)
    rootgroup = utils.get_chart_group(extuser)    
    graphtree = get_graphgroup_children(rootgroup)
    context['graphtree'] = graphtree
    
    return render_to_response(request, template_name, context)

