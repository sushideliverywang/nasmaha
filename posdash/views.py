from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
# Create your views here.

def dashboard(request):
    return render(request, "posdash/dashboard.html")

def login_user(request):
    #check to see if logging in
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        # Authenticate
        user = authenticate(request, username = username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "You Have Been Logged In")
            return redirect('dashboard')
        else:
            messages.success(request, "There Was An Error Logging in ...")
            return redirect('login')
    else:
        return render(request, 'posdash/login.html')

def logout_user(request):
    logout(request)
    messages.success(request, "you have been logged out")
    return redirect('dashboard')

def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            # Authenticate and login
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username = username, password = password)
            login(request, user)
            messages.success(request, "You Have successfully Register")
            return redirect('dashboard')
        
    else:
        form = SignUpForm()
        return render(request, 'posdash/register.html', {'form':form})
    
    return render(request, 'posdash/register.html', {'form':form})

def inventory(request):
    return render(request, "posdash/inventory.html")
