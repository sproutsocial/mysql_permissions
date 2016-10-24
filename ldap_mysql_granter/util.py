# -*- coding: utf-8 -*-
"""
templator simply renders templates
 copyright:  2015, (c) sproutsocial.com
 author:   Nicholas Flink <nicholas@sproutsocial.com>
"""

import getpass
import jinja2
import logging
import os
logger = logging.getLogger(__name__)


def renderTemplate(template, argDict):
    contents = template
    template_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates", template)
    if os.path.exists(template_file):
        fh = open(template_file, "r")
        contents = fh.read()
        fh.close()
    template = jinja2.Template(contents)
    return template.render(argDict)


def askQuestion(context, default=None, password=False):
    if default is None:
        question = context + ": "
    else:
        question = context + " [" + default + "]: "
    if password:
        answer = getpass.getpass(question)
    else:
        answer = raw_input(question)
    if len(answer) == 0 and default is not None:
        answer = default
    return answer


def askPassword(context, default=None):
    return askQuestion(context, default, True)
