from django.contrib import admin
from .models import File, UpdateID, Message, UserState, CompactDictionary


admin.site.register(File, admin.ModelAdmin)
admin.site.register(UpdateID, admin.ModelAdmin)
admin.site.register(Message, admin.ModelAdmin)
admin.site.register(UserState, admin.ModelAdmin)
admin.site.register(CompactDictionary, admin.ModelAdmin)
