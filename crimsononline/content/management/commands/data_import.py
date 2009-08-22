from django.core.management.base import NoArgsCommand
from crimsononline.content.models import *
from crimsononline.settings import *

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list
    help = "Imports data from the old website, hosted on crimson-sql1. Requires pymssql 1.0.2"

    def handle_noargs(self, **options):
        try:
            import pymssql
        except:
            print "Could not import pymssql"
        print DATA_IMPORT_USER
        print DATA_IMPORT_PASSWORD
        conn = pymssql.connect(host='CRIMSON-SQL1', user=DATA_IMPORT_USER,password=DATA_IMPORT_PASSWORD, database='CrimsonWebsite', as_dict=True)
            
        