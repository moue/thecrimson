from django.db import models
from django.contrib.auth.models import User, Group

class UserData(models.Model):
    user = models.ForeignKey(User, unique=True)
    huid_hash = models.CharField('Harvard ID',
        blank=True, null=True, max_length=255,
        help_text='8 digit HUID. Warning: Without an HUID, this ' \
                'contributor won\'t be able to log on to the website. <br> ' \
                'This number will be encrypted before it is stored.')
                
    def __unicode__(self):
        if self.huid_hash is None:
            return str(self.pk)
        return self.huid_hash
    
    """
    def __setattr__(self, name, value):
        # hash the huid before storing it; but actually don't
        #if name == 'huid_hash' and value != None:
        #    value = md5(value).digest()
        return super(UserData, self).__setattr__(name, value)
    """
    
    def parse_token(self):
        # a b c d
        return False
    
    def delete(self):
        self.contributor.clear()
        super(UserData, self).delete()
    

class Board(models.Model):
    """Organizational unit of the Crimson
    
    # create a Board
    >>> b = Board.objects.create(name='biz')
    
    # stupidest test ever
    >>> b.name
    'biz'
    """
    name = models.CharField(blank=False, null=False, max_length=20)
    group = models.ForeignKey(Group, null=True, blank=True)
    
    def __unicode__(self):
        return self.name
