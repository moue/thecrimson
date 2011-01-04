from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = "this is some help text"
    def handle_noargs(self, **options):
        return "this is a test"