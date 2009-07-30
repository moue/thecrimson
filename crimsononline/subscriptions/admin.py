from django.contrib.auth.models import User
from django.contrib import admin
from crimsononline.subscriptions.models import *

class SubscriberBackend:
    """
    Authenticate subscriber from the User database by returning a Subscriber object, not a User
    """

    def authenticate(self, username=None, password=None):
        try:
            subscriber = User.objects.filter(username = username).subscriber
            print "FOUND SUBSCRIBER"
            return subscriber
        except:
            return None
            
    def get_user(self, user_id):
        try:
            subscriber = User.objects.get(pk=user_id).subscriber
            return subscriber
        except User.DoesNotExist:
            return None

            
admin.site.register(Subscriber)
admin.site.register(SubscriberRegistration)