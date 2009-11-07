from django.core.management.base import NoArgsCommand

from subscriptions.models import EmailSubscription

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list
    help = "Sends all the email subscriptions."
    
    def handle_noargs(self, **options):
        EmailSubscription.send_all()