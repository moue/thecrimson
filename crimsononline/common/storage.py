from django.core.files.storage import FileSystemStorage

class OverwriteStorage(FileSystemStorage):
    """
    storage that always overwrites
        see http://code.djangoproject.com/ticket/4339#comment:25
    """
    def _save(self, name, content):
        if self.exists(name):
            self.delete(name)
        return super(OverwriteStorage, self)._save(name, content)
    def get_available_name(self, name):
        if self.exists(name):
            self.delete(name)
        return name