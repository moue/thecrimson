from crimsononline.info.contactform import ContactForm
from django.core.mail import send_mail
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect

#View for the contact page
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
           
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            recipients = ['president@thecrimson.com']
            
            front = 'Message sent from: ' + name + ' with email address ' + email
            message = front + '\n\n' + message
            
            send_mail('Message submitted on thecrimson.com', message, email,
            recipients, fail_silently=False)
                       
            return HttpResponseRedirect('/about/thanks/')
    else:
        form = ContactForm()
        
    return render_to_response('contact.html', {'form': form})

#View for the corrections page
def corrections(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
           
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            recipients = ['cmarks@fas.harvard.edu']
            
            front = 'Correction sent from: ' + name + ' with email address ' + email
            message = front + '\n\n' + message
            
            send_mail('Correction submitted on thecrimson.com', message, email,
            recipients, fail_silently=False)
                       
            return HttpResponseRedirect('/about/thanks/')
    else:
        form = ContactForm()
        
    return render_to_response('corrections.html', {'form': form})

def thank(request):
    return render_to_response('thank.html')
