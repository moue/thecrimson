"""
Forms, widgets, fields.
However, put forms specifically for Admin in admin.py, not here
"""

from django import forms
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image

class ImageSelectMultipleWidget(forms.widgets.SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        output = '<div id="images-bank"><ul class="image-list"></ul>' \
                    '<div class="links"></div></div>\n'
        output += super(ImageSelectMultipleWidget, self). \
            render(name, value, attrs, choices)
        output += '<div id="images-current"><h3>Images in this ' \
                    'Image Gallery</h3><ul class="image-list"></ul></div>'
        return mark_safe(output)

class ImageSelectModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    # super's clean thinks that valid Images = images in the initial queryset
    #    but that's not the case; all images are valid.  we temporarily change
    #    the queryset, do a clean, and then change the queryset back (to
    #    mitigate side effects).
    def clean(self, value):
        qs = self.queryset
        self.queryset = Image.objects
        c = super(ImageSelectModelMultipleChoiceField, self).clean(value)
        self.queryset = qs
        return c
    

class ImageSelectModelChoiceField(forms.ModelChoiceField):
    # see above
    def clean(self, value):
        qs = self.queryset
        self.queryset = Image.objects
        c = super(ImageSelectModelChoiceField, self).clean(value)
        self.queryset = qs
        return c
