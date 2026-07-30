from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def root_health_check(request):
    return JsonResponse({
        "status": "online",
        "message": "Dokan ERP Django API Backend is running successfully!",
        "endpoints": {
            "admin": "/admin/",
            "api_root": "/api/",
            "products": "/api/products/",
            "parties": "/api/parties/",
            "transactions": "/api/transactions/",
            "dashboard_stats": "/api/dashboard/stats/"
        }
    })

urlpatterns = [
    path('', root_health_check, name='root-health-check'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
