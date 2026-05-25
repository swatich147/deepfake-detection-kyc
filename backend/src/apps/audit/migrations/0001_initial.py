from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=50)),
                ('resource_type', models.CharField(blank=True, max_length=50, null=True)),
                ('resource_id', models.UUIDField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('request_method', models.CharField(max_length=10)),
                ('request_path', models.CharField(max_length=500)),
                ('request_body', models.JSONField(blank=True, null=True)),
                ('response_status', models.IntegerField(blank=True, null=True)),
                ('response_time_ms', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.organization')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.user')),
            ],
            options={'db_table': 'audit_logs', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['organization', '-created_at'], name='audit_logs_organiz_1a2b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', '-created_at'], name='audit_logs_user_id_4d5e6f_idx'),
        ),
    ]
