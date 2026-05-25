from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='KYCSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('external_reference', models.CharField(blank=True, max_length=100, null=True)),
                ('applicant_name', models.CharField(blank=True, max_length=255, null=True)),
                ('applicant_document_type', models.CharField(blank=True, max_length=50, null=True)),
                ('applicant_document_number', models.CharField(blank=True, max_length=50, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('recording', 'Recording'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('flagged', 'Flagged'), ('expired', 'Expired')], default='pending', max_length=20)),
                ('video_s3_key', models.CharField(blank=True, max_length=500, null=True)),
                ('video_duration_ms', models.IntegerField(blank=True, null=True)),
                ('video_resolution', models.CharField(blank=True, max_length=20, null=True)),
                ('video_size_bytes', models.BigIntegerField(blank=True, null=True)),
                ('challenge_type', models.CharField(choices=[('none', 'None'), ('random_movement', 'Random Movement'), ('read_text', 'Read Text'), ('blink', 'Blink Detection')], default='none', max_length=50)),
                ('challenge_data', models.JSONField(blank=True, default=dict)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_sessions', to='users.user')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kyc_sessions', to='users.organization')),
            ],
            options={'db_table': 'kyc_sessions', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='VideoChunk',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('chunk_index', models.IntegerField()),
                ('s3_key', models.CharField(max_length=500)),
                ('size_bytes', models.IntegerField(blank=True, null=True)),
                ('duration_ms', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='kyc_sessions.kycsession')),
            ],
            options={'db_table': 'video_chunks', 'ordering': ['chunk_index']},
        ),
        migrations.AddIndex(
            model_name='kycsession',
            index=models.Index(fields=['organization', 'status'], name='kyc_session_organiz_8a0b0d_idx'),
        ),
        migrations.AddIndex(
            model_name='kycsession',
            index=models.Index(fields=['organization', 'external_reference'], name='kyc_session_organiz_6f3c2a_idx'),
        ),
        migrations.AddIndex(
            model_name='kycsession',
            index=models.Index(fields=['-created_at'], name='kyc_session_created_0d5e8f_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='videochunk',
            unique_together={('session', 'chunk_index')},
        ),
    ]
