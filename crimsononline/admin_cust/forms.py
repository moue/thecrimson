from datetime import date, datetime, timedelta
from time import strptime
from re import compile

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from crimsononline.content.models import Issue, ContentGeneric



    

