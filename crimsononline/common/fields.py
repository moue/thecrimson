from os.path import split, exists, splitext
from PIL import Image as pilImage
from django.db.models import ImageField
from django.db.models.fields.files import ImageFieldFile

"""Model fields."""

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
        if file:
            img = pilImage.open(file.path)
            width = min(img.size[0], self.width) if self.width else None
            height = min(img.size[1], self.height) if self.height else None
            width = width or img.size[0]
            height = height or img.size[1]
            img.thumbnail((width, height), pilImage.ANTIALIAS)
            img.save(file.path)
        return file


def size_spec_to_size(size_spec, img_width, img_height):
    """
    converts a size_spec into actual image dimensions for the resulting image 
    """
    max_w, max_h, crop_w, crop_h = size_spec
    # set width / height constraints so we never upscale images
    max_w = min(img_width, max_w) if max_w else img_width
    max_h = min(img_height, max_h) if max_h else img_height
    
    if not crop_w:
        crop_w, crop_h = img_width, img_height
    
    h_ratio = float(max_h) / crop_h
    w_ratio = float(max_w) / crop_w
    ratio = min(h_ratio, w_ratio)
    
    max_w = int(ratio * crop_w)
    max_h = int(ratio * crop_h)
    
    return max_w, max_h
    

class AutosizeImageFieldFile(ImageFieldFile):
    """
    file attr_class, with additional wizardry for dynamically resizing images.
    keeps all resized images in the cache, to preserve disk space
    """
    def __init__(self, *args, **kwargs):
        ImageFieldFile.__init__(self, *args, **kwargs)
        self._url_cache, self._path_cache = {}, {}
    
    def crop_thumb(self, size_spec, crop_coords):
        """
        saves a cropped version of the file
        
        @size_spec => (max_width, max_height, crop_width, crop_height)
            crop_width and crop_height are relative to each other
        @crop_coords => x1,y1, x2, y2 tuple; represents upper left corner and 
            lower right corner of crop region
        """
        max_w, max_h, crop_w, crop_h = size_spec
        # set width / height constraints so we never upscale images
        max_w = min(self.width, max_w) if max_w else self.width
        max_h = min(self.height, max_h) if max_h else self.height
        
        # crop the file
        img = pilImage.open(self.path)
        img = img.transform(size_spec[:2], pilImage.EXTENT, crop_coords)
        
        new_path = self._get_path(size_spec)
        img.save(new_path)
        self._path_cache[size_spec] = new_path
    
    def display_path(self, size_spec):
        """returns the path for a sized image"""
        path = self._path_cache.get(size_spec, None)
        if path: return path
        path = self._get_path(size_spec)
        if not exists(path):
            img = pilImage.open(self.path)
            ht, wd = size_spec_to_size(size_spec, 
                self.width, self.height)
            # cropped image
            if size_spec[2] and size_spec[3]:
                # autogenerate crop_coordinates
                aspect_ratio = float(self.width) / float(self.height)
                crop_ratio = float(size_spec[2]) / size_spec[3]
                # extra space on left / right => preserve height
                if  aspect_ratio > crop_ratio:
                    w = int(self.height * crop_ratio)
                    crop_x1 = (self.width - w) / 2
                    crop_coords = (crop_x1, 0, crop_x1 + w, self.height)
                # extra space on top / bottom => preserve width
                elif aspect_ratio < crop_ratio:
                    h = int(self.width / crop_ratio)
                    crop_y1 = (self.height - h) / 2
                    crop_coords = (0, crop_y1, self.width, crop_y1 + h)
                else:
                    crop_coords = (0, 0, self.width, self.height)
                img = img.transform((ht, wd), pilImage.EXTENT, crop_coords)
            # constrained image
            else:
                img.thumbnail((ht, wd), pilImage.ANTIALIAS)
            img.save(path)
        self._path_cache[size_spec] = path
        return path
    
    def display_url(self, size_spec):
        """returns the path for a sized image"""
        url = self._url_cache.get(size_spec, None)
        if url: return url
        url = '%s/%s' % (split(self.url)[0], 
            split(self.display_path(size_spec))[1])
        self._url_cache[size_spec] = url
        return url
    
    def _get_path(self, size_spec):
        """
        calculates the path, no caching involved
        """
        path, ext = splitext(self.path)
        size = size_spec_to_size(size_spec, self.width, self.height)
        return path + "_%dx%d" % size + ext
    

class SuperImageField(ImageField):
    """
    just like super mario, this imagefield can run, jump, shoot fireballs,
        resize images on upload, overwrite existing images, 
        give you an autosizing image attribute, and fight bowser
    """
    attr_class = AutosizeImageFieldFile
    
    def __init__(self, verbose=None, max_width=None, max_height=None, **kwargs):
        self.width, self.height = max_width, max_height
        return super(SuperImageField, self).__init__(verbose, **kwargs)
    
    def pre_save(self, model_instance, add):
        file = super(SuperImageField, self).pre_save(model_instance, add)
        if file:
            img = pilImage.open(file.path)
            width = min(img.size[0], self.width) if self.width else None
            height = min(img.size[1], self.height) if self.height else None
            width = width or img.size[0]
            height = height or img.size[1]
            img.thumbnail((width, height), pilImage.ANTIALIAS)
            img.save(file.path)
        return file
    