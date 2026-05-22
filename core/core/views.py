from django.shortcuts import render
def login_view(request):
    return render(request, 'login.html')
def register_view(request):
    return render(request, 'register.html')
def download_view(request):
    return render(request, 'downloads.html')
def profile_view(request):
    return render(request, 'profile.html')
def index_view(request):
    return render(request, 'index.html')
def history_view(request):
    return render(request, 'history.html')
def urlsanalysis_view(request):
    return render(request, 'urlsanalyzer.html')
def forgot_password_view(request):
    return render(request, 'forgot-password.html')
def reset_password_view(request, token):
    return render(request, 'reset-password.html')