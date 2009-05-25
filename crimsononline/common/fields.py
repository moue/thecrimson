from PIL import Image as pilImage
from django.db.models import ImageField

class MaxSizeImageField(ImageField):
    """
    Image field with:
    * resizing to a maximum width and/or height
    """
    
    def __init__(self, verbose=None, max_width=None, max_height=None, **kwargs):
        self.width, self.height = max_width, max_height
        return super(MaxSizeImageField, self).__init__(verbose, **kwargs)
    
    def pre_save(self, model_instance, add):
        file = super(MaxSizeImageField, self).pre_save(model_instance, add)
        img = pilImage.open(file.path)
        width = min(img.size[0], self.width) if self.width else None
        height = min(img.size[1], self.height) if self.height else None
        width = width or img.size[0]
        height = height or img.size[1]
        img.thumbnail((width, height), pilImage.ANTIALIAS)
        img.save(file.path)
        print width, height, file.path
        return file
    
    def get_internal_type(self):
        return "ImageField"