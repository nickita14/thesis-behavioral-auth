from django.contrib import admin

from .models import BehaviorProfile


@admin.register(BehaviorProfile)
class BehaviorProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'feature_schema_version', 'detector_version',
        'n_training_samples', 'trained_at', 'is_active',
    )
    list_filter = ('is_active', 'feature_schema_version', 'detector_version')
    search_fields = ('user__username', 'user__email')
    readonly_fields = (
        'trained_at', 'n_training_samples', 'n_training_sessions',
        'training_score_mean', 'training_score_std',
    )
    # model_blob is binary — don't show in admin form
    exclude = ('model_blob',)
